from typing import Any

import pdfplumber


def parse_resume(uploaded_file: Any) -> str:
    name: str = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        with pdfplumber.open(uploaded_file) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages).strip()
    return uploaded_file.read().decode("utf-8", errors="replace").strip()
