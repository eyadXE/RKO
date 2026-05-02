import os
from collections import Counter
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import pandas as pd

from .storage import save_json


def _write_keyword_csv(path: str, data: List[Tuple[str, int]]) -> None:
    df = pd.DataFrame(data, columns=["keyword", "count"])
    df.to_csv(path, index=False)


def _write_count_csv(path: str, data: List[Tuple[str, int]]) -> None:
    df = pd.DataFrame(data, columns=["label", "count"])
    df.to_csv(path, index=False)


def _plot_keyword_bar(path: str, data: List[Tuple[str, int]], top_n: int = 20) -> None:
    if not data:
        return
    df = pd.DataFrame(data, columns=["keyword", "count"]).head(top_n)
    plt.figure(figsize=(10, 6))
    plt.barh(df["keyword"], df["count"], color="#2c7fb8")
    plt.gca().invert_yaxis()
    plt.title("Top Keywords")
    plt.xlabel("Frequency")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def _plot_barh(path: str, title: str, data: List[Tuple[str, int]], top_n: int = 10) -> None:
    if not data:
        return
    df = pd.DataFrame(data, columns=["label", "count"]).head(top_n)
    plt.figure(figsize=(10, 6))
    plt.barh(df["label"], df["count"], color="#5c8a64")
    plt.gca().invert_yaxis()
    plt.title(title)
    plt.xlabel("Count")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def _plot_hist(path: str, values: List[int], title: str, bins: int = 15) -> None:
    if not values:
        return
    plt.figure(figsize=(8, 5))
    plt.hist(values, bins=bins, color="#8c6bb1", edgecolor="#ffffff")
    plt.title(title)
    plt.xlabel("Token Count")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def _count_by_field(
    records: List[Dict[str, Any]],
    field: str,
    split_commas: bool = False,
    top_n: int = 15,
) -> List[Tuple[str, int]]:
    counter: Counter[str] = Counter()
    for record in records:
        value = record.get(field)
        if not value:
            continue
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
        else:
            items = [str(value).strip()]
        expanded: List[str] = []
        for item in items:
            if split_commas:
                expanded.extend([part.strip() for part in item.split(",") if part.strip()])
            else:
                expanded.append(item)
        counter.update(expanded)
    return counter.most_common(top_n)


def write_reports(
    output_dir: str,
    stats: Dict[str, Any],
    keyword_counts: List[Tuple[str, int]],
    industry_keywords: Dict[str, List[Tuple[str, int]]],
    suggestions: List[Tuple[str, int]],
    records: List[Dict[str, Any]],
) -> None:
    os.makedirs(output_dir, exist_ok=True)

    summary_path = os.path.join(output_dir, "summary.json")
    save_json(
        summary_path,
        {
            "stats": stats,
            "top_keywords": keyword_counts,
            "industry_keywords": industry_keywords,
            "keyword_suggestions": suggestions,
            "distributions": {
                "companies": _count_by_field(records, "company"),
                "locations": _count_by_field(records, "location"),
                "industries": _count_by_field(records, "industry", split_commas=True),
                "employment_types": _count_by_field(
                    records, "employment_type", split_commas=True
                ),
            },
        },
    )

    keyword_csv = os.path.join(output_dir, "keyword_frequency.csv")
    _write_keyword_csv(keyword_csv, keyword_counts)

    suggestions_csv = os.path.join(output_dir, "keyword_suggestions.csv")
    _write_keyword_csv(suggestions_csv, suggestions)

    industry_rows: List[Dict[str, Any]] = []
    for industry, items in industry_keywords.items():
        for keyword, count in items:
            industry_rows.append(
                {"industry": industry, "keyword": keyword, "count": count}
            )

    if industry_rows:
        pd.DataFrame(industry_rows).to_csv(
            os.path.join(output_dir, "industry_keywords.csv"), index=False
        )

    company_counts = _count_by_field(records, "company")
    location_counts = _count_by_field(records, "location")
    industry_counts = _count_by_field(records, "industry", split_commas=True)
    employment_counts = _count_by_field(records, "employment_type", split_commas=True)

    _write_count_csv(os.path.join(output_dir, "company_counts.csv"), company_counts)
    _write_count_csv(os.path.join(output_dir, "location_counts.csv"), location_counts)
    _write_count_csv(os.path.join(output_dir, "industry_counts.csv"), industry_counts)
    _write_count_csv(
        os.path.join(output_dir, "employment_type_counts.csv"), employment_counts
    )

    chart_path = os.path.join(output_dir, "top_keywords.png")
    _plot_keyword_bar(chart_path, keyword_counts)

    _plot_barh(
        os.path.join(output_dir, "company_counts.png"),
        "Top Companies",
        company_counts,
    )
    _plot_barh(
        os.path.join(output_dir, "location_counts.png"),
        "Top Locations",
        location_counts,
    )
    _plot_barh(
        os.path.join(output_dir, "industry_counts.png"),
        "Top Industries",
        industry_counts,
    )
    _plot_barh(
        os.path.join(output_dir, "employment_type_counts.png"),
        "Employment Types",
        employment_counts,
    )

    token_counts = [int(record.get("token_count", 0)) for record in records]
    _plot_hist(
        os.path.join(output_dir, "token_count_hist.png"),
        token_counts,
        "Token Count Distribution",
    )
