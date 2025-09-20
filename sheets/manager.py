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
        metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = [s["properties"]["title"] for s in metadata.get("sheets", [])]
        if event_name in existing_sheets:
            logger.warning(f"[Sheets] Sheet '{event_name}' already exists — skipping creation.")
            return

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
        # booking_row already includes Event as the 2nd column
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{MASTER_TAB}!A:A",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [booking_row]}
        ).execute()
        logger.info(f"[Sheets] Booking appended to Master for event '{event_name}'.")
    except Exception as e:
        log_and_raise("Sheets", "appending booking to Master", e)


def append_to_event(event_name: str, booking_row: list):
    """Append a booking to the active event tab (no Event column)."""
    try:
        # Strip out the Event column (index 1) for event tab
        row_for_event = [booking_row[0]] + booking_row[2:]
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{event_name}!A:A",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row_for_event]}
        ).execute()
        logger.info(f"[Sheets] Booking appended to event tab '{event_name}'.")
    except Exception as e:
        log_and_raise("Sheets", f"appending booking to event tab {event_name}", e)

def update_booking_in_sheets(event_name: str, booking):
    """Update a booking row in both Master and event tab using the booking's ticket_ref."""
    try:
        updates = {
            "ArrivalBoatBoarded": str(booking.arrival_boat_boarded or ""),
            "DepartureBoatBoarded": str(booking.departure_boat_boarded or ""),
            "CheckinTime": booking.checkin_time.isoformat() if booking.checkin_time else "",
            "Status": booking.status or "",
            "ID Doc URL": booking.id_doc_url or ""
        }
        ticket_ref = booking.ticket_ref
        update_booking_row(event_name, ticket_ref, updates)
        logger.info(f"[Sheets] Booking {ticket_ref} updated in Master and {event_name}")
    except Exception as e:
        log_and_raise("Sheets", f"updating booking {getattr(booking, 'ticket_ref', booking.id)}", e)


def update_booking_row(event_name: str, booking_id: str, updates: dict):
    """
    Update a booking row in both Master and event tab using TicketRef (booking_id).
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
                # TicketRef is always column index 2
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
                    logger.info(f"[Sheets] Booking {booking_id} updated in {tab} (row {i})")
                    break
    except Exception as e:
        log_and_raise("Sheets", f"updating booking {booking_id}", e)


def update_booking_photo(event_name: str, ticket_ref: str, photo_url: str):
    """Convenience helper: update only the ID Doc URL for a booking in both Master and event tab."""
    try:
        updates = {"ID Doc URL": photo_url}
        update_booking_row(event_name, ticket_ref, updates)
        logger.info(f"[Sheets] Photo URL updated for {ticket_ref} in Master and {event_name}")
    except Exception as e:
        log_and_raise("Sheets", f"updating photo for {ticket_ref}", e)

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
        if not pdf_bytes:
            raise Exception("No PDF bytes generated")

        # Optionally upload to Drive
        filename = f"Boat_{boat_number}_Manifest.pdf"
        url = upload_to_drive(pdf_bytes, filename, event_name or "General")

        logger.info(f"[Sheets] Manifest PDF generated and uploaded for Boat {boat_number}: {url}")
        return url

    except Exception as e:
        log_and_raise("Sheets", f"exporting manifest PDF for boat {boat_number}", e)