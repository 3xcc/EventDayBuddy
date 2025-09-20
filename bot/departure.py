from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from config.envs import ADMIN_CHAT_ID
from db.init import get_db
from db.models import Boat, BoardingSession
from sheets.manager import export_manifest_pdf
from datetime import datetime

# ===== /departed Command =====
async def departed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark boat as departed and export manifest."""
    try:
        user_id = str(update.effective_user.id)
        if user_id != ADMIN_CHAT_ID:
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

            db.commit()

        # Export manifest (stub)
        manifest_summary = export_manifest_pdf(str(boat_number))

        # Reply with summary + export button
        buttons = [
            [InlineKeyboardButton("📄 Export ID Cards (PDF)", callback_data=f"exportpdf:{boat_number}")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        await update.message.reply_text(
            f"🛥️ Boat {boat_number} departed at {departure_time.strftime('%H:%M')}.\n"
            f"{manifest_summary}",
            reply_markup=reply_markup
        )
        logger.info(f"[Departure] Boat {boat_number} marked as departed and manifest export triggered.")

    except Exception as e:
        log_and_raise("Departure", "running /departed", e)