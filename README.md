# Resume Keyword Optimiser

Scrapes job postings from Wuzzuf, extracts the most in-demand keywords, scores your resume against them using AI, and rewrites it to improve your ATS (Applicant Tracking System) match — all through an interactive web UI.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- A free [Groq API key](https://console.groq.com/) (for AI scoring and resume rewriting)

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/AdelSobhy/RKO.git
cd RKO
```

**2. Install dependencies**
```bash
uv sync
```

**3. Add your Groq API key**

Open `.env` and replace the placeholder:
```
GROQ_API_KEY=your_groq_api_key_here
```

## Running the App

```bash
uv run streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

## How to Use

**Tab 1 — Job Market**
1. Enter a job title in the sidebar (e.g. `data analyst`) and set how many records to collect.
2. Click **Run Scraper**. The app fetches live job postings from Wuzzuf (respects robots.txt).
3. View the top keyword chart and per-industry breakdown.

**Tab 2 — Resume Analysis**
1. Upload your resume as `.txt` or `.pdf`.
2. Click **Analyse Resume**.
3. The app returns an AI-generated ATS score (0–100) with an explanation and a list of high-frequency keywords missing from your resume.
4. Select which keywords you want added.

**Tab 3 — Optimise & Compare**
1. Click **Enhance Resume with AI**.
2. The AI rewrites your resume to incorporate the selected keywords naturally.
3. View the before/after ATS scores and a side-by-side comparison of the original and enhanced resume.
4. Download the enhanced resume as a `.txt` file.

## CLI Pipeline (headless)

If you prefer to run without the UI:

```bash
# Single query
uv run python main.py --query "data analyst" --max-records 120 --max-pages 12

# Multiple queries (aggregated, de-duplicated)
uv run python main.py --queries "ai engineer, machine learning, data scientist"

# With a resume file for keyword gap analysis
uv run python main.py --resume path/to/resume.txt --query "data analyst"
```

Outputs are written to `data/` (JSON) and `reports/` (CSV + PNG charts). Open `web/index.html` to view the static report dashboard.

## Project Structure

```
app.py              # Streamlit UI entry point
main.py             # CLI pipeline entry point
rko/
  scraper.py        # Wuzzuf scraper (robots.txt compliant)
  preprocess.py     # Tokenisation and text normalisation
  analysis.py       # Keyword frequency and resume gap analysis
  ats.py            # Rule-based ATS scoring
  ai_client.py      # Groq API — ATS scoring and resume rewriting
  resume.py         # Resume parser (.txt and .pdf)
  reporting.py      # CSV / PNG report generation
  storage.py        # JSON file I/O
  config.py         # All constants and defaults
web/
  index.html        # Static report dashboard
data/               # Scraped JSON (generated at runtime)
reports/            # Charts and CSVs (generated at runtime)
```

## Notes

- The scraper stops early if Wuzzuf returns 403/429 or if robots.txt disallows access.
- The Groq API key is free — sign up at [console.groq.com](https://console.groq.com/).
- `.env` is gitignored and will never be committed.
