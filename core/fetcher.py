"""
Gmail Job Alert Fetcher
Fetches and parses LinkedIn Job Alert emails from the last N hours.
"""

import base64
import re
from datetime import datetime, timedelta
from typing import Optional
from auth.gmail_auth import get_gmail_service

# --- 1. DEFINE YOUR STATUS CLASSIFIER ---
def classify_email(subject, body):
    # Combine both to check for keywords anywhere
    text = (str(subject) + " " + str(body)).lower()
    
    # Order matters: check for terminal statuses first
    if any(word in text for word in ["offer", "congratulations", "onboarding"]):
        return "ACCEPTED"
    if any(word in text for word in ["not moving forward", "sorry", "unsuccessful", "decided to pursue"]):
        return "REJECTED"
    if any(word in text for word in ["viewed", "downloaded", "opened"]):
        return "IN_PROGRESS"
    if any(word in text for word in ["submitted", "application was sent", "received your application"]):
        return "APPLIED"
    
    return "ALERT" # Default for new job listings

def fetch_linkedin_job_alerts(hours: int = 24) -> list[dict]:
    """
    Fetches LinkedIn Job Alert emails from the last N hours.

    Args:
        hours: How many hours back to search (default: 24)

    Returns:
        List of parsed job alert dicts with raw email content
    """
    service = get_gmail_service()

    # Build Gmail search query
    after_date = (datetime.now() - timedelta(hours=hours)).strftime("%Y/%m/%d")
    # Broader, more accurate query
    # Expanded query to catch lifecycle updates
    keywords = '("submitted" OR "application was sent" OR "viewed" OR "downloaded" OR "offer" OR "moving forward" OR "sorry" OR "unsuccessful")'
    query = f'{keywords} after:{after_date}'

    print(f"\n🔍 Searching Gmail: '{query}'")

    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=20
    ).execute()

    messages = results.get("messages", [])

    if not messages:
        print("📭 No LinkedIn Job Alert emails found in the last 24 hours.")
        return []

    print(f"📬 Found {len(messages)} job alert email(s). Parsing...")

    job_alerts = []
    for msg_meta in messages:
        msg = service.users().messages().get(
            userId="me",
            id=msg_meta["id"],
            format="full"
        ).execute()

        parsed = _parse_email(msg)
        if parsed:
            job_alerts.append(parsed)

    print(f"✅ Successfully parsed {len(job_alerts)} email(s).")
    return job_alerts


def _parse_email(msg: dict) -> Optional[dict]:
    """
    Extracts subject, date, and body text from a Gmail message object.
    """
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    subject = headers.get("Subject", "No Subject")
    date = headers.get("Date", "Unknown Date")

    body = _extract_body(msg["payload"])

    return {
        "id": msg["id"],
        "subject": subject,
        "date": date,
        "body": body,
        "raw": msg
    }


def _extract_body(payload: dict) -> str:
    """
    Recursively extracts plain text or HTML body from Gmail payload.
    """
    body_text = ""

    if "parts" in payload:
        for part in payload["parts"]:
            body_text += _extract_body(part)
    else:
        mime_type = payload.get("mimeType", "")
        data = payload.get("body", {}).get("data", "")
        if data and mime_type in ("text/plain", "text/html"):
            decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
            # Strip HTML tags for plain text
            if mime_type == "text/html":
                decoded = re.sub(r'<[^>]+>', ' ', decoded)
                decoded = re.sub(r'\s+', ' ', decoded).strip()
            body_text += decoded

    return body_text


def extract_job_listings(email_body: str) -> list[dict]:
    jobs = []
    
    # 1. NEW: Check for Forwarded Application emails first
    if "Your application was sent to" in email_body:
        # Regex to capture company name after "sent to"
        app_match = re.search(r'Your application was sent to\s+(.+?)(?:\n|$)', email_body)
        if app_match:
            jobs.append({
                "title": "Applied Role", 
                "company": app_match.group(1).strip(),
                "location": "N/A",
                "url": None,
                "status": "Submitted"  # Automatically marks it as Submitted!
            })
            return jobs # Return immediately if we found an application email

    # 2. Existing logic for regular Job Alerts
    job_blocks = re.split(r'\n{2,}', email_body)
    for block in job_blocks:
        block = block.strip()
        if not block: continue
        at_match = re.search(r'^(.+?)\s+at\s+(.+?)(?:\n|·|•|$)', block, re.IGNORECASE)
        if at_match:
            jobs.append({
                "title": at_match.group(1).strip(),
                "company": at_match.group(2).strip(),
                "location": "Not specified",
                "url": None,
                "status": "Saved"
            })
    return jobs

def classify_email_subject(subject):
    subject = subject.lower()
    if "application was sent" in subject:
        return "Submitted"
    elif "interview" in subject:
        return "In-Progress"
    elif "update" in subject or "status" in subject:
        return "Response Received"
    return "Saved"


if __name__ == "__main__":
    alerts = fetch_linkedin_job_alerts(hours=24)
    for alert in alerts:
        print(f"\n📧 Subject: {alert['subject']}")
        jobs = extract_job_listings(alert["body"])
        print(f"   Found {len(jobs)} job listing(s)")
        for job in jobs:
            print(f"   → {job['title']} at {job['company']} | {job['location']}")
