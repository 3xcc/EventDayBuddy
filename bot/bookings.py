from telegram import Update
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from config.envs import DRY_RUN
from db.init import get_db
from db.models import Booking, Config
from sheets.manager import append_to_master, append_to_event

def parse_booking_input(update_text: str):
    """
    Parse booking input in either plain-line or colon-separated format.
    Returns tuple of fields.
    """
    lines = update_text.splitlines()
    # Drop the command itself
    lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith("/newbooking")]

    cleaned = []
    for l in lines:
        # Remove numbering like "1) "
        if len(l) > 2 and l[:2].isdigit() and l[2] in [")", "."]:
            l = l[3:].strip()
        # Handle colon-separated
        if ":" in l:
            parts = l.split(":", 1)
            l = parts[1].strip()
        cleaned.append(l)

    # Map to fields
    name = cleaned[0] if len(cleaned) > 0 else None
    id_number = cleaned[1] if len(cleaned) > 1 else None
    phone = cleaned[2] if len(cleaned) > 2 else None
    male_dep = cleaned[3] if len(cleaned) > 3 else None
    resort_dep = cleaned[4] if len(cleaned) > 4 else None
    paid_amount = cleaned[5] if len(cleaned) > 5 else None
    transfer_ref = cleaned[6] if len(cleaned) > 6 else None
    ticket_type = cleaned[7] if len(cleaned) > 7 else None
    arrival_time = cleaned[8] if len(cleaned) > 8 else None
    departure_time = cleaned[9] if len(cleaned) > 9 else None

    return name, id_number, phone, male_dep, resort_dep, paid_amount, transfer_ref, ticket_type, arrival_time, departure_time



# ===== /newbooking Command =====
async def newbooking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Create a new booking:
    - Reads active event from DB
    - Checks for duplicate ID
    - Saves booking to DB
    - Appends to Master tab and event tab
    """
    try:
        # Try parsing from args first
        if len(context.args) >= 5:
            name = context.args[0]
            id_number = context.args[1]
            phone = context.args[2]
            male_dep = context.args[3]
            resort_dep = context.args[4]
            paid_amount = context.args[5] if len(context.args) > 5 else None
            transfer_ref = context.args[6] if len(context.args) > 6 else None
            ticket_type = context.args[7] if len(context.args) > 7 else None
            arrival_time = context.args[8] if len(context.args) > 8 else None
            departure_time = context.args[9] if len(context.args) > 9 else None
        else:
            # Fallback: parse multi-line input
            name, id_number, phone, male_dep, resort_dep, paid_amount, transfer_ref, ticket_type, arrival_time, departure_time = parse_booking_input(update.message.text)
            if not name or not id_number or not phone:
                await update.message.reply_text(
                    "❌ Could not parse booking. Please use one of the supported formats:\n"
                    "1) Plain lines\n"
                    "2) Colon-separated lines\n"
                    "Or the classic single-line args."
                )
                return

        with get_db() as db:
            # Get active event
            active_event_cfg = db.query(Config).filter(Config.key == "active_event").first()
            if not active_event_cfg or not active_event_cfg.value:
                await update.message.reply_text("⛔ No active event set. Use /cpe first.")
                return
            event_name = active_event_cfg.value

            # Deduplication check
            existing = db.query(Booking).filter(
                Booking.event_name == event_name,
                Booking.id_number.ilike(id_number)
            ).first()

            if existing:
                await update.message.reply_text(
                    f"⚠️ Booking already exists for {existing.name} "
                    f"({existing.id_number}) in event '{event_name}'."
                )
                logger.warning(f"[Booking] Duplicate booking attempt for {id_number} in event '{event_name}'")
                return

            # Generate ticket reference
            prefix = event_name[:3].upper()
            count = db.query(Booking).filter(Booking.event_name == event_name).count()
            ticket_ref = f"{prefix}-{count + 1:03}"

            # Save to DB
            booking = Booking(
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
                status="booked"
            )
            db.add(booking)
            db.commit()
            db.refresh(booking)

            # Prepare row for Sheets
            booking_row = [
                "",  # No — handled by Sheets
                event_name,
                ticket_ref,
                name,
                id_number,
                phone,
                arrival_time or "",
                departure_time or "",
                paid_amount or "",
                transfer_ref or "",
                ticket_type or ""
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
        if paid_amount:
            msg_lines.append(f"Paid: {paid_amount}")
        if ticket_type:
            msg_lines.append(f"Type: {ticket_type}")

        await update.message.reply_text("\n".join(msg_lines))
        logger.info(f"[Booking] New booking for {name} ({id_number}) in event '{event_name}'")

    except Exception as e:
        log_and_raise("Booking", "creating new booking", e)