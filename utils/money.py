from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re

# Common currency prefixes/symbols you might encounter
CURRENCY_PREFIXES = ("rf", "mvr", "usd", "eur", "gbp", "$", "ރ")


def parse_amount(value):
    """
    Accepts strings like 'RF1000', '$400', '1,200.50', '400', 400, '1.200,50'.
    Returns a Decimal quantized to 2 decimal places, or None if invalid.
    """
    if value is None:
        return None

    # Already numeric
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
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

    # Handle European decimal format (e.g., "1.200,50")
    if "," in s and s.count(",") == 1 and "." in s and s.index(",") > s.index("."):
        # Assume last comma is decimal separator
        s = s.replace(".", "").replace(",", ".")
    else:
        # Remove thousands separators
        s = s.replace(",", "")

    # Remove whitespace
    s = re.sub(r"\s+", "", s)

    # Strip out any non-digit/non-dot characters
    s = re.sub(r"[^0-9.]", "", s)

    # Guard against multiple dots
    if s.count(".") > 1 or s == "":
        return None

    try:
        return Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None