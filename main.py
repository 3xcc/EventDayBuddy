from config.logger import logger, log_and_raise
from config.envs import DRY_RUN  # Centralized env var import (future use)
from db.init import init_db

def main():
    try:
        logger.info("🚀 EventDayBuddy starting up...")

        if DRY_RUN:
            logger.warning("[Main] DRY_RUN mode enabled — external services will be skipped.")

        init_db()
        logger.info("✅ Database initialized successfully.")

        # TODO: import bot.handlers and run_bot()
        # from bot.handlers import run_bot
        # run_bot()

    except Exception as e:
        log_and_raise("Main", "starting EventDayBuddy", e)

if __name__ == "__main__":
    main()