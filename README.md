# Resume Keyword Optimser (Phase 1)

Collects job postings from Wuzzuf (only when allowed by robots.txt), stores
structured JSON, cleans and tokenizes text, and generates keyword analysis
reports and visuals.

## Requirements

- Python 3.12+
- Dependencies installed via uv (already listed in pyproject.toml)

## Run the Pipeline

Single query:

```bash
uv run python main.py --query "data analyst" --max-records 120 --max-pages 12
```

Multi-query (comma-separated, aggregated with de-duplication):

```bash
uv run python main.py --queries "ai engineer, machine learning, data scientist"
```

Optional resume text file for keyword suggestions:

```bash
uv run python main.py --resume path/to/resume.txt
```

## CLI Arguments

- --query: single search query (default from config)
- --queries: comma-separated list of queries (overrides --query)
- --max-records: maximum total records to collect
- --max-pages: maximum pages to scan per query
- --raw-out: path to raw JSON output
- --processed-out: path to processed JSON output
- --reports-dir: reports output directory
- --resume: resume text file for missing keyword suggestions
- --top-n: number of keywords to keep in reports
- --min-industry-records: minimum records per industry to report

## Data Schema

Raw records (data/raw_jobs.json):

- source, url, title, company, location, employment_type, industry,
  experience_level, description, requirements, skills, posted_date, scraped_at

Processed records (data/processed_jobs.json) add:

- description_clean
- tokens
- token_count
- missing_description

Tokenization uses lowercase normalization, punctuation stripping, and a fixed
English stopword list.

## Outputs

- data/raw_jobs.json
- data/processed_jobs.json
- reports/summary.json
- reports/keyword_frequency.csv
- reports/industry_keywords.csv (when enough records per industry)
- reports/keyword_suggestions.csv
- reports/top_keywords.png
- reports/company_counts.csv
- reports/location_counts.csv
- reports/industry_counts.csv
- reports/employment_type_counts.csv
- reports/company_counts.png
- reports/location_counts.png
- reports/industry_counts.png
- reports/employment_type_counts.png
- reports/token_count_hist.png

## Static UI

Open web/index.html to view a simple dashboard that displays the charts and
links to the report files.

## Notes and Limitations

- The scraper respects robots.txt and stops if access is disallowed.
- If Wuzzuf blocks requests (403/429), the pipeline stops early.
- The 50-200 record requirement depends on query breadth and availability.
