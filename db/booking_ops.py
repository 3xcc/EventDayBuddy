from services.booking_service import generate_ticket_ref
from typing import List, Dict
from config.logger import logger, log_and_raise
from db.init import get_db
from db.models import Booking, Event
from sqlalchemy.exc import SQLAlchemyError

def bulk_insert_bookings(rows: List[Dict], triggered_by: str) -> List[int]:
    """
    Insert multiple bookings in a single transaction.
    Returns list of inserted booking IDs.
    Rolls back if any insert fails.
    """
    inserted_ids = []
    try:
        with get_db() as db:
            for row in rows:
                # Always generate ticket_ref if not present or empty
                ticket_ref = row.get("ticket_ref")
                if not ticket_ref:
                    event_name = row.get("event_name") or "Master"
                    ticket_ref = generate_ticket_ref(event_name)
                booking = Booking(
                    event_id=_resolve_event_id(db, row.get("event_name")),
                    ticket_ref=ticket_ref,
                    name=row.get("name"),
                    id_number=row.get("id_number"),
                    phone=row.get("phone"),
                    male_dep=row.get("male_dep"),
                    resort_dep=row.get("resort_dep"),
                    paid_amount=row.get("paid_amount"),
                    transfer_ref=row.get("transfer_ref"),
                    ticket_type=row.get("ticket_type"),
                    status="booked",  # default
                )
                db.add(booking)
                db.flush()  # assign ID before commit
                inserted_ids.append(booking.id)

            logger.info(f"[DB] ✅ Bulk inserted {len(inserted_ids)} bookings (by {triggered_by})")

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


def _resolve_event_id(db, event_name: str) -> int:
    """
    Resolve or create an Event ID from event_name.
    Defaults to 'General' if not provided.
    """
    name = event_name or "Master"
    event = db.query(Event).filter(Event.name == name).first()
    if not event:
        event = Event(name=name)
        db.add(event)
        db.flush()
        logger.info(f"[DB] Created new Event '{name}'")
    return event.id