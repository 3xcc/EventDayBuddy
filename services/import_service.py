from config.logger import logger, log_and_raise
from utils.booking_parser import parse_bookings_file
from utils.import_summary import format_import_summary
from db import booking_ops
from db.init import get_db
from db.models import Booking, Event, Config
from sheets import booking_io
from utils.booking_schema import build_master_row  # use canonical builder


def _map_rows_for_sheets(valid_rows: list[dict], event_name: str) -> list[list]:
    """Convert parsed booking dicts into row lists aligned with MASTER_HEADERS."""
    rows = []
    for r in valid_rows:
        booking_dict = {
            "ticket_ref": r.get("ticket_ref", ""),
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


def run_bulk_import(file_bytes: bytes, triggered_by: str, event_name: str = None) -> dict:
    """
    Orchestrates bulk import of bookings from a CSV/XLS file.
    Ensures bookings are tied to the active Event row in DB.
    """
    try:
        # Step 0: Resolve active event
        with get_db() as db:
            if not event_name:
                cfg = db.query(Config).filter(Config.key == "active_event").first()
                event_name = cfg.value if cfg else "Master"

            # Ensure Event row exists
            event = db.query(Event).filter(Event.name == event_name).first()
            if not event:
                event = Event(name=event_name)
                db.add(event)
                db.commit()
                db.refresh(event)

            event_name = event.name

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
    inserted_ids = booking_ops.bulk_insert_bookings(valid_rows, triggered_by, event_name=event_name)
        logger.info(f"[Import] Inserted {len(inserted_ids)} bookings into DB for event '{event_name}'")

        # Step 2.5: Fetch authoritative records back from DB
        with get_db() as db:
            inserted_bookings = db.query(Booking).filter(Booking.id.in_(inserted_ids)).all()
            booking_dicts = []
            for b in inserted_bookings:
                booking_dicts.append({
                    "ticket_ref": b.ticket_ref,
                    "name": b.name,
                    "id_number": b.id_number,
                    "phone": b.phone,
                    "male_dep": b.male_dep,
                    "resort_dep": b.resort_dep,
                    "arrival_time": b.arrival_time,
                    "departure_time": b.departure_time,
                    "paid_amount": b.paid_amount,
                    "transfer_ref": b.transfer_ref,
                    "ticket_type": b.ticket_type,
                    "status": b.status,
                    "id_doc_url": b.id_doc_url,
                    "group_id": b.group_id,
                    "created_at": b.created_at,
                    "updated_at": b.updated_at,
                })

        # Step 3: Append to Sheets
        sheet_rows = _map_rows_for_sheets(booking_dicts, event_name)
        booking_io.bulk_append_bookings(event_name, sheet_rows)
        logger.info(f"[Import] Appended {len(sheet_rows)} bookings to Sheets for event '{event_name}'")

        # Step 4: Collect missing photos
        missing_photos = [row["id_number"] for row in booking_dicts if row.get("id_number")]

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