#!/usr/bin/env python3
"""Convert exported Markdown articles into Hugo page bundles for content/news/.

Supports YAML (---), TOML (+++), or front-matter-less Markdown files:
- Extracts title from front matter or the first `# Heading` (removing the H1
  from the body so Hugo does not render a duplicate heading).
- Normalizes metadata keys (`title`, `date`, `lastmod`, `draft`, `description`,
  `summary`, `author`, `categories`, `tags`, `image`, `imageAlt`,
  `imageCaption`, `translationKey`).
- Derives `description` / `summary` from the opening paragraph when omitted.
- Parses tags from front matter lists, comma-separated strings, or a standalone
  `Tags: ...` / `#tag1 #tag2` metadata line.
- Copies local cover and inline images into the target page bundle and rewrites
  their paths to bundle-relative filenames.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
import tomllib
import unicodedata
from pathlib import Path
from typing import Any

DEFAULT_AUTHOR = "Martin Albrecht"
DEFAULT_CATEGORIES = {
    "en": ["Insights"],
    "de": ["Einblicke"],
}

FRONTMATTER_RE = re.compile(
    r"\A(?P<delim>\+\+\+|---)[ \t]*\r?\n(?P<body>.*?)\r?\n(?P=delim)[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)
H1_RE = re.compile(r"^\s*#\s+(.+?)\s*#*\s*$")
TAG_LINE_RE = re.compile(r"^\s*(?:tags?|keywords?)\s*:\s*(.+?)\s*$", re.IGNORECASE)
HASHTAG_ONLY_LINE_RE = re.compile(r"^\s*(?:#[A-Za-z0-9ÄÖÜäöüß_-]+[\s,]*){2,}\s*$")
MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)")
WIKI_IMAGE_RE = re.compile(r"!\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def slugify(text: str) -> str:
    """Convert text into a URL-safe ASCII slug."""
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "Ä": "ae",
        "Ö": "oe",
        "Ü": "ue",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "untitled-article"


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        inner = value[1:-1]
        if value[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
        return inner
    return value


def parse_scalar(raw: str) -> Any:
    val = raw.strip()
    if not val:
        return ""
    low = val.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        return [strip_quotes(item) for item in split_csv_respecting_quotes(inner) if item.strip()]
    return strip_quotes(val)


def split_csv_respecting_quotes(text: str) -> list[str]:
    items: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    escape = False
    for ch in text:
        if escape:
            buf.append(ch)
            escape = False
            continue
        if ch == "\\" and quote == '"':
            buf.append(ch)
            escape = True
            continue
        if ch in ('"', "'"):
            if quote is None:
                quote = ch
            elif quote == ch:
                quote = None
            buf.append(ch)
            continue
        if ch == "," and quote is None:
            items.append("".join(buf))
            buf.clear()
            continue
        buf.append(ch)
    if buf:
        items.append("".join(buf))
    return items


def parse_simple_yaml(raw: str) -> dict[str, Any]:
    """Parse common YAML front-matter key/value pairs and lists without external deps."""
    data: dict[str, Any] = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, rest = line.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        if rest:
            data[key] = parse_scalar(rest)
            i += 1
            continue

        # Check for indented block list (`- item`)
        items: list[str] = []
        j = i + 1
        while j < len(lines):
            next_line = lines[j]
            next_stripped = next_line.strip()
            if not next_stripped:
                j += 1
                continue
            if re.match(r"^\s*-\s+", next_line):
                item_val = re.sub(r"^\s*-\s+", "", next_line).strip()
                items.append(strip_quotes(item_val))
                j += 1
            else:
                break
        data[key] = items if items else ""
        i = j
    return data


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, markdown_body)."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    delim = match.group("delim")
    raw_meta = match.group("body")
    body = text[match.end():]
    if delim == "+++":
        return tomllib.loads(raw_meta), body
    return parse_simple_yaml(raw_meta), body


def normalize_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(v).strip().lstrip("#") for v in value if str(v).strip()]
    if isinstance(value, str):
        parts = split_csv_respecting_quotes(value) if "," in value else value.split()
        return [strip_quotes(p).lstrip("#") for p in parts if strip_quotes(p)]
    return [str(value).strip()]


def normalize_date(value: Any, fallback: dt.date) -> str:
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, str) and value.strip():
        candidate = value.strip()
        # Handle ISO timestamps like 2026-11-20T10:00:00Z
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", candidate)
        if m:
            return m.group(1)
        for fmt in ("%d.%m.%Y", "%Y/%m/%d", "%d/%m/%Y"):
            try:
                return dt.datetime.strptime(candidate, fmt).date().isoformat()
            except ValueError:
                pass
    return fallback.isoformat()


def strip_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"[*_~]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def derive_description(body: str, max_len: int = 180) -> str:
    paragraphs: list[str] = []
    current: list[str] = []
    in_code = False
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not s:
            if current:
                paragraphs.append(" ".join(current))
                current.clear()
            continue
        if s.startswith(("#", ">", "- ", "* ", "+ ", "|", "![")) or re.match(r"^\d+\.\s", s):
            if current:
                paragraphs.append(" ".join(current))
                current.clear()
            continue
        current.append(s)
    if current:
        paragraphs.append(" ".join(current))

    if not paragraphs:
        return ""
    plain = strip_markdown(paragraphs[0])
    if len(plain) <= max_len:
        return plain
    truncated = plain[:max_len].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{truncated}..."


def extract_body_metadata(body: str) -> tuple[str | None, list[str], str]:
    """Extract optional leading H1 title and trailing/leading tag lines from body."""
    lines = body.splitlines()
    extracted_title: str | None = None
    extracted_tags: list[str] = []
    kept_lines: list[str] = []

    seen_content = False
    for idx, line in enumerate(lines):
        if extracted_title is None and not seen_content:
            if not line.strip():
                continue
            h1_match = H1_RE.match(line)
            if h1_match:
                extracted_title = h1_match.group(1).strip()
                continue

        if line.strip():
            seen_content = True

        tag_match = TAG_LINE_RE.match(line)
        if tag_match and (idx < 5 or idx >= len(lines) - 5):
            extracted_tags.extend(normalize_list(tag_match.group(1)))
            continue

        if HASHTAG_ONLY_LINE_RE.match(line) and (idx < 5 or idx >= len(lines) - 5):
            extracted_tags.extend(normalize_list(line))
            continue

        kept_lines.append(line)

    cleaned_body = "\n".join(kept_lines).strip() + "\n"
    return extracted_title, extracted_tags, cleaned_body


def first_present(meta: dict[str, Any], *keys: str) -> Any:
    lower_map = {k.lower(): v for k, v in meta.items()}
    for key in keys:
        if key in meta and meta[key] not in (None, ""):
            return meta[key]
        if key.lower() in lower_map and lower_map[key.lower()] not in (None, ""):
            return lower_map[key.lower()]
    return None


def resolve_local_image(ref: str, source_dir: Path, assets_dirs: list[Path]) -> Path | None:
    if re.match(r"^(https?://|//|/)", ref):
        return None
    clean_ref = ref.split("?")[0].split("#")[0]
    for base in [source_dir, *assets_dirs]:
        candidate = (base / clean_ref).resolve()
        if candidate.is_file():
            return candidate
        # Also try matching by basename in assets_dirs
        by_name = (base / Path(clean_ref).name).resolve()
        if by_name.is_file():
            return by_name
    return None


def copy_bundle_image(
    src_path: Path, bundle_dir: Path, target_name: str | None = None, dry_run: bool = False
) -> str:
    dest_name = target_name or src_path.name
    if not dry_run:
        bundle_dir.mkdir(parents=True, exist_ok=True)
        dest_path = bundle_dir / dest_name
        if src_path.resolve() != dest_path.resolve():
            shutil.copy2(src_path, dest_path)
    return dest_name


def format_toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, dt.date):
        return value.isoformat()
    text = str(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    return json.dumps(text, ensure_ascii=False)


def render_toml_frontmatter(fields: list[tuple[str, Any]]) -> str:
    lines = ["+++"]
    for key, val in fields:
        lines.append(f"{key} = {format_toml_value(val)}")
    lines.append("+++")
    return "\n".join(lines)


def convert_article(
    input_path: Path,
    repo_root: Path,
    lang: str,
    slug_override: str | None,
    translation_key_override: str | None,
    image_override: str | None,
    draft_override: bool | None,
    assets_dirs: list[Path],
    copy_images: bool,
    overwrite: bool,
    dry_run: bool,
) -> Path:
    raw_text = input_path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(raw_text)
    body_title, body_tags, cleaned_body = extract_body_metadata(body)

    title = first_present(meta, "title") or body_title
    if not title:
        title = input_path.stem.replace("-", " ").replace("_", " ").strip().title()

    today = dt.date.today()
    date_str = normalize_date(
        first_present(meta, "date", "published", "created", "datePublished"), today
    )
    lastmod_str = normalize_date(
        first_present(meta, "lastmod", "updated", "modified", "dateModified"),
        dt.date.fromisoformat(date_str),
    )

    if draft_override is not None:
        draft = draft_override
    else:
        raw_draft = first_present(meta, "draft")
        draft = bool(raw_draft) if isinstance(raw_draft, bool) else False

    description = str(
        first_present(meta, "description", "subtitle", "excerpt") or derive_description(cleaned_body)
    ).strip()
    summary = str(first_present(meta, "summary") or description).strip()
    author = str(first_present(meta, "author") or DEFAULT_AUTHOR).strip()

    categories = normalize_list(first_present(meta, "categories", "category"))
    if not categories:
        categories = DEFAULT_CATEGORIES.get(lang, ["Insights"])

    tags = normalize_list(first_present(meta, "tags", "keywords"))
    for tag in body_tags:
        if tag not in tags:
            tags.append(tag)

    raw_slug = slug_override or first_present(meta, "translationKey", "translation_key", "slug")
    slug = slugify(str(raw_slug) if raw_slug else str(title))
    translation_key = str(translation_key_override or slug)

    bundle_dir = repo_root / "content" / "news" / slug
    filename = "index.md" if lang == "en" else f"index.{lang}.md"
    output_path = bundle_dir / filename

    if output_path.exists() and not overwrite and not dry_run:
        raise FileExistsError(
            f"Target file already exists: {output_path} (pass --overwrite to replace)"
        )

    image_val = image_override or first_present(
        meta, "image", "cover", "featured_image", "featuredImage", "banner", "hero"
    )
    image_str = str(image_val).strip() if image_val else ""
    if image_str and copy_images:
        local_cover = resolve_local_image(image_str, input_path.parent, assets_dirs)
        if local_cover is not None:
            ext = local_cover.suffix.lower() or ".jpg"
            image_str = copy_bundle_image(
                local_cover, bundle_dir, target_name=f"cover{ext}", dry_run=dry_run
            )

    image_alt = str(first_present(meta, "imageAlt", "image_alt", "coverAlt", "alt") or "").strip()
    image_caption = str(
        first_present(meta, "imageCaption", "image_caption", "coverCaption", "caption") or ""
    ).strip()

    if copy_images:
        def replace_wiki_image(match: re.Match[str]) -> str:
            ref = match.group(1).strip()
            alt = (match.group(2) or "").strip()
            local_img = resolve_local_image(ref, input_path.parent, assets_dirs)
            if local_img is not None:
                copied = copy_bundle_image(local_img, bundle_dir, dry_run=dry_run)
                return f"![{alt}]({copied})"
            return f"![{alt}]({ref})"

        def replace_md_image(match: re.Match[str]) -> str:
            alt, ref = match.group(1), match.group(2)
            local_img = resolve_local_image(ref, input_path.parent, assets_dirs)
            if local_img is not None:
                copied = copy_bundle_image(local_img, bundle_dir, dry_run=dry_run)
                return f"![{alt}]({copied})"
            return match.group(0)

        cleaned_body = WIKI_IMAGE_RE.sub(replace_wiki_image, cleaned_body)
        cleaned_body = MD_IMAGE_RE.sub(replace_md_image, cleaned_body)

    fields: list[tuple[str, Any]] = [
        ("title", title),
        ("date", date_str),
        ("lastmod", lastmod_str),
        ("draft", draft),
        ("description", description),
        ("summary", summary),
        ("author", author),
        ("categories", categories),
        ("tags", tags),
    ]
    if image_str:
        fields.append(("image", image_str))
    if image_alt:
        fields.append(("imageAlt", image_alt))
    if image_caption:
        fields.append(("imageCaption", image_caption))
    fields.append(("translationKey", translation_key))

    output_text = f"{render_toml_frontmatter(fields)}\n\n{cleaned_body}"

    if dry_run:
        print(f"=== {output_path} ===")
        print(output_text)
    else:
        bundle_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_text, encoding="utf-8")

    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert an exported Markdown article into a Hugo news page bundle."
    )
    parser.add_argument("input", type=Path, help="Path to the exported Markdown file.")
    parser.add_argument(
        "--lang",
        default="en",
        choices=("en", "de"),
        help="Target language (writes index.md for 'en', index.de.md for 'de').",
    )
    parser.add_argument("--slug", help="Override target folder slug under content/news/.")
    parser.add_argument("--translation-key", help="Override translationKey in front matter.")
    parser.add_argument("--image", help="Cover image path or URL to set in front matter.")
    parser.add_argument(
        "--assets-dir",
        type=Path,
        action="append",
        default=[],
        help="Extra directory to search for local images referenced by the Markdown.",
    )
    parser.add_argument(
        "--no-copy-images",
        action="store_true",
        help="Do not copy local images into the page bundle.",
    )
    parser.add_argument(
        "--draft",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Force draft = true or draft = false (defaults to source front matter or false).",
    )
    parser.add_argument("--overwrite", "-f", action="store_true", help="Overwrite existing output.")
    parser.add_argument("--dry-run", action="store_true", help="Print output without writing files.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    input_path = args.input.expanduser().resolve()
    if not input_path.is_file():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        out = convert_article(
            input_path=input_path,
            repo_root=repo_root,
            lang=args.lang,
            slug_override=args.slug,
            translation_key_override=args.translation_key,
            image_override=args.image,
            draft_override=args.draft,
            assets_dirs=[p.expanduser().resolve() for p in args.assets_dir],
            copy_images=not args.no_copy_images,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not args.dry_run:
        print(f"Created {out.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
