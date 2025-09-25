import json
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from config.envs import GOOGLE_SHEET_ID, GOOGLE_CREDS_JSON
from config.logger import logger, log_and_raise

SPREADSHEET_ID = GOOGLE_SHEET_ID
_service = None

def get_service():
    """Return a Google Sheets API service client, initializing if needed."""
    global _service
    if _service is not None:
        return _service
    try:
        if not GOOGLE_CREDS_JSON:
            raise ValueError("Missing GOOGLE_CREDS_JSON")
        creds = Credentials.from_service_account_info(
            json.loads(GOOGLE_CREDS_JSON),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        _service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        logger.info("[Sheets] Google Sheets API client initialized.")
        return _service
    except Exception as e:
        log_and_raise("Sheets Init", "initializing Google Sheets API client", e)
