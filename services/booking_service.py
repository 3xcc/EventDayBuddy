from db.models import Booking
from config.logger import logger

def create_booking(db, event_name, name, id_number, phone, male_dep, resort_dep,
                   paid_amount, transfer_ref, ticket_type, arrival_time, departure_time, id_doc_url):
    # Deduplication
    existing = db.query(Booking).filter(
        Booking.event_name == event_name,
        Booking.id_number.ilike(id_number)
    ).first()
    if existing:
        raise Exception(f"Booking already exists for {existing.name} ({existing.id_number})")

    # Generate ticket reference
    prefix = event_name[:3].upper()
    count = db.query(Booking).filter(Booking.event_name == event_name).count()
    ticket_ref = f"{prefix}-{count + 1:03}"

    booking = Booking(
        event_name=event_name,
        ticket_ref=ticket_ref,
        name=name,
        id_number=id_number,
        phone=phone,
        male_dep=male_dep,
        resort_dep=resort_dep,
        paid_amount=paid_amount,
        transfer_ref=transfer_ref,
        ticket_type=ticket_type,
       