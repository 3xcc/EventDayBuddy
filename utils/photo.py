import io
from config.logger import logger
from utils.supabase_storage import upload_id_photo
from PIL import Image

MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_FORMATS = {"JPEG", "PNG"}

async def handle_photo_upload(update, id_number: str) -> str:
    try:
        message = update.message
        user_id = str(update.effective_user.id)

        # --- Step 0: Ensure user is registered ---
        from db.init import get_db
        from db.models import User, Config
        with get_db() as db:
            user = db.query(User).filter(User.chat_id == user_id).first()
            if not user:
                await message.reply_text(
                    "⛔ You are not registered to upload photos. "
                    "Please contact an admin to be added first."
                )
                logger.warning(f"[Photo] Upload attempt by unregistered user {user_id}")
                return None

        # --- Step 1: Get file (photo or document) ---
        file = None
        if message.photo:
            photo = message.photo[-1]  # highest resolution
            file = await photo.get_file()
        elif message.document and message.document.mime_type.startswith("image/"):
            file = await message.document.get_file()
        else:
            await message.reply_text("⚠️ Please send a photo or image file (JPEG/PNG under 5MB).")
            logger.warning(f"[Photo] No valid photo/document found in update from {user_id}")
            return None

        # --- Step 2: Size check ---
        if file.file_size and file.file_size > MAX_PHOTO_SIZE:
            await message.reply_text("❌ Photo too large. Please upload an image under 5MB.")
            logger.warning(f"[Photo] File too large ({file.file_size} bytes) for {id_number}")
            return None

        # --- Step 3: Download into memory ---
        file_bytes = io.BytesIO()
        await file.download(out=file_bytes)
        file_bytes.seek(0)

        # --- Step 4: Validate / normalize format ---
        try:
            img = Image.open(file_bytes)
            img_format = img.format.upper()
            logger.info(f"[Photo] Received format={img_format}, size={file.file_size}, mime={file.mime_type}")

            if img_format not in ALLOWED_FORMATS:
                # Convert unsupported formats (e.g. WEBP) to JPEG
                file_bytes = io.BytesIO()
                img.convert("RGB").save(file_bytes, format="JPEG")
                file_bytes.seek(0)
                img_format = "JPEG"
                logger.info(f"[Photo] Converted image to JPEG for {id_number}")

        except Exception as e:
            await message.reply_text("❌ Could not read image. Please upload a valid JPEG/PNG.")
            logger.warning(f"[Photo] Failed to open image for {id_number}: {e}")
            return None

        # --- Step 5: Normalize ID for path ---
        safe_id = id_number.strip().upper().replace(" ", "_")

        # --- Step 6: Get active event name ---
        with get_db() as db:
            active_event_cfg = db.query(Config).filter(Config.key == "active_event").first()
            event_name = active_event_cfg.value if active_event_cfg else "General"

        # --- Step 7: Upload to Supabase ---
        file_bytes.seek(0)  # rewind before upload
        path = upload_id_photo(file_bytes.getvalue(), event_name, safe_id)
        if not path:
            await message.reply_text("❌ Upload failed. Please try again.")
            logger.error(f"[Photo] Supabase upload failed for {safe_id} in event {event_name}")
            return None

        await message.reply_text("✅ Photo uploaded successfully.")
        return path

    except Exception as e:
        logger.error(f"[Photo] Failed to upload photo for {id_number}: {e}", exc_info=True)
        await update.message.reply_text("❌ Failed to process photo. Please try again.")
        return None