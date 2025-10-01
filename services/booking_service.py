# services/booking_service.py - UPDATED VERSION
import uuid
from db.models import Booking, Event, BookingGroup  # ADD BookingGroup import
from config.logger import logger

def generate_ticket_ref(event_name: str) -> str:
    """Generate a unique ticket reference with event prefix and short UUID."""
    prefix = event_name[:3].upper() if event_name else "EVT"
    unique_suffix = str(uuid.uuid4())[:8].upper()
    return f"{prefix}-{unique_suffix}"

def create_booking(
    db,
    event_name,
    name,
    id_number,
    phone,
    male_dep,
    resort_dep,
    paid_amount,
    transfer_ref,
    ticket_type,
    arrival_time,
    departure_time,
    id_doc_url=None,
):
    # === Validation ===
    if not all([event_name, name, id_number, phone]):  # ADD phone to required fields
        raise ValueError("Missing required booking fields: event_name, name, id_number, phone")

    # Normalize inputs
    id_number = id_number.strip().upper()
    phone = phone.strip() if phone else None

    # Fetch event by name (ensure it exists)
    event = db.query(Event).filter(Event.name == event_name).first()
    if not event:
        raise ValueError(f"Event with name {event_name} not found")

    # Deduplication
    existing = db.query(Booking).filter(
        Booking.event_id == event_name,
        Booking.id_number == id_number
    ).first()
    if existing:
        raise Exception(f"Booking already exists for {existing.name} ({existing.id_number})")

    # === GROUP ASSIGNMENT - NEW CODE ===
    group = None
    if phone:
        from services.group_service import get_or_create_group  # Import here to avoid circular imports
        group = get_or_create_group(db, phone, event_name)

    # Generate ticket reference
    ticket_ref = generate_ticket_ref(event_name)

    booking = Booking(
        event_id=event_name,
        ticket_ref=ticket_ref,
        name=name.strip(),
        id_number=id_number,
        phone=phone,
        male_dep=male_dep,
        resort_dep=resort_dep,
        paid_amount=paid_amount,
        transfer_ref=transfer_ref,
        ticket_type=ticket_type,
        arrival_time=arrival_time,
        departure_time=departure_time,
        id_doc_url=id_doc_url,
        group_id=group.id if group else None,  # ADD group assignment
    )

    try:
        db.add(booking)
        db.commit()
        db.refresh(booking)
        logger.info(f"[Booking] Created booking {booking.id} ({booking.ticket_ref}) for {booking.name}, group: {group.id if group else 'None'}")
        return booking
    except Exception as e:
        db.rollback()
        logger.error(f"[Booking] Failed to create booking: {e}", exc_info=True)
        raise