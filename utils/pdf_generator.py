import io
from datetime import datetime
from config.logger import logger, log_and_raise
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generate_manifest_pdf(boat_number: str, event_name: str = None) -> bytes:
    """
    Generate a manifest PDF for a given boat (and optional event filter).
    Includes headers on each page and a passenger count summary.
    Returns PDF as bytes.
    """
    try:
        from sheets.manager import get_manifest_rows

        manifest = get_manifest_rows(boat_number, event_name=event_name)
        logger.info(f"[PDF] Generating manifest PDF for Boat {boat_number} with {len(manifest)} passengers.")

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        page_width, page_height = A4

        # Title + subtitle
        title = f"Boat {boat_number} Manifest"
        subtitle = f"{event_name or 'Event'} — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"

        def draw_page_header():
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, page_height - 40, title)
            c.setFont("Helvetica", 12)
            c.drawString(50, page_height - 60, subtitle)

        def draw_headers(y):
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, "No.")
            c.drawString(80, y, "Name")
            c.drawString(220, y, "ID")
            c.drawString(320, y, "Phone")
            c.drawString(420, y, "Sched Arr/Dep")
            c.drawString(520, y, "Actual Arr/Dep")
            c.setFont("Helvetica", 10)

        # First page header
        draw_page_header()
        y = page_height - 100
        draw_headers(y)
        y -= 20

        # Passenger rows
        for idx, row in enumerate(manifest, start=1):
            name = row.get("Name", "")[:25]  # truncate to avoid overlap
            id_number = row.get("ID", "")[:15]
            phone = row.get("Number", "")[:15]
            sched_arr = row.get("ArrivalTime", "-")
            sched_dep = row.get("DepartureTime", "-")
            actual_arr_boat = row.get("ArrivalBoatBoarded", "-")
            actual_dep_boat = row.get("DepartureBoatBoarded", "-")

            c.drawString(50, y, str(idx))
            c.drawString(80, y, name)
            c.drawString(220, y, id_number)
            c.drawString(320, y, phone)
            c.drawString(420, y, f"{sched_arr}/{sched_dep}")
            c.drawString(520, y, f"{actual_arr_boat}/{actual_dep_boat}")

            y -= 18
            if y < 70:  # new page
                c.showPage()
                draw_page_header()
                y = page_height - 100
                draw_headers(y)
                y -= 20

        # Summary footer at fixed position
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 40, f"Total Passengers: {len(manifest)}")

        # If no passengers, watermark
        if not manifest:
            c.setFont("Helvetica-Bold", 20)
            c.drawCentredString(page_width / 2, page_height / 2, "NO PASSENGERS")

        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        log_and_raise("PDF", f"generating manifest PDF for boat {boat_number}", e)