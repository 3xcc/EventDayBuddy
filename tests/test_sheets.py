import pytest
from unittest.mock import MagicMock
from sheets import booking_io, client, exports, manager, queries, validators

def test_booking_io():
    assert hasattr(booking_io, "import_bookings_from_sheet")

def test_client():
    assert hasattr(client, "get_sheets_service")

def test_exports():
    assert hasattr(exports, "export_bookings_to_sheet")

def test_manager():
    assert hasattr(manager, "SheetManager")

def test_queries():
    assert hasattr(queries, "get_booking_rows")

def test_validators():
    assert hasattr(validators, "validate_booking_row")
