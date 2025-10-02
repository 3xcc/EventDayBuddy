from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from config.envs import ADMIN_CHAT_ID, DRY_RUN
from db.init import get_db
from db.models import Boat, BoardingSession, Booking, Config
from datetime import datetime
from utils.timezone import get_maldives_time, format_maldives_time
from utils.pdf_generator import generate_manifest_pdf
from utils.idcards import generate_idcards_pdf
from utils.supabase_storage import upload_manifest, upload_idcard
from sqlalchemy.exc import OperationalError
from bot.utils.roles import require_role

# ===== /departed Command =====
@require_role("admin")
async def departed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark boat as departed and export manifest + ID cards, with concurrency guard."""
    try:
        user_id = str(update.effective_user.id)

        if not context.args:
            await update.message.reply_text(
                "Usage: /departed <BoatNumber>\n"
                "Marks the boat as departed and generates a manifest.\n"
                "Only admins can use this command."
            )
            return

        boat_number = int(context.args[0])
        if boat_number <= 0:
            await update.message.reply_text("❌ Boat number must be a positive integer.")
            return

        # Use Maldives time
        departure_time = get_maldives_time()
        departure_display = format_maldives_time(departure_time)

        with get_db() as db:
            try:
                # Lock the boat row for update
                boat = (
                    db.query(Boat)
                    .filter(Boat.boat_number == boat_number)
                    .with_for_update(nowait=True)
                    .first()
                )
            except OperationalError:
                await update.message.reply_text(
                    f"⚠️ Boat {boat_number} is already being processed by another admin."
                )
                logger.warning(f"[Departure] Concurrency conflict on Boat {boat_number}")
                return

            if not boat:
                await update.message.reply_text(f"❌ Boat {boat_number} not found.")
                return

            if boat.status == "departed":
                await update.message.reply_text(f"⚠️ Boat {boat_number} has already been marked as departed.")
                return

            boat.status = "departed"
            logger.info(f"[Departure] Boat {boat_number} status set to departed.")

            # End boarding session
            session = (
                db.query(boardingSession)
                .filter(boardingSession.boat_number == boat_number,
                        BoardingSession.is_active.is_(True))
                .with_for_update(nowait=True)
                .first()
            )
            if session:
                session.is_active = False
                session.ended_at = departure_time
                logger.info(f"[Departure] Boarding session for Boat {boat_number} ended.")

            # Build manifest summary
            bookings = db.query(Booking).filter(
                (Booking.arrival_boat_boarded == boat_number) |
                (Booking.departure_boat_boarded == boat_number)
            ).all()

            manifest_lines = ["📋 Manifest:"]
            for b in bookings:
                manifest_lines.append(
                    f"- {b.name} ({b.id_number})\n"
                    f"  Scheduled: Arr {b.arrival_time or '-'} / Dep {b.departure_time or '-'}\n"
                    f"  Actual: ArrBoat {b.arrival_boat_boarded or '-'} / DepBoat {b.departure_boat_boarded or '-'}"
                )
            manifest_text = "\n".join(manifest_lines) if bookings else "No passengers logged."

            # Get active event
            active_event_cfg = db.query(Config).filter(Config.key == "active_event").first()
            event_name = active_event_cfg.value if active_event_cfg else "General"

            db.commit()

        # Generate and upload PDFs
        manifest_pdf = generate_manifest_pdf(str(boat_number), event_name=event_name)
        idcards_pdf = generate_idcards_pdf(str(boat_number), event_name=event_name)

        if not DRY_RUN:
            manifest_path = upload_manifest(manifest_pdf, event_name=event_name, boat_number=str(boat_number))
            if idcards_pdf:
                idcards_path = upload_idcard(idcards_pdf, event_name=event_name, ticket_ref=f"boat_{boat_number}")
                logger.info(f"[Departure] Uploaded manifest to {manifest_path} and ID cards to {idcards_path}")
            else:
                logger.warning(f"[Departure] No ID cards PDF generated for Boat {boat_number}")
                idcards_path = None

        # Reply with summary + export buttons
        buttons = [
            [InlineKeyboardButton("📄 Export Manifest (PDF)", callback_data=f"exportpdf:{boat_number}")],
            [InlineKeyboardButton("🪪 Export ID Cards (PDF)", callback_data=f"exportidcards:{boat_number}")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        await update.message.reply_text(
            f"🛥️ Boat {boat_number} departed at {departure_display}.\n\n"
            f"{manifest_text}",
            reply_markup=reply_markup
        )
        logger.info(f"[Departure] Boat {boat_number} marked as departed at {departure_display}")

    except Exception as e:
        log_and_raise("Departure", "running /departed", e)