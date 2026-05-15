# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Resume Keyword Optimiser (RKO) — scrapes job postings from Wuzzuf (Egyptian job portal), preprocesses and tokenizes the text, and generates keyword analysis reports and visualizations to help align a resume with market demand.

## Commands

This project uses `uv` as its package manager (Python 3.12+).

```bash
# Install dependencies
uv sync

# Run the full pipeline (single query)
uv run python main.py --query "data analyst" --max-records 120 --max-pages 12

# Run with multiple queries (aggregated, de-duplicated)
uv run python main.py --queries "ai engineer, machine learning, data scientist"

# Run with a resume file to get missing keyword suggestions
uv run python main.py --resume path/to/resume.txt --query "data analyst"
```

There are no tests or linting configured in this project.

## Architecture

The pipeline flows linearly through five stages:

```
main.py (CLI + orchestration)
  └── scraper.py     → raw records (List[Dict])
  └── preprocess.py  → enriched records with tokens
  └── analysis.py    → stats, keyword counts, suggestions
  └── reporting.py   → CSV, JSON, PNG outputs
       └── storage.py (shared JSON I/O)
```

**`rko/config.py`** — Single source of truth for all constants: `BASE_URL`, `USER_AGENT`, `REQUEST_DELAY`, `MAX_RECORDS`, `MAX_PAGES`, and output file paths. Change defaults here, not in `main.py`.

**`rko/scraper.py`** — Fetches Wuzzuf search results and job pages. Checks `robots.txt` before every request via `can_fetch()`; returns an empty list if robots.txt is unavailable or disallows access. Parses structured data from `<script type="application/ld+json">` (JSON-LD `JobPosting` schema) first, with HTML fallbacks for each field (`title`, `company`, `location`, `employment_type`, `skills`). Entry points: `crawl_jobs()` (single query) and `crawl_jobs_multi()` (multiple queries with shared deduplication via `seen_links`).

**`rko/preprocess.py`** — Concatenates `description + requirements + skills` per record, normalizes to lowercase, strips non-alphanumeric characters (preserving `+`, `#`, `.` for tech tokens like `c++`, `c#`, `node.js`), tokenizes with `TOKEN_RE`, and filters stopwords. Adds `description_clean`, `tokens`, `token_count`, `missing_description` fields to each record.

**`rko/analysis.py`** — Three functions: `basic_stats()` (descriptive statistics over token counts), `keyword_frequency()` (global top-N tokens by frequency), `keyword_frequency_by_industry()` (per-industry top-N, skipping industries below `min_records` threshold), and `suggest_keywords()` (top-N job-market tokens absent from the user's resume tokens).

**`rko/reporting.py`** — Writes all outputs to `reports/`: `summary.json`, keyword CSVs, distribution CSVs, and matplotlib bar/histogram charts. Depends on `pandas` for CSV and `matplotlib` for charts.

## Data Flow

Raw records schema: `source, url, title, company, location, employment_type, industry, experience_level, description, requirements, skills, posted_date, scraped_at`

Processed records add: `description_clean, tokens, token_count, missing_description`

Output files land in `data/` (JSON) and `reports/` (CSV, JSON, PNG). The static dashboard at `web/index.html` reads from these output paths.

## Known Issue

`rko/scraper.py` imports `from sympy import false` (line 11) — `sympy` is not listed in `pyproject.toml` and `false` is never used. This import should be removed.
