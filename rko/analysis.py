import math
import statistics
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

from .preprocess import STOPWORDS, normalize_text, tokenize


def basic_stats(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    token_counts = [int(record.get("token_count", 0)) for record in records]
    total_tokens = sum(token_counts)
    avg_tokens = round(total_tokens / len(records), 2) if records else 0
    missing_description = sum(1 for record in records if record.get("missing_description"))
    unique_keywords = len({token for record in records for token in record.get("tokens", [])})

    sorted_counts = sorted(token_counts)
    min_tokens = sorted_counts[0] if sorted_counts else 0
    max_tokens = sorted_counts[-1] if sorted_counts else 0
    median_tokens = round(statistics.median(sorted_counts), 2) if sorted_counts else 0
    std_tokens = (
        round(statistics.pstdev(sorted_counts), 2) if len(sorted_counts) > 1 else 0
    )

    def percentile(sorted_values: List[int], pct: float) -> float:
        if not sorted_values:
            return 0
        k = (len(sorted_values) - 1) * (pct / 100)
        lower = math.floor(k)
        upper = math.ceil(k)
        if lower == upper:
            return float(sorted_values[int(k)])
        weight = k - lower
        return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * weight

    p25_tokens = round(percentile(sorted_counts, 25), 2)
    p75_tokens = round(percentile(sorted_counts, 75), 2)

    return {
        "total_records": len(records),
        "missing_description": missing_description,
        "average_token_count": avg_tokens,
        "median_token_count": median_tokens,
        "min_token_count": min_tokens,
        "max_token_count": max_tokens,
        "p25_token_count": p25_tokens,
        "p75_token_count": p75_tokens,
        "std_token_count": std_tokens,
        "unique_keywords": unique_keywords,
    }


def keyword_frequency(records: List[Dict[str, Any]], top_n: int = 30) -> List[Tuple[str, int]]:
    counter: Counter[str] = Counter()
    for record in records:
        counter.update(record.get("tokens", []))
    return counter.most_common(top_n)


def keyword_frequency_by_industry(
    records: List[Dict[str, Any]], top_n: int = 15, min_records: int = 5
) -> Dict[str, List[Tuple[str, int]]]:
    grouped_tokens: Dict[str, List[str]] = defaultdict(list)
    industry_counts: Dict[str, int] = defaultdict(int)
    for record in records:
        industry = record.get("industry") or "Unknown"
        industry_counts[industry] += 1
        grouped_tokens[industry].extend(record.get("tokens", []))

    result: Dict[str, List[Tuple[str, int]]] = {}
    for industry, tokens in grouped_tokens.items():
        if industry_counts[industry] < min_records:
            continue
        if not tokens:
            continue
        result[industry] = Counter(tokens).most_common(top_n)
    return result


def suggest_keywords(
    records: List[Dict[str, Any]], resume_text: str, top_n: int = 20
) -> List[Tuple[str, int]]:
    counter: Counter[str] = Counter()
    for record in records:
        counter.update(record.get("tokens", []))

    resume_tokens = set()
    if resume_text:
        normalized = normalize_text(resume_text)
        resume_tokens = {
            token
            for token in tokenize(normalized)
            if token not in STOPWORDS and len(token) > 2
        }

    suggestions: List[Tuple[str, int]] = []
    for keyword, count in counter.most_common():
        if keyword in resume_tokens:
            continue
        suggestions.append((keyword, count))
        if len(suggestions) >= top_n:
            break
    return suggestions
