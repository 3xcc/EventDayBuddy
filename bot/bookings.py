from telegram import Update
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from config.envs import DRY_RUN  # Centralized env var import (future use)
from db.init import SessionLocal
from db.models import Booking, Config
from sheets.manager import append_to_master, append_to_event

# ===== /newbooking Command =====
async def newbooking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Create a new booking:
    - Reads active event from DB
    - Saves booking to DB
    - Appends to Master tab (with Event column) and event tab (without Event column)
    """
    try:
        # Check args
        if len(context.args) < 5:
            await update.message.reply_text(
                "Usage: /newbooking <Name> <ID> <Phone> <MaleDep> <ResortDep> [PaidAmount] [TransferRef] [TicketType]"
            )
            return

        # Get active event from DB
        db = SessionLocal()
        active_event_cfg = db.query(Config).filter(Config.key == "active_event").first()
        if not active_event_cfg or not active_event_cfg.value:
            await update.message.reply_text("⛔ No active event set. Use /cpe first.")
            db.close()
            return
        event_name = active_event_cfg.value

        # Parse booking data from args
        name = context.args[0]
        id_number = context.args[1]
        phone = context.args[2]
        male_dep = context.args[3]
        resort_dep = context.args[4]
        paid_amount = context.args[5] if len(context.args) > 5 else None
        transfer_ref = context.args[6] if len(context.args) > 6 else None
        ticket_type = context.args[7] if len(context.args) > 7 else None

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
            status="booked"
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)

        # Prepare row for Sheets (excluding No column)
        booking_row = [
            str(booking.id),  # T. Reference
            booking.name,
            booking.id_number,
            booking.phone,
            booking.male_dep,
            booking.resort_dep,
            booking.paid_amount,
            booking.transfer_ref,
            booking.ticket_type,
            "",  # Check in Time
            "",  # Boat
            booking.status,
            ""   # ID Doc URL
        ]

        # Append to Master and Event tabs
        if not DRY_RUN:
            append_to_master(event_name, booking_row)
            append_to_event(event_name, booking_row)
        else:
            logger.info(f"[Booking] DRY_RUN enabled — skipping Sheets append for {name}")

        db.close()

        await update.message.reply_text(f"✅ Booking created for {name} in event '{event_name}'.")
        logger.info(f"[Booking] New booking for {name} ({id_number}) in event '{event_name}'")

    except Exception as e:
        log_and_raise("Booking", "creating new booking", e)