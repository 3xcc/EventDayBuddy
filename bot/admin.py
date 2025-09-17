from telegram import Update
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from config.envs import ADMIN_CHAT_ID  # Centralized env var import
from db.init import SessionLocal
from db.models import Config
from sheets.manager import create_event_tab

# ===== /cpe Command =====
async def cpe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Create Present Event:
    - Creates a new event tab in Google Sheets
    - Sets it as the active event in the DB
    """
    try:
        # Only admins can run this
        user_id = str(update.effective_user.id)
        if user_id != ADMIN_CHAT_ID:
            await update.message.reply_text("⛔ You are not authorized to run this command.")
            logger.warning(f"[Admin] Unauthorized /cpe attempt by {user_id}")
            return

        if not context.args:
            await update.message.reply_text("Usage: /cpe <event_name>")
            return

        event_name = " ".join(context.args).strip()
        logger.info(f"[Admin] Creating new event: {event_name}")

        # Create event tab in Sheets
        create_event_tab(event_name)

        # Store active_event in DB
        db = SessionLocal()
        config_entry = db.query(Config).filter(Config.key == "active_event").first()
        if config_entry:
            config_entry.value = event_name
        else:
            config_entry = Config(key="active_event", value=event_name)
            db.add(config_entry)
        db.commit()
        db.close()

        await update.message.reply_text(f"✅ Active event set to: {event_name}")
        logger.info(f"[Admin] Active event set to '{event_name}'")

    except Exception as e:
        log_and_raise("Admin", "running /cpe", e)