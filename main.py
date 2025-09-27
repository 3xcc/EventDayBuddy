import uvicorn
from config.logger import logger, log_and_raise
from config.envs import DRY_RUN, LOG_LEVEL
from db.init import init_db
from web.server import app, PORT  # ✅ no longer importing init_bot here

def main():
    """Main entrypoint for EventDayBuddy — starts DB and web server."""
    try:
        logger.info("🚀 EventDayBuddy starting up...")

        # Initialize database
        init_db()
        logger.info("✅ Database initialized successfully.")

        if DRY_RUN:
            logger.warning("[Main] DRY_RUN mode enabled — bot external writes are limited.")

        # Start FastAPI server (also serves Telegram webhook endpoint)
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=PORT,
            log_level=LOG_LEVEL.lower() if LOG_LEVEL else "info"
        )

    except Exception as e:
        log_and_raise("Main", "starting EventDayBuddy web service", e)
    finally:
        logger.info("🛑 EventDayBuddy has stopped.")
