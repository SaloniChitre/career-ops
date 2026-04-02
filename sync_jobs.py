import sys
from pathlib import Path
from core.fetcher import fetch_linkedin_job_alerts, extract_job_listings
from utils.dashboard import save_to_log

def sync_jobs(hours: int = 2160, save_log: bool = True):
    print(f"🚀 Syncing {hours}h of LinkedIn Alerts...")

    # 1. Fetch from Gmail
    alerts = fetch_linkedin_job_alerts(hours=hours)
    if not alerts:
        print("No new alerts found.")
        return

    # 2. Extract and Map
    all_jobs = []
    for alert in alerts:
        raw_jobs = extract_job_listings(alert["body"])
        
        for job in raw_jobs:
            # FIX: Capture ACTUAL titles/companies, NO placeholder text
            job['title'] = str(job.get('title', 'Unknown Role')).strip()
            job['company'] = str(job.get('company', 'Unknown Company')).strip()
            job['location'] = str(job.get('location', 'N/A')).strip()
            all_jobs.append(job)

    # 3. Save to JSON
    if save_log and all_jobs:
        save_to_log(all_jobs)
        print(f"✅ Successfully saved {len(all_jobs)} jobs with real titles.")

if __name__ == "__main__":
    sync_jobs()