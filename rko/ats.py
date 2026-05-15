from typing import List


def rule_based_score(resume_tokens: set, top_keywords: List[str]) -> float:
    if not top_keywords:
        return 0.0
    matched = sum(1 for kw in top_keywords if kw in resume_tokens)
    return round(matched / len(top_keywords) * 100, 1)


def score_label(score: float) -> str:
    if score >= 75:
        return "Excellent"
    if score >= 50:
        return "Good"
    if score >= 25:
        return "Fair"
    return "Poor"
