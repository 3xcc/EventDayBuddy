from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from config.logger import logger, log_and_raise
from config.envs import GOOGLE_SHEET_ID, GOOGLE_CREDS_JSON  # Centralized env vars

# ===== Config =====
SPREADSHEET_ID = GOOGLE_SHEET_ID
MASTER_TAB = "Master"

# Headers for Master tab (includes Event column)
MASTER_HEADERS = [
    "No", "Event", "T. Reference", "Name", "ID", "Number",
    "Male' Dep", "Resort Dep", "Paid Amount", "Transfer slip Ref",
    "Ticket Type", "Check in Time", "Boat", "Status", "ID Doc URL"
]

# Headers for Event tabs (no Event column)
EVENT_HEADERS = [
    "No", "T. Reference", "Name", "ID", "Number",
    "Male' Dep", "Resort Dep", "Paid Amount", "Transfer slip Ref",
    "Ticket Type", "Check in Time", "Boat", "Status", "ID Doc URL"
]

# ===== Init Google Sheets API =====
try:
    creds = Credentials.from_service_account_info(
        eval(GOOGLE_CREDS_JSON),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    service = build("sheets", "v4", credentials=creds)
    logger.info("[Sheets] Google Sheets API client initialized.")
except Exception as e:
    log_and_raise("Sheets Init", "initializing Google Sheets API client", e)


# ===== Core Functions =====
def create_event_tab(event_name: str):
    """Create a new event tab with correct headers (no Event column)."""
    try:
        logger.info(f"[Sheets] Creating event tab: {event_name}")
        requests = [{
            "addSheet": {
                "properties": {
                    "title": event_name,
                    "gridProperties": {
                        "rowCount": 1000,
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
    except Exception as e:
        log_and_raise("Sheets", f"creating event tab {event_name}", e)


def append_to_master(event_name: str, booking_row: list):
    """Append a booking to the Master tab (with Event column)."""
    try:
        row_with_event = [None, event_name] + booking_row  # No col left blank for auto-number
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
            body={"values": [[None] + booking_row]}  # No col left blank for auto-number
        ).execute()
        logger.info(f"[Sheets] Booking appended to event tab '{event_name}'.")
    except Exception as e:
        log_and_raise("Sheets", f"appending booking to event tab {event_name}", e)


def update_booking_in_sheets(event_name: str, reference: str, updates: dict):
    """
    Update a booking row in both Master and event tab.
    `updates` is a dict mapping column header to new value.
    """
    try:
        # TODO: Implement search by T. Reference and update cells in both tabs
        logger.info(f"[Sheets] Updating booking {reference} in Master and {event_name} with {updates}")
    except Exception as e:
        log_and_raise("Sheets", f"updating booking {reference}", e)