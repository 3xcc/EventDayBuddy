import pytest
from unittest.mock import MagicMock, patch
from db import booking_ops

def test_get_booking_by_id():
    db = MagicMock()
    booking = MagicMock(id=1)
    db.query().filter().first.return_value = booking
    result = booking_ops.get_booking_by_id(db, 1)
    assert result.id == 1
    db.query().filter.assert_called()

def test_update_booking_status():
    db = MagicMock()
    booking = MagicMock(id=1, status="booked")
    db.query().filter().first.return_value = booking
    booking_ops.update_booking_status(db, 1, "checked_in")
    assert booking.status == "checked_in"
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(booking)

def test_update_booking_status_not_found():
    db = MagicMock()
    db.query().filter().first.return_value = None
    with pytest.raises(Exception):
        booking_ops.update_booking_status(db, 1, "checked_in")
