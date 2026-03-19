import streamlit as st
import json
import pandas as pd
import pdfplumber
from pathlib import Path
from io import BytesIO
from docx import Document
from core.processor import compare_resume_to_job, client

# --- 1. UI STYLING & CONFIG ---
st.set_page_config(page_title="Saloni's Career Ops", page_icon="🎯", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #58a6ff; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #161b22; border-radius: 5px; padding: 10px 20px; color: white;
    }
    .stTabs [aria-selected="true"] { background-color: #238636 !important; }
    </style>
    """, unsafe_allow_html=True)

LOG_PATH = Path("data/jobs_log.json")

# --- 2. HELPER FUNCTIONS ---
def extract_pdf(file):
    if not file: return None
    try:
        with pdfplumber.open(file) as pdf:
            return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
    except Exception: return None

def save_as_docx(content, title):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

def ai_generate(prompt):
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return completion.choices[0].message.content
    except Exception as e: return f"Error: {str(e)}"

def update_job_status(job_id, new_status, all_data):
    for job in all_data:
        if job.get('id') == job_id:
            job['status'] = new_status
            break
    with open(LOG_PATH, "w") as f:
        json.dump(all_data, f, indent=4)
    st.rerun()

# --- 3. UI RENDERING LOGIC ---
def render_job_section(job_list, all_data, key_suffix):
    if not job_list:
        st.info("No active opportunities in this category.")
        return

    df = pd.DataFrame(job_list)
    cols_to_show = ["status", "title", "company", "location"]
    for c in cols_to_show: 
        if c not in df.columns: df[c] = "N/A"
    st.dataframe(df[cols_to_show], use_container_width=True, hide_index=True)

    st.markdown("### 🛠️ Intelligence & Actions")
    for i, job in enumerate(job_list):
        job_id = job.get('id', f"{key_suffix}_{i}")
        with st.expander(f"💼 {job.get('title')} @ {job.get('company')}"):
            
            c1, c2 = st.columns([2, 1])
            with c1:
                action = st.selectbox("Select Action:", 
                    ["Analyze Fit", "Full Resume Rewrite", "Tailor Resume", "Draft Cover Letter", "Outreach Message", "Interview Prep"],
                    key=f"act_{job_id}")
            with c2:
                current_status = job.get('status', 'ALERT')
                status_options = ["ALERT", "APPLIED", "IN_PROGRESS", "REJECTED"]
                status_index = status_options.index(current_status) if current_status in status_options else 0
                new_stat = st.selectbox("Update Status:", status_options, index=status_index, key=f"stat_{job_id}")
                if new_stat != current_status:
                    if st.button("Save Status", key=f"save_{job_id}"):
                        update_job_status(job.get('id'), new_stat, all_data)

            st.divider()
            
            col_in, col_out = st.columns([1, 1.5])
            with col_in:
                st.write("**Job Context**")
                jd_text = st.text_area("Paste Full JD:", key=f"jd_{job_id}", height=200)
                final_jd = jd_text if len(jd_text) > 50 else job.get('description', '')

            with col_out:
                st.write("**AI Output**")
                
                if action == "Analyze Fit":
                    if st.button("Run Match Score", key=f"go_fit_{job_id}"):
                        if not resume_text: st.warning("Upload resume first!"); return
                        res = compare_resume_to_job(resume_text, final_jd)
                        st.metric("Compatibility", f"{res.get('score', 0)}%")
                        st.write("**Matching:** " + ", ".join(res.get('matching_skills', [])))
                        st.write("**Gaps:** " + ", ".join(res.get('missing_skills', [])))

                elif action == "Full Resume Rewrite":
                    if st.button("Generate Full Resume", key=f"go_full_{job_id}"):
                        if not resume_text: st.warning("Upload resume first!"); return
                        prompt = f"Rewrite my entire resume to pass ATS for this job: {final_jd[:1500]}. Current Resume: {resume_text}. Highlight ST-GCN, GNNs, and Agentic RAG. Ensure NYC ResilienceTwin is a key feature."
                        content = ai_generate(prompt)
                        st.text_area("Preview", content, height=300, key=f"txt_full_{job_id}")
                        st.download_button("Download Updated Resume", data=save_as_docx(content, "Full Resume"), file_name=f"Saloni_Resume_{job['company']}.docx", key=f"dl_full_{job_id}")

                elif action == "Tailor Resume":
                    if st.button("Generate Bullets", key=f"go_bul_{job_id}"):
                        content = ai_generate(f"Tailor these bullets: {resume_text[:1000]} for: {final_jd[:1000]}")
                        st.write(content)
                        st.download_button("Download Bullets", data=save_as_docx(content, "Bullets"), file_name=f"Bullets_{job['company']}.docx", key=f"dl_bul_{job_id}")

                elif action == "Draft Cover Letter":
                    if st.button("Generate Letter", key=f"go_cl_{job_id}"):
                        content = ai_generate(f"Write a cover letter for {job['title']} at {job['company']} using {resume_text[:1500]} and {final_jd[:1500]}. Focus on technical fit and local availability.")
                        st.write(content)
                        st.download_button("Download Letter", data=save_as_docx(content, "Cover Letter"), file_name=f"CL_{job['company']}.docx", key=f"dl_cl_{job_id}")

                elif action == "Outreach Message":
                    if st.button("Generate Message", key=f"go_out_{job_id}"):
                        content = ai_generate(f"Write a punchy LinkedIn outreach for {job['title']} at {job['company']}. Focus on ST-GCN/RAG skills. Max 100 words.")
                        st.write(content)

                elif action == "Interview Prep":
                    if st.button("Generate Guide", key=f"go_int_{job_id}"):
                        content = ai_generate(f"Create 5 interview questions for {job['title']} using {resume_text[:1000]} and {final_jd[:1000]}")
                        st.write(content)
                        st.download_button("Download Guide", data=save_as_docx(content, "Prep Guide"), file_name=f"Prep_{job['company']}.docx", key=f"dl_int_{job_id}")

# --- 4. MAIN APP ---
st.sidebar.title("👤 Saloni's Profile")
uploaded_resume = st.sidebar.file_uploader("Upload Resume (PDF)", type=["pdf"])
resume_text = extract_pdf(uploaded_resume) if uploaded_resume else None

if LOG_PATH.exists():
    with open(LOG_PATH, "r") as f:
        data = json.load(f)

    st.title("🚀 Career Ops Command Center")
    m1, m2, m3, m4 = st.columns(4)
    applied = len([j for j in data if j['status'] == 'APPLIED'])
    interviews = len([j for j in data if j['status'] == 'IN_PROGRESS'])
    alerts = len([j for j in data if j['status'] == 'ALERT'])
    m1.metric("Total Apps", applied)
    m2.metric("Interviews", interviews)
    m3.metric("New Alerts", alerts)
    m4.metric("Success Rate", f"{round((interviews/max(applied, 1))*100)}%")

    tabs = st.tabs(["📤 Applied", "👀 In Progress", "🔔 Alerts", "❌ Rejected"])
    with tabs[0]: render_job_section([j for j in data if j['status'] == 'APPLIED'], data, "app")
    with tabs[1]: render_job_section([j for j in data if j['status'] == 'IN_PROGRESS'], data, "prog")
    with tabs[2]: render_job_section([j for j in data if j['status'] == 'ALERT'], data, "alrt")
    with tabs[3]: 
        rej = [j for j in data if j['status'] == 'REJECTED']
        if rej: st.dataframe(pd.DataFrame(rej)[["title", "company"]], use_container_width=True, hide_index=True)
else:
    st.warning("No data found. Run `python sync_jobs.py` first.")