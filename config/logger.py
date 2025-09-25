import logging
import sys
import os
import requests
import threading
import time
import random

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
TELEGRAM_MAX_RETRIES = 3
TELEGRAM_BACKOFF_BASE = 1  # seconds

def _send_alert(message: str, parse_mode: str = None):
    """Internal helper to send a Telegram message to the admin chat with retry/backoff."""
    if not TELEGRAM_TOKEN or not ADMIN_CHAT_ID:
        logger.warning("[Alert] Missing TELEGRAM_TOKEN or ADMIN_CHAT_ID, cannot send admin alert.")
        return

    # Truncate if too long
    if len(message) > TELEGRAM_MAX_MESSAGE_LENGTH:
        message = message[:TELEGRAM_MAX_MESSAGE_LENGTH - 50] + "\n...[truncated]"

    payload = {"chat_id": ADMIN_CHAT_ID, "text": message}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    for attempt in range(1, TELEGRAM_MAX_RETRIES + 1):
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json=payload,
                timeout=TELEGRAM_TIMEOUT
            )
            if resp.status_code == 200:
                return  # success
            else:
                logger.error(f"[Alert] Telegram API returned {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"[Alert] Failed to send admin alert (attempt {attempt}): {e}", exc_info=True)

        # Backoff before retrying
        if attempt < TELEGRAM_MAX_RETRIES:
            sleep_time = TELEGRAM_BACKOFF_BASE * (2 ** (attempt - 1))
            sleep_time += random.uniform(0, 0.5)  # jitter
            logger.info(f"[Alert] Retrying in {sleep_time:.1f}s...")
            time.sleep(sleep_time)

    logger.error("[Alert] Giving up after max retries.")

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