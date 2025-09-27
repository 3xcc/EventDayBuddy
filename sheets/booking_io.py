    from googleapiclient.errors import HttpError
    from config.logger import logger, log_and_raise
    from .client import service, SPREADSHEET_ID
    from .constants import MASTER_TAB, MASTER_HEADERS, EVENT_HEADERS, ROW_FETCH_LIMIT
    from .validators import validate_sheet_alignment
    from utils.booking_schema import build_event_row


    # --- Helpers ---

    def excel_col(n: int) -> str:
        """Convert 1-based column index to Excel column letters (A, B, ..., Z, AA, AB...)."""
        result = ""
        while n:
            n, r = divmod(n - 1, 26)
            result = chr(65 + r) + result
        return result


    # --- Core I/O functions ---

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
                range=f"{MASTER_TAB}!A1",   # ✅ changed from !A:A
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [booking_row]}
                ).execute()
            logger.info(f"[Sheets] Booking appended to Master for event '{event_name}'.")
        except Exception as e:
            log_and_raise("Sheets", "appending booking to Master", e)


    def append_to_event(event_name: str, master_row: list):
        """Append a booking to the event tab using schema mapping."""
        try:
            event_row = build_event_row(master_row)
            service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{event_name}!A1",   # ✅ changed from !A:A
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [event_row]}
            ).execute()
            logger.info(f"[Sheets] Booking appended to event tab '{event_name}'.")
        except Exception as e:
            log_and_raise("Sheets", f"appending booking to event tab {event_name}", e)

    def bulk_append_bookings(event_name: str, master_rows: list[list]):
        """
        Append multiple bookings to both Master and Event tabs.
        master_rows should be aligned with MASTER_HEADERS.
        """
        try:
            if not master_rows:
                logger.info("[Sheets] No rows to append.")
                return

            validate_sheet_alignment(MASTER_TAB, MASTER_HEADERS)
            validate_sheet_alignment(event_name, EVENT_HEADERS)

            # Append to Master
            service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{MASTER_TAB}!A1",   # ✅ changed from !A:A
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": master_rows}
            ).execute()

            # Derive and append to Event
            event_rows = [build_event_row(row) for row in master_rows]
            service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{event_name}!A1",   # ✅ changed from !A:A
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": event_rows}
            ).execute()

            logger.info(f"[Sheets] Bulk appended {len(master_rows)} bookings to Master and '{event_name}' tabs.")

        except Exception as e:
            log_and_raise("Sheets", f"bulk appending bookings for {event_name}", e)


    def update_booking_row(event_name: str, master_row: list, event_row: list):
        """
        Update an existing booking in both Master and Event tabs.
        Looks up by TicketRef (dynamic index from headers).
        """
        try:
            ticket_ref = master_row[MASTER_HEADERS.index("TicketRef")]

            # --- Update Master ---
            validate_sheet_alignment(MASTER_TAB, MASTER_HEADERS)
            master_result = service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{MASTER_TAB}!A2:{excel_col(len(MASTER_HEADERS))}{ROW_FETCH_LIMIT}"
            ).execute()
            master_rows = master_result.get("values", [])

            idx_ticket_master = MASTER_HEADERS.index("TicketRef")
            for idx, row in enumerate(master_rows, start=2):
                if len(row) > idx_ticket_master and row[idx_ticket_master].strip() == ticket_ref:
                    service.spreadsheets().values().update(
                        spreadsheetId=SPREADSHEET_ID,
                        range=f"{MASTER_TAB}!A{idx}:{excel_col(len(MASTER_HEADERS))}{idx}",
                        valueInputOption="RAW",
                        body={"values": [master_row]}
                    ).execute()
                    logger.info(f"[Sheets] Updated Master row {idx} for ticket {ticket_ref}")
                    break

            # --- Update Event ---
            validate_sheet_alignment(event_name, EVENT_HEADERS)
            event_result = service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{event_name}!A2:{excel_col(len(EVENT_HEADERS))}{ROW_FETCH_LIMIT}"
            ).execute()
            event_rows = event_result.get("values", [])

            idx_ticket_event = EVENT_HEADERS.index("T. Reference")
            for idx, row in enumerate(event_rows, start=2):
                if len(row) > idx_ticket_event and row[idx_ticket_event].strip() == ticket_ref:
                    service.spreadsheets().values().update(
                        spreadsheetId=SPREADSHEET_ID,
                        range=f"{event_name}!A{idx}:{excel_col(len(EVENT_HEADERS))}{idx}",
                        valueInputOption="RAW",
                        body={"values": [event_row]}
                    ).execute()
                    logger.info(f"[Sheets] Updated Event row {idx} for ticket {ticket_ref}")
                    break

        except Exception as e:
            log_and_raise("Sheets", f"updating booking {ticket_ref}", e)
            
    def update_booking_photo(event_name: str, ticket_ref: str, photo_url: str):
        """
        Update only the ID Doc URL for a booking in both Master and Event tabs.
        Looks up by TicketRef (col 3 in Master, col 2 in Event).
        """
        try:
            # --- Update Master ---
            validate_sheet_alignment(MASTER_TAB, MASTER_HEADERS)
            master_result = service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{MASTER_TAB}!A2:{excel_col(len(MASTER_HEADERS))}{ROW_FETCH_LIMIT}"
            ).execute()
            master_rows = master_result.get("values", [])

            idx_ticket = MASTER_HEADERS.index("TicketRef")
            idx_photo = MASTER_HEADERS.index("ID Doc URL")

            for idx, row in enumerate(master_rows, start=2):
                if len(row) > idx_ticket and row[idx_ticket] == ticket_ref:
                    service.spreadsheets().values().update(
                        spreadsheetId=SPREADSHEET_ID,
                        range=f"{MASTER_TAB}!{excel_col(idx_photo+1)}{idx}",
                        valueInputOption="RAW",
                        body={"values": [[photo_url]]}
                    ).execute()
                    logger.info(f"[Sheets] Updated Master photo for ticket {ticket_ref} at row {idx}")
                    break

            # --- Update Event ---
            validate_sheet_alignment(event_name, EVENT_HEADERS)
            event_result = service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{event_name}!A2:{excel_col(len(EVENT_HEADERS))}{ROW_FETCH_LIMIT}"
            ).execute()
            event_rows = event_result.get("values", [])

            idx_ticket_event = EVENT_HEADERS.index("T. Reference")
            idx_photo_event = EVENT_HEADERS.index("ID Doc URL")

            for idx, row in enumerate(event_rows, start=2):
                if len(row) > idx_ticket_event and row[idx_ticket_event] == ticket_ref:
                    service.spreadsheets().values().update(
                        spreadsheetId=SPREADSHEET_ID,
                        range=f"{event_name}!{excel_col(idx_photo_event+1)}{idx}",
                        valueInputOption="RAW",
                        body={"values": [[photo_url]]}
                    ).execute()
                    logger.info(f"[Sheets] Updated Event photo for ticket {ticket_ref} at row {idx}")
                    break

        except Exception as e:
            log_and_raise("Sheets", f"updating booking photo for {ticket_ref}", e)