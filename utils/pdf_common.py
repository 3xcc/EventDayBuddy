from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime


def draw_header(c: canvas.Canvas, title: str, subtitle: str = None):
    """Draw a standard header with title and optional subtitle."""
    page_width, page_height = A4
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(page_width / 2, page_height - 40, title)
    if subtitle:
        c.setFont("Helvetica", 10)
        c.drawCentredString(page_width / 2, page_height - 60, subtitle)
    c.setFont("Helvetica", 10)


def draw_footer(c: canvas.Canvas, page_num: int, total_pages: int = None):
    """Draw a footer with page number and timestamp. Supports 'Page X of N'."""
    page_width, _ = A4
    c.setFont("Helvetica", 8)
    if total_pages:
        footer_text = f"Page {page_num} of {total_pages}"
    else:
        footer_text = f"Page {page_num}"
    c.drawRightString(page_width - 40, 20, footer_text)
    c.drawString(30, 20, datetime.now().strftime("%Y-%m-%d %H:%M UTC"))