from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from config.logger import logger, log_and_raise
from config.envs import ADMIN_CHAT_ID
from db.init import get_db
from db.models import Config, Boat, BoardingSession, User
from sheets.manager import create_event_tab
from googleapiclient.errors import HttpError

from drive.utils import ensure_drive_subfolder  # Add this at the top

VALID_ROLES = ["admin", "checkin_staff", "booking_staff"]

# ===== /cpe Command =====
async def cpe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create Present Event — sets active event and creates tab in Sheets."""
    try:
        user_id = str(update.effective_user.id)
        if user_id != ADMIN_CHAT_ID:
            await update.message.reply_text("⛔ You are not authorized to run this command.")
            logger.warning(f"[Admin] Unauthorized /cpe attempt by {user_id}")
            return

        if not context.args:
            await update.message.reply_text("Usage: /cpe <event_name>")
            return

        event_name = " ".join(context.args).strip()
        logger.info(f"[Admin] Creating new event: {event_name}")

        # Gracefully skip sheet creation if tab already exists
        try:
            create_event_tab(event_name)
        except HttpError as sheet_error:
            if "already exists" in str(sheet_error):
                logger.warning(f"[Sheets] Sheet '{event_name}' already exists — skipping creation.")
            else:
                raise sheet_error

        with get_db() as db:
            config_entry = db.query(Config).filter(Config.key == "active_event").first()
            if config_entry:
                config_entry.value = event_name
            else:
                config_entry = Config(key="active_event", value=event_name)
                db.add(config_entry)
            db.commit()

        # Ensure Drive folder exists for this event
        folder_id = ensure_drive_subfolder("IDs", event_name)
        context.bot_data["drive_folder_id"] = folder_id
        logger.info(f"[Drive] Folder ready for event '{event_name}' — ID: {folder_id}")

        await update.message.reply_text(f"✅ Active event set to: {event_name}")
        logger.info(f"[Admin] Active event set to '{event_name}'")

    except Exception as e:
        log_and_raise("Admin", "running /cpe", e)

# ===== /boatready Command =====
async def boatready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start boarding session for a boat."""
    try:
        user_id = str(update.effective_user.id)
        if user_id != ADMIN_CHAT_ID:
            await update.message.reply_text("⛔ You are not authorized to run this command.")
            return

        if not context.args:
            await update.message.reply_text(
                "Usage: /boatready <BoatNumber> <Capacity>\n"
                "Starts a boarding session for the specified boat.\n"
                "Only admins can use this command."
            )
            return

        boat_number = int(context.args[0])
        seat_count = int(context.args[1]) if len(context.args) > 1 else 60

        if seat_count <= 0:
            await update.message.reply_text("❌ Seat count must be a positive number.")
            return

        with get_db() as db:
            # Upsert boat
            boat = db.query(Boat).filter(Boat.boat_number == boat_number).first()
            if boat:
                boat.capacity = seat_count
                boat.status = "open"
                logger.info(f"[Admin] Updated Boat {boat_number} capacity to {seat_count} and status to open.")
            else:
                boat = Boat(boat_number=boat_number, capacity=seat_count, status="open")
                db.add(boat)
                logger.info(f"[Admin] Created Boat {boat_number} with capacity {seat_count}.")

            # End any previous active sessions
            db.query(BoardingSession).filter(BoardingSession.is_active.is_(True)).update({"is_active": False})

            # Start new session
            session = BoardingSession(
                boat_number=boat_number,
                started_by=user_id,
                is_active=True
            )
            db.add(session)
            db.commit()

        await update.message.reply_text(
            f"🛳 Boat {boat_number} is now boarding with {seat_count} seats.\n"
            f"Check-in mode is ready. Use /checkinmode to begin scanning."
        )
        logger.info(f"[Admin] Boat {boat_number} boarding session started.")

    except Exception as e:
        log_and_raise("Admin", "running /boatready", e)

# ===== /checkinmode Command =====
async def checkinmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activate check-in mode for current boat session."""
    
    try:
        user_id = str(update.effective_user.id)
        if user_id != ADMIN_CHAT_ID:
            await update.message.reply_text("⛔ You are not authorized to run this command.")
            return
            
        if not context.args:
            await update.message.reply_text(
            "Usage: /checkinmode <on/off>\n"
            "Enables or disables check-in mode for the active boat.\n"
            "Only admins can use this command."
        )
            return

        with get_db() as db:
            session = db.query(BoardingSession).filter(BoardingSession.is_active.is_(True)).first()

        if not session:
            await update.message.reply_text("⚠️ No active boat session found. Use /boatready first.")
            return

        await update.message.reply_text(
            f"✅ Check-in mode activated for Boat {session.boat_number}.\n"
            f"Use /i <id_number> or /p <phone_number> to check in passengers."
        )
        logger.info(f"[Admin] Check-in mode activated for Boat {session.boat_number}.")

    except Exception as e:
        log_and_raise("Admin", "running /checkinmode", e)

# ===== /editseats Command =====
async def editseats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit seat count for a boat during boarding."""
    try:
        user_id = str(update.effective_user.id)
        if user_id != ADMIN_CHAT_ID:
            await update.message.reply_text("⛔ You are not authorized to run this command.")
            return

        if not context.args:
            await update.message.reply_text(
                "Usage: /editseats <BoatNumber> <NewCapacity>\n"
                "Updates the seat count for a boat.\n"
                "Only admins can use this command."
            )
        return

        if len(context.args) != 2:
            await update.message.reply_text("Usage: /editseats <boat_number> <new_count>")
            return

        boat_number = int(context.args[0])
        new_count = int(context.args[1])

        if new_count <= 0:
            await update.message.reply_text("❌ Seat count must be a positive number.")
            return

        with get_db() as db:
            boat = db.query(Boat).filter(Boat.boat_number == boat_number).first()
            if not boat:
                await update.message.reply_text(f"❌ Boat {boat_number} not found.")
                return

            boat.capacity = new_count
            db.commit()

        await update.message.reply_text(f"✅ Boat {boat_number} seat count updated to {new_count}.")
        logger.info(f"[Admin] Boat {boat_number} seat count updated to {new_count}.")

    except Exception as e:
        log_and_raise("Admin", "running /editseats", e)

# ===== /Register Command =====
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin-only command to register a user with a role.
    Usage: /register <telegramid> <role>
    Roles: admin, checkin_staff, booking_staff
    """
    try:
        caller_id = str(update.effective_user.id)

        # Only the admin account can run this
        if caller_id != ADMIN_CHAT_ID:
            await update.message.reply_text("⛔ Only the admin can register users.")
            return

        if len(context.args) != 2:
            await update.message.reply_text(
                "Usage: /register <telegramid> <role>\n"
                f"Roles: {', '.join(VALID_ROLES)}\n"
                "Example: /register 123456789 checkin_staff"
            )
            return

        target_chat_id = context.args[0].strip()
        role = context.args[1].strip()

        if role not in VALID_ROLES:
            await update.message.reply_text(
                f"❌ Invalid role. Valid roles: {', '.join(VALID_ROLES)}"
            )
            return

        with get_db() as db:
            existing = db.query(User).filter(User.chat_id == target_chat_id).first()
            if existing:
                existing.role = role
                logger.info(f"[Register] Updated role for {target_chat_id} to {role}")
            else:
                new_user = User(chat_id=target_chat_id, role=role)
                db.add(new_user)
                logger.info(f"[Register] Registered new user {target_chat_id} as {role}")
            db.commit()

        await update.message.reply_text(
            f"✅ User {target_chat_id} registered as {role}."
        )

    except Exception as e:
        log_and_raise("Admin", "registering user", e)
        
# ===== /UnRegister Command =====
async def unregister(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin-only command to remove a registered user.
    Usage: /unregister <telegramid>
    """
    try:
        caller_id = str(update.effective_user.id)

        # Only the admin account can run this
        if caller_id != ADMIN_CHAT_ID:
            await update.message.reply_text("⛔ Only the admin can unregister users.")
            return

        if not context.args or len(context.args) != 1:
            await update.message.reply_text(
                "Usage: /unregister <telegramid>\n"
                "Example: /unregister 123456789"
            )
            return

        target_chat_id = context.args[0].strip()

        with get_db() as db:
            user = db.query(User).filter(User.chat_id == target_chat_id).first()
            if user:
                db.delete(user)
                db.commit()
                await update.message.reply_text(f"✅ Unregistered {user.name or target_chat_id}.")
                logger.info(f"[Unregister] Removed user {target_chat_id}")
            else:
                await update.message.reply_text("⚠️ User not found.")

    except Exception as e:
        log_and_raise("Admin", "unregistering user", e)
