import csv, io, logging
from utils.money import parse_amount
from decimal import Decimal, InvalidOperation
from utils.booking_schema import MASTER_HEADERS, EVENT_HEADERS


def parse_booking_input(update_text: str) -> dict:
    """
    Parse staff-formatted booking text into a structured dict.
    Expected 8 lines:
    Name, ID, Phone, Male' Dep, Resort Dep, Paid Amount, Transfer Ref, Ticket Type
    """
    lines = update_text.splitlines()
    lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith("/newbooking")]

    cleaned = []
    for l in lines:
        # Strip leading numbering like "1)", "1.", or "1 -"
        if len(l) > 2 and l[:2].isdigit() and l[2] in [")", ".", "-", "–"]:
            l = l[3:].strip()
        # Strip "Field: value" → "value"
        if ":" in l:
            _, val = l.split(":", 1)
            l = val.strip()
        cleaned.append(l)

    if len(cleaned) < 8:
        raise ValueError(f"Expected 8 lines, got {len(cleaned)}")

    fields = [
        "name", "id_number", "phone", "male_dep", "resort_dep",
        "paid_amount", "transfer_ref", "ticket_type"
    ]
    data = {field: cleaned[i] for i, field in enumerate(fields)}

    # Normalize
    if data["id_number"]:
        data["id_number"] = data["id_number"].strip().upper()
    if data["phone"]:
        data["phone"] = "".join(ch for ch in data["phone"] if ch.isdigit() or ch == "+")
    if data["paid_amount"]:
        try:
            data["paid_amount"] = Decimal(data["paid_amount"].replace(",", "").replace("$", ""))
        except (InvalidOperation, AttributeError):
            raise ValueError(f"Invalid amount format: {data['paid_amount']}")

    # Validation
    missing = [f for f in ["name", "id_number", "phone"] if not data.get(f)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    return data

def parse_bookings_file(file_bytes: bytes) -> tuple[list[dict], list[str]]:
    """
    Parse a CSV/XLS file into structured booking dicts.
    Supports both Master and Event tab formats.
    Returns (valid_rows, errors).
    """
    valid_rows, errors = [], []

    # --- Decode with fallback encodings ---
    text = None
    for enc in ("utf-8-sig", "utf-16", "latin1"):
        try:
            text = file_bytes.decode(enc)
            logging.info(f"[Parser] Decoded file using {enc}")
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("Unsupported file encoding")

    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip() for h in reader.fieldnames or []]

    # --- Detect schema ---
    is_master = "Event" in headers and "TicketRef" in headers
    is_event = "T. Reference" in headers and "ID" in headers

    if not (is_master or is_event):
        raise ValueError("Unrecognized file format: headers do not match Master or Event schema")

    # --- Row parsing ---
    for idx, row in enumerate(reader, start=2):
        booking, row_errors = {}, []

        if is_master:
            # Map Master headers
            booking = {
                "ticket_ref": row.get("TicketRef", "").strip(),
                "name": row.get("Name", "").strip(),
                "id_number": row.get("IDNumber", "").strip(),
                "phone": row.get("Phone", "").strip(),
                "male_dep": row.get("MaleDep", "").strip(),
                "resort_dep": row.get("ResortDep", "").strip(),
                "arrival_time": row.get("ArrivalTime", "").strip(),
                "departure_time": row.get("DepartureTime", "").strip(),
                "paid_amount": row.get("PaidAmount", "").strip(),
                "transfer_ref": row.get("TransferRef", "").strip(),
                "ticket_type": row.get("TicketType", "").strip(),
                "status": row.get("Status", "").strip() or "booked",
                "id_doc_url": row.get("ID Doc URL", "").strip(),
                "group_id": row.get("GroupID", "").strip(),
            }

        elif is_event:
            # Map Event headers
            booking = {
                "ticket_ref": row.get("T. Reference", "").strip(),
                "name": row.get("Name", "").strip(),
                "id_number": row.get("ID", "").strip(),
                "phone": row.get("Number", "").strip(),
                "male_dep": row.get("Male' Dep", "").strip(),
                "resort_dep": row.get("Resort Dep", "").strip(),
                "arrival_time": row.get("ArrivalTime", "").strip(),
                "departure_time": row.get("DepartureTime", "").strip(),
                "paid_amount": row.get("Paid Amount", "").strip(),
                "transfer_ref": row.get("Transfer slip Ref", "").strip(),
                "ticket_type": row.get("Ticket Type", "").strip(),
                "status": row.get("Status", "").strip() or "booked",
                "id_doc_url": row.get("ID Doc URL", "").strip(),
                "group_id": "",  # Event tab doesn’t have this
            }

        # --- Validation ---
        if not booking["ticket_ref"] or not booking["name"]:
            row_errors.append(f"Row {idx}: Missing TicketRef or Name")

        if row_errors:
            errors.extend(row_errors)
        else:
            valid_rows.append(booking)

    return valid_rows, errors
