import uvicorn
from config.logger import logger, log_and_raise
from config.envs import DRY_RUN, LOG_LEVEL
from db.init import init_db
from bot.handlers import init_bot  # <-- new import for webhook mode
from web.server import app, PORT

def main():
    """Main entrypoint for EventDayBuddy — starts DB, bot (webhook), and web server."""
    try:
        logger.info("🚀 EventDayBuddy starting up...")

        # Initialize database
        init_db()
        logger.info("✅ Database initialized successfully.")

        if DRY_RUN:
            logger.warning("[Main] DRY_RUN mode enabled — bot external writes are limited; starting web server only.")
        else:
            # Initialize bot and set webhook
            init_bot()

        # Start FastAPI server (also serves Telegram webhook endpoint)
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=PORT,
            log_level=LOG_LEVEL.lower() if LOG_LEVEL else "info"
        )

    except Exception as e:
        log_and_raise("Main", "starting EventDayBuddy web service", e)

if __name__ == "__main__":
    main()