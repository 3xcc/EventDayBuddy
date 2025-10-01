#!/usr/bin/env python3
"""Script to update checkin.py to use session leg_type"""

import re

# Read the file
with open('bot/checkin.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("Starting checkin.py updates...")

# 1. Update show_booking_selection function to use session leg_type
# Replace the logic that checks both legs with logic that uses session leg_type

old_show_booking_logic = '''        # Check which legs are needed
        needs_arrival = not booking.arrival_boat_boarded
        needs_departure = not booking.departure_boat_boarded
        
        # If both legs are completed
        if not needs_arrival and not needs_departure:
            await update.message.reply_text(
                f"✅ {booking.name} is already checked in for both arrival and departure.\\n"
                f"Arrival: Boat {booking.arrival_boat_boarded}\\n"
                f"Departure: Boat {booking.departure_boat_boarded}"
            )
            return

        # Build appropriate buttons
        buttons = []
        if needs_arrival:
            buttons.append([InlineKeyboardButton("✅ Arrival Boarding", callback_data=f"confirm:arrival:{booking.id}")])
        if needs_departure:
            buttons.append([InlineKeyboardButton("✅ Departure Boarding", callback_data=f"confirm:departure:{booking.id}")])
        
        buttons.append([InlineKeyboardButton("⏭️ Skip", callback_data=f"skip:{booking.id}")])
        reply_markup = InlineKeyboardMarkup(buttons)'''

new_show_booking_logic = '''        # Get active session to determine leg type
        with get_db() as db:
            session = db.query(BoardingSession).filter(BoardingSession.is_active.is_(True)).first()
            if not session:
                await update.message.reply_text("⚠️ No active boat session. Use /boatready first.")
                return

            leg_type = session.leg_type

        # Check which leg is needed based on session leg_type
        if leg_type == "arrival":
            needs_checkin = not booking.arrival_boat_boarded
            leg_status = f"Boat {booking.arrival_boat_boarded}" if booking.arrival_boat_boarded else "Not checked in"
        else:  # departure
            needs_checkin = not booking.departure_boat_boarded
            leg_status = f"Boat {booking.departure_boat_boarded}" if booking.departure_boat_boarded else "Not checked in"

        # If already checked in for this leg
        if not needs_checkin:
            leg_emoji = "🛬" if leg_type == "arrival" else "🛫"
            await update.message.reply_text(
                f"✅ {booking.name} is already checked in for {leg_emoji} {leg_type.upper()}.\\n"
                f"{leg_type.capitalize()}: {leg_status}"
            )
            return

        # Build check-in button for current leg only
        leg_emoji = "🛬" if leg_type == "arrival" else "🛫"
        buttons = [
            [InlineKeyboardButton(f"✅ {leg_emoji} Check-in for {leg_type.capitalize()}", callback_data=f"confirm:{leg_type}:{booking.id}")],
            [InlineKeyboardButton("⏭️ Skip", callback_data=f"skip:{booking.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)'''

content = content.replace(old_show_booking_logic, new_show_booking_logic)

# 2. Update group checkin capacity check
old_group_capacity = '''            # Count current passengers
            current_passenger_count = db.query(Booking).filter(
                Booking.arrival_boat_boarded == session.boat_number
            ).count()

            # Count how many in this group need check-in
            group_needs_checkin = [b for b in bookings if not b.arrival_boat_boarded or not b.departure_boat_boarded]'''

new_group_capacity = '''            leg_type = session.leg_type

            # Count current passengers for this leg
            if leg_type == "arrival":
                current_passenger_count = db.query(Booking).filter(
                    Booking.arrival_boat_boarded == session.boat_number
                ).count()
            else:  # departure
                current_passenger_count = db.query(Booking).filter(
                    Booking.departure_boat_boarded == session.boat_number
                ).count()

            # Count how many in this group need check-in for this leg
            if leg_type == "arrival":
                group_needs_checkin = [b for b in bookings if not b.arrival_boat_boarded]
            else:  # departure
                group_needs_checkin = [b for b in bookings if not b.departure_boat_boarded]'''

content = content.replace(old_group_capacity, new_group_capacity)

# 3. Update group checkin logic
old_group_checkin = '''            # Check in all passengers that need it
            now = datetime.now()
            checked_in_count = 0

            for booking in group_needs_checkin:
                # Determine which legs to check in
                needs_arrival = not booking.arrival_boat_boarded
                needs_departure = not booking.departure_boat_boarded

                if needs_arrival:
                    booking.arrival_boat_boarded = session.boat_number
                if needs_departure:
                    booking.departure_boat_boarded = session.boat_number

                booking.status = "checked_in"
                booking.checkin_time = now

                # Log check-in
                legs_checked = []
                if needs_arrival:
                    legs_checked.append("arrival")
                if needs_departure:
                    legs_checked.append("departure")

                checkin_log = CheckinLog(
                    booking_id=booking.id,
                    boat_number=session.boat_number,
                    confirmed_by=user_id,
                    method=f"group-{'-'.join(legs_checked)}"
                )
                db.add(checkin_log)
                checked_in_count += 1'''

new_group_checkin = '''            # Check in all passengers that need it for this leg
            now = datetime.now()
            checked_in_count = 0

            for booking in group_needs_checkin:
                # Update only the current leg
                if leg_type == "arrival":
                    booking.arrival_boat_boarded = session.boat_number
                else:  # departure
                    booking.departure_boat_boarded = session.boat_number

                # Update status to checked_in if at least one leg is completed
                if booking.arrival_boat_boarded or booking.departure_boat_boarded:
                    booking.status = "checked_in"
                    booking.checkin_time = now

                # Log check-in for this leg
                checkin_log = CheckinLog(
                    booking_id=booking.id,
                    boat_number=session.boat_number,
                    confirmed_by=user_id,
                    method=f"group-{leg_type}"
                )
                db.add(checkin_log)
                checked_in_count += 1'''

content = content.replace(old_group_checkin, new_group_checkin)

# 4. Update group checkin success message
old_success_msg = '''        await query.edit_message_text(
            f"✅ Group check-in completed!\\n"
            f"📞 Phone: {phone_number}\\n"
            f"👥 Checked in: {checked_in_count} passenger(s)\\n"
            f"🛳 Boat: {session.boat_number}"
        )'''

new_success_msg = '''        leg_emoji = "🛬" if leg_type == "arrival" else "🛫"
        await query.edit_message_text(
            f"✅ Group check-in completed!\\n"
            f"📞 Phone: {phone_number}\\n"
            f"👥 Checked in: {checked_in_count} passenger(s)\\n"
            f"🛳 Boat: {session.boat_number}\\n"
            f"Leg: {leg_emoji} {leg_type.upper()}"
        )'''

content = content.replace(old_success_msg, new_success_msg)

# 5. Update confirm_boarding capacity check to verify leg matches session
old_confirm_capacity = '''            # === FIXED CAPACITY CHECK ===
            if leg == "arrival":
                # Count bookings with arrival on THIS boat (regardless of status)
                current_passenger_count = db.query(Booking).filter(
                    Booking.arrival_boat_boarded == session.boat_number
                ).count()
            else:  # departure
                # Count bookings with departure on THIS boat (regardless of status)
                current_passenger_count = db.query(Booking).filter(
                    Booking.departure_boat_boarded == session.boat_number
                ).count()'''

new_confirm_capacity = '''            # Verify leg matches session leg_type
            if leg != session.leg_type:
                await query.edit_message_text(
                    f"❌ Current session is for {session.leg_type.upper()} boarding.\\n"
                    f"Cannot check in for {leg.upper()} boarding.\\n"
                    f"Please start a new session with /boatready for {leg} boarding."
                )
                return

            # === FIXED CAPACITY CHECK ===
            if leg == "arrival":
                # Count bookings with arrival on THIS boat (regardless of status)
                current_passenger_count = db.query(Booking).filter(
                    Booking.arrival_boat_boarded == session.boat_number
                ).count()
            else:  # departure
                # Count bookings with departure on THIS boat (regardless of status)
                current_passenger_count = db.query(Booking).filter(
                    Booking.departure_boat_boarded == session.boat_number
                ).count()'''

content = content.replace(old_confirm_capacity, new_confirm_capacity)

# 6. Update show_booking_selection caption to include current session info
old_caption = '''        caption = (
            f"👤 {booking.name}\\n"
            f"ID: {booking.id_number}\\n"
            f"Phone: {booking.phone}\\n"
            f"Male Dep: {booking.male_dep or '-'}\\n"
            f"Resort Dep: {booking.resort_dep or '-'}\\n"
        )'''

new_caption = '''        caption = (
            f"👤 {booking.name}\\n"
            f"ID: {booking.id_number}\\n"
            f"Phone: {booking.phone}\\n"
            f"Male Dep: {booking.male_dep or '-'}\\n"
            f"Resort Dep: {booking.resort_dep or '-'}\\n\\n"
            f"Current Session: {leg_emoji} {leg_type.upper()}\\n"
        )'''

content = content.replace(old_caption, new_caption)

# Write the updated content
with open('bot/checkin.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated bot/checkin.py")
print("Summary of changes:")
print("1. show_booking_selection now uses session leg_type instead of showing both legs")
print("2. Group check-in capacity checks use leg-specific counts")
print("3. Group check-in only updates the current leg type")
print("4. Added leg type verification in confirm_boarding")
print("5. Updated UI messages to show current session leg type")
