import pytest
from unittest.mock import MagicMock, patch
from bot.admin import boat_admin, event_admin, user_admin

@pytest.fixture
def context():
    return MagicMock()

@pytest.fixture
def update():
    return MagicMock()

def test_boat_admin_add_boat(context, update):
    with patch("bot.admin.boat_admin.add_boat_to_db") as add_boat:
        add_boat.return_value = True
        result = boat_admin.add_boat_command(update, context)
        assert result is not None
        add_boat.assert_called()

def test_event_admin_create_event(context, update):
    with patch("bot.admin.event_admin.create_event_in_db") as create_event:
        create_event.return_value = True
        result = event_admin.create_event_command(update, context)
        assert result is not None
        create_event.assert_called()

def test_user_admin_promote_user(context, update):
    with patch("bot.admin.user_admin.promote_user_in_db") as promote_user:
        promote_user.return_value = True
        result = user_admin.promote_user_command(update, context)
        assert result is not None
        promote_user.assert_called()
