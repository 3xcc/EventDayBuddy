from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from config.envs import ADMIN_CHAT_ID, DRY_RUN
from db.init import get_db
from db.models import Boat, BoardingSession, Booking, Config
from datetime import datetime
from utils.pdf_generator import generate_manifest_pdf
from utils.idcards import generate_idcards_pdf
from utils.supabase_storage import upload_manifest, upload_idcard

# ===== /departed Command =====
async def departed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark boat as departed and export manifest + ID cards."""
    try:
        user_id = str(update.effective_user.id)
        if str(ADMIN_CHAT_ID) != user_id:
            await update.message.reply_text("⛔ You are not authorized to run this command.")
            logger.warning(f"[Departure] Unauthorized /departed attempt by {user_id}")
            return

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

        departure_time = datetime.utcnow()

        with get_db() as db:
            # Update boat status
            boat = db.query(Boat).filter(Boat.boat_number == boat_number).first()
            if not boat:
                await update.message.reply_text(f"❌ Boat {boat_number} not found.")
                return

            boat.status = "departed"
            logger.info(f"[Departure] Boat {boat_number} status set to departed.")

            # End boarding session
            session = db.query(BoardingSession).filter(
                BoardingSession.boat_number == boat_number,
                BoardingSession.is_active.is_(True)
            ).first()
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
            idcards_path = upload_idcard(idcards_pdf, event_name=event_name, ticket_ref=f"boat_{boat_number}")
            logger.info(f"[Departure] Uploaded manifest to {manifest_path} and ID cards to {idcards_path}")

        # Reply with summary + export buttons
        buttons = [
            [InlineKeyboardButton("📄 Export Manifest (PDF)", callback_data=f"exportpdf:{boat_number}")],
            [InlineKeyboardButton("🪪 Export ID Cards (PDF)", callback_data=f"exportidcards:{boat_number}")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        await update.message.reply_text(
            f"🛥️ Boat {boat_number} departed at {departure_time.strftime('%H:%M')}.\n\n"
            f"{manifest_text}",
            reply_markup=reply_markup
        )
        logger.info(f"[Departure] Boat {boat_number} marked as departed and manifest export triggered.")

    except Exception as e:
        log_and_raise("Departure", "running /departed", e)