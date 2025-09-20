import io, uuid
from drive.utils import upload_file_to_drive, ensure_drive_subfolder
from config.logger import logger

async def handle_photo_upload(update, id_number: str) -> str:
    try:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        file_bytes = io.BytesIO()
        await file.download(out=file_bytes)
        file_bytes.seek(0)

        # Use event folder under IDs
        from db.init import get_db
        from db.models import Config
        with get_db() as db:
            active_event_cfg = db.query(Config).filter(Config.key == "active_event").first()
            event_name = active_event_cfg.value if active_event_cfg else "General"

        folder_id = ensure_drive_subfolder("IDs", event_name)
        filename = f"{uuid.uuid4()}_{id_number}.jpg"
        url = upload_file_to_drive(folder_id, file_bytes, filename, "image/jpeg")
        return url
    except Exception as e:
        logger.error(f"[Photo] Failed to upload photo: {e}", exc_info=True)
        return None