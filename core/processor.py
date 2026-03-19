import os
import json
from groq import Groq
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Initialize Groq Client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def compare_resume_to_job(resume_text, job_description):
    """
    Uses the latest Llama 3.3 via Groq to analyze the match.
    """
    if not resume_text or not job_description or len(job_description) < 10:
        return {
            "score": 0,
            "matching_skills": [],
            "missing_skills": [],
            "verdict": "Insufficient data provided for analysis."
        }

    prompt = f"""
    You are an expert Technical Recruiter. Compare the following Resume to the Job Description.
    
    RESUME:
    {resume_text[:4000]}

    JOB DESCRIPTION:
    {job_description[:4000]}

    Return ONLY a valid JSON object with the following keys:
    "score": an integer from 0-100
    "matching_skills": a list of strings
    "missing_skills": a list of strings
    "verdict": a one-sentence summary of the fit.
    """

    try:
        # UPDATED MODEL NAME: llama-3.3-70b-versatile
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON response
        return json.loads(completion.choices[0].message.content)
        
    except Exception as e:
        return {
            "score": 0, 
            "matching_skills": [], 
            "missing_skills": [], 
            "verdict": f"Groq AI Error: {str(e)}"
        }