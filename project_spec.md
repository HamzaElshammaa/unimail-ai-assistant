# Project Specification: UniMail AI Assistant (Headless)

## 1. Project Overview
A headless, automated pipeline designed to bypass a university's restricted legacy Exchange firewall. The system fetches unread automated emails (which have vague, generic subject lines), processes them through a Large Language Model (LLM) to extract actionable data, and routes the clean data to a Telegram bot for immediate notification and to Google Calendar for deadline tracking.

**Target User:** Personal use (Headless UI).
**Primary Goal:** Zero-friction academic tracking. Never miss a quiz, tutorial task, or assignment deadline due to cluttered, poorly formatted university emails.

## 2. Architecture & Data Flow
1. **Cron/Scheduler:** A local Windows task or simple Python loop runs every 15-30 minutes.
2. **Data Fetching (Python):** Connects to `mail.guc.edu.eg/EWS/Exchange.asmx` using the `exchangelib` library, bypassing firewall restrictions using specific User-Agent spoofing.
3. **AI Parsing (Python/LLM):** Passes the raw `item.subject` and `item.text_body` to an LLM (e.g., OpenAI `gpt-4o-mini` or Gemini) via API.
4. **Routing (n8n):** Python script sends the clean JSON output via an HTTP POST request to an n8n Webhook.
5. **Action (n8n Nodes):**
   - If "Urgency" is Medium/High or an action is required: n8n triggers the **Telegram Bot API** to send a clean summary message.
   - If a valid "Date/Time" is present: n8n triggers the **Google Calendar API** to create an event.

## 3. Tech Stack
* **Language:** Python 3.13
* **Mail Protocol API:** `exchangelib` (connecting via EWS, as standard IMAP/SMTP port 993 is blocked).
* **AI Provider:** OpenAI API or Google Gemini API.
* **Automation Engine:** n8n (Self-hosted or Cloud).
* **Outputs:** Telegram Bot API, Google Calendar.

## 4. Crucial Technical Context & Bypasses (DO NOT MODIFY)
The university firewall actively blocks modern Python requests and strict TLS handshakes, resulting in `10054 ConnectionResetError` or `11001 NameResolutionError`. 
**The Python EWS script MUST include the following bypasses to function:**

```python
import urllib3
from exchangelib.protocol import BaseProtocol, NoVerifyHTTPAdapter

# 1. Suppress insecure warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 2. Downgrade TLS strictness for vintage Exchange server
BaseProtocol.HTTP_ADAPTER_CLS = NoVerifyHTTPAdapter

# 3. Spoof iOS device to bypass WAF bot-blocking
BaseProtocol.USERAGENT = 'AppleExchangeWebServices/815.120'

The LLM must strictly output a JSON object matching this schema:
{
  "course_code": "String (e.g., CSEN1001, HUMA 1001)",
  "event_type": "String (Quiz, Assignment, Tutorial, Announcement, Other)",
  "date": "ISO 8601 Date String or null (Parse relative dates like 'this Wednesday' to actual dates if context allows)",
  "action_required": "String (1-2 sentence summary of what the student must do)",
  "urgency": "String (High, Medium, Low)"
}