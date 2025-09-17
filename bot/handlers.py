import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler
from config.logger import logger, log_and_raise
from config.envs import TELEGRAM_TOKEN
from bot.admin import cpe
from bot.bookings import newbooking

# ===== Command Handlers =====
async def start(update, context):
    """Basic /start command."""
    try:
        await update.message.reply_text("👋 EventDayBuddy is online and ready.")
        logger.info(f"[Bot] /start used by {update.effective_user.id}")
    except Exception as e:
        log_and_raise("Bot", "handling /start command", e)

# ===== Bot Runner =====
def run_bot():
    try:
        logger.info("[Bot] Initializing Telegram bot application...")
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

        # Register commands
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("cpe", cpe))
        app.add_handler(CommandHandler("newbooking", newbooking))

        logger.info("[Bot] ✅ Handlers registered. Starting polling...")

        # Create and set an event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run polling without signal handlers (safe in background thread)
        app.run_polling(stop_signals=None)

    except Exception as e:
        log_and_raise("Bot Init", "starting Telegram bot", e)