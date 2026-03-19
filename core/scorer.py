"""
Job Scorer
Uses Claude API to score each job listing against Saloni's resume profile.
Returns structured match ratings: GREEN / YELLOW / RED
"""

import json
import re
import os
import time
from dotenv import load_dotenv
import requests
from typing import Optional

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

# Saloni's resume profile — update as needed
RESUME_PROFILE = """
NAME: Saloni Chitre
LOCATION: New York, NY
EDUCATION: MS Data Science, Pace University (GPA 3.71, May 2026) | BS Computer Science, Mithibai College

EXPERIENCE:
- Data Scientist @ Monk Soft Technologies (Feb 2024 – Aug 2024): XGBoost, PyTorch, Hugging Face LLMs, Spark, AWS S3/SageMaker, ETL
- Marketing Data Analyst Intern @ Jaspytech (Sep–Dec 2023): SQL, BigQuery, ETL workflows, PowerBI, Tableau
- Data Analyst Intern @ Times of India (Apr–Aug 2023): Python, Pandas, Scikit-Learn, Power BI, SQL

PROJECTS:
- Vibe-Studio: Full-stack AI ad generator (Next.js, FastAPI, LangChain, OpenAI SDK, BeautifulSoup, Selenium)
- AI-Powered ATS Optimizer: Resume parser (FastAPI, PyMuPDF, Sentence-Transformers, spaCy, OpenAI SDK, Streamlit)
- NL2SQL System: Natural language to SQL (Python, FastAPI, Streamlit, LLM prompt engineering)

SKILLS:
- ML/AI: XGBoost, PyTorch, Hugging Face, LLMs, NLP, spaCy, Sentence-Transformers, Scikit-Learn
- Data Engineering: Spark, AWS SageMaker, BigQuery, ETL/ELT, MySQL, PostgreSQL
- Analytics & BI: PowerBI, Tableau, Pandas, NumPy, Plotly, Streamlit
- Full-Stack/APIs: FastAPI, Next.js, React.js, LangChain, OpenAI SDK, Python
- Other: Git, Google Cloud (Vertex AI), Microsoft Office

PREFERENCES:
- Target roles: Data Scientist, ML Engineer, AI/LLM Engineer, Analytics Engineer, Data Analyst
- Location: NYC preferred, Remote OK
- NOT interested in: Pure healthcare domain, pure SWE with no data/ML, roles requiring 5+ years experience
"""

SCORING_PROMPT = """
You are a career advisor scoring job listings against a candidate's resume profile.

CANDIDATE PROFILE:
{resume}

JOB LISTING:
Title: {title}
Company: {company}
Location: {location}
Description: {description}

Score this job and respond ONLY with a valid JSON object in this exact format:
{{
  "rating": "GREEN" | "YELLOW" | "RED",
  "emoji": "🟢" | "🟡" | "🔴",
  "match_score": <integer 0-100>,
  "top_matches": ["skill or requirement that matches", ...],
  "gaps": ["missing skill or requirement", ...],
  "verdict": "<one sentence summary>",
  "resume_tweak": "<specific resume adjustment suggested, or null if RED>",
  "recruiter_message": "<one paragraph cold outreach message, or null if RED>"
}}

Rating guide:
- GREEN (75-100): Strong match, apply immediately
- YELLOW (40-74): Good foundation but needs 1-2 tweaks
- RED (0-39): Domain mismatch or hard blockers
"""


def classify_category(title: str) -> str:
    title_lower = title.lower()
    if any(k in title_lower for k in ["data scien", "ml ", "machine learning", "ai ", "llm", "deep learning", "nlp", "generative"]):
        return "Data Science / ML"
    if any(k in title_lower for k in ["data analyst", "analytics", "business analyst", "bi ", "tableau", "power bi"]):
        return "Data Analytics"
    if any(k in title_lower for k in ["data engineer", "etl", "pipeline", "spark", "databricks", "dbt"]):
        return "Data Engineering"
    if any(k in title_lower for k in ["software engineer", "backend", "frontend", "full stack", "developer", "swe", "sde"]):
        return "Software Engineering"
    if any(k in title_lower for k in ["product manager", "product owner", "program manager"]):
        return "Product Management"
    if any(k in title_lower for k in ["marketing", "social media", "seo", "ads", "media buyer", "content", "brand", "influencer", "e-commerce", "ecommerce", "digital"]):
        return "Marketing"
    if any(k in title_lower for k in ["consult", "architect", "strategy", "advisor"]):
        return "Consulting"
    return "Other"


def score_job(title: str, company: str, location: str, description: str, status: str = "ALERT") -> dict:
    """
    Scores a job listing against the resume profile. 
    Skips AI scoring if the status indicates a terminal state (Accepted/Rejected).
    """
    
    category = classify_category(title)

    # 1. Short-circuit for Known Outcomes (Saves API Credits)
    if status in ["ACCEPTED", "REJECTED"]:
        return {
            "title": title,
            "company": company,
            "category": category,
            "rating": "GREEN" if status == "ACCEPTED" else "RED",
            "emoji": "🏆" if status == "ACCEPTED" else "❌",
            "match_score": 100 if status == "ACCEPTED" else 0,
            "top_matches": ["Confirmed Offer"] if status == "ACCEPTED" else [],
            "gaps": ["Application Closed"] if status == "REJECTED" else [],
            "verdict": f"Lifecycle Update: {status.replace('_', ' ').title()}",
            "resume_tweak": None,
            "recruiter_message": None,
            "status": status
        }

    # 2. Guard clause: Skip scoring if description is missing (only for new Alerts)
    if not description or len(description.strip()) < 20:
        return {
            "title": title,
            "company": company,
            "category": category,
            "rating": "RED",
            "match_score": 0,
            "verdict": "Scoring skipped: Missing or insufficient job description.",
            "status": status
        }

    # 3. Define headers and payload for Groq
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"
    }

    payload = {
        "model": MODEL,
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": SCORING_PROMPT.format(
                    resume=RESUME_PROFILE,
                    title=title,
                    company=company,
                    location=location,
                    description=description[:2000]
                )
            }
        ]
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        raw_text = data["choices"][0]["message"]["content"]
        
        # Parse JSON from AI response
        clean = re.sub(r'```json|```', '', raw_text).strip()
        result = json.loads(clean)
        
        # 4. Inject original metadata, status, and category
        result["title"] = title
        result["company"] = company
        result["status"] = status
        result["category"] = category
        return result

    except Exception as e:
        return {
            "title": title,
            "company": company,
            "category": category,
            "rating": "RED",
            "match_score": 0,
            "verdict": f"Scoring failed: {str(e)}",
            "status": status
        }

def score_all_jobs(jobs: list[dict]) -> list[dict]:
    """
    Scores a list of job listings and returns sorted results (GREEN first).
    """
    print(f"\n🤖 Scoring {len(jobs)} job(s) against your resume...")
    scored = []

    for i, job in enumerate(jobs, 1):
        print(f"   [{i}/{len(jobs)}] Scoring: {job['title']} @ {job['company']}...")
        result = score_job(
            title=job.get("title", "Unknown"),
            company=job.get("company", "Unknown"),
            location=job.get("location", "Not specified"),
            description=job.get("raw_block", ""),
            status=job.get("status", "ALERT")
        )
        result["url"] = job.get("url")
        scored.append(result)
        time.sleep(0.5)  # Avoid Groq rate limits

    # Sort: GREEN → YELLOW → RED
    order = {"GREEN": 0, "YELLOW": 1, "RED": 2, "ERROR": 3}
    scored.sort(key=lambda x: order.get(x["rating"], 3))

    print(f"✅ Scoring complete.")
    return scored


if __name__ == "__main__":
    # Quick test with a sample job
    test = score_job(
        title="Data Scientist",
        company="Acme Corp",
        location="New York, NY",
        description="Looking for a Data Scientist with Python, SQL, ML experience. XGBoost, AWS, and NLP a plus."
    )
    print(json.dumps(test, indent=2))
