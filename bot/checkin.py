import io
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from config.logger import logger, log_and_raise
from config.envs import DRY_RUN
from db.init import get_db
from db.models import Booking, BoardingSession, CheckinLog, Config
from utils.supabase_storage import fetch_signed_file
from utils.booking_schema import build_master_row, build_event_row
from sheets.manager import update_booking
from bot.utils.roles import require_role


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


async def handle_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    """Shared logic for /i and /p commands."""
    try:
        query = context.args[0] if context.args else None
        if not query:
            await update.message.reply_text(f"Usage: /{method} <value>")
            return

        with get_db() as db:
            # Active session
            session = db.query(BoardingSession).filter(BoardingSession.is_active.is_(True)).first()
            if not session:
                await update.message.reply_text("⚠️ No active boat session. Use /boatready first.")
                return

            # Active event
            active_event_cfg = db.query(Config).filter(Config.key == "active_event").first()
            if not active_event_cfg or not active_event_cfg.value:
                await update.message.reply_text("⛔ No active event set. Use /cpe first.")
                return
            event_name = active_event_cfg.value

            # Lookup booking
            if method == "id":
                booking = db.query(Booking).filter(
                    Booking.status == "booked",
                    Booking.event_id == event_name,
                    Booking.id_number.ilike(f"%{query}%")
                ).first()
            else:
                booking = db.query(Booking).filter(
                    Booking.status == "booked",
                    Booking.event_id == event_name,
                    Booking.phone.ilike(f"%{query}%")
                ).first()

            if not booking:
                await update.message.reply_text(f"❌ No booking found for {method}: {query}")
                return

            # Prompt with photo + buttons
            buttons = [
                [InlineKeyboardButton("✅ Arrival Boarding", callback_data=f"confirm:arrival:{booking.id}")],
                [InlineKeyboardButton("✅ Departure Boarding", callback_data=f"confirm:departure:{booking.id}")],
                [InlineKeyboardButton("⏭️ Skip", callback_data=f"skip:{booking.id}")]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)

            caption = (
                f"👤 {booking.name}\n"
                f"ID: {booking.id_number}\n"
                f"Phone: {booking.phone}\n"
                f"Male Dep: {booking.male_dep or '-'}\n"
                f"Resort Dep: {booking.resort_dep or '-'}"
            )
            if booking.id_doc_url:
                try:
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
            now = datetime.utcnow()
            if leg == "arrival":
                booking.arrival_boat_boarded = session.boat_number
            elif leg == "departure":
                booking.departure_boat_boarded = session.boat_number

            booking.status = "checked_in"
            booking.checkin_time = now
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

            # Build rows for Sheets sync
            event_name = booking.event_id
            booking_dict = {
                "ticket_ref": booking.ticket_ref,
                "name": booking.name,
                "id_number": booking.id_number,
                "phone": booking.phone,
                "male_dep": booking.male_dep,
                "resort_dep": booking.resort_dep,
                "arrival_time": booking.arrival_time,
                "departure_time": booking.departure_time,
                "paid_amount": booking.paid_amount,
                "transfer_ref": booking.transfer_ref,
                "ticket_type": booking.ticket_type,
                "status": booking.status,
                "id_doc_url": booking.id_doc_url,
                "group_id": booking.group_id,
                "created_at": booking.created_at,
                "ArrivalBoatBoarded": booking.arrival_boat_boarded,
                "DepartureBoatBoarded": booking.departure_boat_boarded,
                "checkin_time": booking.checkin_time,
            }
            master_row = build_master_row(booking_dict, event_name)
            event_row = build_event_row(master_row)

            def serialize_datetimes(row):
                """Convert all datetime values in a dict or list to ISO strings."""
                if isinstance(row, dict):
                    return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in row.items()}
                elif isinstance(row, list):
                    return [(v.isoformat() if isinstance(v, datetime) else v) for v in row]
                return row

            master_row = serialize_datetimes(master_row)
            event_row = serialize_datetimes(event_row)

        # Push update to Sheets
        if not DRY_RUN:
            try:
                update_booking(event_name, master_row, event_row)
            except Exception as e:
                logger.error(f"[Sheets] Failed to update booking {booking.id} in Sheets: {e}")

        # Choose reply method: always send a new message
        caption_text = f"✅ {booking.name} checked in for {leg.capitalize()} Boat {session.boat_number}."
        await query.message.reply_text(caption_text)

        logger.info(
            f"[Checkin] Booking {booking.id} {leg} check-in on Boat {session.boat_number} "
            f"by {user_id} (event={booking.event_id})"
        )

    except Exception as e:
        log_and_raise("Checkin", "confirming boarding", e)

@require_role("checkin_staff")
async def skip_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        parts = query.data.split(":")
        booking_id = int(parts[1])
        user_id = str(query.from_user.id)

        with get_db() as db:
            booking = db.query(Booking).filter(Booking.id == booking_id).first()
            if not booking:
                await query.edit_message_text("❌ Booking not found.")
                return

            # Log skip (optional, for audit trail)
            skip_log = CheckinLog(
                booking_id=booking.id,
                boat_number=None,
                confirmed_by=user_id,
                method="skip"
            )
            db.add(skip_log)
            db.commit()

        await query.edit_message_text(
            f"⏭️ Skipped {booking.name} ({booking.id_number}). Still available for check-in later."
        )
        logger.info(f"[Checkin] Skipped booking {booking.id} ({booking.name}) by {user_id}")

    except Exception as e:
        log_and_raise("Checkin", "skipping passenger", e)

# ===== Handler registration =====
def register_checkin_handlers(app):
    """Register all check-in related handlers on the bot application."""
    app.add_handler(
        CallbackQueryHandler(
            require_role("checkin_staff")(confirm_boarding),
            pattern=r"^confirm:(arrival|departure):\d+$"
        )
    )
    app.add_handler
        (CallbackQueryHandler(
            require_role("checkin_staff")(skip_checkin),
            pattern=r"^skip:\d+$"
        )
    )
