"""
rko/ir_engine.py
Information Retrieval engine for the RKO pipeline.

Provides:
  - build_inverted_index   : token → list of (doc_idx, positions)
  - compute_tfidf          : corpus-level TF-IDF ranking
  - keyword_frequency_stats: raw + document frequency table
  - index_summary          : top posting-list sizes
  - save_ir_reports        : write JSON artefacts consumed by the web UI
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# 1. Inverted Index
# ---------------------------------------------------------------------------

def build_inverted_index(
    records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """
    Build a positional inverted index.

    Returns
    -------
    {
      "python": [
          {"doc_idx": 0, "positions": [3, 17]},
          {"doc_idx": 2, "positions": [1]},
          ...
      ],
      ...
    }
    """
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for doc_idx, record in enumerate(records):
        tokens: list[str] = record.get("tokens") or []
        pos_map: dict[str, list[int]] = defaultdict(list)
        for pos, token in enumerate(tokens):
            pos_map[token].append(pos)
        for token, positions in pos_map.items():
            index[token].append({"doc_idx": doc_idx, "positions": positions})

    return dict(index)


def index_summary(
    index: dict[str, list[dict[str, Any]]],
    top_n: int = 50,
) -> list[dict[str, Any]]:
    """Return the top-N tokens by posting-list length (document frequency)."""
    items = [
        {"token": token, "doc_freq": len(postings)}
        for token, postings in index.items()
    ]
    items.sort(key=lambda x: x["doc_freq"], reverse=True)
    return items[:top_n]


# ---------------------------------------------------------------------------
# 2. TF-IDF
# ---------------------------------------------------------------------------

def compute_tfidf(
    records: list[dict[str, Any]],
    top_n: int = 50,
) -> list[dict[str, Any]]:
    """
    Compute a corpus-level TF-IDF score for every token.

    TF  = term count in doc / doc length
    IDF = log( N / (1 + df) )   [smoothed]
    score per token = mean TF-IDF across all docs that contain it
    """
    N = len(records)
    if N == 0:
        return []

    # Document frequency
    df: dict[str, int] = defaultdict(int)
    for record in records:
        for token in set(record.get("tokens") or []):
            df[token] += 1

    # Accumulate TF-IDF sums
    tfidf_sum: dict[str, float] = defaultdict(float)
    for record in records:
        tokens: list[str] = record.get("tokens") or []
        if not tokens:
            continue
        doc_len = len(tokens)
        tf_map: dict[str, int] = defaultdict(int)
        for t in tokens:
            tf_map[t] += 1
        for token, count in tf_map.items():
            tf = count / doc_len
            idf = math.log((N + 1) / (1 + df[token]))
            tfidf_sum[token] += tf * idf

    results = [
        {
            "token": token,
            "tfidf_score": round(score / N, 6),
            "doc_freq": df[token],
            "doc_pct": round(100 * df[token] / N, 1),
        }
        for token, score in tfidf_sum.items()
        if df[token] > 1  # drop hapax legomena
    ]
    results.sort(key=lambda x: x["tfidf_score"], reverse=True)
    return results[:top_n]


# ---------------------------------------------------------------------------
# 3. Keyword Frequency Statistics
# ---------------------------------------------------------------------------

def keyword_frequency_stats(
    records: list[dict[str, Any]],
    top_n: int = 50,
) -> list[dict[str, Any]]:
    """
    Extended frequency table with total occurrence count, document frequency,
    and document percentage.
    """
    total_freq: dict[str, int] = defaultdict(int)
    doc_freq: dict[str, int] = defaultdict(int)

    N = len(records)
    for record in records:
        tokens: list[str] = record.get("tokens") or []
        for t in set(tokens):
            doc_freq[t] += 1
        for t in tokens:
            total_freq[t] += 1

    results = [
        {
            "token": token,
            "total_freq": total_freq[token],
            "doc_freq": doc_freq[token],
            "doc_pct": round(100 * doc_freq[token] / N, 1) if N else 0,
        }
        for token in total_freq
    ]
    results.sort(key=lambda x: x["total_freq"], reverse=True)
    return results[:top_n]


# ---------------------------------------------------------------------------
# 4. Persist IR artefacts
# ---------------------------------------------------------------------------

def save_ir_reports(
    reports_dir: str | Path,
    records: list[dict[str, Any]],
    top_n: int = 50,
) -> None:
    """
    Compute all IR metrics and write them as JSON files in *reports_dir*:

      ir_index_summary.json   – top tokens by doc-freq (index stats)
      ir_tfidf.json           – TF-IDF ranked tokens
      ir_freq_stats.json      – full keyword frequency table
    """
    out = Path(reports_dir)
    out.mkdir(parents=True, exist_ok=True)

    index = build_inverted_index(records)
    summary = index_summary(index, top_n=top_n)
    tfidf = compute_tfidf(records, top_n=top_n)
    freq = keyword_frequency_stats(records, top_n=top_n)

    (out / "ir_index_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    (out / "ir_tfidf.json").write_text(
        json.dumps(tfidf, indent=2), encoding="utf-8"
    )
    (out / "ir_freq_stats.json").write_text(
        json.dumps(freq, indent=2), encoding="utf-8"
    )

    print(f"[IR] Saved index summary ({len(summary)} tokens)")
    print(f"[IR] Saved TF-IDF ranking ({len(tfidf)} tokens)")
    print(f"[IR] Saved frequency stats ({len(freq)} tokens)")
