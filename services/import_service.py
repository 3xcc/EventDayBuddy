from config.logger import logger, log_and_raise
from utils.booking_parser import parse_bookings_file
from utils.import_summary import format_import_summary
from db import booking_ops
from sheets import booking_io
from utils.booking_schema import build_master_row  # use canonical builder


def _map_rows_for_sheets(valid_rows: list[dict], event_name: str) -> list[list]:
    """
    Convert parsed booking dicts into row lists aligned with MASTER_HEADERS.
    Uses build_master_row to ensure schema consistency.
    """
    rows = []
    for r in valid_rows:
        booking_dict = {
            "ticket_ref": r.get("ticket_ref", ""),  # Use ticket_ref if present, else blank
            "name": r.get("name"),
            "id_number": r.get("id_number"),
            "phone": r.get("phone"),
            "male_dep": r.get("male_dep"),
            "resort_dep": r.get("resort_dep"),
            "arrival_time": r.get("arrival_time"),
            "departure_time": r.get("departure_time"),
            "paid_amount": r.get("paid_amount"),
            "transfer_ref": r.get("transfer_ref"),
            "ticket_type": r.get("ticket_type"),
            "status": "booked",
            "id_doc_url": None,
            "group_id": r.get("group_id"),
            "created_at": None,
            "updated_at": None,
        }
        rows.append(build_master_row(booking_dict, event_name))
    return rows


def run_bulk_import(file_bytes: bytes, triggered_by: str, event_name: str = "Master") -> dict:
    """
    Orchestrates bulk import of bookings from a CSV/XLS file.
    Returns a structured result dict:
    {
        "inserted": int,
        "skipped": int,
        "errors": list[str],
        "missing_photos": list[str]
    }
    """
    try:
        # Step 1: Parse file
        valid_rows, errors = parse_bookings_file(file_bytes)
        logger.info(f"[Import] Parsed {len(valid_rows)} valid rows, {len(errors)} errors")

        if not valid_rows:
            return {
                "inserted": 0,
                "skipped": len(errors),
                "errors": errors or ["No valid rows found"],
                "missing_photos": []
            }

        # Step 2: Insert into DB (atomic transaction)
        inserted_ids = booking_ops.bulk_insert_bookings(valid_rows, triggered_by)
        logger.info(f"[Import] Inserted {len(inserted_ids)} bookings into DB")

        # Step 3: Append to Sheets (map dicts → Master rows)
        sheet_rows = _map_rows_for_sheets(valid_rows, event_name)
        booking_io.bulk_append_bookings(event_name, sheet_rows)
        logger.info(f"[Import] Appended {len(sheet_rows)} bookings to Sheets")

        # Step 4: Collect missing photos
        missing_photos = [row["id_number"] for row in valid_rows if row.get("id_number")]

        # Step 5: Build result object
        result = {
            "inserted": len(valid_rows),
            "skipped": len(errors),
            "errors": errors,
            "missing_photos": missing_photos,
        }

        return result

    except Exception as e:
        log_and_raise("ImportService", "running bulk import", e)


def summarize_import(result: dict) -> str:
    """Formats operator-facing summary message."""
    return format_import_summary(result)