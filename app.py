import streamlit as st
import json
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Saloni's Career Ops", page_icon="💼", layout="wide")

LOG_PATH = Path("data/jobs_log.json")

def load_data():
    if not LOG_PATH.exists():
        return []
    with open(LOG_PATH, "r") as f:
        return json.load(f)

st.sidebar.title("🚀 Career Ops Manager")
if st.sidebar.button("Refresh Data"):
    st.rerun()

data = load_data()

if not data:
    st.warning("No data found. Run `python3 sync_jobs.py` first!")
else:
    st.title("🗂️ Job Application Tracker")

    # Tab definitions — APPLIED and IN_PROGRESS both appear in "In Progress"
    tab_titles = ["Accepted 🏆", "In Progress 👀", "Alerts 🔔", "Rejected ❌"]
    t_accepted, t_inprogress, t_alerts, t_rejected = st.tabs(tab_titles)

    TAB_STATUS_MAP = {
        t_accepted:   ["ACCEPTED"],
        t_inprogress: ["IN_PROGRESS", "APPLIED"],
        t_alerts:     ["ALERT"],
        t_rejected:   ["REJECTED"],
    }

    CATEGORY_ORDER = [
        "Data Science / ML",
        "Data Analytics",
        "Data Engineering",
        "Software Engineering",
        "Product Management",
        "Consulting",
        "Marketing",
        "Other"
    ]

    for tab_obj, statuses in TAB_STATUS_MAP.items():
        with tab_obj:
            filtered_jobs = [j for j in data if j.get("status") in statuses]

            if not filtered_jobs:
                st.info("No jobs in this category yet.")
                continue

            # Show a sub-label in In Progress so user knows which are Applied vs In Progress
            if statuses == ["IN_PROGRESS", "APPLIED"]:
                applied = [j for j in filtered_jobs if j.get("status") == "APPLIED"]
                in_prog  = [j for j in filtered_jobs if j.get("status") == "IN_PROGRESS"]
                if applied:
                    st.caption(f"✅ Applied: {len(applied)}  |  👀 Actively In Progress: {len(in_prog)}")

            # Group by category
            grouped = {}
            for job in filtered_jobs:
                cat = job.get("category", "Other")
                grouped.setdefault(cat, []).append(job)

            for cat in CATEGORY_ORDER:
                if cat not in grouped:
                    continue
                jobs_in_cat = grouped[cat]
                st.subheader(f"📂 {cat} ({len(jobs_in_cat)})")

                df = pd.DataFrame(jobs_in_cat)
                display_cols = [c for c in ["status", "match_score", "title", "company", "verdict"] if c in df.columns]
                st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

                with st.expander("🔍 View Detailed AI Insights"):
                    for job in jobs_in_cat:
                        st.subheader(f"{job['title']} @ {job['company']}")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write("**✅ Top Matches:**")
                            st.write(", ".join(job.get("top_matches", [])) or "—")
                        with col_b:
                            st.write("**⚠️ Gaps:**")
                            st.write(", ".join(job.get("gaps", [])) or "—")
                        if job.get("recruiter_message"):
                            st.info(f"**📨 Recruiter Outreach:**\n\n{job['recruiter_message']}")
                        st.divider()
