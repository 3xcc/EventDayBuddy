from telegram import Update
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from db.init import get_db
from db.models import Boat, BoardingSession
from datetime import datetime
from bot.utils.roles import require_role


@require_role("admin")
async def boatready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start boarding session for a boat."""
    try:
        user_id = str(update.effective_user.id)

        if not context.args:
            await update.message.reply_text("Usage: /boatready <BoatNumber> <Capacity>")
            return

        boat_number = int(context.args[0])
        seat_count = int(context.args[1]) if len(context.args) > 1 else 60
        if seat_count <= 0:
            await update.message.reply_text("❌ Seat count must be a positive number.")
            return

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
                "ended_at": datetime.now()
            })

            # Start new session
            session = BoardingSession(
                boat_number=boat_number,
                started_by=user_id,
                is_active=True,
                started_at=datetime.now()
            )
            db.add(session)
            db.commit()

        await update.message.reply_text(
            f"🛳 Boat {boat_number} is now boarding with {seat_count} seats.\n"
            f"Check-in mode is ready. Use /checkinmode to begin scanning."
        )
        logger.info(f"[Admin] Boat {boat_number} boarding session started by {user_id}.")

    except Exception as e:
        log_and_raise("Admin", "running /boatready", e)


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