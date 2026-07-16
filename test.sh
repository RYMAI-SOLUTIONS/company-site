#!/usr/bin/env bash

echo "Checking hugo installation..."
hugo --printPathWarnings --gc --printI18nWarnings
if [ $? -ne 0 ]; then
  exit 1
fi

echo "Checking for missing translations..."
MISSING_TRANSLATIONS=$(comm -23 <(grep -Eo '^\[[^]]+\]|^[a-zA-Z0-9_-]+\s*=' i18n/en.toml | sort) <(grep -Eo '^\[[^]]+\]|^[a-zA-Z0-9_-]+\s*=' i18n/de.toml | sort))

if [ -n "$MISSING_TRANSLATIONS" ]; then
  echo "Error: Missing translations found:"
  for translation in $MISSING_TRANSLATIONS; do
    echo "  - $translation"
  done
  exit 1
else
  echo "All translations are present."
fi
