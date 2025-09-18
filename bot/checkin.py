from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from config.logger import logger, log_and_raise
from config.envs import ADMIN_CHAT_ID
from db.init import get_db
from db.models import Booking, BoardingSession, CheckinLog, User, Config
from sqlalchemy import or_
from datetime import datetime

# ===== Lookup and prompt =====
async def checkin_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_checkin(update, context, method="id")

async def checkin_by_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_checkin(update, context, method="phone")

async def handle_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    try:
        user_id = str(update.effective_user.id)
        query = context.args[0] if context.args else None
        if not query:
            await update.message.reply_text(f"Usage: /{method} <value>")
            return

        with get_db() as db:
            # Get active boat session
            session = db.query(BoardingSession).filter(BoardingSession.is_active.is_(True)).first()
            if not session:
                await update.message.reply_text("⚠️ No active boat session. Use /boatready first.")
                return

            # Get active event name
            active_event_cfg = db.query(Config).filter(Config.key == "active_event").first()
            if not active_event_cfg or not active_event_cfg.value:
                await update.message.reply_text("⛔ No active event set. Use /cpe first.")
                return
            event_name = active_event_cfg.value

            # Lookup booking
            booking = db.query(Booking).filter(
                Booking.status == "booked",
                Booking.event_name == event_name,
                or_(
                    Booking.id_number.ilike(query) if method == "id" else False,
                    Booking.phone.ilike(query) if method == "phone" else False
                )
            ).first()

            if not booking:
                await update.message.reply_text(f"❌ No booking found for {method}: {query}")
                return

            # Show photo + confirm button
            buttons = [
                [InlineKeyboardButton("✅ Confirm Boarding", callback_data=f"confirm:{booking.id}")]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)

            if booking.id_doc_url:
                await update.message.reply_photo(
                    photo=booking.id_doc_url,
                    caption=f"👤 {booking.name}\nID: {booking.id_number}\nPhone: {booking.phone}",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    f"👤 {booking.name}\nID: {booking.id_number}\nPhone: {booking.phone}\n(No photo available)",
                    reply_markup=reply_markup
                )

    except Exception as e:
        log_and_raise("Checkin", f"handling /{method}", e)

# ===== Confirm boarding callback =====
async def confirm_boarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        booking_id = int(query.data.split(":")[1])
        user_id = str(query.from_user.id)

        with get_db() as db:
            booking = db.query(Booking).filter(Booking.id == booking_id).first()
            if not booking:
                await query.edit_message_text("❌ Booking not found.")
                return

            # Get active boat session
            session = db.query(BoardingSession).filter(BoardingSession.is_active.is_(True)).first()
            if not session:
                await query.edit_message_text("⚠️ No active boat session.")
                return

            # Update booking status
            booking.status = "checked-in"
            booking.checkin_time = datetime.utcnow()
            booking.boat = session.boat_number

            # Log check-in
            checkin_log = CheckinLog(
                booking_id=booking.id,
                boat_number=session.boat_number,
                confirmed_by=user_id,
                method="manual"
            )
            db.add(checkin_log)
            db.commit()

        await query.edit_message_text(f"✅ {booking.name} checked in for Boat {booking.boat}.")
        logger.info(f"[Checkin] Booking {booking.id} checked in for Boat {booking.boat} by {user_id}")

    except Exception as e:
        log_and_raise("Checkin", "confirming boarding", e)

# ===== Handler registration =====
def register_checkin_handlers(app):
    app.add_handler(CallbackQueryHandler(confirm_boarding, pattern=r"^confirm:\d+$"))