# 🚀 Career Ops Manager

An automated job alert scoring system that fetches LinkedIn Job Alert emails from Gmail and scores each role against your resume using Claude AI.

---

## 📁 Project Structure

```
career-ops/
├── auth/
│   └── gmail_auth.py        # Google OAuth2 authentication
├── core/
│   ├── fetcher.py           # Gmail fetcher & email parser
│   └── scorer.py            # Claude AI job scorer
├── utils/
│   └── dashboard.py         # Markdown dashboard renderer & job log
├── data/
│   └── jobs_log.json        # Auto-created: persistent job history
├── sync_jobs.py             # ✅ Main entry point — run this!
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup (One-Time)

### Step 1 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Create Google Cloud Project & Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., `career-ops`)
3. Go to **APIs & Services → Library**
4. Search for **Gmail API** → Click **Enable**

### Step 3 — Create OAuth2 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth Client ID**
3. Application type: **Desktop App**
4. Name it: `Career Ops Manager`
5. Click **Create** → **Download JSON**
6. Rename the downloaded file to `credentials.json`
7. Place it in the `auth/` folder:
   ```
   career-ops/auth/credentials.json
   ```

### Step 4 — Configure OAuth Consent Screen

1. Go to **APIs & Services → OAuth Consent Screen**
2. User Type: **External**
3. Fill in App Name (e.g., `Career Ops`) and your email
4. Add scope: `https://www.googleapis.com/auth/gmail.readonly`
5. Add your Gmail address as a **Test User**

---

## 🏃 Running the Sync

### Basic Sync (last 24 hours)
```bash
python sync_jobs.py
```

### Sync last 48 hours
```bash
python sync_jobs.py --hours 48
```

### Save dashboard to a Markdown file
```bash
python sync_jobs.py --output dashboard.md
```

### First Run
On first run, a browser window will open asking you to authorize Gmail access.
- Sign in with your Google account
- Click **Allow**
- Token is saved locally — you won't need to do this again

---

## 📊 Dashboard Output

```
🗂️ Saloni's Career Ops Dashboard
Last Synced: 2026-03-09 14:30  |  Jobs Found: 8

| # | Rating | Score | Job Title           | Company     | Location    | Verdict                        |
|---|--------|-------|---------------------|-------------|-------------|--------------------------------|
| 1 | 🟢     | 88/100 | Data Scientist     | Stripe      | New York    | Strong ML + Python match       |
| 2 | 🟢     | 82/100 | ML Engineer        | Databricks  | Remote      | Excellent stack alignment      |
| 3 | 🟡     | 65/100 | Analytics Engineer | Spotify     | New York    | Missing dbt, tweak recommended |
| 4 | 🔴     | 22/100 | Data Analyst       | HealthCorp  | Chicago     | Healthcare domain hard blocker |
```

For 🟢 roles, the dashboard also includes:
- ✅ Matching skills
- ⚠️ Gaps to address
- 💡 Specific resume tweak suggestion
- 📨 Ready-to-send recruiter outreach message

---

## 🔧 Customization

### Update Your Resume Profile
Edit `RESUME_PROFILE` in `core/scorer.py` as your experience grows.

### Change Job Preferences
Modify the rating guide in `SCORING_PROMPT` in `core/scorer.py`.

### Automate Daily Syncs (Optional)
Add a cron job to run automatically each morning:
```bash
# Run every day at 8 AM
0 8 * * * cd /path/to/career-ops && python sync_jobs.py --output dashboard.md
```

---

## 🛡️ Privacy & Security

- `credentials.json` and `token.pickle` are **never** committed to Git
- Gmail access is **read-only** — the app cannot send, delete, or modify emails
- All processing happens locally on your machine

Add to `.gitignore`:
```
auth/credentials.json
auth/token.pickle
data/jobs_log.json
```

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| `credentials.json not found` | Download from Google Cloud Console → place in `auth/` |
| `No job alerts found` | Check LinkedIn alert email settings; try `--hours 72` |
| `0 jobs parsed from email` | LinkedIn may have changed email format; check `fetcher.py` |
| `Token expired` | Delete `auth/token.pickle` and re-run to re-authenticate |
