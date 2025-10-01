from services.booking_service import generate_ticket_ref
from typing import List, Dict
from config.logger import logger, log_and_raise
from db.init import get_db
from db.models import Booking, Event, BookingGroup
from sqlalchemy.exc import SQLAlchemyError

def bulk_insert_bookings(rows: List[Dict], triggered_by: str, event_name: str) -> List[int]:
    """
    Insert multiple bookings in a single transaction, tied to a specific event_name (string).
    Returns list of inserted booking IDs. Rolls back if any insert fails.
    """
    inserted_ids = []
    try:
        with get_db() as db:
            # === GROUP PREPARATION - NEW CODE ===
            # Get all unique phones from the rows
            unique_phones = set(row.get("phone") for row in rows if row.get("phone"))
            phone_to_group = {}
            
            # Get or create groups for each unique phone
            for phone in unique_phones:
                from services.group_service import get_or_create_group  # Import here to avoid circular imports
                group = get_or_create_group(db, phone, event_name)
                phone_to_group[phone] = group

            # Process each row
            for row in rows:
                # Always generate ticket_ref if not present or empty
                ticket_ref = row.get("ticket_ref")
                if not ticket_ref:
                    ticket_ref = generate_ticket_ref(str(event_name))

                # Get group for this booking's phone
                group = None
                phone = row.get("phone")
                if phone and phone in phone_to_group:
                    group = phone_to_group[phone]

                booking = Booking(
                    event_id=event_name,
                    ticket_ref=ticket_ref,
                    name=row.get("name"),
                    id_number=row.get("id_number"),
                    phone=phone,
                    male_dep=row.get("male_dep"),
                    resort_dep=row.get("resort_dep"),
                    paid_amount=row.get("paid_amount"),
                    transfer_ref=row.get("transfer_ref"),
                    ticket_type=row.get("ticket_type"),
                    status="booked",  # default
                    group_id=group.id if group else None,  # ADD group assignment
                )
                db.add(booking)
                db.flush()  # assign ID before commit
                inserted_ids.append(booking.id)

            logger.info(f"[DB] ✅ Bulk inserted {len(inserted_ids)} bookings for event_name={event_name} (by {triggered_by})")
            logger.info(f"[DB] 📞 Created/used {len(phone_to_group)} groups for {len(unique_phones)} unique phones")

        return inserted_ids

    except SQLAlchemyError as e:
        log_and_raise("DB BulkInsert", "inserting bookings", e)


def update_booking(booking_id: int, fields: Dict, triggered_by: str) -> bool:
    """
    Update a single booking with provided fields.
    Returns True if updated, False if not found.
    """
    try:
        with get_db() as db:
            booking = db.query(Booking).filter(Booking.id == booking_id).first()
            if not booking:
                logger.warning(f"[DB] ⚠️ Booking {booking_id} not found for update (by {triggered_by})")
                return False

            for key, value in fields.items():
                if hasattr(booking, key):
                    setattr(booking, key, value)

            logger.info(f"[DB] ✅ Updated booking {booking_id} (by {triggered_by})")
            return True

    except SQLAlchemyError as e:
        log_and_raise("DB Update", f"updating booking {booking_id}", e)


def _resolve_event_name(db, event_name: str) -> str:
    """
    Resolve or create an Event by name, returns the event name (string).
    Defaults to 'Master' if not provided.
    """
    name = event_name or "Master"
    event = db.query(Event).filter(Event.name == name).first()
    if not event:
        event = Event(name=name)
        db.add(event)
        db.flush()
        logger.info(f"[DB] Created new Event '{name}'")
    return event.name