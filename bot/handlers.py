from telegram.ext import ApplicationBuilder, CommandHandler
from config.logger import logger, log_and_raise
from config.envs import TELEGRAM_TOKEN  # Centralized env var import
from bot.admin import cpe               # Admin commands
from bot.bookings import newbooking     # Booking commands

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

        # Register commands here
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("cpe", cpe))                # Admin: Create Present Event
        app.add_handler(CommandHandler("newbooking", newbooking))  # Booking: Create new booking

        logger.info("[Bot] ✅ Handlers registered. Starting polling...")
        app.run_polling()

    except Exception as e:
        log_and_raise("Bot Init", "starting Telegram bot", e)