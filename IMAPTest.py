import imaplib
import os

# GUC Server Settings
IMAP_SERVER = os.getenv("IMAP_SERVER", "mail.guc.edu.eg")
PORT = int(os.getenv("IMAP_PORT", "993"))

# Credentials (loaded from environment variables)
EMAIL = os.getenv("GUC_EMAIL", "your.email@student.guc.edu.eg")
PASSWORD = os.getenv("GUC_PASSWORD", "your_password_here")

try:
    print(f"Attempting to connect to {IMAP_SERVER} on port {PORT}...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, PORT)
    print("Connection established! Attempting login...")
    mail.login(EMAIL, PASSWORD)
    print("\n✅ SUCCESS: IMAP is open! The university allows direct email access.")
    mail.logout()
except imaplib.IMAP4.error as e:
    print(f"\n❌ LOGIN FAILED: The server is open, but rejected the credentials. Error: {e}")
except Exception as e:
    print(f"\n❌ CONNECTION FAILED: GUC is actively blocking IMAP traffic. Error: {e}")
