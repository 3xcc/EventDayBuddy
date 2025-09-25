from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from config.logger import logger
from db.init import get_db
from db.models import User

# Role hierarchy: higher index = more privileges
ROLE_ORDER = ["viewer", "checkin_staff", "booking_staff", "admin"]

def has_role(user_role: str, required_role: str) -> bool:
    """Check if user_role >= required_role in hierarchy."""
    try:
        return ROLE_ORDER.index(user_role) >= ROLE_ORDER.index(required_role)
    except ValueError:
        return False

def require_role(required_role: str):
    """Decorator to enforce role checks on bot commands."""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = str(update.effective_user.id)

            # Look up user in DB
            with get_db() as db:
                user = db.query(User).filter(User.telegram_id == user_id).first()

            if not user:
                await update.message.reply_text("⛔ You are not registered in the system.")
                logger.warning(f"[Auth] Unauthorized attempt by {user_id} (not in DB)")
                return

            if not has_role(user.role, required_role):
                await update.message.reply_text("⛔ You are not authorized to run this command.")
                logger.warning(f"[Auth] Unauthorized attempt by {user_id} (role={user.role}, required={required_role})")
                return

            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator