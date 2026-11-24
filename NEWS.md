# Adding a news article

Articles live in `content/news/`. Each article is a page bundle: a folder with an `index.md` file and, optionally, images.

## Create an article

From the project root:

```bash
hugo new content news/my-article-title/index.md
```

This uses `archetypes/news.md` and creates:

```text
content/news/my-article-title/
└── index.md
```

### Or import an exported Markdown file

If you write articles in another app and export them as Markdown, run:

```bash
python3 scripts/import_news.py path/to/exported-article.md
# German translation into the same bundle:
python3 scripts/import_news.py path/to/exported-article.de.md --lang de --slug my-article-title
```

The script reads YAML (`---`), TOML (`+++`), or plain Markdown (extracting the leading `# Title`, `Tags: ...` / `#tag` lines, opening-paragraph `description`/`summary`, and copying local cover/inline images into the page bundle). Pass `--dry-run` to preview or `--help` for all options.

Edit the front matter and write the article in Markdown. Set `draft = false` when it is ready to publish, or preview drafts with `hugo server -D`.

## Front matter fields

| Field | Purpose |
| --- | --- |
| `title` | Article headline |
| `date` | Publication date, used for sorting |
| `description` | Short deck shown under the headline and in cards |
| `summary` | Optional fallback summary for cards and meta tags |
| `author` | Byline name |
| `categories` | One or more categories, e.g. `["Insights"]` |
| `tags` | Any number of tags |
| `image` | Optional cover image |
| `imageAlt` | Alt text for the cover image |
| `imageCaption` | Optional caption under the cover image |
| `translationKey` | Links translations of the same article |

## Cover images

Put the image in the article folder and reference it by filename:

```toml
image = "cover.jpg"
```

Or use a shared image from `static/images/news/`:

```toml
image = "/images/news/my-image.jpg"
```

If no image is set, the layout shows a branded gradient placeholder.

## German translation

Create a sibling file in the same folder:

```bash
hugo new content news/my-article-title/index.de.md --kind news
```

Keep the same `translationKey` in both files. The language switcher and `hreflang` tags will then connect the two versions.

## URLs and listings

- Article URL: `/en/news/my-article-title/` (and `/de/news/my-article-title/` for the translation)
- News index: `/en/news/` and `/de/news/`
- Tag index: `/en/tags/` and `/de/tags/`
- Category index: `/en/categories/` and `/de/categories/`

The three newest articles also appear in the "Latest news" section on the homepage.
