from config.logger import logger, log_and_raise
from .client import service, SPREADSHEET_ID
from .constants import MASTER_TAB, MASTER_HEADERS, ROW_FETCH_LIMIT
from .validators import validate_sheet_alignment


def excel_col(n: int) -> str:
    """Convert 1-based column index to Excel column letters (A, B, ..., Z, AA, AB...)."""
    result = ""
    while n:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result


def get_manifest_rows(boat_number: str, event_name: str = None):
    """
    Return all checked-in bookings for a given boat from Master tab.
    Optionally filter by event_name.
    - Normalizes status, boat number, and event comparisons.
    - Validates headers before reading.
    """
    try:
        # Validate headers before querying
        validate_sheet_alignment(MASTER_TAB, MASTER_HEADERS)

        # Dynamic range based on header length
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{MASTER_TAB}!A2:{excel_col(len(MASTER_HEADERS))}{ROW_FETCH_LIMIT}"
        ).execute()
        rows = result.get("values", [])
        headers = MASTER_HEADERS

        manifest = []
        for row in rows:
            # Pad row to header length
            if len(row) < len(headers):
                row = row + [""] * (len(headers) - len(row))

            idx_event = headers.index("Event")
            idx_status = headers.index("Status")
            idx_arrival_boarded = headers.index("ArrivalBoatBoarded")
            idx_departure_boarded = headers.index("DepartureBoatBoarded")

            # Normalize values for comparison
            status_val = row[idx_status].strip().lower() if row[idx_status] else ""
            arrival_val = str(row[idx_arrival_boarded]).strip()
            departure_val = str(row[idx_departure_boarded]).strip()
            boat_val = str(boat_number).strip()
            event_val = row[idx_event].strip() if row[idx_event] else ""

            boat_match = (arrival_val == boat_val) or (departure_val == boat_val)
            status_match = status_val == "checked-in"
            event_match = True if not event_name else event_val == event_name.strip()

            if boat_match and status_match and event_match:
                manifest.append(dict(zip(headers, row)))

        logger.info(
            f"[Sheets] Retrieved {len(manifest)} checked-in rows for Boat {boat_number}"
            + (f" (event '{event_name}')" if event_name else "")
        )
        return manifest

    except Exception as e:
        log_and_raise("Sheets", f"getting manifest for boat {boat_number}", e)