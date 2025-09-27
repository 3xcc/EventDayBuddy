from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from config.envs import DRY_RUN, PHOTO_REQUIRED
from db.init import get_db
from db.models import Booking, Config
from sheets.manager import append_to_master, append_to_event, update_booking_photo
from utils.money import parse_amount
from utils.booking_parser import parse_booking_input
from utils.photo import handle_photo_upload
from utils.booking_schema import build_master_row
from services.booking_service import create_booking
from bot.utils.roles import require_role

# ===== /newbooking Command =====
@require_role("booking_staff")
async def newbooking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new booking and append to DB + Sheets."""
    try:
        if (not context.args) and (not update.message.text or update.message.text.strip() == "/newbooking"):
            await update.message.reply_text(
                "📝 To create a booking, please provide details in one of these formats:\n\n"
                "Option 1: Multi‑line (8 lines)\n"
                "1. Name\n"
                "2. ID Number\n"
                "3. Phone\n"
                "4. Male Departure\n"
                "5. Resort Departure\n"
                "6. Paid Amount\n"
                "7. Transfer Ref\n"
                "8. Ticket Type\n"
                "(Arrival/Departure times optional)\n\n"
                "Option 2: Single line with arguments:\n"
                "`/newbooking JohnDoe ID123 987654321 Male Resort 400 REF123 VIP`\n\n"
                "👉 Send again with the details in one of these formats."
            )
            return   
        # Parse args or multi-line input
        if len(context.args) >= 5:
            name = context.args[0]
            id_number = context.args[1]
            phone = context.args[2]
            male_dep = context.args[3]
            resort_dep = context.args[4]
            paid_amount_raw = context.args[5] if len(context.args) > 5 else None
            transfer_ref = context.args[6] if len(context.args) > 6 else None
            ticket_type = context.args[7] if len(context.args) > 7 else None
            arrival_time = context.args[8] if len(context.args) > 8 else None
            departure_time = context.args[9] if len(context.args) > 9 else None
        else:
            parsed = parse_booking_input(update.message.text)
            name = parsed["name"]
            id_number = parsed["id_number"]
            phone = parsed["phone"]
            male_dep = parsed["male_dep"]
            resort_dep = parsed["resort_dep"]
            paid_amount_raw = parsed["paid_amount"]
            transfer_ref = parsed["transfer_ref"]
            ticket_type = parsed["ticket_type"]
            arrival_time = parsed.get("arrival_time")
            departure_time = parsed.get("departure_time")

            if not name or not id_number or not phone:
                await update.message.reply_text(
                    "❌ Could not parse booking. Please use one of the supported formats:\n"
                    "1) Plain lines\n"
                    "2) Colon-separated lines\n"
                    "Or the classic single-line args."
                )
                return

        # Sanitize paid_amount
        paid_amount = parse_amount(paid_amount_raw)
        if paid_amount_raw and paid_amount is None:
            await update.message.reply_text("❌ Invalid amount. Use numbers like 400 or 1,200.50.")
            return

        # Handle inline photo later
        id_doc_url = None
        if PHOTO_REQUIRED and not update.message.photo:
            await update.message.reply_text("❌ Photo ID is required for booking. Please attach a photo.")
            return

        with get_db() as db:
            active_event_cfg = db.query(Config).filter(Config.key == "active_event").first()
            if not active_event_cfg or not active_event_cfg.value:
                await update.message.reply_text("⛔ No active event set. Use /cpe first.")
                return
            event_name = active_event_cfg.value.strip()

            booking = create_booking(
                db=db,
                event_name=event_name,
                name=name,
                id_number=id_number,
                phone=phone,
                male_dep=male_dep,
                resort_dep=resort_dep,
                paid_amount=paid_amount,
                transfer_ref=transfer_ref,
                ticket_type=ticket_type,
                arrival_time=arrival_time,
                departure_time=departure_time,
                id_doc_url=id_doc_url,
            )
            ticket_ref = booking.ticket_ref

            # Build Master row using schema utility
            booking_dict = {
                "ticket_ref": ticket_ref,
                "name": name,
                "id_number": id_number,
                "phone": phone,
                "male_dep": male_dep,
                "resort_dep": resort_dep,
                "arrival_time": arrival_time,
                "departure_time": departure_time,
                "paid_amount": paid_amount,
                "transfer_ref": transfer_ref,
                "ticket_type": ticket_type,
                "status": "booked",
                "id_doc_url": id_doc_url,
                "group_id": getattr(booking, "group_id", ""),
                "created_at": getattr(booking, "created_at", None),
            }
            master_row = build_master_row(booking_dict, event_name)

            if not DRY_RUN:
                append_to_master(event_name, master_row)
                append_to_event(event_name, master_row)  # let booking_io build event row

        # Confirmation message + inline button
        msg_lines = [
            "✅ Booking Created",
            f"Name: {name}",
            f"ID: {id_number}",
            f"Phone: {phone}",
            f"Event: {event_name}",
            f"Ticket: {ticket_ref}",
        ]
        if arrival_time: msg_lines.append(f"Arrival Time: {arrival_time}")
        if departure_time: msg_lines.append(f"Departure Time: {departure_time}")
        if paid_amount is not None: msg_lines.append(f"Paid: {paid_amount}")
        if ticket_type: msg_lines.append(f"Type: {ticket_type}")

        buttons = [[InlineKeyboardButton("📷 Attach ID Photo", callback_data=f"attachphoto:{booking.id}")]]
        reply_markup = InlineKeyboardMarkup(buttons)

        await update.message.reply_text("\n".join(msg_lines), reply_markup=reply_markup)
        logger.info(f"[Booking] New booking for {name} ({id_number}) in event '{event_name}'")

    except Exception as e:
        log_and_raise("Booking", "creating new booking", e)


# ===== Callback for Attach Photo =====
@require_role(["booking_staff", "checkin_staff"])
async def attach_photo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    booking_id = int(query.data.split(":")[1])
    context.user_data["awaiting_photo_for_booking"] = booking_id
    await query.message.reply_text("📷 Please send the ID photo now, and I’ll attach it to the booking.")


# ===== Photo Handler =====
@require_role(["booking_staff", "checkin_staff"])
async def handle_booking_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    booking_id = context.user_data.get("awaiting_photo_for_booking")
    if not booking_id:
        await update.message.reply_text(
            "❌ No booking is awaiting a photo. Please use the '📷 Attach ID Photo' button on a booking first."
        )
        return

    with get_db() as db:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return

        # Upload photo to Supabase
        file_url = await handle_photo_upload(update, booking.ticket_ref)
        if file_url:
            booking.id_doc_url = file_url
            db.commit()
            db.refresh(booking)

            if not DRY_RUN:
                # Update only the photo column in both tabs
                update_booking_photo(booking.event_name, booking.ticket_ref, file_url)

            await update.message.reply_text(
                f"✅ Photo attached to {booking.name} ({booking.ticket_ref})"
            )
            logger.info(f"[Booking] Photo attached for {booking.name} ({booking.ticket_ref})")

    # Clear state
    context.user_data.pop("awaiting_photo_for_booking", None)