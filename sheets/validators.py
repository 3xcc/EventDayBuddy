from config.logger import logger
from .client import service, SPREADSHEET_ID


def excel_col(n: int) -> str:
    """Convert 1-based column index to Excel column letters (A, B, ..., Z, AA, AB...)."""
    result = ""
    while n:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result


def validate_sheet_alignment(sheet_name: str, expected_columns: list) -> bool:
    """
    Validate that the first row (headers) of the given sheet matches the expected columns.
    Logs mismatches and returns True if aligned, False otherwise.
    """
    try:
        # Dynamic range based on expected column count
        last_col = excel_col(len(expected_columns))
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A1:{last_col}1"
        ).execute()
        actual_headers = result.get("values", [[]])[0]

        # Pad to expected length
        actual_headers += [""] * (len(expected_columns) - len(actual_headers))

        aligned = True
        for idx, expected in enumerate(expected_columns):
            actual = actual_headers[idx] if idx < len(actual_headers) else ""
            if actual != expected:
                logger.warning(
                    f"[Sheets] Header mismatch in '{sheet_name}' col {idx+1}: "
                    f"expected '{expected}', got '{actual}'"
                )
                aligned = False

        if len(actual_headers) > len(expected_columns):
            for idx in range(len(expected_columns), len(actual_headers)):
                logger.warning(
                    f"[Sheets] Extra header in '{sheet_name}' col {idx+1}: "
                    f"'{actual_headers[idx]}' (not expected)"
                )
            aligned = False

        if aligned:
            logger.info(f"[Sheets] Header alignment OK for '{sheet_name}'")

        return aligned

    except Exception as e:
        logger.error(f"[Sheets] Error validating headers for '{sheet_name}': {e}")
        return False