import re
from typing import Any, Dict, List

STOPWORDS = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "me",
    "more",
    "most",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "now",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
}

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#.]{1,}")


def normalize_text(text: str) -> str:
    lowered = text.lower()
    cleaned = re.sub(r"[^a-z0-9+#.\s]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text)


def preprocess_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for record in records:
        description = (record.get("description") or "").strip()
        requirements = (record.get("requirements") or "").strip()
        skills = record.get("skills") or []
        skills_text = " ".join(skills) if isinstance(skills, list) else str(skills)
        text_source = " ".join(
            part for part in (description, requirements, skills_text) if part
        ).strip()
        normalized = normalize_text(text_source)
        tokens = [
            token
            for token in tokenize(normalized)
            if token not in STOPWORDS and len(token) > 2
        ]
        updated = dict(record)
        updated["description_clean"] = normalized
        updated["tokens"] = tokens
        updated["token_count"] = len(tokens)
        updated["missing_description"] = not bool(text_source)
        if updated["missing_description"]:
            continue
        if not updated.get("industry"):
            updated["industry"] = "Unknown"
        cleaned.append(updated)
    return cleaned
