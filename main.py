import threading
import uvicorn
from config.logger import logger, log_and_raise
from config.envs import DRY_RUN, LOG_LEVEL
from db.init import init_db
from bot.handlers import run_bot
from web.server import app, PORT

def start_bot():
    """Start the Telegram bot in its own thread."""
    logger.info("🤖 Starting Telegram bot in background thread...")
    try:
        run_bot()
    except Exception as e:
        # Log full stack trace so we can debug startup issues
        logger.exception("[Main] Telegram bot thread crashed.")
        log_and_raise("Main", "starting Telegram bot", e)

def main():
    """Main entrypoint for EventDayBuddy — starts DB, bot, and web server."""
    try:
        logger.info("🚀 EventDayBuddy starting up...")

        # Initialize database
        init_db()
        logger.info("✅ Database initialized successfully.")

        bot_thread = None
        if DRY_RUN:
            logger.warning("[Main] DRY_RUN mode enabled — bot external writes are limited; starting web server only.")
        else:
            # Start bot in a separate thread
            bot_thread = threading.Thread(target=start_bot, daemon=True, name="TelegramBotThread")
            bot_thread.start()
            logger.info("[Main] Bot thread started.")

        # Start FastAPI server for Render health checks
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=PORT,
            log_level=LOG_LEVEL.lower() if LOG_LEVEL else "info"
        )

        # Optional: keep main alive if bot thread is running
        if bot_thread and bot_thread.is_alive():
            bot_thread.join()

    except Exception as e:
        log_and_raise("Main", "starting EventDayBuddy web service", e)

if __name__ == "__main__":
    main()