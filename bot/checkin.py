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

            # === DIFFERENT LOGIC FOR ID vs PHONE ===
            if method == "id":
                # Single booking lookup (existing logic)
                booking = db.query(Booking).filter(
                    Booking.event_id == event_name,
                    Booking.id_number.ilike(f"%{query}%")
                ).first()

                if not booking:
                    await update.message.reply_text(f"❌ No booking found for ID: {query}")
                    return

                await show_booking_selection(update, [booking], method)

            else:  # method == "phone" - GROUP CHECK-IN
                # Find all bookings with this phone number
                bookings = db.query(Booking).filter(
                    Booking.event_id == event_name,
                    Booking.phone.ilike(f"%{query}%")
                ).all()

                if not bookings:
                    await update.message.reply_text(f"❌ No bookings found for phone: {query}")
                    return

                # If only one booking, treat as single check-in
                if len(bookings) == 1:
                    await show_booking_selection(update, bookings, method)
                else:
                    # Multiple bookings - show group selection
                    await show_group_selection(update, bookings, query)

    except Exception as e:
        log_and_raise("Checkin", f"handling /{method}", e)


async def show_group_selection(update: Update, bookings: list, phone_number: str):
    """Show group selection for multiple bookings with same phone number."""
    try:
        # Build selection buttons - one per passenger
        buttons = []
        for booking in bookings:
            # Check which legs are needed for this passenger
            needs_arrival = not booking.arrival_boat_boarded
            needs_departure = not booking.departure_boat_boarded
            
            status_indicator = ""
            if needs_arrival and needs_departure:
                status_indicator = "❌"
            elif needs_arrival or needs_departure:
                status_indicator = "🟡"
            else:
                status_indicator = "✅"
            
            button_text = f"{status_indicator} {booking.name} (ID: {booking.id_number})"
            buttons.append([InlineKeyboardButton(button_text, callback_data=f"select:{booking.id}")])

        # Add group action buttons
        group_buttons = []
        if len(bookings) > 1:
            # Only show "Check All" if at least one passenger needs check-in
            needs_checkin = any(not b.arrival_boat_boarded or not b.departure_boat_boarded for b in bookings)
            if needs_checkin:
                group_buttons.append([InlineKeyboardButton("✅ Check All In", callback_data=f"group:all:{phone_number}")])
        
        group_buttons.append([InlineKeyboardButton("⏭️ Skip Group", callback_data=f"group:skip:{phone_number}")])
        
        if group_buttons:
            buttons.extend(group_buttons)

        reply_markup = InlineKeyboardMarkup(buttons)

        group_info = f"📞 Group found for phone: {phone_number}\n"
        group_info += f"👥 {len(bookings)} passenger(s) found:\n\n"
        
        for i, booking in enumerate(bookings, 1):
            arrival_status = f"Boat {booking.arrival_boat_boarded}" if booking.arrival_boat_boarded else "Not checked in"
            departure_status = f"Boat {booking.departure_boat_boarded}" if booking.departure_boat_boarded else "Not checked in"
            group_info += f"{i}. {booking.name}\n"
            group_info += f"   ID: {booking.id_number}\n"
            group_info += f"   Arrival: {arrival_status}\n"
            group_info += f"   Departure: {departure_status}\n\n"

        group_info += "Select individual passengers or use group actions below."

        await update.message.reply_text(group_info, reply_markup=reply_markup)

    except Exception as e:
        log_and_raise("Checkin", "showing group selection", e)


async def show_booking_selection(update: Update, bookings: list, method: str):
    """Show check-in options for single or selected booking(s)."""
    try:
        # For single booking or individual selection from group
        booking = bookings[0]  # First booking in list
        
        # Check which legs are needed
        needs_arrival = not booking.arrival_boat_boarded
        needs_departure = not booking.departure_boat_boarded
        
        # If both legs are completed
        if not needs_arrival and not needs_departure:
            await update.message.reply_text(
                f"✅ {booking.name} is already checked in for both arrival and departure.\n"
                f"Arrival: Boat {booking.arrival_boat_boarded}\n"
                f"Departure: Boat {booking.departure_boat_boarded}"
            )
            return

        # Build appropriate buttons
        buttons = []
        if needs_arrival:
            buttons.append([InlineKeyboardButton("✅ Arrival Boarding", callback_data=f"confirm:arrival:{booking.id}")])
        if needs_departure:
            buttons.append([InlineKeyboardButton("✅ Departure Boarding", callback_data=f"confirm:departure:{booking.id}")])
        
        buttons.append([InlineKeyboardButton("⏭️ Skip", callback_data=f"skip:{booking.id}")])
        reply_markup = InlineKeyboardMarkup(buttons)

        caption = (
            f"👤 {booking.name}\n"
            f"ID: {booking.id_number}\n"
            f"Phone: {booking.phone}\n"
            f"Male Dep: {booking.male_dep or '-'}\n"
            f"Resort Dep: {booking.resort_dep or '-'}\n"
        )
        
        # Show leg status
        if booking.arrival_boat_boarded:
            caption += f"Arrival: ✅ Boat {booking.arrival_boat_boarded}\n"
        else:
            caption += "Arrival: ❌ Not checked in\n"
            
        if booking.departure_boat_boarded:
            caption += f"Departure: ✅ Boat {booking.departure_boat_boarded}"
        else:
            caption += "Departure: ❌ Not checked in"

        # Handle photo display (existing logic)
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
        log_and_raise("Checkin", "showing booking selection", e)

# ===== Group Selection Callback =====
@require_role("checkin_staff")
async def handle_group_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle group selection and group actions."""
    try:
        query = update.callback_query
        await query.answer()

        parts = query.data.split(":")
        action = parts[1]
        
        if action == "all":  # Check All In
            phone_number = parts[2]
            await handle_group_checkin(update, context, phone_number, "all")
        elif action == "skip":  # Skip Group
            phone_number = parts[2]
            await handle_group_skip(update, context, phone_number)
        elif action.startswith("select"):  # Individual selection
            booking_id = int(parts[1])
            await handle_individual_selection(update, context, booking_id)

    except Exception as e:
        log_and_raise("Checkin", "handling group selection", e)


async def handle_individual_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, booking_id: int):
    """Show check-in options for individually selected passenger."""
    with get_db() as db:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            await update.callback_query.edit_message_text("❌ Booking not found.")
            return

    await show_booking_selection(update, [booking], "individual")


async def handle_group_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str, action: str):
    """Check in entire group or handle group actions."""
    try:
        query = update.callback_query
        user_id = str(query.from_user.id)

        with get_db() as db:
            # Get all bookings for this phone number that need check-in
            bookings = db.query(Booking).filter(
                Booking.phone.ilike(f"%{phone_number}%")
            ).all()

            if not bookings:
                await query.edit_message_text("❌ No bookings found for this group.")
                return

            # Check capacity before proceeding
            session = db.query(BoardingSession).filter(BoardingSession.is_active.is_(True)).first()
            if not session:
                await query.edit_message_text("⚠️ No active boat session.")
                return

            boat = db.query(Boat).filter(Boat.boat_number == session.boat_number).first()
            if not boat:
                await query.edit_message_text("❌ Boat not found.")
                return

            # Count current passengers
            current_passenger_count = db.query(Booking).filter(
                Booking.arrival_boat_boarded == session.boat_number,
                Booking.status == "checked_in"
            ).count()

            # Count how many in this group need check-in
            group_needs_checkin = [b for b in bookings if not b.arrival_boat_boarded or not b.departure_boat_boarded]
            
            if current_passenger_count + len(group_needs_checkin) > boat.capacity:
                await query.edit_message_text(
                    f"🚫 Boat {session.boat_number} doesn't have enough capacity for this group.\n"
                    f"Current: {current_passenger_count}/{boat.capacity}\n"
                    f"Group needs: {len(group_needs_checkin)} seats\n"
                    f"Please ask admin to /editseats or check in passengers individually."
                )
                return

            # Check in all passengers that need it
            now = datetime.utcnow()
            checked_in_count = 0

            for booking in group_needs_checkin:
                # Determine which legs to check in
                needs_arrival = not booking.arrival_boat_boarded
                needs_departure = not booking.departure_boat_boarded

                if needs_arrival:
                    booking.arrival_boat_boarded = session.boat_number
                if needs_departure:
                    booking.departure_boat_boarded = session.boat_number

                booking.status = "checked_in"
                booking.checkin_time = now

                # Log check-in
                legs_checked = []
                if needs_arrival:
                    legs_checked.append("arrival")
                if needs_departure:
                    legs_checked.append("departure")
                
                checkin_log = CheckinLog(
                    booking_id=booking.id,
                    boat_number=session.boat_number,
                    confirmed_by=user_id,
                    method=f"group-{'-'.join(legs_checked)}"
                )
                db.add(checkin_log)
                checked_in_count += 1

            db.commit()

        await query.edit_message_text(
            f"✅ Group check-in completed!\n"
            f"📞 Phone: {phone_number}\n"
            f"👥 Checked in: {checked_in_count} passenger(s)\n"
            f"🛳 Boat: {session.boat_number}"
        )

        logger.info(f"[Checkin] Group check-in for phone {phone_number}: {checked_in_count} passengers by {user_id}")

    except Exception as e:
        log_and_raise("Checkin", "handling group check-in", e)


async def handle_group_skip(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    """Skip entire group."""
    try:
        query = update.callback_query
        user_id = str(query.from_user.id)

        with get_db() as db:
            bookings = db.query(Booking).filter(Booking.phone.ilike(f"%{phone_number}%")).all()
            
            # Log skip for each booking
            for booking in bookings:
                skip_log = CheckinLog(
                    booking_id=booking.id,
                    boat_number=None,
                    confirmed_by=user_id,
                    method="group-skip"
                )
                db.add(skip_log)
            
            db.commit()

        await query.edit_message_text(
            f"⏭️ Skipped entire group for phone: {phone_number}\n"
            f"👥 {len(bookings)} passenger(s) skipped"
        )

        logger.info(f"[Checkin] Skipped group for phone {phone_number}: {len(bookings)} passengers by {user_id}")

    except Exception as e:
        log_and_raise("Checkin", "skipping group", e)

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

            # === CAPACITY CHECK - NEW CODE ===
            # Count current passengers on this boat for this leg
            if leg == "arrival":
                current_passenger_count = db.query(Booking).filter(
                    Booking.arrival_boat_boarded == session.boat_number,
                    Booking.status == "checked_in"
                ).count()
                boat_field = "arrival_boat_boarded"
            else:  # departure
                current_passenger_count = db.query(Booking).filter(
                    Booking.departure_boat_boarded == session.boat_number,
                    Booking.status == "checked_in"
                ).count()
                boat_field = "departure_boat_boarded"

            # Get boat capacity
            boat = db.query(Boat).filter(Boat.boat_number == session.boat_number).first()
            if not boat:
                await query.edit_message_text("❌ Boat not found in inventory.")
                return

            # Check if boat is full
            if current_passenger_count >= boat.capacity:
                await query.edit_message_text(
                    f"🚫 Boat {session.boat_number} is now full ({current_passenger_count}/{boat.capacity}).\n"
                    f"Please ask admin to /editseats or start /boatready with the next available boat."
                )
                return
            # === END CAPACITY CHECK ===

            # Update booking (existing code continues...)
            now = datetime.utcnow()
            if leg == "arrival":
                booking.arrival_boat_boarded = session.boat_number
            elif leg == "departure":
                booking.departure_boat_boarded = session.boat_number

            booking.status = "checked_in"
            booking.checkin_time = now
            
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
    app.add_handler(
        CallbackQueryHandler(
            require_role("checkin_staff")(skip_checkin),
            pattern=r"^skip:\d+$"
        )
    )
