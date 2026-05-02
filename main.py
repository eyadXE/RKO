import argparse
from typing import Optional

from rko.analysis import (
    basic_stats,
    keyword_frequency,
    keyword_frequency_by_industry,
    suggest_keywords,
)
from rko.config import (
    DEFAULT_QUERY,
    DEFAULT_QUERIES,
    MAX_PAGES,
    MAX_RECORDS,
    PROCESSED_DATA_PATH,
    RAW_DATA_PATH,
    REPORTS_DIR,
)
from rko.preprocess import preprocess_records
from rko.reporting import write_reports
from rko.scraper import crawl_jobs_multi
from rko.storage import save_json


def read_text_file(path: Optional[str]) -> str:
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except OSError:
        print(f"Could not read resume file: {path}")
        return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resume Keyword Optimser - Phase 1 pipeline"
    )
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Search query")
    parser.add_argument(
        "--queries",
        default=None,
        help="Comma-separated queries (overrides --query)",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=MAX_RECORDS,
        help="Max job postings to collect",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=MAX_PAGES,
        help="Max search pages to scan",
    )
    parser.add_argument(
        "--raw-out",
        default=RAW_DATA_PATH,
        help="Path to save raw JSON",
    )
    parser.add_argument(
        "--processed-out",
        default=PROCESSED_DATA_PATH,
        help="Path to save processed JSON",
    )
    parser.add_argument(
        "--reports-dir",
        default=REPORTS_DIR,
        help="Directory for reports",
    )
    parser.add_argument(
        "--resume",
        default=None,
        help="Optional resume text file for keyword suggestions",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=30,
        help="Top keywords to keep",
    )
    parser.add_argument(
        "--min-industry-records",
        type=int,
        default=5,
        help="Minimum records per industry for industry keywords",
    )
    return parser.parse_args()


def _parse_queries(args: argparse.Namespace) -> list[str]:
    if args.queries:
        queries = [item.strip() for item in args.queries.split(",") if item.strip()]
        return queries or DEFAULT_QUERIES
    if args.query:
        return [args.query]
    return DEFAULT_QUERIES


def run_pipeline(args: argparse.Namespace) -> int:
    queries = _parse_queries(args)
    records = crawl_jobs_multi(queries, args.max_records, args.max_pages)
    if not records:
        print("No records collected. Check robots.txt or network access.")
        return 1

    save_json(args.raw_out, records)
    processed = preprocess_records(records)
    save_json(args.processed_out, processed)

    stats = basic_stats(processed)
    keyword_counts = keyword_frequency(processed, top_n=args.top_n)
    industry_keywords = keyword_frequency_by_industry(
        processed, top_n=args.top_n, min_records=args.min_industry_records
    )

    resume_text = read_text_file(args.resume)
    suggestions = suggest_keywords(processed, resume_text, top_n=args.top_n)

    write_reports(
        args.reports_dir,
        stats,
        keyword_counts,
        industry_keywords,
        suggestions,
        processed,
    )

    print(f"Records collected: {stats['total_records']}")
    print(f"Reports directory: {args.reports_dir}")
    return 0


def main() -> None:
    args = parse_args()
    raise SystemExit(run_pipeline(args))


if __name__ == "__main__":
    main()
