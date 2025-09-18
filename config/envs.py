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

# Google Drive folder IDs

DRIVE_MANIFESTS_FOLDER_ID = os.getenv("DRIVE_MANIFESTS_FOLDER_ID")
if not DRIVE_MANIFESTS_FOLDER_ID:
    log_and_raise("Env", "loading DRIVE_MANIFESTS_FOLDER_ID", Exception("DRIVE_MANIFESTS_FOLDER_ID is not set"))

DRIVE_IDS_FOLDER_ID = os.getenv("DRIVE_IDS_FOLDER_ID")
if not DRIVE_IDS_FOLDER_ID:
    log_and_raise("Env", "loading DRIVE_IDS_FOLDER_ID", Exception("DRIVE_IDS_FOLDER_ID is not set"))


# ===== Optional Settings =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Feature toggles for ops behavior
CHECKIN_STRICT = os.getenv("CHECKIN_STRICT", "false").lower() == "true"
PHOTO_REQUIRED = os.getenv("PHOTO_REQUIRED", "false").lower() == "true"

# Example numeric setting (future use)
# MAX_SEATS_DEFAULT = int(os.getenv("MAX_SEATS_DEFAULT", "60"))

# Public URL for webhook
PUBLIC_URL = os.getenv("PUBLIC_URL")
if not PUBLIC_URL:
    log_and_raise("Env", "loading PUBLIC_URL", Exception("PUBLIC_URL is not set"))