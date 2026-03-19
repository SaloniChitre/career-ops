# 🚀 Career Ops Manager

An automated job lifecycle tracker that fetches emails from Gmail, detects job application statuses, scores each role against your resume using **Groq AI (Llama 3.3 70B)**, and displays everything in a **Streamlit dashboard** — organized by status and category.

---

## 📁 Project Structure

```
career-ops/
├── auth/
│   └── gmail_auth.py        # Google OAuth2 authentication
├── core/
│   ├── fetcher.py           # Gmail fetcher, email parser & status classifier
│   └── scorer.py            # Groq AI job scorer with category detection
├── utils/
│   └── dashboard.py         # Markdown dashboard renderer & job log
├── data/
│   └── jobs_log.json        # Auto-created: persistent job history
├── app.py                   # Streamlit dashboard UI
├── sync_jobs.py             # ✅ Main entry point — run this!
├── requirements.txt
└── README.md
```

---

## ✨ Features

- **Automatic Status Detection** — classifies emails as `ACCEPTED`, `APPLIED`, `IN_PROGRESS`, or `REJECTED` using keyword analysis
- **Dual Gmail Search** — fetches job alert emails from LinkedIn/Indeed + lifecycle emails (offer letters, rejections, confirmations) from any sender
- **AI Scoring** — scores each job against your resume using Groq (free, fast, Llama 3.3 70B)
- **Category Grouping** — organises jobs by role type: Data Science/ML, Analytics, Engineering, Marketing, etc.
- **90-Day Window** — syncs the last 90 days of emails by default
- **Streamlit Dashboard** — 4 tabs: Accepted, In Progress (Applied + Active), Alerts, Rejected

---

## ⚙️ Setup (One-Time)

### Step 1 — Install Dependencies
```bash
pip install -r requirements.txt
pip install streamlit anthropic python-dotenv pandas
```

### Step 2 — Create a `.env` file
```
GROQ_API_KEY=your_groq_api_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here   # optional fallback
```

Get a free Groq API key at [console.groq.com](https://console.groq.com)

### Step 3 — Create Google Cloud Project & Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., `career-ops`)
3. Go to **APIs & Services → Library**
4. Search for **Gmail API** → Click **Enable**

### Step 4 — Create OAuth2 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth Client ID**
3. Application type: **Web application**
4. Add `http://localhost:3000/` to **Authorized redirect URIs**
5. Click **Create** → **Download JSON**
6. Rename to `credentials.json` and place in `auth/`:
   ```
   career-ops/auth/credentials.json
   ```

### Step 5 — Configure OAuth Consent Screen

1. Go to **APIs & Services → OAuth Consent Screen**
2. User Type: **External**
3. Fill in App Name and your email
4. Add scope: `https://www.googleapis.com/auth/gmail.readonly`
5. Add your Gmail address as a **Test User**

---

## 🏃 Running

### Step 1 — Sync emails & score jobs (last 90 days)
```bash
python3 sync_jobs.py
```

### Step 2 — Launch the dashboard
```bash
streamlit run app.py
```
Then open [http://localhost:8501](http://localhost:8501)

### Custom time range
```bash
python3 sync_jobs.py --hours 48       # last 48 hours
python3 sync_jobs.py --hours 2160     # last 90 days (default)
```

### First Run
A browser window will open for Gmail OAuth2 login. Sign in and click **Allow**. Token is saved locally for future runs.

---

## 📊 Dashboard Tabs

| Tab | Shows |
|-----|-------|
| **Accepted 🏆** | Emails with job offers, selection confirmations |
| **In Progress 👀** | Applied confirmations + active recruiter contact |
| **Alerts 🔔** | New job listings from LinkedIn/Indeed alerts |
| **Rejected ❌** | Rejection emails |

Each tab groups jobs by category (Data Science/ML, Analytics, Engineering, Marketing, etc.) and shows AI match scores, skill gaps, and recruiter outreach messages for relevant roles.

---

## 🔧 Customization

### Update Resume Profile
Edit `RESUME_PROFILE` in `core/scorer.py` to match your current experience.

### Change Job Preferences
Modify the rating guide in `SCORING_PROMPT` in `core/scorer.py`.

### Automate Daily Syncs (Optional)
```bash
# Run every day at 8 AM
0 8 * * * cd /path/to/career-ops && python3 sync_jobs.py
```

---

## 🛡️ Privacy & Security

- `credentials.json`, `token.pickle`, and `.env` are **never** committed to Git
- Gmail access is **read-only** — the app cannot send, delete, or modify emails
- All AI processing happens via API calls — no data is stored externally

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| `credentials.json not found` | Download from Google Cloud Console → place in `auth/` |
| `redirect_uri_mismatch` | Add `http://localhost:3000/` to OAuth redirect URIs in Google Cloud Console |
| `No job alerts found` | Try `--hours 720` to search further back |
| `0 jobs parsed from email` | LinkedIn may have changed email format; check `fetcher.py` |
| `Token expired` | Delete `auth/token.pickle` and re-run to re-authenticate |
| `Groq 429 rate limit` | Reduce batch size or wait a minute and re-run |
