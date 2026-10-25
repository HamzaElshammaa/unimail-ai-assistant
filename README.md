<div align="center">

# UniMail AI Assistant 📬🤖

### **Headless University Email Fetcher, LLM Deadline Extractor & n8n Automation Pipeline**

[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Google Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-Structured_JSON-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![n8n](https://img.shields.io/badge/n8n-Workflow_Automation-EA4B71?style=for-the-badge&logo=n8n&logoColor=white)](https://n8n.io/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Instant_Alerts-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)

*An automated, zero-friction academic assistant engineered to bypass restrictive legacy Exchange firewalls, parse vague university announcements into structured JSON via LLMs, and dispatch actionable alerts to Telegram and Google Calendar.*

</div>

---

## 🏗️ Pipeline Architecture

```text
┌───────────────────────────┐
│  Scheduled Python Worker  │
└─────────────┬─────────────┘
              │ 1. EWS / OWA Fetch (Custom TLS Adapter + iOS User-Agent Spoof)
              ▼
┌───────────────────────────┐
│  Legacy Exchange Server   │
│  (mail.guc.edu.eg/EWS)    │
└─────────────┬─────────────┘
              │ 2. Raw Unread Email Subject & Body
              ▼
┌───────────────────────────┐
│  LLM Extraction Engine    │
│  (Gemini 2.5 Flash JSON)  │
└─────────────┬─────────────┘
              │ 3. Structured JSON (course_code, event_type, ISO date, urgency)
              ▼
┌───────────────────────────┐       ┌───────────────────────────┐
│   n8n Webhook Workflow    │──────▶│   Telegram Bot Instant    │
│     (`Phase2.json`)       │       │   Urgency Notification    │
└─────────────┬─────────────┘       └───────────────────────────┘
              │
              ▼
┌───────────────────────────┐
│   Google Calendar Event   │
│   (Quizzes & Deadlines)   │
└───────────────────────────┘
```

---

## ✨ Key Engineering Highlights

### 1. Legacy Exchange Firewall & TLS Handshake Navigation
University Exchange servers often block standard IMAP (`port 993`) and reject modern Python TLS handshakes (`10054 ConnectionResetError`). UniMail implements two resilient ingestion strategies:
- **Exchange Web Services (`n8n_email_pusher.py`, `mvp_test.py`):** Uses `exchangelib` paired with `NoVerifyHTTPAdapter` and whitelisted `AppleExchangeWebServices/815.120` User-Agent headers.
- **Reverse-Engineered OWA Session Scraper (`ReverseEngineeredEmailPusher.py`):** Authenticates against `/owa/auth.owa`, extracts the `X-OWA-CANARY` CSRF token, parses unread message rows via BeautifulSoup, and marks processed items as read (`hidcmdpst=mr`) to guarantee idempotency.

### 2. Schema-Enforced LLM Parsing
Converts unstructured academic emails into strict JSON payloads:
```json
{
  "course_code": "CSEN1001",
  "event_type": "Quiz",
  "date": "2026-10-28T10:00:00Z",
  "action_required": "Prepare Lecture 1-3 material for Quiz 1 in Hall C1.",
  "urgency": "High"
}
```

### 3. Self-Hosted n8n Automation Workflow (`Phase2.json`)
Importable n8n workflow that receives webhook payloads, filters by urgency (`High` / `Medium`), formats HTML notifications for Telegram, and creates deadline events in Google Calendar.

---

## 🚀 Getting Started

### 1. Configure Environment (`.env`)
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

### 2. Install Dependencies & Run
```bash
pip install exchangelib requests beautifulsoup4 google-generativeai openai

# Run standalone MVP (EWS -> Gemini -> Telegram)
python mvp_test.py

# Or run the OWA -> n8n webhook pusher
python ReverseEngineeredEmailPusher.py
```
