+++
title = "{{ replace .File.ContentBaseName "-" " " | title }}"
date = {{ .Date }}
lastmod = {{ .Date }}
draft = true
description = ""
summary = ""
author = "Martin Albrecht"
categories = ["Insights"]
tags = []
image = ""
imageAlt = ""
imageCaption = ""
translationKey = "{{ .File.ContentBaseName }}"
+++

Write the article here. Use `##` for section headings, `###` for subsections, and normal Markdown for lists, quotes, tables, and images.

To add a cover image, place it next to this file (for example `cover.jpg`) and set `image = "cover.jpg"` in the front matter. You can also point to a shared image with `image = "/images/news/my-image.jpg"`.
