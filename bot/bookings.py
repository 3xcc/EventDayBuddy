from telegram import Update
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from config.envs import DRY_RUN
from db.init import get_db
from db.models import Booking, Config
from sheets.manager import append_to_master, append_to_event

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
        if len(context.args) < 5:
            await update.message.reply_text(
                "Usage: /newbooking <Name> <ID> <Phone> <MaleDep> <ResortDep> "
                "[PaidAmount] [TransferRef] [TicketType] [BoatNumber]"
            )
            return

        with get_db() as db:
            # Get active event
            active_event_cfg = db.query(Config).filter(Config.key == "active_event").first()
            if not active_event_cfg or not active_event_cfg.value:
                await update.message.reply_text("⛔ No active event set. Use /cpe first.")
                return
            event_name = active_event_cfg.value

            # Parse args
            name = context.args[0]
            id_number = context.args[1]
            phone = context.args[2]
            male_dep = context.args[3]
            resort_dep = context.args[4]
            paid_amount = context.args[5] if len(context.args) > 5 else None
            transfer_ref = context.args[6] if len(context.args) > 6 else None
            ticket_type = context.args[7] if len(context.args) > 7 else None
            boat_number = context.args[8] if len(context.args) > 8 else None

            # Deduplication check (case-insensitive ID match)
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
                boat=boat_number,
                status="booked"
            )
            db.add(booking)
            db.commit()
            db.refresh(booking)

            # Prepare row for Sheets
            booking_row = [
                str(booking.id),
                booking.name,
                booking.id_number,
                booking.phone,
                booking.male_dep,
                booking.resort_dep,
                booking.paid_amount,
                booking.transfer_ref,
                booking.ticket_type,
                "",  # Check-in Time
                booking.boat or "",  # Boat
                booking.status,
                ""   # ID Doc URL
            ]

            if not DRY_RUN:
                append_to_master(event_name, booking_row)
                append_to_event(event_name, booking_row)
            else:
                logger.info(f"[Booking] DRY_RUN enabled — skipping Sheets append for {name}")

        await update.message.reply_text(f"✅ Booking created for {name} in event '{event_name}'.")
        logger.info(f"[Booking] New booking for {name} ({id_number}) in event '{event_name}'")

    except Exception as e:
        log_and_raise("Booking", "creating new booking", e)