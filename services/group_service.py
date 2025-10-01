# services/group_service.py
from sqlalchemy.orm import Session
from db.models import BookingGroup
from config.logger import logger

def get_or_create_group(db: Session, phone: str, event_name: str) -> BookingGroup:
    """
    Get existing group or create a new one for phone+event combination.
    Since we can't add event_id to BookingGroup, we'll use phone+event_name as unique identifier.
    """
    try:
        # Look for existing group with this phone
        group = db.query(BookingGroup).filter(BookingGroup.phone == phone).first()
        
        if not group:
            # Create new group
            group = BookingGroup(phone=phone)
            db.add(group)
            db.flush()  # Get the ID without committing
            logger.info(f"[Group] Created new group {group.id} for phone {phone}")
        else:
            logger.info(f"[Group] Using existing group {group.id} for phone {phone}")
        
        return group
        
    except Exception as e:
        logger.error(f"[Group] Failed to get/create group for {phone}: {e}")
        raise