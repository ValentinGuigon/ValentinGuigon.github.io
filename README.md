# Valentin Guigon — Personal Website

This repository contains the source code for my personal academic website, built with Jekyll and based on the al-folio theme.

The site hosts my research profile, publications, teaching material, and selected writing. It is deployed via GitHub Pages.

## Structure

- `_pages/` — static pages (about, research, teaching, etc.)
- `_posts/` — blog posts
- `_data/` — structured data used by the site (CV, feeds, metadata)
- `assets/` — static assets (CSS, JS, images)
- `.github/` — GitHub configuration (no automated content fetching)

## Local development

Requirements:

- Ruby (version compatible with GitHub Pages)
- Bundler

Install dependencies:

```bash
bundle install
```

Serve the site locally:

```bash
bundle exec jekyll serve
```

The site will be available at http://localhost:4000.

## Substack feed update (manual)

Substack content is not fetched automatically.
The feed is updated manually to avoid reliability issues with automated fetches.

A PowerShell script is provided to fetch the Substack RSS feed and store it locally.
From the repository root, run:

```powershell
.\scripts\fetch-substack.ps1
```

After running the script:

1. Verify the file begins with valid XML (<?xml …?> or <rss>).
2. Commit the updated \_data/substack_feed.xml.
3. Push to main. GitHub Pages will rebuild the site automatically.

Notes

- Substack actively blocks automated fetches from CI environments.
- For this reason, feed updates are intentionally manual and local.
- This keeps the site stable and avoids committing corrupted HTML challenge pages.

## Acknowledgements

The website is built using the [al-folio Jekyll theme](https://github.com/alshedivat/al-folio).
