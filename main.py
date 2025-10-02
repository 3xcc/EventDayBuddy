import uvicorn
import traceback

from config.logger import logger, log_and_raise
from config.envs import DRY_RUN, LOG_LEVEL
from db.init import init_db
from web.server import app, PORT
from utils.timezone import set_maldives_timezone

def main():
    """Main entrypoint for EventDayBuddy — starts DB and web server."""
    try:
        print("[DEBUG] main() starting...")
        logger.info("🚀 EventDayBuddy starting up...")

        # Set Maldives timezone (GMT+5) for the application
        set_maldives_timezone()
        logger.info("🕐 Set application timezone to Maldives time (GMT+5)")

        print("[DEBUG] Initializing database...")
        # Initialize database safely
        init_db()
        print("[DEBUG] Database initialized.")
        logger.info("✅ Database initialized successfully.")

        if DRY_RUN:
            logger.warning("[Main] DRY_RUN mode enabled — bot external writes are limited.")

        print(f"[DEBUG] Starting FastAPI server on port {PORT}...")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=PORT,
            log_level=LOG_LEVEL.lower() if LOG_LEVEL else "info"
        )
        print("[DEBUG] uvicorn.run() has returned (should not happen unless server stopped)")

    except Exception as e:
        print("[DEBUG] Exception in main():", e)
        traceback.print_exc()
        log_and_raise("Main", "starting EventDayBuddy web service", e)

    finally:
        print("[DEBUG] main() finally block reached.")
        logger.info("🛑 EventDayBuddy has stopped.")

if __name__ == "__main__":
    main()
