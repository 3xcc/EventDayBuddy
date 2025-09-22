import json
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError
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
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=creds)
    logger.info("[Sheets] Google Sheets API client initialized.")
except Exception as e:
    log_and_raise("Sheets Init", "initializing Google Sheets API client", e)


def _headers_for_tab(tab: str) -> list:
    return MASTER_HEADERS if tab == MASTER_TAB else EVENT_HEADERS


def _ticket_ref_col_for_tab(tab: str) -> int:
    # Master has Event column, so TicketRef is index 2; Event tabs have no Event column, so TicketRef is index 1
    return 2 if tab == MASTER_TAB else 1


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
            "Check in Time": booking.checkin_time.isoformat() if booking.checkin_time else "",
            "Status": booking.status or "",
            "ID Doc URL": booking.id_doc_url or ""
        }
        ticket_ref = booking.ticket_ref
        update_booking_row(event_name, ticket_ref, updates)
        logger.info(f"[Sheets] Booking {ticket_ref} updated in Master and {event_name}")
    except Exception as e:
        ident = getattr(booking, "ticket_ref", getattr(booking, "id", "unknown"))
        log_and_raise("Sheets", f"updating booking {ident}", e)


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
            headers = _headers_for_tab(tab)
            ref_col = _ticket_ref_col_for_tab(tab)

            result = sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{tab}!A2:Z{ROW_FETCH_LIMIT}"
            ).execute()
            rows = result.get("values", [])

            found = False
            for i, row in enumerate(rows, start=2):
                if len(row) > ref_col and str(row[ref_col]).strip().lower() == booking_id_lower:
                    updated_row = list(row)

                    # Ensure row has at least the number of header columns
                    if len(updated_row) < len(headers):
                        updated_row.extend([""] * (len(headers) - len(updated_row)))

                    for key, value in updates.items():
                        if key in headers:
                            col_index = headers.index(key)
                            updated_row[col_index] = value

                    sheet.values().update(
                        spreadsheetId=SPREADSHEET_ID,
                        range=f"{tab}!A{i}",
                        valueInputOption="RAW",
                        body={"values": [updated_row]}
                    ).execute()
                    logger.info(f"[Sheets] Booking {booking_id} updated in {tab} (row {i})")
                    found = True
                    break

            if not found:
                logger.warning(f"[Sheets] Booking {booking_id} not found in {tab}")

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
            # Ensure row is padded to header length for safe indexing
            if len(row) < len(headers):
                row = row + [""] * (len(headers) - len(row))

            # Column indices in MASTER_HEADERS
            idx_event = headers.index("Event")            # 1
            idx_status = headers.index("Status")          # 12
            idx_arrival_boarded = headers.index("ArrivalBoatBoarded")    # 16
            idx_departure_boarded = headers.index("DepartureBoatBoarded") # 17

            boat_match = (str(row[idx_arrival_boarded]) == str(boat_number)) or \
                         (str(row[idx_departure_boarded]) == str(boat_number))
            status_match = row[idx_status] == "checked-in"
            event_match = True if not event_name else row[idx_event] == event_name

            if boat_match and status_match and event_match:
                manifest.append(dict(zip(headers, row)))

        logger.info(f"[Sheets] Retrieved {len(manifest)} checked-in rows for Boat {boat_number}")
        return manifest
    except Exception as e:
        log_and_raise("Sheets", f"getting manifest for boat {boat_number}", e)


def export_manifest_pdf(boat_number: str, event_name: str = None):
    """
    Generate and upload a manifest PDF to Supabase.
    Returns the Supabase path (e.g. manifests/<event>/boat_<n>.pdf).
    """
    try:
        from utils.supabase_storage import upload_manifest
        from utils.pdf_generator import generate_manifest_pdf

        pdf_bytes = generate_manifest_pdf(boat_number, event_name=event_name)
        if not pdf_bytes:
            raise Exception("No PDF bytes generated")

        path = upload_manifest(pdf_bytes, event_name or "General", boat_number)
        logger.info(f"[Sheets] Manifest PDF uploaded to Supabase for Boat {boat_number}: {path}")
        return path
    except Exception as e:
        log_and_raise("Sheets", f"exporting manifest PDF for boat {boat_number}", e)