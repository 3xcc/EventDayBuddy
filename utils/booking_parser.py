import csv, io, logging
from utils.money import parse_amount
from decimal import Decimal, InvalidOperation

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
    Returns (valid_rows, errors).
    """
    valid_rows, errors = [], []

    # Try decoding with common encodings
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

    # Validate headers
    missing_headers = [h for h in BOOKING_SCHEMA.keys() if h not in reader.fieldnames]
    if missing_headers:
        raise ValueError(f"Missing required headers: {', '.join(missing_headers)}")

    for idx, row in enumerate(reader, start=2):  # start=2 for header offset
        booking = {}
        row_errors = []
        for header, spec in BOOKING_SCHEMA.items():
            raw_val = (row.get(header) or "").strip()
            if not raw_val and spec.get("required"):
                row_errors.append(f"Row {idx}: Missing {header}")
                continue
            if raw_val and "normalize" in spec:
                try:
                    raw_val = spec["normalize"](raw_val)
                except Exception as e:
                    row_errors.append(f"Row {idx}: Invalid {header} ({e})")
            booking[spec["field"]] = raw_val or None

        if row_errors:
            errors.extend(row_errors)
        else:
            valid_rows.append(booking)

    return valid_rows, errors
