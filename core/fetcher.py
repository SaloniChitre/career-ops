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
    text = (str(subject) + " " + str(body)).lower()

    # ACCEPTED — must have job-specific offer/selection language
    if any(phrase in text for phrase in [
        "offer of employment", "job offer", "offer letter",
        "you have been selected for the position",
        "we are pleased to offer you",
        "pleased to extend", "we'd like to offer you the position",
        "welcome to the team", "you've been hired", "you have been hired",
        "we are happy to offer", "confirm your joining",
        "selected for the role", "selected for this position"
    ]):
        return "ACCEPTED"

    # REJECTED — must be job-specific
    if any(phrase in text for phrase in [
        "not moving forward with your application",
        "decided to pursue other candidates",
        "will not be moving forward",
        "not selected for this position",
        "your application was not successful",
        "regret to inform you", "we won't be moving forward",
        "after careful consideration", "position has been filled"
    ]):
        return "REJECTED"

    # IN_PROGRESS — recruiter/employer activity
    if any(phrase in text for phrase in [
        "viewed your profile", "downloaded your resume", "opened your application",
        "schedule an interview", "invite you to interview",
        "next steps in your application", "hiring manager would like",
        "shortlisted for", "phone screen", "coding challenge",
        "technical assessment", "we'd like to move forward with you"
    ]):
        return "IN_PROGRESS"

    # APPLIED — confirmed submission
    if any(phrase in text for phrase in [
        "application was sent", "received your application",
        "successfully applied", "thank you for applying to",
        "thanks for applying to", "your application to",
        "your application for the", "we have received your application"
    ]):
        return "APPLIED"

    return "ALERT"

def fetch_linkedin_job_alerts(hours: int = 24) -> list[dict]:
    """
    Fetches LinkedIn Job Alert emails from the last N hours.

    Args:
        hours: How many hours back to search (default: 24)

    Returns:
        List of parsed job alert dicts with raw email content
    """
    service = get_gmail_service()
    after_date = (datetime.now() - timedelta(hours=hours)).strftime("%Y/%m/%d")

    # Query 1: New job alert listings — restricted to job platforms
    platform_senders = '(from:linkedin.com OR from:indeed.com OR from:glassdoor.com OR from:lever.co OR from:greenhouse.io OR from:workday.com OR from:icims.com OR from:myworkdayjobs.com OR from:jobvite.com OR from:smartrecruiters.com)'
    alert_query = f'{platform_senders} ("job alert" OR "new jobs" OR "jobs matching") after:{after_date}'

    # Query 2: Lifecycle emails — from ANY sender (direct employer emails)
    lifecycle_keywords = '("offer of employment" OR "offer letter" OR "job offer" OR "you have been selected for the position" OR "pleased to offer you" OR "confirm your joining" OR "thank you for applying to" OR "your application to" OR "application was sent to" OR "your application was sent" OR "we have received your application" OR "schedule an interview" OR "invite you to interview" OR "regret to inform you" OR "not moving forward with your application" OR "decided to pursue other candidates" OR "viewed your profile" OR "downloaded your resume")'
    lifecycle_query = f'{lifecycle_keywords} after:{after_date}'

    all_message_ids = set()
    all_messages = []

    for query_label, query in [("alerts", alert_query), ("lifecycle", lifecycle_query)]:
        print(f"\n🔍 Searching Gmail [{query_label}]: '{query}'")
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=20
        ).execute()
        msgs = results.get("messages", [])
        print(f"   → Found {len(msgs)} email(s)")
        for m in msgs:
            if m["id"] not in all_message_ids:
                all_message_ids.add(m["id"])
                all_messages.append(m)

    if not all_messages:
        print(f"📭 No job emails found in the last {hours} hours.")
        return []

    print(f"\n📬 Fetching {len(all_messages)} unique email(s)...")
    job_alerts = []
    for msg_meta in all_messages:
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

    status = classify_email(subject, body)

    return {
        "id": msg["id"],
        "subject": subject,
        "date": date,
        "body": body,
        "status": status,
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


def extract_job_listings(email_body: str, email_status: str = "ALERT", email_subject: str = "") -> list[dict]:
    jobs = []

    # 1. LinkedIn "Your application was sent to [Company]" emails
    if "Your application was sent to" in email_body or "application was sent to" in email_body.lower():
        company_match = re.search(r'[Yy]our application was sent to\s+(.+?)(?:\n|$)', email_body)
        if company_match:
            company = company_match.group(1).strip()
            # The job title appears on the next non-empty line after the company name
            title = "Applied Role"
            lines = email_body.splitlines()
            for idx, line in enumerate(lines):
                if company in line:
                    # Look forward for job title (first non-empty line after company)
                    for next_line in lines[idx + 1:idx + 5]:
                        candidate = next_line.strip()
                        if candidate and len(candidate) > 3 and not any(
                            skip in candidate.lower() for skip in
                            ["applied on", "easy apply", "view job", "http", "new york", "on-site", "remote", "hybrid"]
                        ):
                            title = candidate
                            break
                    break
            # Also try subject: "[Name], your application was sent to [Company]"
            subj_match = re.search(r'application was sent to (.+?)(?:\s*$)', email_subject, re.IGNORECASE)
            if subj_match and company == "Applied Role":
                company = subj_match.group(1).strip()
            jobs.append({
                "title": title,
                "company": company,
                "location": "N/A",
                "url": None,
                "raw_block": f"{title} {company}",
                "status": email_status
            })
            return jobs

    # 2. LinkedIn email format:
    #    Title\nCompany\nLocation\nApply with...\nView job: <url>
    # Find all "View job:" URLs first, then extract the block above each
    lines = email_body.splitlines()
    skip_phrases = {"apply with resume & profile", "apply now", "new jobs match your preferences.",
                    "your job alert", "fast growing", "actively recruiting", "promoted", ""}

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.lower().startswith("view job:"):
            url_match = re.search(r'https?://\S+', line)
            url = url_match.group(0) if url_match else None
            # Look back for title, company, location in the preceding lines
            title, company, location = None, None, None
            for j in range(i - 1, max(i - 6, -1), -1):
                prev = lines[j].strip()
                if not prev or prev.lower() in skip_phrases:
                    continue
                if location is None:
                    location = prev
                elif company is None:
                    company = prev
                elif title is None:
                    title = prev
                    break
            if title and company:
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location or "Not specified",
                    "url": url,
                    "raw_block": f"{title} {company} {location or ''}",
                    "status": email_status
                })
        i += 1

    # 3. Lifecycle fallback — for ACCEPTED/REJECTED/APPLIED/IN_PROGRESS emails
    #    that have no "View job:" links (e.g. direct employer emails)
    if not jobs and email_status in ("ACCEPTED", "REJECTED", "APPLIED", "IN_PROGRESS"):
        title, company = "Unknown Role", "Unknown Company"
        subj = email_subject.strip()
        body = email_body

        patterns = [
            # "Your application to [TITLE] at [COMPANY]"
            (r'[Yy]our application to (.+?) at (.+?)(?:\s*[-|,]|\s*$)', 'title_company'),
            # "Update on your application for [TITLE] job/position"
            (r'[Uu]pdate on your application for (.+?)(?:\s+job|\s+position|\s*$)', 'title_only'),
            # "Thank you for applying to [COMPANY]"
            (r'[Tt]hank(?:s)? for applying to (.+?)(?:[!,]|\s*$)', 'company_only'),
            # "Thank you for your interest in [COMPANY]"
            (r'[Tt]hank(?:s)? for your interest in (.+?)(?:[!,]|\s*$)', 'company_only'),
            # "Offer from [COMPANY]" / "RE: Offer from [COMPANY]"
            (r'[Oo]ffer from (.+?)(?:,|\s*$)', 'company_only'),
            # "Next Step: Continue your application for the [TITLE] position"
            (r'application for the (.+?) position', 'title_only'),
            # "[COMPANY] Application Update"
            (r'^(.+?)\s+[Aa]pplication [Uu]pdate', 'company_only'),
            # "RE: Offer - [COMPANY]" or "Offer - [COMPANY]"
            (r'[Oo]ffer\s*[-–]\s*(.+?)(?:\s*$)', 'company_only'),
        ]

        for pattern, mode in patterns:
            m = re.search(pattern, subj)
            if m:
                if mode == 'title_company':
                    title, company = m.group(1).strip(), m.group(2).strip()
                elif mode == 'company_only':
                    company = m.group(1).strip()
                elif mode == 'title_only':
                    title = m.group(1).strip()
                break

        # Try to extract title from body if still unknown
        if title == "Unknown Role":
            m = re.search(r'(?:position of|role of|position:)\s+([^\n.]+)', body, re.IGNORECASE)
            if m:
                title = m.group(1).strip()[:80]

        jobs.append({
            "title": title,
            "company": company,
            "location": "N/A",
            "url": None,
            "raw_block": f"{title} {company}",
            "status": email_status
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
