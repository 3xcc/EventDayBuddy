from decimal import Decimal, InvalidOperation
import re

# Common currency prefixes/symbols you might encounter
CURRENCY_PREFIXES = ("rf", "mvr", "usd", "eur", "gbp", "$", "ރ")

def parse_amount(value):
    """
    Accepts strings like 'RF1000', '$400', '1,200.50', '400', 400.
    Returns a Decimal or None if invalid.
    """
    if value is None:
        return None

    # Already numeric
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None

    s = str(value).strip()
    if not s:
        return None

    sl = s.lower()

    # Remove known currency prefixes/suffixes
    for pref in CURRENCY_PREFIXES:
        if sl.startswith(pref):
            s = s[len(pref):].strip()
            break
        if sl.endswith(pref):
            s = s[: -len(pref)].strip()
            break

    # Remove thousands separators and whitespace
    s = s.replace(",", "")
    s = re.sub(r"\s+", "", s)

    # Strip out any non‑digit/non‑dot characters
    s = re.sub(r"[^0-9.]", "", s)

    # Guard against multiple dots
    if s.count(".") > 1 or s == "":
        return None

    try:
        return Decimal(s)
    except InvalidOperation:
        return None