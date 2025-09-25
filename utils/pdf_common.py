# utils/pdf_common.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

def draw_footer(c: canvas.Canvas, page_num: int):
    """Draws a footer with page number and timestamp."""
    c.setFont("Helvetica", 8)
    c.drawString(500, 20, f"Page {page_num}")
    c.drawString(30, 20, datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

def setup_page(c: canvas.Canvas, title: str):
    """Draws a standard header for manifests/ID cards."""
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(A4[0] / 2, A4[1] - 40, title)
    c.setFont("Helvetica", 10)