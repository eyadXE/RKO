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
            # clear downstream state so stale results don't persist
            for key in ("ats_before", "ats_after", "enhanced_text", "suggestions"):
                st.session_state.pop(key, None)
            st.success(f"Collected {len(processed)} records.")

    st.divider()
    st.caption("Set GROQ_API_KEY in your environment before using AI features.")

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Job Market", "📋 Resume Analysis", "✨ Optimise & Compare"])

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
