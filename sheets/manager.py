import json
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from config.logger import logger, log_and_raise
from config.envs import GOOGLE_SHEET_ID, GOOGLE_CREDS_JSON  # Centralized env vars

# ===== Config =====
SPREADSHEET_ID = GOOGLE_SHEET_ID
MASTER_TAB = "Master"
ROW_FETCH_LIMIT = 1000  # Max rows to fetch in updates/lookups

# Headers for Master tab (includes Event column)
MASTER_HEADERS = [
    "No", "Event", "T. Reference", "Name", "ID", "Number",
    "Male' Dep", "Resort Dep", "Paid Amount", "Transfer slip Ref",
    "Ticket Type", "Check in Time", "Status", "ID Doc URL",
    # Extended fields for scheduled vs actual tracking
    "ArrivalTime", "DepartureTime", "ArrivalBoatBoarded", "DepartureBoatBoarded"
]

# Headers for Event tabs (no Event column)
EVENT_HEADERS = [
    "No", "T. Reference", "Name", "ID", "Number",
    "Male' Dep", "Resort Dep", "Paid Amount", "Transfer slip Ref",
    "Ticket Type", "Check in Time", "Status", "ID Doc URL",
    "ArrivalTime", "DepartureTime", "ArrivalBoatBoarded", "DepartureBoatBoarded"
]

# ===== Init Google Sheets API =====
try:
    creds = Credentials.from_service_account_info(
        json.loads(GOOGLE_CREDS_JSON),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    service = build("sheets", "v4", credentials=creds)
    logger.info("[Sheets] Google Sheets API client initialized.")
except Exception as e:
    log_and_raise("Sheets Init", "initializing Google Sheets API client", e)

from googleapiclient.errors import HttpError


def create_event_tab(event_name: str):
    """Create a new event tab with correct headers (no Event column)."""
    try:
        logger.info(f"[Sheets] Creating event tab: {event_name}")

        # ✅ Pre-check: list existing sheets
        metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = [s["properties"]["title"] for s in metadata.get("sheets", [])]

        if event_name in existing_sheets:
            logger.warning(f"[Sheets] Sheet '{event_name}' already exists — skipping creation.")
            return

        # Create the new sheet
        requests = [{
            "addSheet": {
                "properties": {
                    "title": event_name,
                    "gridProperties": {
                        "rowCount": ROW_FETCH_LIMIT,
                        "columnCount": len(EVENT_HEADERS)
                    }
                }
            }
        }]
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": requests}
        ).execute()

        # Write headers
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{event_name}!A1",
            valueInputOption="RAW",
            body={"values": [EVENT_HEADERS]}
        ).execute()

        logger.info(f"[Sheets] Event tab '{event_name}' created successfully.")

    except HttpError as e:
        log_and_raise("Sheets", f"creating event tab {event_name}", e)
    except Exception as e:
        log_and_raise("Sheets", f"creating event tab {event_name}", e)


def append_to_master(event_name: str, booking_row: list):
    """Append a booking to the Master tab (with Event column)."""
    try:
        row_with_event = [None, event_name] + booking_row
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{MASTER_TAB}!A:A",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row_with_event]}
        ).execute()
        logger.info(f"[Sheets] Booking appended to Master for event '{event_name}'.")
    except Exception as e:
        log_and_raise("Sheets", "appending booking to Master", e)


def append_to_event(event_name: str, booking_row: list):
    """Append a booking to the active event tab (no Event column)."""
    try:
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{event_name}!A:A",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [[None] + booking_row]}
        ).execute()
        logger.info(f"[Sheets] Booking appended to event tab '{event_name}'.")
    except Exception as e:
        log_and_raise("Sheets", f"appending booking to event tab {event_name}", e)


def update_booking_in_sheets(event_name: str, booking):
    """
    Update a booking row in both Master and event tab using the booking's ticket_ref.
    """
    try:
        # Build updates dict from Booking object
        updates = {
            "ArrivalBoatBoarded": str(booking.arrival_boat_boarded or ""),
            "DepartureBoatBoarded": str(booking.departure_boat_boarded or ""),
            "Check in Time": booking.checkin_time.isoformat() if booking.checkin_time else "",
            "Status": booking.status or "",
            "ID Doc URL": booking.id_doc_url or ""
        }

        # Use the stored ticket_ref as the row key
        ticket_ref = booking.ticket_ref

        update_booking_row(event_name, ticket_ref, updates)
        logger.info(f"[Sheets] Booking {ticket_ref} updated in Master and {event_name}")

    except Exception as e:
        log_and_raise("Sheets", f"updating booking {getattr(booking, 'ticket_ref', booking.id)}", e)

        
def update_booking_row(event_name: str, booking_id: str, updates: dict):
    """
    Update a booking row in both Master and event tab using T. Reference (booking_id).
    `updates` is a dict mapping column header to new value.
    """
    try:
        sheet = service.spreadsheets()
        tabs = [MASTER_TAB, event_name]
        booking_id_lower = str(booking_id).strip().lower()

        for tab in tabs:
            result = sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{tab}!A2:Z{ROW_FETCH_LIMIT}"
            ).execute()
            rows = result.get("values", [])

            for i, row in enumerate(rows, start=2):
                if len(row) > 2 and str(row[2]).strip().lower() == booking_id_lower:
                    headers = MASTER_HEADERS if tab == MASTER_TAB else EVENT_HEADERS
                    updated_row = row.copy()
                    for key, value in updates.items():
                        if key in headers:
                            col_index = headers.index(key)
                            while len(updated_row) <= col_index:
                                updated_row.append("")
                            updated_row[col_index] = value

                    sheet.values().update(
                        spreadsheetId=SPREADSHEET_ID,
                        range=f"{tab}!A{i}",
                        valueInputOption="RAW",
                        body={"values": [updated_row]}
                    ).execute()
                    logger.info(f"[Sheets] Booking {booking_id} updated in {tab}")
                    break
    except Exception as e:
        log_and_raise("Sheets", f"updating booking {booking_id}", e)


def get_manifest_rows(boat_number: str, event_name: str = None):
    """
    Return all checked-in bookings for a given boat from Master tab.
    Optionally filter by event_name.
    Includes scheduled vs actual fields.
    """
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{MASTER_TAB}!A2:Z{ROW_FETCH_LIMIT}"
        ).execute()
        rows = result.get("values", [])
        headers = MASTER_HEADERS

        manifest = []
        for row in rows:
            if len(row) >= len(headers):
                # Boat match now only checks actual boarded columns
                boat_match = (row[14] == boat_number) or (row[15] == boat_number)
                status_match = row[12] == "checked-in"
                event_match = True if not event_name else row[1] == event_name
                if boat_match and status_match and event_match:
                    manifest.append(dict(zip(headers, row)))

        logger.info(f"[Sheets] Retrieved {len(manifest)} checked-in rows for Boat {boat_number}")
        return manifest
    except Exception as e:
        log_and_raise("Sheets", f"getting manifest for boat {boat_number}", e)


def export_manifest_pdf(boat_number: str, event_name: str = None):
    """
    Generate and optionally upload a manifest PDF for a departed boat.
    Returns a summary string (and could be extended to return a URL).
    """
    try:
        # Local import to avoid circular dependency
        from drive.manifest import generate_manifest_pdf, upload_to_drive

        # Generate PDF bytes
        pdf_bytes = generate_manifest_pdf(boat_number, event_name=event_name)

        logger.info(f"[Sheets] Manifest PDF generated for Boat {boat_number} ({len(pdf_bytes)} bytes)")
        return f"Manifest PDF for Boat {boat_number} generated ({len(pdf_bytes)} bytes)."

    except Exception as e:
        log_and_raise("Sheets", f"exporting manifest PDF for boat {boat_number}", e)