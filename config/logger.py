import logging
import sys
import os
import requests
import threading

# ===== Base logger setup =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("EventDayBuddy")

# ===== Telegram admin alert config =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TELEGRAM_TIMEOUT = 5  # seconds

def _send_alert(message: str, parse_mode: str = None):
    """Internal helper to send a Telegram message to the admin chat."""
    if not TELEGRAM_TOKEN or not ADMIN_CHAT_ID:
        logger.warning("[Alert] Missing TELEGRAM_TOKEN or ADMIN_CHAT_ID, cannot send admin alert.")
        return

    # Truncate if too long
    if len(message) > TELEGRAM_MAX_MESSAGE_LENGTH:
        message = message[:TELEGRAM_MAX_MESSAGE_LENGTH - 50] + "\n...[truncated]"

    try:
        payload = {"chat_id": ADMIN_CHAT_ID, "text": message}
        if parse_mode:
            payload["parse_mode"] = parse_mode

        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json=payload,
            timeout=TELEGRAM_TIMEOUT
        )
        if resp.status_code != 200:
            logger.error(f"[Alert] Telegram API returned {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.error(f"[Alert] Failed to send admin alert: {e}", exc_info=True)

def alert_admin(message: str, parse_mode: str = None, async_send: bool = True):
    """
    Send a Telegram message to the admin chat.
    Only used for errors/warnings that need immediate attention.
    async_send=True will send in a background thread to avoid blocking.
    """
    if async_send:
        threading.Thread(target=_send_alert, args=(message, parse_mode), daemon=True).start()
    else:
        _send_alert(message, parse_mode)

def log_info(module: str, action: str):
    """Standardized info log."""
    logger.info(f"[{module}] {action}")

def log_and_raise(module: str, action: str, error: Exception):
    """
    Logs an error, alerts admin, and re-raises.
    Use this in any try/except where failure should stop execution.
    """
    msg = f"[{module}] ❌ Failed while {action}: {error}"
    logger.error(msg, exc_info=True)
    alert_admin(msg)
    raise error

def log_and_alert(module: str, action: str, warning: str):
    """
    Logs a warning and alerts admin without raising.
    Use for recoverable issues.
    """
    msg = f"[{module}] ⚠️ {action}: {warning}"
    logger.warning(msg)
    alert_admin(msg)