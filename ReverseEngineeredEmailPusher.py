import requests
import os
from pathlib import Path
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup

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

# ── CONFIG ──────────────────────────────────────────────────────────────────
USERNAME    = os.getenv("GUC_EMAIL")
PASSWORD    = os.getenv("GUC_PASSWORD")
N8N_WEBHOOK = os.getenv("N8N_WEBHOOK_URL")

OWA_BASE   = os.getenv("OWA_BASE", "https://mail.guc.edu.eg")
LOGIN_PAGE = f"{OWA_BASE}/owa/auth/logon.aspx"
LOGIN_POST = f"{OWA_BASE}/owa/auth.owa"
INBOX_URL  = f"{OWA_BASE}/owa/"

# Exact User-Agent from Unimail app — likely whitelisted by GUC
HEADERS = {
    "User-Agent":      "UniMail/2 CFNetwork/3860.100.1 Darwin/25.0.0",
    "Accept":          "*/*",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}
# ────────────────────────────────────────────────────────────────────────────



def login():
    session = requests.Session()
    session.headers.update(HEADERS)

    print("Fetching login page...")
    session.get(LOGIN_PAGE, timeout=30)

    print("Logging in...")
    payload = {
        "destination":    INBOX_URL,
        "flags":          "4",
        "forcedownlevel": "0",
        "username":       USERNAME,
        "password":       PASSWORD,
        "passwordText":   "",
        "isUtf8":         "1",
    }
    r = session.post(
        LOGIN_POST,
        data=payload,
        headers={
            **HEADERS,
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin":       OWA_BASE,
            "Referer":      LOGIN_PAGE,
        },
        allow_redirects=True,
        timeout=30,
    )

    if r.status_code == 500 or "errorfe.aspx" in r.url:
        raise Exception("❌ Server error — too many sessions. Wait 5 mins and retry.")
    if "logon.aspx" in r.url:
        raise Exception("❌ Login failed — check credentials")

    r.raise_for_status()

    # Try cookie first, then fall back to hidden input in HTML
    canary = session.cookies.get("X-OWA-CANARY", "")
    if not canary:
        soup = BeautifulSoup(r.text, "html.parser")
        canary_input = soup.find("input", {"name": "X-OWA-CANARY"})
        if canary_input:
            canary = canary_input.get("value", "")

    if not canary:
        raise Exception("❌ Could not get X-OWA-CANARY token")

    print(f"✅ Logged in! Canary token acquired.")
    return session, canary



def fetch_email_list(session, canary):
    """Just GET the inbox directly after login"""
    print("Fetching inbox...")
    r = session.get(
        f"{OWA_BASE}/owa/",
        headers={
            **HEADERS,
            "X-OWA-CANARY": canary,
        },
        timeout=30,
    )
    r.raise_for_status()
    
    # Save for inspection
    with open("inbox_debug.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print(f"📄 Saved inbox HTML ({len(r.text)} bytes)")
    return r.text


#def parse_email_list(html):
    """Extract email IDs and subjects from OWA inbox HTML"""
    soup = BeautifulSoup(html, "html.parser")
    emails = []

    # OWA renders email rows with data attributes containing the item ID
    for row in soup.select("[data-itemid]"):
        item_id = row.get("data-itemid", "")
        subject_el = row.select_one(".subject, [data-subject]")
        is_read = "read" in row.get("class", [])

        if item_id and not is_read:
            emails.append({
                "id":      item_id,
                "subject": subject_el.get_text(strip=True) if subject_el else "(no subject)",
            })

    return emails


#def parse_email_list(html):
    """Debug version - dump HTML to file so we can inspect it"""
    with open("inbox_debug.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"📄 Inbox HTML saved to inbox_debug.html ({len(html)} bytes)")
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Try multiple selector strategies and report what we find
    print(f"  [data-itemid] elements: {len(soup.select('[data-itemid]'))}")
    print(f"  [data-convid] elements: {len(soup.select('[data-convid]'))}")
    print(f"  tr elements: {len(soup.select('tr'))}")
    print(f"  div.lvw elements: {len(soup.select('div.lvw'))}")
    print(f"  All divs with 'item' in class: {len([d for d in soup.find_all('div') if any('item' in c.lower() for c in d.get('class', []))])}")
    
    return []

def parse_email_list(html):
    soup = BeautifulSoup(html, "html.parser")
    emails = []

    # Find all email rows — unread ones have font-weight:bold style
    rows = soup.select("tr")
    
    for row in rows:
        # Check if it has a chkmsg checkbox (email row)
        checkbox = row.find("input", {"name": "chkmsg"})
        if not checkbox:
            continue

        item_id = checkbox.get("value", "")
        if not item_id:
            continue

        # Check if unread — unread rows have msg-unrd.png icon
        is_unread = bool(row.find("img", src=lambda s: s and "msg-unrd" in s))
        if not is_unread:
            continue

        # Extract subject from h1 > a
        subject_el = row.select_one("h1 a")
        subject = subject_el.get_text(strip=True) if subject_el else "(no subject)"

        # Extract sender — first td with nowrap that has text (before subject td)
        tds = row.find_all("td", attrs={"nowrap": True})
        sender = ""
        for td in tds:
            text = td.get_text(strip=True)
            if text and not td.find("input") and not td.find("img") and not td.find("h1"):
                sender = text
                break

        # Extract received date — td with class "sc"
        date_td = row.select_one("td.sc")
        received = date_td.get_text(strip=True) if date_td else ""

        emails.append({
            "id":       item_id,
            "subject":  subject,
            "sender":   sender,
            "received": received,
        })

    print(f"📬 Found {len(emails)} unread email(s)")
    return emails


def fetch_email_body(session, canary, item_id):
    """Fetch individual email body using the exact GET Unimail uses"""
    r = session.get(
        f"{OWA_BASE}/owa/",
        params={
            "ae": "Item",
            "t":  "IPM.Note",
            "id": item_id,
        },
        headers={
            **HEADERS,
            "X-OWA-CANARY": canary,
            "Referer":      INBOX_URL,
        },
        timeout=30,
    )
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    # Extract subject
    subject = ""
    subj_el = soup.select_one("h1, .subject, [data-subject]")
    if subj_el:
        subject = subj_el.get_text(strip=True)

    # Extract sender
    sender = ""
    from_el = soup.select_one(".from, [data-sender]")
    if from_el:
        sender = from_el.get_text(strip=True)

    # Extract body text
    body = ""
    body_el = soup.select_one(".readingPaneContent, #divBodyCell, .message-body, [data-body]")
    if body_el:
        body = body_el.get_text(separator="\n", strip=True)
    else:
        # Fallback: get all text from body tag
        body_tag = soup.find("body")
        if body_tag:
            body = body_tag.get_text(separator="\n", strip=True)[:3000]

    return subject, sender, body


def mark_as_read(session, canary, item_id):
    """Mark email as read to prevent duplicate processing"""
    payload = {
        "hidpnst":    "",
        "hidactbrfld": "",
        "hidcmdpst":  "mr",  # mr = mark read
        "hidcid":     item_id,
        "hidso":      "1",
        "hidpid":     "MessageView",
        "hidcanary":  canary,
    }
    session.post(
        f"{OWA_BASE}/owa/?pg=1",
        data=payload,
        headers={
            **HEADERS,
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "X-OWA-CANARY": canary,
        },
        timeout=30,
    )


def post_to_n8n(email_data):
    r = requests.post(N8N_WEBHOOK, json=email_data, timeout=30)
    print(f"  → n8n: {email_data['subject'][:50]} [{r.status_code}]")
    return r.status_code == 200


def main():
    print(f"\n{'='*50}")
    print(f"UniMail OWA Fetcher — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    try:
        session, canary = login()

        # Fetch inbox list
        inbox_html = fetch_email_list(session, canary)
        unread = parse_email_list(inbox_html)
        print(f"📬 Found {len(unread)} unread email(s)")

        if not unread:
            print("✅ No unread emails.")
            return

        for email in unread:
            print(f"\n📧 Processing: {email['subject'][:60]}")

            # Fetch full body
            subject, sender, body = fetch_email_body(session, canary, email["id"])

            payload = {
                "message_id":    email["id"],
                "subject":       subject or email["subject"],
                "body":          body,
                "sender":        sender,
                "received_date": datetime.utcnow().isoformat() + "Z",
            }

            # POST to n8n then mark as read
            if post_to_n8n(payload):
                mark_as_read(session, canary, email["id"])
                print(f"  ✅ Sent and marked as read")
            else:
                print(f"  ⚠️ n8n POST failed — not marking as read")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        raise


if __name__ == "__main__":
    main()