import csv, io, logging
from decimal import Decimal, InvalidOperation
from utils.booking_schema import MASTER_HEADERS, EVENT_HEADERS


def _normalize_amount(value: str):
    """Convert amount strings like '1,200.00' or 'MVR 1200' into Decimal if possible."""
    if not value:
        return None
    try:
        cleaned = value.replace(",", "").replace("$", "").replace("MVR", "").strip()
        return Decimal(cleaned)
    except (InvalidOperation, AttributeError):
        return value  # leave as-is if not parseable


def _normalize_phone(value: str):
    """Keep only digits and leading +."""
    if not value:
        return None
    return "".join(ch for ch in value if ch.isdigit() or ch == "+")


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
        data["phone"] = _normalize_phone(data["phone"])
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
    Parse a CSV file into structured booking dicts.
    Supports Master tab, Event tab, and raw snake_case CSV formats.
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

    # Important: newline="" prevents _csv.Error on embedded newlines
    reader = csv.DictReader(io.StringIO(text, newline=""))
    headers = [h.strip() for h in (reader.fieldnames or [])]

    # --- Detect schema ---
    is_master = "Event" in headers and "TicketRef" in headers
    is_event = "T. Reference" in headers and "ID" in headers
    is_raw   = "ticket_ref" in headers and "id_number" in headers

    if not (is_master or is_event or is_raw):
        raise ValueError("Unrecognized file format: headers do not match Master, Event, or Raw schema")

    # --- Row parsing ---
    for idx, row in enumerate(reader, start=2):
        booking, row_errors = {}, []

        if is_master:
            booking = {
                "ticket_ref": (row.get("TicketRef") or "").strip(),
                "name": (row.get("Name") or "").strip(),
                "id_number": (row.get("IDNumber") or "").strip().upper(),
                "phone": _normalize_phone(row.get("Phone") or ""),
                "male_dep": (row.get("MaleDep") or "").strip(),
                "resort_dep": (row.get("ResortDep") or "").strip(),
                "arrival_time": (row.get("ArrivalTime") or "").strip(),
                "departure_time": (row.get("DepartureTime") or "").strip(),
                "paid_amount": _normalize_amount(row.get("PaidAmount") or ""),
                "transfer_ref": (row.get("TransferRef") or "").strip(),
                "ticket_type": (row.get("TicketType") or "").strip(),
                "status": (row.get("Status") or "").strip() or "booked",
                "id_doc_url": (row.get("ID Doc URL") or "").strip(),
                "group_id": (row.get("GroupID") or "").strip(),
            }

        elif is_event:
            booking = {
                "ticket_ref": (row.get("T. Reference") or "").strip(),
                "name": (row.get("Name") or "").strip(),
                "id_number": (row.get("ID") or "").strip().upper(),
                "phone": _normalize_phone(row.get("Number") or ""),
                "male_dep": (row.get("Male' Dep") or "").strip(),
                "resort_dep": (row.get("Resort Dep") or "").strip(),
                "arrival_time": (row.get("ArrivalTime") or "").strip(),
                "departure_time": (row.get("DepartureTime") or "").strip(),
                "paid_amount": _normalize_amount(row.get("Paid Amount") or ""),
                "transfer_ref": (row.get("Transfer slip Ref") or "").strip(),
                "ticket_type": (row.get("Ticket Type") or "").strip(),
                "status": (row.get("Status") or "").strip() or "booked",
                "id_doc_url": (row.get("ID Doc URL") or "").strip(),
                "group_id": "",
            }

        elif is_raw:
            booking = {
                "ticket_ref": (row.get("ticket_ref") or "").strip(),
                "name": (row.get("name") or "").strip(),
                "id_number": (row.get("id_number") or "").strip().upper(),
                "phone": _normalize_phone(row.get("phone") or ""),
                "male_dep": (row.get("male_dep") or "").strip(),
                "resort_dep": (row.get("resort_dep") or "").strip(),
                "arrival_time": (row.get("arrival_time") or "").strip(),
                "departure_time": (row.get("departure_time") or "").strip(),
                "paid_amount": _normalize_amount(row.get("paid_amount") or ""),
                "transfer_ref": (row.get("transfer_ref") or "").strip(),
                "ticket_type": (row.get("ticket_type") or "").strip(),
                "status": "booked",
                "id_doc_url": None,
                "group_id": (row.get("group_id") or "").strip(),
            }

        # --- Validation ---
        if not booking["name"] or not booking["id_number"]:
            row_errors.append(f"Row {idx}: Missing Name or IDNumber")

        if row_errors:
            errors.extend(row_errors)
        else:
            valid_rows.append(booking)

    return valid_rows, errors