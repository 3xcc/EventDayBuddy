from decimal import Decimal, InvalidOperation

def parse_booking_input(update_text: str) -> dict:
    """
    Parse free-form booking text into a structured dict.
    Expected fields: name, id_number, phone, male_dep, resort_dep,
                     paid_amount, transfer_ref, ticket_type,
                     arrival_time, departure_time
    """
    lines = update_text.splitlines()
    lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith("/newbooking")]

    cleaned = []
    for l in lines:
        # Strip leading numbering like "1)" or "1."
        if len(l) > 2 and l[:2].isdigit() and l[2] in [")", "."]:
            l = l[3:].strip()
        # Strip "Field: value" → "value"
        if ":" in l:
            _, val = l.split(":", 1)
            l = val.strip()
        cleaned.append(l)

    # Map into dict
    fields = [
        "name", "id_number", "phone", "male_dep", "resort_dep",
        "paid_amount", "transfer_ref", "ticket_type",
        "arrival_time", "departure_time"
    ]
    data = {field: cleaned[i] if i < len(cleaned) else None for i, field in enumerate(fields)}

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