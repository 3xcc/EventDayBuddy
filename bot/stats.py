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

            # Get bookings for this event with male_dep or resort_dep
            bookings = db.query(Booking).filter(
                Booking.event_id == event_name,
                or_(Booking.male_dep.isnot(None), Booking.resort_dep.isnot(None))
            ).all()

            if not bookings:
                await update.message.reply_text(f"❌ No bookings found for event: {event_name}")
                return

            # Time & Attendance section
            time_stats = {}
            for booking in bookings:
                # Use departure_time as the time slot (format as HH:MM)
                time_slot = None
                if booking.departure_time:
                    time_slot = booking.departure_time.strftime("%H:%M")
                elif booking.arrival_time:
                    time_slot = booking.arrival_time.strftime("%H:%M")

                if time_slot:
                    if time_slot not in time_stats:
                        time_stats[time_slot] = {"booked": 0, "checked_in": 0}
                    time_stats[time_slot]["booked"] += 1
                    if booking.status == "checked_in":
                        time_stats[time_slot]["checked_in"] += 1

            # Ticket Type section
            ticket_stats = {}
            for booking in bookings:
                ticket_type = booking.ticket_type or "Unknown"
                ticket_stats[ticket_type] = ticket_stats.get(ticket_type, 0) + 1

            # Status update count (checkin logs)
            checkin_logs = db.query(CheckinLog).filter(
                CheckinLog.booking_id.in_([b.id for b in bookings])
            ).all()
            status_update_count = len(checkin_logs)

            # Build response message
            response = "📊 **Event Statistics**\n"
            response += f"Event: {event_name}\n"
            response += f"Total Bookings: {len(bookings)}\n\n"

            # Add summary section
            total_booked = len(bookings)
            total_checked_in = sum(1 for booking in bookings if booking.status == "checked_in")

            response += "**📈 Summary**\n"
            response += f"Total booked = {total_booked}\n"
            response += f"Total Checkedin = {total_checked_in}\n\n"

            # Time & Attendance section
            response += "**⏰ Time & Attendance**\n"
            if time_stats:
                for time_slot in sorted(time_stats.keys()):
                    counts = time_stats[time_slot]
                    response += f"{time_slot} - {counts['booked']}\n"
                    response += f"  booked = {counts['booked']}\n"
                    response += f"  checked_in = {counts['checked_in']}\n"
            else:
                response += "No time slots found.\n"

            response += "\n**🎫 Ticket Type + Total**\n"
            if ticket_stats:
                total_tickets = sum(ticket_stats.values())
                for ticket_type, count in ticket_stats.items():
                    response += f"{count} - {ticket_type}\n"
                response += f"Total {total_tickets}\n"
            else:
                response += "No ticket types found.\n"

            response += f"\n**📋 Status Updates**\n"
            response += f"Total check-in logs: {status_update_count}\n"

            await update.message.reply_text(response, parse_mode='Markdown')

            logger.info(f"[Stats] Statistics shown for event {event_name} by {update.effective_user.id}")

    except Exception as e:
        log_and_raise("Stats", "generating statistics", e)