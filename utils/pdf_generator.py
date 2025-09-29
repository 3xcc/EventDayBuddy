import io
from datetime import datetime
from config.logger import logger, log_and_raise
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from utils.pdf_common import draw_header, draw_footer
from db.init import get_db
from db.models import Booking


def generate_manifest_pdf(boat_number: str, event_name: str = None) -> bytes:
    """
    Generate a manifest PDF for a given boat (and optional event filter).
    Shows only Name, ID number, Phone number, and Boarded Boat.
    Returns PDF as bytes.
    """
    boat_number = int(boat_number)

    try:
        # --- Query DB instead of Sheets ---
        with get_db() as db:
            q = db.query(Booking).filter(
                (Booking.arrival_boat_boarded == boat_number) |
                (Booking.departure_boat_boarded == boat_number)
            )
            if event_name:
                q = q.filter(Booking.event_id == event_name)
            bookings = q.all()

        manifest = []
        for b in bookings:
            manifest.append({
                "Name": b.name,
                "ID": b.id_number,
                "Number": b.phone,
                "ArrivalBoatBoarded": b.arrival_boat_boarded,
                "DepartureBoatBoarded": b.departure_boat_boarded,
            })

        logger.info(f"[PDF] Generating manifest PDF for Boat {boat_number} with {len(manifest)} passengers.")

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        page_width, page_height = A4

        # Title + subtitle
        title = f"Boat {boat_number} Manifest"
        subtitle = f"{event_name or 'Event'} — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"

        def draw_headers(y):
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, "No.")
            c.drawString(80, y, "Name")
            c.drawString(220, y, "ID Number")
            c.drawString(360, y, "Phone")
            c.drawString(480, y, "Boarded Boat")
            c.setFont("Helvetica", 10)

        # --- First page setup ---
        draw_header(c, title, subtitle)
        y = page_height - 100
        draw_headers(y)
        y -= 20

        current_page = 1

        # Passenger rows
        for idx, row in enumerate(manifest, start=1):
            name = row.get("Name", "")[:25]
            id_number = row.get("ID", "")[:15]
            phone = row.get("Number", "")[:15]
            boarded_boat = row.get("ArrivalBoatBoarded") or row.get("DepartureBoatBoarded") or "-"

            c.drawString(50, y, str(idx))
            c.drawString(80, y, name)
            c.drawString(220, y, id_number)
            c.drawString(360, y, phone)
            c.drawString(480, y, str(boarded_boat))

            y -= 18
            if y < 70:  # new page
                draw_footer(c, current_page)  # show "Page X"
                c.showPage()
                current_page += 1
                draw_header(c, title, subtitle)
                y = page_height - 100
                draw_headers(y)
                y -= 20

        total_pages = current_page

        # Summary footer
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 40, f"Total Passengers: {len(manifest)}")

        # Watermark if empty
        if not manifest:
            c.setFont("Helvetica-Bold", 20)
            c.drawCentredString(page_width / 2, page_height / 2, "NO PASSENGERS")

        # Final footer with total pages
        draw_footer(c, current_page, total_pages)

        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        log_and_raise("PDF", f"generating manifest PDF for boat {boat_number}", e)