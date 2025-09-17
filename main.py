import threading
import uvicorn
from config.logger import logger, log_and_raise
from config.envs import DRY_RUN, LOG_LEVEL
from db.init import init_db
from bot.handlers import run_bot
from web.server import app, PORT

def start_bot():
    try:
        logger.info("🤖 Starting Telegram bot in background thread...")
        run_bot()
    except Exception as e:
        log_and_raise("Main", "starting Telegram bot", e)

def main():
    try:
        logger.info("🚀 EventDayBuddy starting up...")

        init_db()
        logger.info("✅ Database initialized successfully.")

        if DRY_RUN:
            logger.warning("[Main] DRY_RUN mode enabled — bot external writes are limited; starting web server only.")
        else:
            # Start bot in a separate thread
            bot_thread = threading.Thread(target=start_bot, daemon=True)
            bot_thread.start()

        # Start FastAPI server for Render health checks
        uvicorn.run(app, host="0.0.0.0", port=PORT, log_level=LOG_LEVEL.lower())

    except Exception as e:
        log_and_raise("Main", "starting EventDayBuddy web service", e)

if __name__ == "__main__":
    main()