from telegram import Update
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from config.envs import ADMIN_CHAT_ID, DRY_RUN
from db.init import get_db
from db.models import Config
from sheets.manager import create_event_tab
from googleapiclient.errors import HttpError

async def cpe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create Present Event — sets active event and creates tab in Sheets."""
    try:
        user_id = str(update.effective_user.id)
        if str(ADMIN_CHAT_ID) != user_id:
            await update.message.reply_text("⛔ You are not authorized to run this command.")
            return

        if not context.args:
            await update.message.reply_text("Usage: /cpe <event_name>")
            return

        event_name = " ".join(context.args).strip()
        if not event_name or "/" in event_name or len(event_name) > 50:
            await update.message.reply_text("❌ Invalid event name. Please choose a simpler name (no slashes, max 50 chars).")
            return

        logger.info(f"[Admin] Creating new event: {event_name}")

        # Create tab in Sheets unless DRY_RUN
        if not DRY_RUN:
            try:
                create_event_tab(event_name)
            except HttpError as sheet_error:
                if "already exists" in str(sheet_error):
                    logger.warning(f"[Sheets] Sheet '{event_name}' already exists — skipping creation.")
                else:
                    logger.error(f"[Sheets] Failed to create sheet for event '{event_name}': {sheet_error}")
                    raise sheet_error

        # Update DB config
        with get_db() as db:
            config_entry = db.query(Config).filter(Config.key == "active_event").first()
            if config_entry:
                config_entry.value = event_name
            else:
                db.add(Config(key="active_event", value=event_name))
            db.commit()

        await update.message.reply_text(f"✅ Active event set to: {event_name}")
        logger.info(f"[Admin] Active event set to '{event_name}'")

    except Exception as e:
        log_and_raise("Admin", "running /cpe", e)