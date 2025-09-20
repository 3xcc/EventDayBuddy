from telegram import Update
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from config.envs import DRY_RUN, PHOTO_REQUIRED
from db.init import get_db
from db.models import Booking, Config
from sheets.manager import append_to_master, append_to_event
from utils.money import parse_amount
from utils.booking_parser import parse_booking_input   # moved parsing here
from utils.photo import handle_photo_upload            # new helper
from services.booking_service import create_booking    # new service

# ===== /newbooking Command =====
async def newbooking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Create a new booking:
    - Reads active event from DB
    - Checks for duplicate ID
    - Saves booking to DB
    - Appends to Master tab and event tab
    - Optionally saves attached photo ID
    """
    try:
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
            name, id_number, phone, male_dep, resort_dep, paid_amount_raw, transfer_ref, ticket_type, arrival_time, departure_time = parse_booking_input(update.message.text)
            if not name or not id_number or not phone:
                await update.message.reply_text(
                    "❌ Could not parse booking. Please use one of the supported formats:\n"
                    "1) Plain lines\n"
                    "2) Colon-separated lines\n"
                    "Or the classic single-line args."
                )
                return

        # ✅ Sanitize paid_amount
        paid_amount = parse_amount(paid_amount_raw)
        if paid_amount_raw and paid_amount is None:
            await update.message.reply_text(
                "❌ Invalid amount. Use numbers like 400 or 1,200.50 (currency symbols allowed)."
            )
            return

        # Handle photo upload if present
        id_doc_url = None
        if update.message.photo:
            id_doc_url = await handle_photo_upload(update, id_number)
        if PHOTO_REQUIRED and not id_doc_url:
            await update.message.reply_text("❌ Photo ID is required for booking. Please attach a photo.")
            return

        with get_db() as db:
            # Get active event
            active_event_cfg = db.query(Config).filter(Config.key == "active_event").first()
            if not active_event_cfg or not active_event_cfg.value:
                await update.message.reply_text("⛔ No active event set. Use /cpe first.")
                return
            event_name = active_event_cfg.value

            # Create booking in DB (deduplication + ticket_ref handled inside service)
            booking, ticket_ref = create_booking(
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
                id_doc_url=id_doc_url
            )

            # Prepare row for Sheets
            booking_row = [
                "",  # No — auto
                event_name,
                ticket_ref,
                name,
                id_number,
                phone,
                male_dep or "",
                resort_dep or "",
                arrival_time or "",
                departure_time or "",
                str(paid_amount) if paid_amount is not None else "",
                transfer_ref or "",
                ticket_type or "",
                "",  # ArrivalBoatBoarded
                "",  # DepartureBoatBoarded
                "",  # CheckinTime
                "booked",  # Status
                id_doc_url or "",
                "",  # GroupID
                "",  # CreatedAt
                "",  # UpdatedAt
            ]

            if not DRY_RUN:
                append_to_master(event_name, booking_row)
                append_to_event(event_name, booking_row)
            else:
                logger.info(f"[Booking] DRY_RUN enabled — skipping Sheets append for {name}")

        # Confirmation message
        msg_lines = [
            "✅ Booking Created",
            f"Name: {name}",
            f"ID: {id_number}",
            f"Phone: {phone}",
            f"Event: {event_name}",
            f"Ticket: {ticket_ref}"
        ]
        if arrival_time:
            msg_lines.append(f"Arrival Time: {arrival_time}")
        if departure_time:
            msg_lines.append(f"Departure Time: {departure_time}")
        if paid_amount is not None:
            msg_lines.append(f"Paid: {paid_amount}")
        if ticket_type:
            msg_lines.append(f"Type: {ticket_type}")
        if id_doc_url:
            msg_lines.append("📎 Photo ID attached")

        await update.message.reply_text("\n".join(msg_lines))
        logger.info(f"[Booking] New booking for {name} ({id_number}) in event '{event_name}'")

    except Exception as e:
        log_and_raise("Booking", "creating new booking", e)