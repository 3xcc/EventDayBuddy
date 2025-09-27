import pytest
from unittest.mock import MagicMock, patch
from services import booking_service

class DummyEvent:
    def __init__(self, id, name):
        self.id = id
        self.name = name

class DummyBooking:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

@pytest.fixture
def db_session():
    return MagicMock()

def test_generate_ticket_ref():
    ref = booking_service.generate_ticket_ref("MyEvent")
    assert ref.startswith("MYE-")
    assert len(ref.split("-")) == 2
    assert len(ref.split("-")[1]) == 8
    ref2 = booking_service.generate_ticket_ref("")
    assert ref2.startswith("EVT-")

def test_create_booking_success(db_session):
    event = DummyEvent(id=1, name="TestEvent")
    db_session.query().filter().first.side_effect = [event, None]
    with patch("services.booking_service.Booking", DummyBooking):
        booking = booking_service.create_booking(
            db_session,
            event_id=1,
            name="Alice",
            id_number="ID123",
            phone="1234567890",
            male_dep="A",
            resort_dep="B",
            paid_amount=100,
            transfer_ref="TREF",
            ticket_type="VIP",
            arrival_time=None,
            departure_time=None,
            id_doc_url=None,
        )
        assert booking.event_id == 1
        assert booking.name == "Alice"
        assert booking.ticket_ref.startswith("TES-")
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()
        db_session.refresh.assert_called_once_with(booking)

def test_create_booking_missing_fields(db_session):
    with pytest.raises(ValueError):
        booking_service.create_booking(db_session, None, "Alice", "ID123", "123", "A", "B", 100, "TREF", "VIP", None, None)
    with pytest.raises(ValueError):
        booking_service.create_booking(db_session, 1, None, "ID123", "123", "A", "B", 100, "TREF", "VIP", None, None)
    with pytest.raises(ValueError):
        booking_service.create_booking(db_session, 1, "Alice", None, "123", "A", "B", 100, "TREF", "VIP", None, None)

def test_create_booking_event_not_found(db_session):
    db_session.query().filter().first.side_effect = [None]
    with pytest.raises(ValueError):
        booking_service.create_booking(db_session, 99, "Alice", "ID123", "123", "A", "B", 100, "TREF", "VIP", None, None)

def test_create_booking_duplicate(db_session):
    event = DummyEvent(id=1, name="TestEvent")
    existing = DummyBooking(name="Bob", id_number="ID123", event_id=1)
    db_session.query().filter().first.side_effect = [event, existing]
    with pytest.raises(Exception):
        booking_service.create_booking(db_session, 1, "Alice", "ID123", "123", "A", "B", 100, "TREF", "VIP", None, None)

def test_create_booking_db_error(db_session):
    event = DummyEvent(id=1, name="TestEvent")
    db_session.query().filter().first.side_effect = [event, None]
    db_session.add.side_effect = Exception("DB error")
    with patch("services.booking_service.Booking", DummyBooking):
        with pytest.raises(Exception):
            booking_service.create_booking(db_session, 1, "Alice", "ID123", "123", "A", "B", 100, "TREF", "VIP", None, None)
    db_session.rollback.assert_called_once()
