import pytest
from db import models

def test_booking_model_fields():
    booking = models.Booking()
    assert hasattr(booking, "event_id")
    assert hasattr(booking, "ticket_ref")
    assert hasattr(booking, "name")
    assert hasattr(booking, "id_number")
    assert hasattr(booking, "status")

def test_event_model_fields():
    event = models.Event()
    assert hasattr(event, "id")
    assert hasattr(event, "name")
    assert hasattr(event, "bookings")

def test_config_model_fields():
    config = models.Config()
    assert hasattr(config, "key")
    assert hasattr(config, "value")
