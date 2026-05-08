import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheets_service():
    private_key = os.environ.get("GOOGLE_PRIVATE_KEY", "")
    private_key = private_key.replace("\\n", "\n")
    
    creds_dict = {
        "type": os.environ.get("GOOGLE_TYPE", "service_account"),
        "project_id": os.environ.get("GOOGLE_PROJECT_ID"),
        "private_key_id": os.environ.get("GOOGLE_PRIVATE_KEY_ID"),
        "private_key": private_key,
        "client_email": os.environ.get("GOOGLE_CLIENT_EMAIL"),
        "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/finanzas-bot%40finanzas-bot-495615.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }
    
    creds = service_account.Credentials.from
