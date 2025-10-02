from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from config.logger import logger, log_and_raise
from db.init import get_db
from db.models import Boat, BoardingSession
from datetime import datetime
from bot.utils.roles import require_role


@require_role("admin")
async def boatready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start boarding session for a boat - prompts for leg type selection."""
    try:
        user_id = str(update.effective_user.id)

        if not context.args:
            await update.message.reply_text(
                "Usage: /boatready <BoatNumber> <Capacity> [leg_type]\n\n"
                "Examples:\n"
                "  /boatready 1 60 arrival\n"
                "  /boatready 2 50 departure\n"
                "  /boatready 3 60  (will prompt for leg type)"
            )
            return

        boat_number = int(context.args[0])
        seat_count = int(context.args[1]) if len(context.args) > 1 else 60
        leg_type = context.args[2].lower() if len(context.args) > 2 else None

        if seat_count <= 0:
            await update.message.reply_text("❌ Seat count must be a positive number.")
            return

        # Validate leg_type if provided
        if leg_type and leg_type not in ["arrival", "departure"]:
            await update.message.reply_text("❌ Leg type must be 'arrival' or 'departure'.")
            return

        # If leg_type not provided, show selection buttons
        if not leg_type:
            buttons = [
                [InlineKeyboardButton("🛬 Arrival Boarding", callback_data=f"boatready:arrival:{boat_number}:{seat_count}")],
                [InlineKeyboardButton("🛫 Departure Boarding", callback_data=f"boatready:departure:{boat_number}:{seat_count}")]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await update.message.reply_text(
                f"🛳 Starting Boat {boat_number} with {seat_count} seats.\n\n"
                f"Select boarding type:",
                reply_markup=reply_markup
            )
            return

        # Create the boarding session with leg_type
        await _create_boarding_session(update, boat_number, seat_count, leg_type, user_id)

    except Exception as e:
        log_and_raise("Admin", "running /boatready", e)


async def _create_boarding_session(update, boat_number: int, seat_count: int, leg_type: str, user_id: str):
    """Helper function to create a boarding session."""
    with get_db() as db:
        boat = db.query(Boat).filter(Boat.boat_number == boat_number).first()
        if boat:
            boat.capacity = seat_count
            boat.status = "open"
        else:
            boat = Boat(boat_number=boat_number, capacity=seat_count, status="open")
            db.add(boat)

        # End any active sessions
        db.query(BoardingSession).filter(BoardingSession.is_active.is_(True)).update({
            "is_active": False,
            "ended_at": get_maldives_time()
        })

        # Start new session with leg_type
        session = BoardingSession(
            boat_number=boat_number,
            started_by=user_id,
            leg_type=leg_type,
            is_active=True,
            started_at=get_maldives_time()
        )
        db.add(session)
        db.commit()

    leg_emoji = "🛬" if leg_type == "arrival" else "🛫"
    message_text = (
        f"🛳 Boat {boat_number} is now boarding for {leg_emoji} {leg_type.upper()} with {seat_count} seats.\n"
        f"Check-in mode is ready. Use /checkinmode to begin scanning."
    )

    # Check if this is a callback query or regular message
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(message_text)
    else:
        await update.message.reply_text(message_text)

    logger.info(f"[Admin] Boat {boat_number} {leg_type} boarding session started by {user_id}.")


@require_role("admin")
async def boatready_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle leg type selection for boatready command."""
    try:
        query = update.callback_query
        await query.answer()

        parts = query.data.split(":")
        leg_type = parts[1]
        boat_number = int(parts[2])
        seat_count = int(parts[3])
        user_id = str(query.from_user.id)

        await _create_boarding_session(update, boat_number, seat_count, leg_type, user_id)

    except Exception as e:
        log_and_raise("Admin", "handling boatready callback", e)


@require_role("admin")
async def checkinmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activate check-in mode for current boat session."""
    try:
        user_id = str(update.effective_user.id)

        with get_db() as db:
            session = db.query(BoardingSession).filter(BoardingSession.is_active.is_(True)).first()

        if not session:
            await update.message.reply_text("⚠️ No active boat session found. Use /boatready first.")
            return

        await update.message.reply_text(
            f"✅ Check-in mode activated.\n"
            f"Active Boat: {session.boat_number}\n"
            f"Use /i <id_number> or /p <phone_number> to check in passengers."
        )
        logger.info(f"[Admin] Check-in mode activated for Boat {session.boat_number} by {user_id}.")

    except Exception as e:
        log_and_raise("Admin", "running /checkinmode", e)


@require_role("admin")
async def editseats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit seat count for a boat during boarding."""
    try:
        user_id = str(update.effective_user.id)

        if len(context.args) != 2:
            await update.message.reply_text("Usage: /editseats <BoatNumber> <NewCapacity>")
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
        logger.info(f"[Admin] Boat {boat_number} seat count updated to {new_count} by {user_id}.")

    except Exception as e:
        log_and_raise("Admin", "running /editseats", e)