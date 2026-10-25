import urllib3
import requests
import os
from pathlib import Path
import json
from exchangelib import Credentials, Account, Configuration, DELEGATE
from exchangelib.protocol import BaseProtocol, NoVerifyHTTPAdapter


def load_dotenv(dotenv_path: str = ".env"):
    """Minimal .env loader to avoid adding external dependencies."""
    env_file = Path(dotenv_path)
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv()

# --- 1. CONFIGURATION ---
GUC_EMAIL = os.getenv("GUC_EMAIL")
GUC_PASSWORD = os.getenv("GUC_PASSWORD")
EWS_ENDPOINT = os.getenv("EWS_ENDPOINT", "https://mail.guc.edu.eg/EWS/Exchange.asmx")

# Paste your n8n TEST Webhook URL here
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

required_values = {
    "GUC_EMAIL": GUC_EMAIL,
    "GUC_PASSWORD": GUC_PASSWORD,
    "N8N_WEBHOOK_URL": N8N_WEBHOOK_URL,
}
missing_keys = [key for key, value in required_values.items() if not value]
if missing_keys:
    raise ValueError(f"Missing required .env values: {', '.join(missing_keys)}")

# --- 2. EWS FIREWALL BYPASSES ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
BaseProtocol.HTTP_ADAPTER_CLS = NoVerifyHTTPAdapter
BaseProtocol.USERAGENT = 'AppleExchangeWebServices/815.120'

print("Connecting to GUC...")
try:
    # --- 3. FETCH THE EMAILS ---
    credentials = Credentials(GUC_EMAIL, GUC_PASSWORD)
    config = Configuration(service_endpoint=EWS_ENDPOINT, credentials=credentials)
    account = Account(primary_smtp_address=GUC_EMAIL, config=config, autodiscover=False, access_type=DELEGATE)
    
    # Grab the 3 most recent emails to send to n8n
    recent_emails = account.inbox.all().order_by('-datetime_received')[:3]
    
    email_payload = []
    for item in recent_emails:
        email_payload.append({
            "message_id": item.message_id, 
            "subject": item.subject,
            "body": str(item.text_body)[:1500].replace('\n', ' ').strip(),
            "received_date": str(item.datetime_received)
        })
    
    print(f"✅ Fetched {len(email_payload)} emails. Sending to n8n...")

    # --- 4. POST TO N8N ---
    headers = {'Content-Type': 'application/json'}
    response = requests.post(N8N_WEBHOOK_URL, json=email_payload, headers=headers)
    
    if response.status_code == 200:
        print("🚀 SUCCESS! Data delivered to n8n.")
    else:
        print(f"⚠️ Failed to send. n8n responded with: {response.status_code} - {response.text}")

except Exception as e:
    print(f"❌ ERROR: {e}")