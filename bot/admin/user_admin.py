from telegram import Update
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from config.envs import ADMIN_CHAT_ID
from db.init import get_db
from db.models import User

VALID_ROLES = ["admin", "checkin_staff", "booking_staff"]

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register a user with a role (admin-only)."""
    try:
        caller_id = str(update.effective_user.id)
        if str(ADMIN_CHAT_ID) != caller_id:
            await update.message.reply_text("⛔ Only the admin can register users.")
            return

        if len(context.args) != 2:
            await update.message.reply_text(
                "Usage: /register <telegramid> <role>\n"
                f"Roles: {', '.join(VALID_ROLES)}"
            )
            return

        target_chat_id = context.args[0].strip()
        role = context.args[1].strip().lower()
        if role not in VALID_ROLES:
            await update.message.reply_text(f"❌ Invalid role. Valid roles: {', '.join(VALID_ROLES)}")
            return

        with get_db() as db:
            existing = db.query(User).filter(User.chat_id == target_chat_id).first()
            if existing:
                existing.role = role
                logger.info(f"[Register] Updated role for {target_chat_id} to {role}")
            else:
                name = update.effective_user.full_name if update.effective_user else None
                db.add(User(chat_id=target_chat_id, role=role, name=name))
                logger.info(f"[Register] Registered new user {target_chat_id} as {role} ({name})")
            db.commit()

        await update.message.reply_text(f"✅ User {target_chat_id} registered as {role}.")

    except Exception as e:
        log_and_raise("UserAdmin", "registering user", e)

async def unregister(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unregister a user (admin-only)."""
    try:
        caller_id = str(update.effective_user.id)
        if str(ADMIN_CHAT_ID) != caller_id:
            await update.message.reply_text("⛔ Only the admin can unregister users.")
            return

        if not context.args or len(context.args) != 1:
            await update.message.reply_text("Usage: /unregister <telegramid>")
            return

        target_chat_id = context.args[0].strip()
        with get_db() as db:
            user = db.query(User).filter(User.chat_id == target_chat_id).first()
            if user:
                display_name = user.name or target_chat_id
                db.delete(user)
                db.commit()
                await update.message.reply_text(f"✅ Unregistered {display_name}.")
                logger.info(f"[Unregister] Removed user {target_chat_id} ({display_name})")
            else:
                await update.message.reply_text("⚠️ User not found.")

    except Exception as e:
        log_and_raise("UserAdmin", "unregistering user", e)