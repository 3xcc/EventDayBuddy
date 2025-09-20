def parse_booking_input(update_text: str):
    lines = update_text.splitlines()
    lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith("/newbooking")]
    cleaned = []
    for l in lines:
        if len(l) > 2 and l[:2].isdigit() and l[2] in [")", "."]:
            l = l[3:].strip()
        if ":" in l:
            parts = l.split(":", 1)
            l = parts[1].strip()
        cleaned.append(l)
    return (
        cleaned[0] if len(cleaned) > 0 else None,
        cleaned[1] if len(cleaned) > 1 else None,
        cleaned[2] if len(cleaned) > 2 else None,
        cleaned[3] if len(cleaned) > 3 else None,
        cleaned[4] if len(cleaned) > 4 else None,
        cleaned[5] if len(cleaned) > 5 else None,
        cleaned[6] if len(cleaned) > 6 else None,
        cleaned[7] if len(cleaned) > 7 else None,
        cleaned[8] if len(cleaned) > 8 else None,
        cleaned[9] if len(cleaned) > 9 else None,
    )