import urllib3
import requests
import json
import os
from pathlib import Path
from openai import OpenAI
import google.generativeai as genai
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
# GUC Settings
GUC_EMAIL = os.getenv("GUC_EMAIL")
GUC_PASSWORD = os.getenv("GUC_PASSWORD")
EWS_ENDPOINT = os.getenv("EWS_ENDPOINT", "https://mail.guc.edu.eg/EWS/Exchange.asmx")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
Gemini_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

required_values = {
    "GUC_EMAIL": GUC_EMAIL,
    "GUC_PASSWORD": GUC_PASSWORD,
    "GEMINI_API_KEY": Gemini_API_KEY,
    "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
    "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
}
missing_keys = [key for key, value in required_values.items() if not value]
if missing_keys:
    raise ValueError(f"Missing required .env values: {', '.join(missing_keys)}")

# --- 2. EWS FIREWALL BYPASSES ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
BaseProtocol.HTTP_ADAPTER_CLS = NoVerifyHTTPAdapter
BaseProtocol.USERAGENT = 'AppleExchangeWebServices/815.120'

# Initialize OpenAI Client
""" client = OpenAI(api_key=OPENAI_API_KEY) """

# Initialize Gemini Client
genai.configure(api_key=Gemini_API_KEY)
# Enforce JSON output directly in the model config
model = genai.GenerativeModel('gemini-2.5-flash', generation_config={
    "response_mime_type": "application/json"
})


def send_telegram_message(text):
    """Sends a message to your Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    response = requests.post(url, json=payload)
    print(f"Telegram response: {response.status_code} - {response.text}")

print("Connecting to GUC...")
try:
    # --- 3. FETCH THE EMAIL ---
    credentials = Credentials(GUC_EMAIL, GUC_PASSWORD)
    config = Configuration(service_endpoint=EWS_ENDPOINT, credentials=credentials)
    account = Account(primary_smtp_address=GUC_EMAIL, config=config, autodiscover=False, access_type=DELEGATE)
    
    # Grab just the single newest email for the test
    latest_email = list(account.inbox.all().order_by('-datetime_received')[:1])[0]
    raw_text = f"Subject: {latest_email.subject}\nBody: {latest_email.text_body}"
    print(f"✅ Fetched email: {latest_email.subject}")

    # --- 4. THE AI BRAIN ---
    print("🧠 Passing to LLM for extraction...")
    prompt = f"""
    You are an academic assistant. Extract the core details from this university email.
    Output ONLY a valid JSON object matching this schema:
    {{"course_code": "...", "event_type": "...", "date": "...", "action_required": "...", "urgency": "High/Medium/Low"}}
    
    Email content:
    {raw_text[:1500]} 
    """ # Capping at 1500 chars to save tokens

    response = model.generate_content(prompt)
    extracted_data = json.loads(response.text)
    print("✅ AI Extraction Complete:", extracted_data)
    
    # --- 5. THE NOTIFICATION ---
    print("📱 Sending to Telegram...")
    notification_text = (
        f"🚨 <b>{extracted_data.get('course_code', 'Unknown Course')}</b>\n"
        f"<b>Type:</b> {extracted_data.get('event_type', 'Update')}\n"
        f"<b>Due:</b> {extracted_data.get('date', 'No date specified')}\n"
        f"<b>Action:</b> {extracted_data.get('action_required', 'None')}"
    )
    
    send_telegram_message(notification_text)
    print("✅ MVP Complete! Check your phone.")

except Exception as e:
    print(f"❌ ERROR: {e}")