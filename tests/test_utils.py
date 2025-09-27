import pytest
from unittest.mock import MagicMock
from utils import booking_parser, booking_schema, idcards, import_summary, money, pdf_common, pdf_generator, photo, supabase_storage

def test_booking_parser_parse():
    assert hasattr(booking_parser, "parse_booking_row")

def test_booking_schema_fields():
    assert hasattr(booking_schema, "BookingSchema")

def test_idcards_generate():
    assert hasattr(idcards, "generate_id_card")

def test_import_summary():
    assert hasattr(import_summary, "summarize_import")

def test_money_format():
    assert hasattr(money, "format_money")

def test_pdf_common():
    assert hasattr(pdf_common, "merge_pdfs")

def test_pdf_generator():
    assert hasattr(pdf_generator, "generate_pdf")

def test_photo_upload():
    assert hasattr(photo, "upload_photo")

def test_supabase_storage():
    assert hasattr(supabase_storage, "upload_to_supabase")
