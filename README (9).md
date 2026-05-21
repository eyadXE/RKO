# RKO — Resume Keyword Optimizer

> **An AI-powered job market intelligence and CV optimization system — from raw scraping to LLM-driven resume rewriting, in one Streamlit app.**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Groq](https://img.shields.io/badge/LLM-Groq_Llama_3.3_70B-F97316?style=flat-square)](https://groq.com)
[![NLP](https://img.shields.io/badge/NLP-TF--IDF_+_IR-8B5CF6?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)

---

## What This Project Demonstrates

This project was built to showcase practical AI engineering skills across the full stack: **data collection, NLP, information retrieval, LLM integration, and interactive UI**. It is not a demo — it runs against live job market data and produces real, measurable CV improvement.

```
Live Job Market (Wuzzuf)
        │
        ▼
 ETL Scraping Pipeline        ← robots.txt-compliant, multi-query, deduplicated
        │
        ▼
 NLP & IR Analysis             ← tokenization, inverted index, TF-IDF corpus analysis
        │
        ▼
 AI ATS Scorer                 ← Groq LLM scores resume fit 0–100 with explanation
        │
        ▼
 AI Resume Rewriter            ← LLM rewrites bullets to naturally embed missing keywords
        │
        ▼
 AI CV Advisor                 ← Llama 3.3 70B cross-references resume against market data
                                  → recommends specific projects and technologies to build
```

---

## Features

### 📊 Tab 1 — Job Market Intelligence
Scrapes live job postings from Wuzzuf across multiple queries simultaneously. Deduplicates by URL, normalizes text, and visualizes the top 20 in-demand keywords and per-industry breakdowns.

### 📋 Tab 2 — Resume Analysis
Accepts `.txt` and `.pdf` resume uploads. Runs two scoring methods in parallel:
- **Rule-based ATS score** — keyword overlap percentage against market top-N
- **LLM ATS score** — Groq (Llama 3.3 70B) reads the resume in context and returns a 0–100 score with a natural-language explanation of gaps

### ✨ Tab 3 — Optimize & Compare
Sends the resume + selected missing keywords to the LLM for contextual rewriting. Shows a before/after score comparison (both rule-based and AI) with a side-by-side diff view. The enhanced resume is downloadable.

### 🔍 Tab 4 — Information Retrieval Analysis
A dedicated IR engine built on top of the scraped corpus:
- **Inverted Index** — maps every token to its posting list, ranked by document frequency
- **TF-IDF Ranking** — identifies discriminative skills (high importance, not just high frequency)
- **Frequency Stats** — total occurrences vs. document-level market penetration percentage

All three views are searchable and rendered as interactive charts.

### 🤖 Tab 5 — AI CV Advisor
The most technically involved feature. Feeds the candidate's resume **and the full IR market context** (TF-IDF top terms, frequency stats, posting counts) to Llama 3.3 70B via Groq. The model produces a structured career plan:

- Skills gap analysis grounded in real market data
- Specific portfolio projects to build, with tech stack and rationale
- Technologies to learn, prioritized by corpus demand
- Immediate CV quick wins

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Package management | `uv` |
| UI | Streamlit |
| LLM | Llama 3.3 70B via Groq API |
| NLP | Custom tokenizer, stopword list, TF-IDF implementation |
| Scraping | `httpx` / `BeautifulSoup`, robots.txt-compliant |
| PDF parsing | `PyMuPDF` / `pdfminer` |
| Visualization | Matplotlib |
| Config & secrets | `python-dotenv` |

---

## Project Structure

```
rko/
├── scraper.py        # Multi-query Wuzzuf scraper — robots.txt enforced, 429-aware
├── preprocess.py     # Tokenization, normalization, stopword filtering
├── analysis.py       # Keyword frequency, industry segmentation, resume gap detection
├── ats.py            # Rule-based ATS scorer
├── ai_client.py      # Groq API — LLM ATS scoring and resume rewriting
├── resume.py         # Resume parser (.txt + .pdf)
├── reporting.py      # CSV and PNG report generation
├── storage.py        # JSON I/O
└── config.py         # All constants and defaults

streamlit_app.py      # Full 5-tab Streamlit UI
app.py                # Alternative entry point
main.py               # Headless CLI pipeline

data/                 # Raw + processed job records (generated at runtime)
reports/              # Charts, CSVs, keyword reports (generated at runtime)
web/index.html        # Static report dashboard (no server needed)
```

---

## Setup

**1. Clone and install**

```bash
git clone https://github.com/eyadXE/RKO.git
cd RKO
uv sync
```

**2. Add your Groq API key**

Create a `.env` file:

```
GROQ_API_KEY=your_groq_api_key_here
```

Get a free key at [console.groq.com](https://console.groq.com).

**3. Run**

```bash
uv run streamlit run streamlit_app.py
```

Open `http://localhost:8501` in your browser.

---

## CLI Pipeline (headless)

Run the full scrape → analyze → report pipeline without the UI:

```bash
# Single query
uv run python main.py --query "data analyst" --max-records 120 --max-pages 12

# Multiple queries — aggregated and deduplicated
uv run python main.py --queries "ai engineer, machine learning, data scientist"

# With resume for keyword gap analysis
uv run python main.py --resume path/to/resume.txt --query "data analyst"
```

Outputs land in `data/` (JSON) and `reports/` (CSV + PNG). Open `web/index.html` for the static dashboard.

---

## Engineering Notes

**Ethical scraping.** `robots.txt` is fetched and enforced on every run — not cached from a previous run. The scraper implements exponential backoff on 429 responses and stops cleanly on 403. Nothing is scraped that the site disallows.

**Multi-query deduplication.** Running several queries fans out to separate crawl passes and merges results using URL as the deduplication key, so keyword frequencies reflect real market distribution rather than query overlap.

**IR engine from scratch.** TF-IDF is computed directly over the scraped corpus — no sklearn wrapper — so the weights reflect this specific job market and query, not a general-purpose model.

**LLM context design.** The AI CV Advisor doesn't just send a resume to the LLM. It builds a structured market context string — TF-IDF top terms, frequency stats, posting counts — and sends it alongside the resume so the model's recommendations are grounded in the actual data collected, not general knowledge.

**Session-state architecture.** The Streamlit app maintains a clean in-session pipeline: scrape → IR compute → resume upload → score → rewrite → advise. Each stage caches its results so switching tabs doesn't trigger recomputation.

---

## Notes

- The Groq API key is free. Sign up at [console.groq.com](https://console.groq.com).
- `.env` is gitignored and will never be committed.
- The scraper stops early if Wuzzuf returns 403/429 or blocks via robots.txt.
- All data is processed in your local session — nothing is stored externally.

---

## Author

**Eyad** — AI Engineer  
[github.com/eyadXE](https://github.com/eyadXE)

Built on the original pipeline by [AdelSobhy](https://github.com/AdelSobhy/RKO).
