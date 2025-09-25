import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from config.logger import logger, log_and_raise
from config.envs import ADMIN_CHAT_ID, DRY_RUN
from db.init import get_db
from db.models import Booking, BoardingSession, CheckinLog, User, Config
from sqlalchemy import or_
from datetime import datetime
from sheets.manager import update_booking
from utils.supabase_storage import fetch_signed_file  # ✅ added import

# ===== Lookup and prompt =====
@require_role("checkin_staff")
async def checkin_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /i <IDNumber>\n"
            "Checks in a passenger by ID.\n"
            "Only staff can use this command."
        )
        return
    await handle_checkin(update, context, method="id")

@require_role("checkin_staff")
async def checkin_by_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /p <PhoneNumber>\n"
            "Checks in passengers by phone number.\n"
            "Only staff can use this command."
        )
        return
    await handle_checkin(update, context, method="phone")

@require_role("checkin_staff")
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

            # Build filter dynamically
            if method == "id":
                booking = db.query(Booking).filter(
                    Booking.status == "booked",
                    Booking.event_name == event_name,
                    Booking.id_number.ilike(f"%{query}%")
                ).first()
            else:  # phone
                booking = db.query(Booking).filter(
                    Booking.status == "booked",
                    Booking.event_name == event_name,
                    Booking.phone.ilike(f"%{query}%")
                ).first()

            if not booking:
                await update.message.reply_text(f"❌ No booking found for {method}: {query}")
                return

            # Show photo + confirm buttons
            buttons = [
                [InlineKeyboardButton("✅ Arrival Boarding", callback_data=f"confirm:arrival:{booking.id}")],
                [InlineKeyboardButton("✅ Departure Boarding", callback_data=f"confirm:departure:{booking.id}")]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)

            caption = f"👤 {booking.name}\nID: {booking.id_number}\nPhone: {booking.phone}"
            if booking.id_doc_url:
                try:
                    # ✅ Fetch the file bytes from Supabase and send as file-like object
                    photo_bytes = fetch_signed_file(booking.id_doc_url, expiry=60)
                    await update.message.reply_photo(
                        photo=io.BytesIO(photo_bytes),
                        caption=caption,
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.warning(f"[Checkin] Failed to fetch photo for {booking.name}: {e}")
                    await update.message.reply_text(caption + "\n(Photo unavailable)", reply_markup=reply_markup)
            else:
                await update.message.reply_text(caption + "\n(No photo available)", reply_markup=reply_markup)

    except Exception as e:
        log_and_raise("Checkin", f"handling /{method}", e)

# ===== Confirm boarding callback =====
@require_role("checkin_staff")
async def confirm_boarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        parts = query.data.split(":")
        leg = parts[1]       # "arrival" or "departure"
        booking_id = int(parts[2])
        user_id = str(query.from_user.id)

        with get_db() as db:
            booking = db.query(Booking).filter(Booking.id == booking_id).first()
            if not booking:
                await query.edit_message_text("❌ Booking not found.")
                return

            session = db.query(BoardingSession).filter(BoardingSession.is_active.is_(True)).first()
            if not session:
                await query.edit_message_text("⚠️ No active boat session.")
                return

            # Update booking
            if leg == "arrival":
                booking.arrival_boat_boarded = session.boat_number
            elif leg == "departure":
                booking.departure_boat_boarded = session.boat_number

            booking.status = "checked-in"
            booking.checkin_time = datetime.utcnow()

            # Log check-in
            checkin_log = CheckinLog(
                booking_id=booking.id,
                boat_number=session.boat_number,
                confirmed_by=user_id,
                method=f"{leg}-manual"
            )
            db.add(checkin_log)
            db.commit()
            db.refresh(booking)

        # Push update to Sheets
        if not DRY_RUN:
            try:
                update_booking(event_name, master_row, event_row)
            except Exception as e:
                logger.error(f"[Sheets] Failed to update booking {booking.id} in Sheets: {e}")

        await query.edit_message_caption(
            caption=f"✅ {booking.name} checked in for {leg.capitalize()} Boat {session.boat_number}."
        )
        logger.info(f"[Checkin] Booking {booking.id} {leg} check-in on Boat {session.boat_number} by {user_id} (event={booking.event_name})")

    except Exception as e:
        log_and_raise("Checkin", "confirming boarding", e)

# ===== Handler registration =====
@require_role("checkin_staff")
def register_checkin_handlers(app):
    app.add_handler(CallbackQueryHandler(confirm_boarding, pattern=r"^confirm:(arrival|departure):\d+$"))