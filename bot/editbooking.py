from telegram import Update
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from db.init import get_db
from db.models import Booking, BookingEditLog
from sheets.manager import update_booking_row
from utils.booking_schema import build_master_row, build_event_row
from bot.utils.roles import require_role

# Map user-friendly field names to DB attributes
FIELD_ALIASES = {
    "phone": "phone",
    "id": "id_number",
    "idnumber": "id_number",
    "male": "male_dep",
    "malé": "male_dep",
    "resort": "resort_dep",
    "departuretime": "departure_time",
    "arrivaltime": "arrival_time",
    "paid": "paid_amount",
    "amount": "paid_amount",
    "transfer": "transfer_ref",
    "ticket": "ticket_type",
    "status": "status",
}


def parse_edit_args(args, raw_text: str) -> dict:
    """Parse edit arguments from inline args or multi-line text."""
    updates = {}

    # Inline args (field=value)
    for arg in args:
        if "=" in arg:
            field, val = arg.split("=", 1)
            key = FIELD_ALIASES.get(field.strip().lower(), field.strip().lower())
            updates[key] = val.strip()

    # Multi-line parsing
    lines = raw_text.splitlines()[1:]  # skip command line
    for line in lines:
        if ":" in line:
            field, val = line.split(":", 1)
            key = FIELD_ALIASES.get(field.strip().lower(), field.strip().lower())
            updates[key] = val.strip()

    return updates


@require_role("booking_staff")
async def editbooking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit an existing booking by ticket_ref. Updates DB, logs changes, and syncs to Sheets."""
    try:
        if not context.args:
            await update.message.reply_text("❌ Usage: /editbooking <ticket_ref> field=value ...")
            return

        ticket_ref = context.args[0]
        updates = parse_edit_args(context.args[1:], update.message.text)

        if not updates:
            await update.message.reply_text("ℹ️ No updates provided.")
            return

        with get_db() as db:
            booking = db.query(Booking).filter(Booking.ticket_ref == ticket_ref).first()
            if not booking:
                await update.message.reply_text("❌ Booking not found.")
                return

            changes = []
            for field, new_val in updates.items():
                if not hasattr(booking, field):
                    continue  # skip unknown fields
                old_val = getattr(booking, field)
                if str(old_val) != str(new_val):
                    setattr(booking, field, new_val)
                    changes.append((field, old_val, new_val))

            if not changes:
                await update.message.reply_text("ℹ️ No changes applied.")
                return

            db.commit()
            db.refresh(booking)

            # Audit log
            for field, old_val, new_val in changes:
                log_entry = BookingEditLog(
                    booking_id=booking.id,
                    field=field,
                    old_value=str(old_val),
                    new_value=str(new_val),
                    edited_by=str(update.effective_user.id),
                )
                db.add(log_entry)
            db.commit()

            # Sheets sync
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
            }
            master_row = build_master_row(booking_dict, booking.event_name)
            event_row = build_event_row(master_row)
            update_booking_row(booking.event_name, master_row, event_row)

        # Feedback
        msg = [f"✅ Booking {ticket_ref} updated:"]
        msg += [f"- {f}: {o} → {n}" for f, o, n in changes]
        await update.message.reply_text("\n".join(msg))
        logger.info(f"[Booking] Edited booking {ticket_ref}: {changes}")

    except Exception as e:
        log_and_raise("Booking", "editing booking", e)