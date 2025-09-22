import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from config.logger import logger
from sheets.manager import get_manifest_rows
from utils.supabase_storage import fetch_signed_file

def generate_idcards_pdf(boat_number: str, event_name: str = None) -> bytes:
    """
    Generate an ID cards PDF for all checked-in passengers on a boat.
    Layout: 2 columns × 3 rows per A4 page (6 cards per page).
    Each card includes Name, ID number, photo (if available), and footer info.
    Returns PDF bytes.
    """
    try:
        rows = get_manifest_rows(boat_number, event_name=event_name)

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        page_width, page_height = A4

        # Card dimensions
        card_width = 90 * mm
        card_height = 60 * mm
        margin_x = 20 * mm
        margin_y = 20 * mm
        spacing_x = 10 * mm
        spacing_y = 15 * mm

        # Starting position
        x = margin_x
        y = page_height - margin_y - card_height

        # Page header
        def draw_page_header():
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(page_width / 2, page_height - 15 * mm,
                                f"Event: {event_name or 'General'} | Boat: {boat_number}")

        draw_page_header()

        for i, row in enumerate(rows, start=1):
            name = row.get("Name", "")
            id_number = row.get("ID", "")
            photo_path = row.get("ID Doc URL", "")
            event = row.get("Event", event_name or "")
            boat = boat_number

            # Draw card border
            c.rect(x, y, card_width, card_height)

            # Name + ID
            c.setFont("Helvetica-Bold", 12)
            c.drawString(x + 10, y + card_height - 20, name or "Unknown")
            c.setFont("Helvetica", 10)
            c.drawString(x + 10, y + card_height - 35, f"ID: {id_number or 'N/A'}")

            # Photo (top-right)
            photo_x = x + card_width - 40 * mm
            photo_y = y + 10
            if photo_path:
                try:
                    photo_bytes = fetch_signed_file(photo_path, expiry=60)
                    img = ImageReader(io.BytesIO(photo_bytes))
                    c.drawImage(img, photo_x, photo_y, 30 * mm, 40 * mm, preserveAspectRatio=True)
                except Exception as e:
                    logger.warning(f"[IDCards] Failed to load photo for {name}: {e}")
                    c.rect(photo_x, photo_y, 30 * mm, 40 * mm)
                    c.setFont("Helvetica", 8)
                    c.drawCentredString(photo_x + 15 * mm, photo_y + 20 * mm, "No Photo")
            else:
                c.rect(photo_x, photo_y, 30 * mm, 40 * mm)
                c.setFont("Helvetica", 8)
                c.drawCentredString(photo_x + 15 * mm, photo_y + 20 * mm, "No Photo")

            # Footer (event + boat)
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(x + 10, y + 10, f"Event: {event} | Boat: {boat}")

            # Move to next card position
            x += card_width + spacing_x
            if x + card_width > page_width - margin_x:
                x = margin_x
                y -= card_height + spacing_y
            if y < margin_y:
                c.showPage()
                x = margin_x
                y = page_height - margin_y - card_height
                draw_page_header()

        # Add summary page
        c.showPage()
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(page_width / 2, page_height / 2,
                            f"Total ID Cards Generated: {len(rows)}")

        c.save()
        pdf_bytes = buffer.getvalue()
        buffer.close()
        logger.info(f"[IDCards] Generated ID cards PDF for Boat {boat_number} ({len(rows)} passengers)")
        return pdf_bytes

    except Exception as e:
        logger.error(f"[IDCards] Failed to generate ID cards PDF: {e}", exc_info=True)
        return None