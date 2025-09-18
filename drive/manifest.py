import io
from datetime import datetime
from config.logger import logger, log_and_raise
from sheets.manager import get_manifest_rows

# Optional: choose your PDF library
# from reportlab.lib.pagesizes import A4
# from reportlab.pdfgen import canvas
# OR:
# from fpdf import FPDF

def generate_manifest_pdf(boat_number: str, event_name: str = None) -> bytes:
    """
    Generate a manifest PDF for a given boat (and optional event filter).
    Returns PDF as bytes.
    """
    try:
        manifest = get_manifest_rows(boat_number, event_name=event_name)
        logger.info(f"[Drive] Generating manifest PDF for Boat {boat_number} with {len(manifest)} passengers.")

        # === Example with reportlab ===
        buffer = io.BytesIO()
        # c = canvas.Canvas(buffer, pagesize=A4)
        # c.setFont("Helvetica", 12)
        # c.drawString(50, 800, f"Boat {boat_number} Manifest - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        # y = 770
        # for idx, row in enumerate(manifest, start=1):
        #     c.drawString(50, y, f"{idx}. {row.get('Name', '')} - {row.get('ID', '')} - {row.get('Number', '')}")
        #     y -= 20
        # c.showPage()
        # c.save()
        # buffer.seek(0)

        # For now, just return an empty PDF placeholder
        return buffer.getvalue()

    except Exception as e:
        log_and_raise("Drive", f"generating manifest PDF for boat {boat_number}", e)

def upload_to_drive(file_bytes: bytes, filename: str) -> str:
    """
    Stub: Upload a file to Google Drive and return the file URL.
    """
    try:
        logger.info(f"[Drive] Uploading {filename} to Google Drive...")
        # TODO: Implement Drive API upload
        return f"https://drive.google.com/file/d/{filename}_stub"
    except Exception as e:
        log_and_raise("Drive", f"uploading {filename} to Google Drive", e)