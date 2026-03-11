import streamlit as st
import json
import pandas as pd
from pathlib import Path

# Page Config
st.set_page_config(page_title="Saloni's Career Ops", page_icon="💼", layout="wide")

# Path to your data
LOG_PATH = Path("data/jobs_log.json")

def load_data():
    if not LOG_PATH.exists():
        return []
    with open(LOG_PATH, "r") as f:
        return json.load(f)

# Sidebar Info
st.sidebar.title("🚀 Career Ops Manager")
if st.sidebar.button("Refresh Data"):
    st.rerun()

data = load_data()

if not data:
    st.warning("No data found. Run `python3 sync_jobs.py` first!")
else:
    st.title("🗂️ Job Application Tracker")
    
    # 1. Create Tabs for different statuses
    tab_titles = ["Accepted 🏆", "In Progress 👀", "Applied ✅", "Alerts 🔔", "Rejected ❌"]
    t1, t2, t3, t4, t5 = st.tabs(tab_titles)

    # Map internal status to tabs
    mapping = {
        "ACCEPTED": t1,
        "IN_PROGRESS": t2,
        "APPLIED": t3,
        "ALERT": t4,
        "REJECTED": t5
    }

    for status_key, tab_obj in mapping.items():
        with tab_obj:
            filtered_jobs = [j for j in data if j.get("status") == status_key]
            
            if not filtered_jobs:
                st.info(f"No jobs currently in {status_key.lower()} status.")
                continue

            # Display a clean table for each status
            df = pd.DataFrame(filtered_jobs)
            # Reorder columns for readability
            cols = ["match_score", "title", "company", "verdict"]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)

            # Detailed Breakdown Section
            with st.expander("🔍 View Detailed AI Insights"):
                for job in filtered_jobs:
                    st.subheader(f"{job['title']} @ {job['company']}")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write("**✅ Top Matches:**")
                        st.write(", ".join(job.get("top_matches", [])))
                    with col_b:
                        st.write("**⚠️ Gaps:**")
                        st.write(", ".join(job.get("gaps", [])))
                    
                    if job.get("recruiter_message"):
                        st.info(f"**📨 Recruiter Outreach:**\n\n{job['recruiter_message']}")
                    st.divider()