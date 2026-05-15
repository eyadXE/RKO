import json
import os
from typing import Any, Dict, List

from groq import Groq

from .config import GROQ_MODEL

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set.")
        _client = Groq(api_key=api_key)
    return _client


def score_ats(resume_text: str, job_keywords: List[str], job_query: str) -> Dict[str, Any]:
    keywords_str = ", ".join(job_keywords[:50])
    user_msg = (
        f"Job query: {job_query}\n"
        f"Top job keywords: {keywords_str}\n\n"
        f"Resume:\n{resume_text[:4000]}"
    )
    response = _get_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an ATS (Applicant Tracking System) evaluator. "
                    "Given a resume and a list of keywords from real job postings, "
                    "return a JSON object with exactly two keys: "
                    "\"score\" (integer 0-100, how well the resume matches the job keywords) "
                    "and \"explanation\" (2-3 sentences explaining the score). "
                    "Return only the JSON object, no markdown, no extra text."
                ),
            },
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
        max_tokens=300,
    )
    raw = response.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
        return {
            "score": int(data.get("score", 0)),
            "explanation": str(data.get("explanation", "")),
        }
    except (json.JSONDecodeError, ValueError):
        return {"score": 0, "explanation": raw}


def enhance_resume(resume_text: str, keywords_to_add: List[str]) -> str:
    keywords_str = ", ".join(keywords_to_add)
    user_msg = (
        f"Missing keywords to incorporate: {keywords_str}\n\n"
        f"Resume:\n{resume_text}"
    )
    response = _get_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional resume writer. "
                    "Given a resume and a list of missing keywords, rewrite the resume "
                    "to incorporate these keywords naturally into existing sections. "
                    "Preserve all original experience, facts, and structure. "
                    "Return only the full rewritten resume text, no commentary."
                ),
            },
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
        max_tokens=2048,
    )
    return response.choices[0].message.content.strip()
