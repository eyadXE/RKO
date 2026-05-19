import math
from collections import defaultdict

import matplotlib.pyplot as plt
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from rko.ai_client import enhance_resume, score_ats
from rko.analysis import (
    basic_stats,
    keyword_frequency,
    keyword_frequency_by_industry,
    suggest_keywords,
)
from rko.ats import rule_based_score, score_label
from rko.config import MAX_PAGES, MAX_RECORDS, TOP_N_KEYWORDS
from rko.preprocess import STOPWORDS, normalize_text, preprocess_records, tokenize
from rko.resume import parse_resume
from rko.scraper import crawl_jobs_multi

st.set_page_config(page_title="Resume Keyword Optimiser", page_icon="📄", layout="wide")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📄 RKO")
    st.caption("Resume Keyword Optimiser")
    st.divider()

    query_input = st.text_input("Job query", value="data analyst")
    max_records = st.slider("Max records", 10, 200, MAX_RECORDS, step=10)
    max_pages = st.slider("Max pages", 1, 15, MAX_PAGES)

    run_scraper = st.button("🔍 Run Scraper", use_container_width=True, type="primary")

    if run_scraper:
        queries = [q.strip() for q in query_input.split(",") if q.strip()]
        with st.spinner("Scraping job postings…"):
            raw = crawl_jobs_multi(queries, max_records, max_pages)
        if not raw:
            st.error("No records collected. Check network access or robots.txt.")
        else:
            processed = preprocess_records(raw)
            st.session_state["records"] = processed
            st.session_state["keyword_counts"] = keyword_frequency(processed, top_n=TOP_N_KEYWORDS)
            st.session_state["query"] = query_input
            for key in ("ats_before", "ats_after", "enhanced_text", "suggestions"):
                st.session_state.pop(key, None)
            st.success(f"Collected {len(processed)} records.")

    st.divider()
    st.caption("Set GROQ_API_KEY in your environment before using AI features.")

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Job Market",
    "📋 Resume Analysis",
    "✨ Optimise & Compare",
    "🔍 IR Analysis",
    "🤖 AI CV Advisor",
])

# ── Tab 1: Job Market ─────────────────────────────────────────────────────────
with tab1:
    st.header("Job Market Keywords")

    if "records" not in st.session_state:
        st.info("Run the scraper from the sidebar to load job market data.")
    else:
        records = st.session_state["records"]
        kw_counts = st.session_state["keyword_counts"]
        stats = basic_stats(records)

        c1, c2, c3 = st.columns(3)
        c1.metric("Records collected", stats["total_records"])
        c2.metric("Unique keywords", stats["unique_keywords"])
        c3.metric("Avg tokens / posting", stats["average_token_count"])

        st.subheader("Top Keywords")
        if kw_counts:
            top20 = kw_counts[:20]
            labels = [k for k, _ in top20]
            values = [v for _, v in top20]
            fig, ax = plt.subplots(figsize=(9, 5))
            ax.barh(labels[::-1], values[::-1], color="#d1495b")
            ax.set_xlabel("Frequency")
            ax.set_title("Top 20 Job Keywords")
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

        with st.expander("Per-industry keywords"):
            industry_kw = keyword_frequency_by_industry(records, top_n=15, min_records=3)
            if industry_kw:
                for industry, pairs in industry_kw.items():
                    st.markdown(f"**{industry}**")
                    st.write(", ".join(f"{k} ({c})" for k, c in pairs))
            else:
                st.write("Not enough records per industry to segment.")

# ── Tab 2: Resume Analysis ────────────────────────────────────────────────────
with tab2:
    st.header("Resume Analysis")

    if "records" not in st.session_state:
        st.info("Run the scraper first to load job market keywords.")
    else:
        uploaded = st.file_uploader("Upload your resume", type=["txt", "pdf"])

        if uploaded:
            resume_text = parse_resume(uploaded)
            st.session_state["resume_text"] = resume_text

        analyse = st.button("Analyse Resume", type="primary", disabled="resume_text" not in st.session_state)

        if analyse and "resume_text" in st.session_state:
            resume_text = st.session_state["resume_text"]
            kw_counts = st.session_state["keyword_counts"]
            top_keywords = [k for k, _ in kw_counts]

            resume_tokens = set(
                t for t in tokenize(normalize_text(resume_text))
                if t not in STOPWORDS and len(t) > 2
            )
            st.session_state["resume_tokens"] = resume_tokens

            rule_score = rule_based_score(resume_tokens, top_keywords)
            st.session_state["rule_score_before"] = rule_score

            with st.spinner("Scoring resume with AI…"):
                ats = score_ats(resume_text, top_keywords, st.session_state.get("query", ""))
            st.session_state["ats_before"] = ats

            suggestions = suggest_keywords(
                st.session_state["records"], resume_text, top_n=TOP_N_KEYWORDS
            )
            st.session_state["suggestions"] = suggestions
            st.session_state.pop("ats_after", None)
            st.session_state.pop("enhanced_text", None)

        if "ats_before" in st.session_state:
            ats = st.session_state["ats_before"]
            rule_score = st.session_state.get("rule_score_before", 0)
            label = score_label(ats["score"])

            c1, c2 = st.columns(2)
            c1.metric("AI ATS Score (before)", f"{ats['score']} / 100", label)
            c2.metric("Keyword match (rule-based)", f"{rule_score}%")
            st.info(ats["explanation"])

            suggestions = st.session_state.get("suggestions", [])
            if suggestions:
                st.subheader("Recommended keywords to add")
                default_selection = [k for k, _ in suggestions[:10]]
                st.multiselect(
                    "Select keywords to incorporate into your resume",
                    options=[k for k, _ in suggestions],
                    default=default_selection,
                    key="selected_keywords",
                )

# ── Tab 3: Optimise & Compare ─────────────────────────────────────────────────
with tab3:
    st.header("Optimise & Compare")

    ready = (
        "resume_text" in st.session_state
        and "ats_before" in st.session_state
        and st.session_state.get("selected_keywords")
    )

    if not ready:
        st.info("Complete Resume Analysis (Tab 2) and select keywords before enhancing.")
    else:
        enhance = st.button("✨ Enhance Resume with AI", type="primary")

        if enhance:
            keywords_to_add = st.session_state["selected_keywords"]
            resume_text = st.session_state["resume_text"]
            kw_counts = st.session_state["keyword_counts"]
            top_keywords = [k for k, _ in kw_counts]

            with st.spinner("Rewriting resume…"):
                enhanced = enhance_resume(resume_text, keywords_to_add)
            st.session_state["enhanced_text"] = enhanced

            with st.spinner("Scoring enhanced resume…"):
                ats_after = score_ats(enhanced, top_keywords, st.session_state.get("query", ""))
            st.session_state["ats_after"] = ats_after

            enhanced_tokens = set(
                t for t in tokenize(normalize_text(enhanced))
                if t not in STOPWORDS and len(t) > 2
            )
            st.session_state["rule_score_after"] = rule_based_score(enhanced_tokens, top_keywords)

    if "enhanced_text" in st.session_state:
        ats_before = st.session_state["ats_before"]
        ats_after = st.session_state["ats_after"]
        rule_before = st.session_state.get("rule_score_before", 0)
        rule_after = st.session_state.get("rule_score_after", 0)
        delta = ats_after["score"] - ats_before["score"]

        c1, c2, c3 = st.columns(3)
        c1.metric("ATS Score Before", f"{ats_before['score']} / 100")
        c2.metric("ATS Score After", f"{ats_after['score']} / 100", f"{delta:+d} pts")
        c3.metric("Keyword match improvement", f"{rule_after}%", f"{rule_after - rule_before:+.1f}%")

        st.divider()
        col_orig, col_new = st.columns(2)
        with col_orig:
            st.subheader("Original Resume")
            st.text_area("", value=st.session_state["resume_text"], height=500, disabled=True, key="orig_display")
        with col_new:
            st.subheader("Enhanced Resume")
            st.text_area("", value=st.session_state["enhanced_text"], height=500, key="enhanced_display")

        st.divider()
        st.subheader("AI Feedback")
        st.info(f"**Before:** {ats_before['explanation']}")
        st.success(f"**After:** {ats_after['explanation']}")

        st.download_button(
            label="⬇ Download Enhanced Resume",
            data=st.session_state["enhanced_text"],
            file_name="enhanced_resume.txt",
            mime="text/plain",
            use_container_width=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# ── Tab 4: IR Analysis ────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("Information Retrieval Analysis")

    if "records" not in st.session_state:
        st.info("Run the scraper from the sidebar first to load job market data.")
    else:
        records = st.session_state["records"]

        # ── Compute IR metrics (cached in session state so they don't recompute on every interaction) ──
        if "ir_computed" not in st.session_state:
            N = len(records)

            # --- Inverted index ---
            index = defaultdict(list)
            for doc_idx, record in enumerate(records):
                tokens = record.get("tokens") or []
                pos_map = defaultdict(list)
                for pos, token in enumerate(tokens):
                    pos_map[token].append(pos)
                for token, positions in pos_map.items():
                    index[token].append({"doc_idx": doc_idx, "positions": positions})

            index_summary = sorted(
                [{"token": t, "doc_freq": len(p)} for t, p in index.items()],
                key=lambda x: x["doc_freq"], reverse=True
            )[:50]

            # --- TF-IDF ---
            df_map = defaultdict(int)
            for record in records:
                for token in set(record.get("tokens") or []):
                    df_map[token] += 1

            tfidf_sum = defaultdict(float)
            for record in records:
                tokens = record.get("tokens") or []
                if not tokens:
                    continue
                doc_len = len(tokens)
                tf_map = defaultdict(int)
                for t in tokens:
                    tf_map[t] += 1
                for token, count in tf_map.items():
                    tf = count / doc_len
                    idf = math.log((N + 1) / (1 + df_map[token]))
                    tfidf_sum[token] += tf * idf

            tfidf_ranking = sorted(
                [
                    {"token": t, "tfidf_score": round(s / N, 6), "doc_freq": df_map[t],
                     "doc_pct": round(100 * df_map[t] / N, 1)}
                    for t, s in tfidf_sum.items() if df_map[t] > 1
                ],
                key=lambda x: x["tfidf_score"], reverse=True
            )[:50]

            # --- Frequency stats ---
            total_freq = defaultdict(int)
            doc_freq = defaultdict(int)
            for record in records:
                tokens = record.get("tokens") or []
                for t in set(tokens):
                    doc_freq[t] += 1
                for t in tokens:
                    total_freq[t] += 1

            freq_stats = sorted(
                [
                    {"token": t, "total_freq": total_freq[t], "doc_freq": doc_freq[t],
                     "doc_pct": round(100 * doc_freq[t] / N, 1)}
                    for t in total_freq
                ],
                key=lambda x: x["total_freq"], reverse=True
            )[:50]

            st.session_state["ir_index_summary"] = index_summary
            st.session_state["ir_tfidf"]          = tfidf_ranking
            st.session_state["ir_freq_stats"]      = freq_stats
            st.session_state["ir_computed"]        = True

        index_summary = st.session_state["ir_index_summary"]
        tfidf_ranking  = st.session_state["ir_tfidf"]
        freq_stats     = st.session_state["ir_freq_stats"]

        # ── Sub-section selector ──────────────────────────────────────────────
        ir_section = st.radio(
            "Select view",
            ["📂 Inverted Index", "📈 TF-IDF Ranking", "📊 Frequency Stats"],
            horizontal=True,
        )

        # ── Inverted Index ────────────────────────────────────────────────────
        if ir_section == "📂 Inverted Index":
            st.subheader("Inverted Index — Top Terms by Document Frequency")
            st.caption(
                "An inverted index maps each token to every job posting that contains it — "
                "the same structure search engines use. Here we show the top 25 tokens ranked "
                "by how many distinct postings (posting-list length) they appear in."
            )

            top25 = index_summary[:25]
            labels = [d["token"] for d in top25]
            values = [d["doc_freq"] for d in top25]

            fig, ax = plt.subplots(figsize=(9, 5))
            ax.barh(labels[::-1], values[::-1], color="#4f8ef7")
            ax.set_xlabel("Document Frequency (# postings)")
            ax.set_title("Top 25 Tokens — Posting List Length")
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

            st.divider()
            search = st.text_input("🔎 Filter tokens", placeholder="e.g. python", key="idx_search")
            rows = [d for d in index_summary if not search or search.lower() in d["token"]]
            st.dataframe(
                {"Rank": range(1, len(rows)+1), "Token": [d["token"] for d in rows],
                 "Doc Frequency": [d["doc_freq"] for d in rows]},
                use_container_width=True, hide_index=True,
            )

        # ── TF-IDF ───────────────────────────────────────────────────────────
        elif ir_section == "📈 TF-IDF Ranking":
            st.subheader("TF-IDF Ranking")
            st.caption(
                "TF-IDF weights each token by how often it appears in a posting relative to "
                "how common it is across *all* postings. High score = important and discriminative. "
                "The score shown is the mean TF-IDF across the whole corpus."
            )
            st.code(
                "TF-IDF(t,d) = [count(t,d) / |d|]  ×  log( (N+1) / (1 + df(t)) )",
                language=None,
            )

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Top token",       tfidf_ranking[0]["token"])
            col_b.metric("Top TF-IDF score", tfidf_ranking[0]["tfidf_score"])
            col_c.metric("Tokens ranked",    len(tfidf_ranking))

            top25 = tfidf_ranking[:25]
            labels = [d["token"] for d in top25]
            values = [d["tfidf_score"] for d in top25]

            fig, ax = plt.subplots(figsize=(9, 5))
            ax.barh(labels[::-1], values[::-1], color="#f59e0b")
            ax.set_xlabel("Mean TF-IDF Score")
            ax.set_title("Top 25 Tokens by TF-IDF")
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

            st.divider()
            search = st.text_input("🔎 Filter tokens", placeholder="e.g. sql", key="tfidf_search")
            rows = [d for d in tfidf_ranking if not search or search.lower() in d["token"]]
            st.dataframe(
                {"Rank": range(1, len(rows)+1), "Token": [d["token"] for d in rows],
                 "TF-IDF Score": [d["tfidf_score"] for d in rows],
                 "Doc Freq": [d["doc_freq"] for d in rows],
                 "Doc %": [d["doc_pct"] for d in rows]},
                use_container_width=True, hide_index=True,
            )

        # ── Frequency Stats ───────────────────────────────────────────────────
        elif ir_section == "📊 Frequency Stats":
            st.subheader("Keyword Frequency Statistics")
            st.caption(
                "Raw occurrence count vs document-level presence. "
                "Doc % = percentage of all job postings that contain this token."
            )

            top20 = freq_stats[:20]
            labels = [d["token"] for d in top20]

            col1, col2 = st.columns(2)
            with col1:
                fig, ax = plt.subplots(figsize=(6, 5))
                ax.barh(labels[::-1], [d["total_freq"] for d in top20][::-1], color="#34d399")
                ax.set_xlabel("Total Occurrences")
                ax.set_title("Total Occurrences — Top 20")
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

            with col2:
                fig, ax = plt.subplots(figsize=(6, 5))
                ax.barh(labels[::-1], [d["doc_pct"] for d in top20][::-1], color="#a78bfa")
                ax.set_xlabel("% of Job Postings")
                ax.set_title("Market Penetration % — Top 20")
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

            st.divider()
            search = st.text_input("🔎 Filter tokens", placeholder="e.g. excel", key="freq_search")
            rows = [d for d in freq_stats if not search or search.lower() in d["token"]]
            st.dataframe(
                {"Rank": range(1, len(rows)+1), "Token": [d["token"] for d in rows],
                 "Total Freq": [d["total_freq"] for d in rows],
                 "Doc Freq": [d["doc_freq"] for d in rows],
                 "Doc %": [d["doc_pct"] for d in rows]},
                use_container_width=True, hide_index=True,
            )

# ══════════════════════════════════════════════════════════════════════════════
# ── Tab 5: AI CV Advisor ──────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.header("🤖 AI CV Advisor")
    st.caption(
        "Paste your resume and the AI will cross-reference it against the real job-market "
        "data to recommend projects and technologies that will strengthen your CV."
    )

    if "records" not in st.session_state:
        st.info("Run the scraper from the sidebar first so the advisor has market data to work with.")
    else:
        # ── Resume input ──────────────────────────────────────────────────────
        # Pre-fill from Tab 2 if a resume was already uploaded there
        prefill = st.session_state.get("resume_text", "")
        advisor_resume = st.text_area(
            "Your resume text",
            value=prefill,
            height=260,
            placeholder="Paste your resume here, or upload one in the Resume Analysis tab first.",
        )

        target_role = st.text_input(
            "Target job role (optional)",
            placeholder="e.g. Data Analyst, ML Engineer, Backend Developer",
        )

        # ── Build market context from session-state IR / keyword data ─────────
        def build_market_context() -> str:
            parts = []

            if "ir_tfidf" in st.session_state:
                top_tfidf = ", ".join(d["token"] for d in st.session_state["ir_tfidf"][:25])
                parts.append(f"Top discriminative skills (TF-IDF): {top_tfidf}")

            if "ir_freq_stats" in st.session_state:
                top_freq = ", ".join(
                    f"{d['token']} ({d['doc_pct']}% of postings)"
                    for d in st.session_state["ir_freq_stats"][:20]
                )
                parts.append(f"Most common skills across all postings: {top_freq}")

            if "keyword_counts" in st.session_state:
                kw = st.session_state["keyword_counts"]
                raw_top = ", ".join(f"{k}({v})" for k, v in kw[:20])
                parts.append(f"Raw keyword frequency top 20: {raw_top}")

            records = st.session_state.get("records", [])
            if records:
                parts.append(f"Total job postings analysed: {len(records)}")

            return "\n".join(parts) if parts else "No market data available."

        # ── Analyse button ────────────────────────────────────────────────────
        if st.button("✨ Get Project & Technology Recommendations", type="primary"):
            if not advisor_resume.strip():
                st.warning("Please paste your resume text above.")
            else:
                import os
                from groq import Groq

                market_ctx  = build_market_context()
                role_line   = f"Target role: {target_role}" if target_role else ""
                query_line  = f"Job query used for scraping: {st.session_state.get('query', '')}"

                system_prompt = (
                    "You are an expert career coach and technical recruiter specialising in tech roles.\n"
                    "You receive a candidate's resume and real job-market keyword data scraped from "
                    "actual job postings.\n\n"
                    "Produce a concrete, actionable CV enhancement plan in these sections:\n"
                    "## 📊 Skills Gap Analysis\n"
                    "## 🛠️ Recommended Projects\n"
                    "   For each project: name, 2-sentence description, tech stack, and why it helps.\n"
                    "## 💡 Technologies to Learn\n"
                    "   Prioritised by market demand from the data provided.\n"
                    "## ✅ Quick Wins\n"
                    "   Things the candidate can add or fix in their CV immediately.\n\n"
                    "Be specific. Name real tools, libraries, and frameworks. No generic advice."
                )

                user_message = (
                    f"## Job Market Data (real scraped data)\n{market_ctx}\n\n"
                    f"{query_line}\n{role_line}\n\n"
                    f"## Candidate Resume\n{advisor_resume[:4000]}"
                )

                with st.spinner("Analysing your resume against market data…"):
                    try:
                        client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            max_tokens=1800,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user",   "content": user_message},
                            ],
                        )
                        advice = response.choices[0].message.content
                        st.session_state["cv_advice"] = advice
                    except Exception as exc:
                        st.error(f"Groq API error: {exc}")

        # ── Display advice ────────────────────────────────────────────────────
        if "cv_advice" in st.session_state:
            st.divider()
            st.markdown(st.session_state["cv_advice"])
            st.download_button(
                "⬇ Download Advice as .md",
                data=st.session_state["cv_advice"],
                file_name="cv_advice.md",
                mime="text/markdown",
                use_container_width=True,
            )

        with st.expander("ℹ️ How does this work?"):
            st.markdown(
                "1. The scraper collects real job postings for your query.\n"
                "2. The IR engine computes TF-IDF and keyword frequencies across the corpus.\n"
                "3. That market data is sent alongside your resume to **Llama 3.3 70B via Groq**.\n"
                "4. The model identifies your gaps and recommends specific projects and tech "
                "that match what employers are actually looking for.\n"
                "5. Nothing is stored — all processing happens in your session."
            )