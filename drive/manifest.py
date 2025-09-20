import io
from datetime import datetime
from config.logger import logger, log_and_raise

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def generate_manifest_pdf(boat_number: str, event_name: str = None) -> bytes:
    """
    Generate a manifest PDF for a given boat (and optional event filter).
    Returns PDF as bytes.
    """
    try:
        from sheets.manager import get_manifest_rows

        manifest = get_manifest_rows(boat_number, event_name=event_name)
        logger.info(f"[Drive] Generating manifest PDF for Boat {boat_number} with {len(manifest)} passengers.")

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica", 12)

        title = f"Boat {boat_number} Manifest"
        subtitle = f"{event_name or 'Event'} — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        c.drawString(50, 800, title)
        c.drawString(50, 785, subtitle)

        y = 760
        for idx, row in enumerate(manifest, start=1):
            # Expecting row dict to include scheduled + actual fields
            name = row.get("Name", "")
            id_number = row.get("ID", "")
            phone = row.get("Number", "")

            sched_arr = row.get("ArrivalTime", "-")
            sched_dep = row.get("DepartureTime", "-")
            actual_arr_boat = row.get("ArrivalBoatBoarded", "-")
            actual_dep_boat = row.get("DepartureBoatBoarded", "-")

            line1 = f"{idx}. {name} | {id_number} | {phone}"
            line2 = f"   Scheduled: Arr {sched_arr} / Dep {sched_dep}"
            line3 = f"   Actual: ArrBoat {actual_arr_boat} / DepBoat {actual_dep_boat}"

            c.drawString(50, y, line1)
            y -= 16
            c.drawString(70, y, line2)
            y -= 16
            c.drawString(70, y, line3)
            y -= 22

            if y < 50:
                c.showPage()
                c.setFont("Helvetica", 12)
                y = 800

        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        log_and_raise("Drive", f"generating manifest PDF for boat {boat_number}", e)


def upload_to_drive(file_bytes: bytes, filename: str, event_name: str) -> str:
    """
    Upload a manifest PDF to the correct Drive folder and return its URL.
    """
    try:
        from drive.utils import ensure_drive_subfolder, upload_file_to_drive

        folder_id = ensure_drive_subfolder("Manifests", event_name)
        file_stream = io.BytesIO(file_bytes)
        file_stream.seek(0)

        url = upload_file_to_drive(folder_id, file_stream, filename, mimetype="application/pdf")
        logger.info(f"[Drive] Manifest uploaded: {url}")
        return url

    except Exception as e:
        log_and_raise("Drive", f"uploading manifest '{filename}' to Drive", e)