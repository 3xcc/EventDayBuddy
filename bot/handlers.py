import asyncio
from io import BytesIO
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config.logger import logger, log_and_raise
from config.envs import TELEGRAM_TOKEN

# Core commands
from bot.admin import cpe, boatready, checkinmode, editseats
from bot.bookings import newbooking
from bot.checkin import checkin_by_id, checkin_by_phone, register_checkin_handlers
from bot.departure import departed
from drive.manifest import generate_manifest_pdf

# ===== Command Handlers =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Basic /start command."""
    try:
        await update.message.reply_text("👋 EventDayBuddy is online and ready.")
        logger.info(f"[Bot] /start used by {update.effective_user.id}")
    except Exception as e:
        log_and_raise("Bot", "handling /start command", e)

# ===== Export PDF Callback =====
async def export_pdf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle export button after /departed — generate and send manifest PDF."""
    try:
        query = update.callback_query
        await query.answer()

        if not query.data or ":" not in query.data:
            await query.edit_message_text("⚠️ Invalid export request.")
            logger.warning("[Callback] Received malformed exportpdf callback data.")
            return

        boat_number = query.data.split(":")[1]

        # Generate PDF bytes
        pdf_bytes = generate_manifest_pdf(boat_number)

        if not pdf_bytes:
            await query.edit_message_text(f"❌ Failed to generate manifest PDF for Boat {boat_number}.")
            logger.error(f"[Callback] No PDF bytes generated for Boat {boat_number}")
            return

        # Send PDF as Telegram document
        pdf_stream = BytesIO(pdf_bytes)
        pdf_stream.name = f"Boat_{boat_number}_Manifest.pdf"

        await query.message.reply_document(
            document=pdf_stream,
            caption=f"📄 Manifest PDF for Boat {boat_number}"
        )

        logger.info(f"[Callback] Manifest PDF sent for Boat {boat_number}")

    except Exception as e:
        log_and_raise("Callback", "handling exportpdf", e)

# ===== Bot Runner =====
def run_bot():
    """Initialize and run the Telegram bot."""
    try:
        logger.info("[Bot] Initializing Telegram bot application...")
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

        # Register commands
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("cpe", cpe))
        app.add_handler(CommandHandler("newbooking", newbooking))
        app.add_handler(CommandHandler("boatready", boatready))
        app.add_handler(CommandHandler("checkinmode", checkinmode))
        app.add_handler(CommandHandler("editseats", editseats))
        app.add_handler(CommandHandler("i", checkin_by_id))
        app.add_handler(CommandHandler("p", checkin_by_phone))
        app.add_handler(CommandHandler("departed", departed))

        # Register callbacks
        register_checkin_handlers(app)
        app.add_handler(CallbackQueryHandler(export_pdf_callback, pattern=r"^exportpdf:\d+$"))

        logger.info("[Bot] ✅ All handlers registered. Starting polling...")

        # If running in a background thread, create a new loop
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                logger.info("[Bot] Running in existing event loop.")
                app.run_polling(stop_signals=None)
            else:
                app.run_polling()
        except RuntimeError:
            # No running loop — safe to start normally
            app.run_polling()

    except Exception as e:
        log_and_raise("Bot Init", "starting Telegram bot", e)