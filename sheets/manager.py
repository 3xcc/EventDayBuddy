from .validators import validate_sheet_alignment
from .booking_io import (
    create_event_tab,
    append_to_master,
    append_to_event,
    update_booking_row,
    update_booking_photo,
)
from .queries import get_manifest_rows
from .exports import export_manifest_pdf
from .constants import MASTER_HEADERS, EVENT_HEADERS, MASTER_TAB
from utils.booking_schema import build_master_row, build_event_row


# --- High-level orchestration helpers ---

def ensure_event_tab(event_name: str):
    """Ensure an event tab exists and is aligned."""
    validate_sheet_alignment(MASTER_TAB, MASTER_HEADERS)
    create_event_tab(event_name)
    validate_sheet_alignment(event_name, EVENT_HEADERS)


def add_booking(event_name: str, booking_row: list):
    """Append a booking to both Master and Event sheets."""
    append_to_master(event_name, booking_row)
    append_to_event(event_name, booking_row)


def update_booking(event_name: str, master_row: list, event_row: list):
    """Update booking in both Master and Event sheets."""
    update_booking_row(event_name, master_row, event_row)


def update_photo(event_name: str, ticket_ref: str, photo_url: str):
    """Update only the ID Doc URL for a booking."""
    update_booking_photo(event_name, ticket_ref, photo_url)


def manifest_for_boat(boat_number: str, event_name: str = None):
    """Retrieve checked-in bookings for a given boat."""
    return get_manifest_rows(boat_number, event_name)


def export_manifest(boat_number: str, event_name: str = None):
    """Generate and upload a manifest PDF."""
    return export_manifest_pdf(boat_number, event_name)