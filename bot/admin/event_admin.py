from telegram import Update
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from config.envs import ADMIN_CHAT_ID
from db.init import get_db
from db.models import Config
from sheets.manager import create_event_tab
from drive.utils import ensure_drive_subfolder
from googleapiclient.errors import HttpError

async def cpe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create Present Event — sets active event and creates tab in Sheets."""
    try:
        user_id = str(update.effective_user.id)
        if user_id != ADMIN_CHAT_ID:
            await update.message.reply_text("⛔ You are not authorized to run this command.")
            return

        if not context.args:
            await update.message.reply_text("Usage: /cpe <event_name>")
            return

        event_name = " ".join(context.args).strip()
        logger.info(f"[Admin] Creating new event: {event_name}")

        try:
            create_event_tab(event_name)
        except HttpError as sheet_error:
            if "already exists" in str(sheet_error):
                logger.warning(f"[Sheets] Sheet '{event_name}' already exists — skipping creation.")
            else:
                raise sheet_error

        with get_db() as db:
            config_entry = db.query(Config).filter(Config.key == "active_event").first()
            if config_entry:
                config_entry.value = event_name
            else:
                db.add(Config(key="active_event", value=event_name))
            db.commit()

        folder_id = ensure_drive_subfolder("IDs", event_name)
        context.bot_data["drive_folder_id"] = folder_id
        await update.message.reply_text(f"✅ Active event set to: {event_name}")
        logger.info(f"[Admin] Active event set to '{event_name}'")

    except Exception as e:
        log_and_raise("Admin", "running /cpe", e)