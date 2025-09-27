import pytest
from unittest.mock import MagicMock, patch
from bot import handlers

def test_init_bot_registers_handlers():
    app = MagicMock()
    with patch("bot.handlers.ApplicationBuilder") as builder:
        builder().token().build.return_value = app
        with patch("bot.handlers.CommandHandler"), \
             patch("bot.handlers.CallbackQueryHandler"), \
             patch("bot.handlers.MessageHandler"), \
             patch("bot.handlers.filters"), \
             patch("bot.handlers.bookings_bulk.register_handlers"), \
             patch("bot.handlers.register_checkin_handlers"):
            handlers.TELEGRAM_TOKEN = "token"
            handlers.PUBLIC_URL = "https://test.url"
            handlers.logger = MagicMock()
            handlers.init_bot()
            assert app.add_handler.called
