"""
Gmail OAuth2 Authentication
Handles Google OAuth2 flow and token management for Gmail API access.
"""

import os
import json
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes needed - read-only is sufficient for fetching job alert emails
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

TOKEN_PATH = Path(__file__).parent / "token.pickle"
CREDENTIALS_PATH = Path(__file__).parent / "credentials.json"


def get_gmail_service():
    """
    Authenticates and returns an authorized Gmail API service instance.
    
    First run: Opens browser for OAuth2 consent and saves token.
    Subsequent runs: Loads saved token (refreshes if expired).
    
    Returns:
        googleapiclient.discovery.Resource: Authorized Gmail API service
    """
    creds = None

    # Load existing token if available
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as token_file:
            creds = pickle.load(token_file)

    # Refresh or re-authenticate if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("🔐 Opening browser for Google OAuth2 login...")
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"credentials.json not found at {CREDENTIALS_PATH}\n"
                    "Please download it from Google Cloud Console and place it in the auth/ folder."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=3000)

        # Save token for next run
        with open(TOKEN_PATH, "wb") as token_file:
            pickle.dump(creds, token_file)
        print("✅ Token saved successfully.")

    service = build("gmail", "v1", credentials=creds)
    print("✅ Gmail service authenticated.")
    return service


if __name__ == "__main__":
    # Quick test
    service = get_gmail_service()
    profile = service.users().getProfile(userId="me").execute()
    print(f"✅ Connected as: {profile['emailAddress']}")
