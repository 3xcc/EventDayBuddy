import io
import os
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from config.logger import logger
from bot.utils.roles import require_role
from services import import_service

ALLOWED_EXTENSIONS = {".csv", ".xls", ".xlsx"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


# ✅ Pass a string, not a list
@require_role("admin")
async def newbookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /newbookings command with attached CSV/XLS file.
    Usage: /newbookings [EventName]
    """
    try:
        message = update.message
        if not message or not message.document:
            await update.message.reply_text("⚠️ Please attach a CSV/XLS file with the bookings.")
            return

        # Validate file type
        filename = message.document.file_name or ""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            await message.reply_text("❌ Invalid file type. Please upload a CSV or Excel file.")
            return

        # Validate file size
        if message.document.file_size and message.document.file_size > MAX_FILE_SIZE:
            await message.reply_text("❌ File too large. Please upload a file under 5 MB.")
            return

        # Download file
        file = await message.document.get_file()
        file_bytes = io.BytesIO()
        await file.download_to_memory(out=file_bytes)
        file_bytes.seek(0)

        # Event name (from command args or default)
        event_name = context.args[0] if context.args else "General"

        logger.info(f"[Bot] /newbookings triggered by {update.effective_user.id} for event '{event_name}'")

        # Run import pipeline
        result = import_service.run_bulk_import(
            file_bytes.getvalue(),
            str(update.effective_user.id),
            event_name=event_name
        )

        # Format operator summary
        summary = import_service.summarize_import(result)
        await message.reply_text(summary)

    except Exception as e:
        logger.error(f"[Bot] Failed to process /newbookings: {e}", exc_info=True)
        await update.message.reply_text("❌ Bulk import failed. Please check the file and try again.")


def register_handlers(application):
    """
    Register /newbookings handler with the bot application.
    """
    application.add_handler(CommandHandler("newbookings", newbookings))
    application.add_handler(
        MessageHandler(
            filters.Document.ALL & filters.CaptionRegex(r"^/newbookings"),
            newbookings
        )
    )