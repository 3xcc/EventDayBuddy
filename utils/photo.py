import io
from config.logger import logger
from utils.supabase_storage import upload_id_photo
from PIL import Image

# Max photo size in bytes (e.g. 5 MB)
MAX_PHOTO_SIZE = 5 * 1024 * 1024
# Allowed formats
ALLOWED_FORMATS = {"JPEG", "PNG"}

async def handle_photo_upload(update, id_number: str) -> str:
    try:
        message = update.message

        # Ensure a photo exists
        if not message.photo:
            await message.reply_text("⚠️ No photo detected. Please attach a JPEG/PNG under 5MB.")
            logger.warning("[Photo] No photo found in update")
            return None

        # Get the highest resolution photo
        photo = message.photo[-1]
        file = await photo.get_file()

        # Check file size before downloading
        if file.file_size and file.file_size > MAX_PHOTO_SIZE:
            await message.reply_text("❌ Photo too large. Please upload an image under 5MB.")
            logger.warning(f"[Photo] File too large ({file.file_size} bytes) for {id_number}")
            return None

        # Download into memory
        file_bytes = io.BytesIO()
        await file.download(out=file_bytes)
        file_bytes.seek(0)

        # Validate image format using Pillow
        try:
            img = Image.open(file_bytes)
            img_format = img.format.upper()
            if img_format not in ALLOWED_FORMATS:
                await message.reply_text("❌ Unsupported format. Please upload a JPEG or PNG image.")
                logger.warning(f"[Photo] Unsupported image format '{img_format}' for {id_number}")
                return None
        except Exception as e:
            await message.reply_text("❌ Could not read image. Please upload a valid JPEG/PNG.")
            logger.warning(f"[Photo] Failed to open image for {id_number}: {e}")
            return None

        # Normalize id_number for path safety
        safe_id = id_number.strip().upper().replace(" ", "_")

        # Get active event name from DB
        from db.init import get_db
        from db.models import Config
        with get_db() as db:
            active_event_cfg = db.query(Config).filter(Config.key == "active_event").first()
            event_name = active_event_cfg.value if active_event_cfg else "General"

        # Upload to Supabase
        path = upload_id_photo(file_bytes.getvalue(), event_name, safe_id)
        if not path:
            await message.reply_text("❌ Upload failed. Please try again.")
            logger.error(f"[Photo] Supabase upload failed for {safe_id} in event {event_name}")
            return None

        await message.reply_text("✅ Photo uploaded successfully.")
        return path  # store this in DB/Sheets

    except Exception as e:
        logger.error(f"[Photo] Failed to upload photo for {id_number}: {e}", exc_info=True)
        await update.message.reply_text("❌ Failed to process photo. Please try again.")
        return None