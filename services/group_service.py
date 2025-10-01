from sqlalchemy.orm import Session
from db.models import BookingGroup
from config.logger import logger

def get_or_create_group(db: Session, phone: str, event_name: str) -> BookingGroup:
    """
    Get existing group or create a new one for phone+event combination.
    """
    try:
        # Look for existing group with this phone AND event
        group = db.query(BookingGroup).filter(
            BookingGroup.phone == phone,
            BookingGroup.event_id == event_name
        ).first()
        
        if not group:
            # Create new group scoped to event - FIX: PASS event_name as event_id
            group = BookingGroup(phone=phone, event_id=event_name)  # THIS WAS MISSING
            db.add(group)
            db.flush()
            logger.info(f"[Group] Created new group {group.id} for phone {phone} in event {event_name}")
        else:
            logger.info(f"[Group] Using existing group {group.id} for phone {phone} in event {event_name}")
        
        return group
        
    except Exception as e:
        logger.error(f"[Group] Failed to get/create group for {phone} in {event_name}: {e}")
        raise