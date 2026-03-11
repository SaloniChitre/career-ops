import os
from dotenv import load_dotenv

# Load the key from the .env file
load_dotenv()

# Check if it loaded, but don't 'raise' an error that crashes the script
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("⚠️ WARNING: ANTHROPIC_API_KEY is still missing from the environment!")
else:
    print("✅ API Key successfully loaded.")

"""
Career Ops Manager — Main Entry Point
Run this script to sync LinkedIn Job Alerts and score them against your resume.

Usage:
    python sync_jobs.py           # Sync last 24 hours
    python sync_jobs.py --hours 48  # Sync last 48 hours
    python sync_jobs.py --output dashboard.md  # Save dashboard to file
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.fetcher import fetch_linkedin_job_alerts, extract_job_listings
from core.scorer import score_all_jobs
from utils.dashboard import render_dashboard, save_to_log


def sync_jobs(hours: int = 24, output_file: str = None, save_log: bool = True):
    """
    Full pipeline: Fetch → Parse → Score → Render Dashboard
    """
    print("=" * 60)
    print("🚀 Career Ops Manager — Sync Jobs")
    print(f"   Scanning LinkedIn Job Alerts from last {hours} hour(s)")
    print("=" * 60)

    # Step 1: Fetch emails
    alerts = fetch_linkedin_job_alerts(hours=hours)
    if not alerts:
        print("\n📭 No job alerts found. Try increasing the --hours range.")
        return

    # Step 2: Extract job listings from emails
    all_jobs = []
    for alert in alerts:
        jobs = extract_job_listings(alert["body"])
        all_jobs.extend(jobs)

    if not all_jobs:
        print("\n⚠️ Emails found but no job listings could be parsed.")
        print("   This may happen if LinkedIn changed their email format.")
        print("   Check core/fetcher.py → extract_job_listings() to update parsing.")
        return

    print(f"\n📋 Total job listings extracted: {len(all_jobs)}")

    # Step 3: Score jobs against resume
    scored = score_all_jobs(all_jobs)

    # Step 4: Save to log
    if save_log:
        save_to_log(scored)

    # Step 5: Render dashboard
    sync_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    dashboard = render_dashboard(scored, sync_time=sync_time)

    # Step 6: Output
    if output_file:
        with open(output_file, "w") as f:
            f.write(dashboard)
        print(f"\n✅ Dashboard saved to: {output_file}")
    else:
        print("\n" + dashboard)

    # Summary
    green = sum(1 for j in scored if j.get("rating") == "GREEN")
    yellow = sum(1 for j in scored if j.get("rating") == "YELLOW")
    red = sum(1 for j in scored if j.get("rating") == "RED")

    print("\n" + "=" * 60)
    print(f"✅ Sync Complete! 🟢 {green} High Match  🟡 {yellow} Needs Tweak  🔴 {red} Skip")
    print("=" * 60)

    return scored


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Career Ops Manager — Sync LinkedIn Job Alerts")
    parser.add_argument("--hours", type=int, default=24, help="How many hours back to search (default: 24)")
    parser.add_argument("--output", type=str, default=None, help="Save dashboard to a markdown file")
    parser.add_argument("--no-log", action="store_true", help="Don't save results to jobs log")
    args = parser.parse_args()

    sync_jobs(hours=args.hours, output_file=args.output, save_log=not args.no_log)
