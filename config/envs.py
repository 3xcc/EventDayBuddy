import os
from config.logger import log_and_raise

# ===== Env Helpers =====
def get_bool_env(key: str, default: bool = False) -> bool:
    """Parse a boolean environment variable."""
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes")

def get_int_env(key: str, default: int = 0) -> int:
    """Parse an integer environment variable."""
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default

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

# ===== Supabase =====
SUPABASE_URL = os.getenv("SUPABASE_URL")
if not SUPABASE_URL:
    log_and_raise("Env", "loading SUPABASE_URL", Exception("SUPABASE_URL is not set"))

SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_KEY:
    log_and_raise("Env", "loading SUPABASE_KEY", Exception("SUPABASE_KEY is not set"))

SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")
if not SUPABASE_BUCKET:
    log_and_raise("Env", "loading SUPABASE_BUCKET", Exception("SUPABASE_BUCKET is not set"))

# ===== Optional Settings =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DRY_RUN = get_bool_env("DRY_RUN", False)

# Feature toggles for ops behavior
CHECKIN_STRICT = get_bool_env("CHECKIN_STRICT", False)
PHOTO_REQUIRED = get_bool_env("PHOTO_REQUIRED", False)

# Example numeric setting (future use)
# MAX_SEATS_DEFAULT = get_int_env("MAX_SEATS_DEFAULT", 60)

# Public URL for webhook
PUBLIC_URL = os.getenv("PUBLIC_URL")
if not PUBLIC_URL:
    log_and_raise("Env", "loading PUBLIC_URL", Exception("PUBLIC_URL is not set"))

# Boarding flow toggles
WAITLIST_AUTO_ASSIGN = get_bool_env("WAITLIST_AUTO_ASSIGN", False)
GROUP_CHECKIN_PROMPT = get_bool_env("GROUP_CHECKIN_PROMPT", False)

# ===== CORS Settings =====
# Comma-separated list of allowed origins in production, e.g. "https://myapp.com,https://admin.myapp.com"
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*")

# Normalize into list
if CORS_ALLOWED_ORIGINS == "*":
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]