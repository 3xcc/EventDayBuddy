# drive/utils.py

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config.logger import logger, log_and_raise
from config.envs import GOOGLE_CREDS_JSON
import json

def ensure_drive_subfolder(folder_type: str, event_name: str) -> str:
    """
    Ensure a Drive folder exists at: EventDayBuddy/{folder_type}/{event_name}
    Returns the folder ID.
    """
    try:
        creds = json.loads(GOOGLE_CREDS_JSON)
        service = build("drive", "v3", credentials=creds)

        # Step 1: Find root "EventDayBuddy" folder
        results = service.files().list(
            q="name='EventDayBuddy' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces="drive",
            fields="files(id, name)"
        ).execute()
        root_folders = results.get("files", [])
        if not root_folders:
            raise Exception("Root folder 'EventDayBuddy' not found in Drive.")
        root_id = root_folders[0]["id"]

        # Step 2: Find or create subfolder (Manifests or IDs)
        subfolder_q = f"'{root_id}' in parents and name='{folder_type}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        subfolder_results = service.files().list(q=subfolder_q, spaces="drive", fields="files(id, name)").execute()
        subfolders = subfolder_results.get("files", [])
        if not subfolders:
            subfolder_metadata = {
                "name": folder_type,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [root_id]
            }
            subfolder = service.files().create(body=subfolder_metadata, fields="id").execute()
            subfolder_id = subfolder["id"]
            logger.info(f"[Drive] Created subfolder '{folder_type}' under EventDayBuddy.")
        else:
            subfolder_id = subfolders[0]["id"]

        # Step 3: Find or create event folder
        event_q = f"'{subfolder_id}' in parents and name='{event_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        event_results = service.files().list(q=event_q, spaces="drive", fields="files(id, name)").execute()
        event_folders = event_results.get("files", [])
        if not event_folders:
            event_metadata = {
                "name": event_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [subfolder_id]
            }
            event_folder = service.files().create(body=event_metadata, fields="id").execute()
            event_id = event_folder["id"]
            logger.info(f"[Drive] Created event folder '{event_name}' under {folder_type}.")
        else:
            event_id = event_folders[0]["id"]

        return event_id

    except HttpError as e:
        log_and_raise("Drive", f"ensuring subfolder for {event_name} in {folder_type}", e)