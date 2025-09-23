import os
import io
import requests
from supabase import create_client
from PIL import Image
from config.envs import SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET

MAX_PHOTO_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED_IMAGE_TYPES = {"JPEG", "PNG"}

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_id_photo(file_bytes: bytes, event_name: str, ticket_ref: str) -> str:
    """Upload a passenger ID photo to Supabase under ids/<event>/<ticket>.jpg"""
    if len(file_bytes) > MAX_PHOTO_SIZE:
        raise ValueError("Photo too large. Max size is 2 MB.")

    # Validate image format with Pillow
    try:
        img = Image.open(io.BytesIO(file_bytes))
        if img.format.upper() not in ALLOWED_IMAGE_TYPES:
            raise ValueError("Invalid image type. Only JPEG/PNG allowed.")
    except Exception:
        raise ValueError("Invalid image file. Could not open.")

    path = f"ids/{event_name}/{ticket_ref}.jpg"
    
    res = supabase.storage.from_(SUPABASE_BUCKET).upload(
    path,
    file_bytes,
    {"x-upsert": "true"}   # correct header
    )

    if isinstance(res, dict) and res.get("error"):
        raise RuntimeError(f"Supabase upload failed: {res['error']}")
    return path

def upload_manifest(pdf_bytes: bytes, event_name: str, boat_number: str) -> str:
    """Upload a manifest PDF to Supabase under manifests/<event>/boat_<n>.pdf"""
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("Invalid file type. Only PDF allowed.")

    path = f"manifests/{event_name}/boat_{boat_number}.pdf"
    res = supabase.storage.from_(SUPABASE_BUCKET).upload(path, pdf_bytes, {"upsert": True})
    if isinstance(res, dict) and res.get("error"):
        raise RuntimeError(f"Supabase upload failed: {res['error']}")
    return path

def upload_idcard(pdf_bytes: bytes, event_name: str, ticket_ref: str) -> str:
    """Upload an ID card PDF under ids/<event>/idcards/<ticket>.pdf"""
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("Invalid file type. Only PDF allowed.")

    path = f"ids/{event_name}/idcards/{ticket_ref}.pdf"
    res = supabase.storage.from_(SUPABASE_BUCKET).upload(path, pdf_bytes, {"upsert": True})
    if isinstance(res, dict) and res.get("error"):
        raise RuntimeError(f"Supabase upload failed: {res['error']}")
    return path

def fetch_signed_file(path: str, expiry: int = 60) -> bytes:
    """Generate a signed URL and fetch the file bytes"""
    res = supabase.storage.from_(SUPABASE_BUCKET).create_signed_url(path, expiry)
    url = res.get("signedURL") if isinstance(res, dict) else None
    if not url:
        raise RuntimeError(f"Failed to create signed URL for {path}")

    resp = requests.get(url)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch file from Supabase: {resp.status_code}")
    return resp.content