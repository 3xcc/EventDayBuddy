import os
import time
from datetime import datetime, timezone, timedelta

# Maldives Time (GMT+5)
MALDIVES_TZ = timezone(timedelta(hours=5))

def get_maldives_time() -> datetime:
    """Get current time in Maldives timezone (GMT+5)."""
    return datetime.now(MALDIVES_TZ)

def set_maldives_timezone():
    """Set the system timezone to Maldives time for this process."""
    os.environ['TZ'] = 'Indian/Maldives'
    time.tzset()

def format_maldives_time(dt: datetime = None) -> str:
    """Format datetime for Maldives time display."""
    if dt is None:
        dt = get_maldives_time()
    return dt.strftime('%Y-%m-%d %H:%M') + " (GMT+5)"
