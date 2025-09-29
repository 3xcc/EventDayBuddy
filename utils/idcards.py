import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from config.logger import logger
from sheets.manager import get_manifest_rows
from utils.supabase_storage import fetch_signed_file
from utils.pdf_common import draw_header, draw_footer


def generate_idcards_pdf(boat_number: str, event_name: str = None) -> bytes:
    """
    Generate an ID cards PDF in landscape orientation.
    Layout: 3 columns × 2 rows per page (6 cards per page).
    Each card shows full ID photo (resized), with Name + Phone above.
    Adds a header banner on each page, page footers with page numbers,
    and a summary page at the end.
    """
    try:
        rows = get_manifest_rows(boat_number, event_name=event_name)

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(A4))
        page_width, page_height = landscape(A4)

        cols, rows_per_page = 3, 2
        cards_per_page = cols * rows_per_page
        card_width = page_width / cols
        card_height = page_height / rows_per_page

        total_pages = (len(rows) + cards_per_page - 1) // cards_per_page
        current_page = 1

        # First page header
        draw_header(c, f"Event: {event_name or 'General'} | Boat: {boat_number}")

        for idx, row in enumerate(rows):
            col = idx % cols
            row_idx = (idx // cols) % rows_per_page

            if idx > 0 and idx % cards_per_page == 0:
                draw_footer(c, current_page, total_pages + 1, landscape_mode=True)
                c.showPage()
                current_page += 1
                draw_header(c, f"Event: {event_name or 'General'} | Boat: {boat_number}", landscape_mode=True)

            x = col * card_width
            y = page_height - (row_idx + 1) * card_height

            name = row.get("Name", "Unknown")
            phone = row.get("Number", "N/A")
            photo_path = row.get("ID Doc URL", "")

            # Caption
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(x + card_width / 2, y + card_height - 25, name)
            c.setFont("Helvetica", 10)
            c.drawCentredString(x + card_width / 2, y + card_height - 40, f"Phone: {phone}")

            # Photo area
            photo_x = x + 10
            photo_y = y + 10
            photo_w = card_width - 20
            photo_h = card_height - 70  # leave space for captions

            if photo_path:
                try:
                    photo_bytes = fetch_signed_file(photo_path, expiry=60)
                    img = ImageReader(io.BytesIO(photo_bytes))
                    c.drawImage(
                        img,
                        photo_x,
                        photo_y,
                        photo_w,
                        photo_h,
                        preserveAspectRatio=True,
                        anchor="c",
                    )
                except Exception as e:
                    logger.warning(f"[IDCards] Failed to load photo for {name}: {e}")
                    c.rect(photo_x, photo_y, photo_w, photo_h)
                    c.drawCentredString(x + card_width / 2, y + card_height / 2, "Photo Error")
            else:
                c.rect(photo_x, photo_y, photo_w, photo_h)
                c.drawCentredString(x + card_width / 2, y + card_height / 2, "No Photo")

        # Footer for last card page
        draw_footer(c, current_page, total_pages + 1)

        # Summary page
        c.showPage()
        current_page += 1
        draw_header(c, f"Event: {event_name or 'General'} | Boat: {boat_number}", landscape_mode=True)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(page_width / 2, page_height / 2, f"Total ID Cards Generated: {len(rows)}")
        draw_footer(c, current_page, total_pages + 1, landscape_mode=True)

        c.save()
        pdf_bytes = buffer.getvalue()
        buffer.close()
        logger.info(f"[IDCards] Generated ID cards PDF for Boat {boat_number} ({len(rows)} passengers)")
        return pdf_bytes

    except Exception as e:
        logger.error(f"[IDCards] Failed to generate ID cards PDF: {e}", exc_info=True)
        return None