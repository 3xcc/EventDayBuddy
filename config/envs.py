import os
from config.logger import log_and_raise

# ===== Database =====
DB_URL = os.getenv("DB_URL")
if not DB_URL:
    log_and_raise("Env", "loading DB_URL", Exception("DB_URL is not set"))

# ===== Telegram Bot =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    log_and_raise("Env", "loading TELEGRAM_TOKEN", Exception("TELEGRAM_TOKEN is not set"))

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
if not ADMIN_CHAT_ID:
    log_and_raise("Env", "loading ADMIN_CHAT_ID", Exception("ADMIN_CHAT_ID is not set"))

# ===== Google Sheets =====
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
if not GOOGLE_SHEET_ID:
    log_and_raise("Env", "loading GOOGLE_SHEET_ID", Exception("GOOGLE_SHEET_ID is not set"))

GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
if not GOOGLE_CREDS_JSON:
    log_and_raise("Env", "loading GOOGLE_CREDS_JSON", Exception("GOOGLE_CREDS_JSON is not set"))

# ===== Optional Settings =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()