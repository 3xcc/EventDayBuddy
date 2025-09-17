import logging
import sys
import os

# Log level can be set via env var LOG_LEVEL (default INFO)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("EventDayBuddy")

def log_and_raise(module: str, action: str, error: Exception):
    """
    Logs an error with context and re-raises it.
    :param module: Name of the module or file
    :param action: Description of what was being attempted
    :param error: The caught exception
    """
    logger.error(f"[{module}] Failed while {action}: {error}", exc_info=True)
    raise error