import io
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from config.logger import logger, log_and_raise
from db.init import get_db
from db.models import Booking, CheckinLog, Config
from bot.utils.roles import require_role
from sqlalchemy import or_


@require_role("admin")
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show booking statistics for active event."""
    try:
        with get_db() as db:
            # Get active event
            active_event_cfg = db.query(Config).filter(Config.key == "active_event").first()
            if not active_event_cfg or not active_event_cfg.value:
                await update.message.reply_text("❌ No active event set. Use /cpe first.")
                return
            event_name = active_event_cfg.value

            # Get bookings for this event (must have at least one leg time)
            bookings = db.query(Booking).filter(
                Booking.event_id == event_name,
                or_(Booking.male_dep.isnot(None), Booking.resort_dep.isnot(None))
            ).all()

            if not bookings:
                await update.message.reply_text(f"❌ No bookings found for event: {event_name}")
                return

            # Time & Attendance by legs
            male_stats, resort_stats = {}, {}

            def _add(slot_dict, slot_key: str, is_checked: bool):
                if not slot_key:
                    return
                slot_dict.setdefault(slot_key, {"booked": 0, "checked_in": 0})
                slot_dict[slot_key]["booked"] += 1
                if is_checked:
                    slot_dict[slot_key]["checked_in"] += 1

            for b in bookings:
                _add(male_stats,   (b.male_dep   or "").strip(), b.status == "checked_in")
                _add(resort_stats, (b.resort_dep or "").strip(), b.status == "checked_in")

            # Ticket Type counts
            ticket_stats = {}
            for b in bookings:
                ticket_stats[b.ticket_type or "Unknown"] = ticket_stats.get(b.ticket_type or "Unknown", 0) + 1

            # Check-in log count
            status_update_count = db.query(CheckinLog).filter(
                CheckinLog.booking_id.in_([b.id for b in bookings])
            ).count()

            # ─── Build message ──────────────────────────────────────────────
            total_booked = len(bookings)
            total_checked_in = sum(1 for b in bookings if b.status == "checked_in")

            resp = "📊 **Event Statistics**\n"
            resp += f"Event: {event_name}\n"
            resp += f"Total Bookings: {total_booked}\n\n"

            resp += "**📈 Summary**\n"
            resp += f"Total booked = {total_booked}\n"
            resp += f"Total checked-in = {total_checked_in}\n\n"

            # Time & Attendance
            resp += "**⏰ Time & Attendance**\n"
            if male_stats or resort_stats:
                if male_stats:
                    resp += "\n**🛬 Male ➔ Resort (Arrival Leg)**\n"
                    for t in sorted(male_stats):
                        c = male_stats[t]
                        resp += f"{t}  —  booked: {c['booked']}, checked-in: {c['checked_in']}\n"
                if resort_stats:
                    resp += "\n**🛫 Resort ➔ Male (Departure Leg)**\n"
                    for t in sorted(resort_stats):
                        c = resort_stats[t]
                        resp += f"{t}  —  booked: {c['booked']}, checked-in: {c['checked_in']}\n"
            else:
                resp += "No time slots found.\n"

            # Ticket type
            resp += "\n**🎫 Ticket Type + Total**\n"
            if ticket_stats:
                total_tickets = sum(ticket_stats.values())
                for tt, cnt in ticket_stats.items():
                    resp += f"{cnt} - {tt}\n"
                resp += f"Total {total_tickets}\n"
            else:
                resp += "No ticket types found.\n"

            await update.message.reply_text(resp, parse_mode="Markdown")
            logger.info(f"[Stats] Statistics shown for event {event_name} by {update.effective_user.id}")

    except Exception as e:
        log_and_raise("Stats", "generating statistics", e)