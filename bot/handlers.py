import subprocess
import tempfile
import os
import asyncio
from io import BytesIO
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config.logger import logger, log_and_raise
from config.envs import TELEGRAM_TOKEN, PUBLIC_URL
from bot.admin import cpe, boatready, boatready_callback, checkinmode, editseats, register, unregister
from bot.bookings import newbooking, attach_photo_callback, handle_booking_photo
from bot.checkin import checkin_by_id, checkin_by_phone, register_checkin_handlers, reset_booking
from bot.stats import stats_command
from bot.editbooking import editbooking
from bot import bookings_bulk
from utils.supabase_storage import fetch_signed_file
from db.init import get_db
from db.models import User, Config

# Global application instance so FastAPI route can access it
application = None
bot_ready = False  # ✅ Used by /health endpoint

# ===== Command Handlers =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)
        with get_db() as db:
            user = db.query(User).filter(User.chat_id == user_id).first()
            role = user.role if user else "viewer"

        logger.info(f"[Bot] /start used by {user_id} ({role})")

        if role == "admin":
            help_text = (
                "👋 Welcome, Admin!\n\n"
                "You have full access. Here are your available commands:\n"
                "• /cpe — Set or view the active event\n"
                "• /boatready — Start boarding session\n"
                "• /checkinmode — Enable check-in mode\n"
                "• /editseats — Adjust boat capacity\n"
                "• /departed — Mark boat departed\n"
                "• /newbooking — Add a single booking\n"
                "• /editbooking — Search and edit bookings\n"
                "• /newbookings [EventName] — Bulk import bookings\n"
                "• /attachphoto — Attach an ID photo\n"
                "• /i — Check-in by ID\n"
                "• /p — Check-in by phone\n"
                "• /sleeptime — Gracefully shut down the bot\n"
                "• /stats — Show event statistics\n"
                "• /start — Show this help menu"
            )
        elif role in ["checkin_staff", "booking_staff"]:
            help_text = (
                "👋 Welcome, Event Staff!\n\n"
                "Here are your available commands:\n"
                "• /newbooking — Add a single booking\n"
                "• /editbooking — Search and edit bookings\n"
                "• /newbookings [EventName] — Bulk import bookings\n"
                "• /attachphoto — Attach an ID photo\n"
                "• /i — Check-in by ID\n"
                "• /p — Check-in by phone\n"
                "• /start — Show this help menu"
            )
        else:
            help_text = (
                "👋 Welcome to EventDayBuddy!\n\n"
                "This bot helps manage event check-ins and boat boarding.\n"
                "If you're an event staff member, ask your admin to register you."
            )

        await update.message.reply_text(help_text)

    except Exception as e:
        log_and_raise("Bot", "handling /start command", e)

# ===== Export PDF Callback =====
async def export_pdf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        boat_number = query.data.split(":")[1]

        with get_db() as db:
            active_event_cfg = db.query(Config).filter(Config.key == "active_event").first()
            event_name = active_event_cfg.value if active_event_cfg else "General"

        path = f"manifests/{event_name}/boat_{boat_number}.pdf"
        pdf_bytes = fetch_signed_file(path)

        pdf_stream = BytesIO(pdf_bytes)
        pdf_stream.name = f"Boat_{boat_number}_Manifest.pdf"

        await query.message.reply_document(
            document=pdf_stream,
            caption=f"📄 Manifest PDF for Boat {boat_number} ({event_name})"
        )
    except Exception as e:
        await update.callback_query.message.reply_text("❌ Failed to fetch manifest PDF.")
        log_and_raise("Callback", f"handling exportpdf for boat {boat_number}", e)

# ===== Export ID Cards Callback =====
async def export_idcards_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        boat_number = query.data.split(":")[1]

        with get_db() as db:
            active_event_cfg = db.query(Config).filter(Config.key == "active_event").first()
            event_name = active_event_cfg.value if active_event_cfg else "General"

        path = f"ids/{event_name}/idcards/boat_{boat_number}.pdf"
        pdf_bytes = fetch_signed_file(path)

        pdf_stream = BytesIO(pdf_bytes)
        pdf_stream.name = f"Boat_{boat_number}_IDCards.pdf"

        await query.message.reply_document(
            document=pdf_stream,
            caption=f"🪪 ID Cards PDF for Boat {boat_number} ({event_name})"
        )
    except Exception as e:
        await update.callback_query.message.reply_text("❌ Failed to fetch ID cards PDF.")
        log_and_raise("Callback", f"handling exportidcards for boat {boat_number}", e)

# ===== Sleeptime Command =====
async def sleeptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)
        with get_db() as db:
            user = db.query(User).filter(User.chat_id == user_id).first()
            role = user.role if user else "viewer"

        if role != "admin":
            await update.message.reply_text("❌ Only admins can put the bot to sleep.")
            return

        await update.message.reply_text("😴 Going to sleep now... shutting down gracefully.")
        logger.info(f"[Bot] /sleeptime triggered by admin {user_id}")

        if application and getattr(application, "running", False):
            await application.stop()
            await application.shutdown()
            logger.info("[Bot] ✅ Application stopped via /sleeptime")
        else:
            logger.warning("[Bot] ⚠️ Application was already stopped.")

    except Exception as e:
        log_and_raise("Bot", "handling /sleeptime command", e)

# ===== Bot Initializer for Webhook Mode =====
# ===== Bot Initializer for Webhook Mode =====
async def init_bot():
    global application, bot_ready
    import traceback
    try:
        logger.info("[Bot] Initializing Telegram bot application...")
        print("[DEBUG] Building Application...")
        
        # ✅ Use ApplicationBuilder with webhook settings
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

        # Register commands
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("cpe", cpe))
        app.add_handler(CommandHandler("newbooking", newbooking))
        app.add_handler(CommandHandler("boatready", boatready))
        app.add_handler(CommandHandler("checkinmode", checkinmode))
        app.add_handler(CommandHandler("editseats", editseats))
        app.add_handler(CommandHandler("i", checkin_by_id))
        app.add_handler(CommandHandler("p", checkin_by_phone))
        app.add_handler(CommandHandler("departed", departed))
        app.add_handler(CommandHandler("register", register))
        app.add_handler(CommandHandler("unregister", unregister))
        app.add_handler(CommandHandler("editbooking", editbooking))
        app.add_handler(CommandHandler("sleeptime", sleeptime))
        app.add_handler(CommandHandler("resetbooking", reset_booking))
        app.add_handler(CommandHandler("stats", stats_command))

        bookings_bulk.register_handlers(app)
        register_checkin_handlers(app)

        app.add_handler(CallbackQueryHandler(export_pdf_callback, pattern=r"^exportpdf:\d+$"))
        app.add_handler(CallbackQueryHandler(export_idcards_callback, pattern=r"^exportidcards:\d+$"))
        app.add_handler(CallbackQueryHandler(attach_photo_callback, pattern=r"^attachphoto:\d+$"))
        app.add_handler(CallbackQueryHandler(boatready_callback, pattern=r"^boatready:(arrival|departure):\d+:\d+$"))
        app.add_handler(MessageHandler(filters.PHOTO, handle_booking_photo))

        print("[DEBUG] Awaiting app.initialize()...")
        await app.initialize()
        print("[DEBUG] app.initialize() complete.")

        # ✅ CRITICAL: For webhook mode, we need to start the application
        # but not with polling. We start it to process the update queue.
        print("[DEBUG] Starting application for webhook processing...")
        await app.start()
        print("[DEBUG] app.start() complete for webhook mode.")

        application = app
        bot_ready = True

        # ✅ Set webhook
        webhook_url = f"{PUBLIC_URL.rstrip('/')}/{TELEGRAM_TOKEN}"
        print(f"[DEBUG] Webhook URL: {webhook_url}")
        if not webhook_url.startswith("https://"):
            logger.warning("[Bot] PUBLIC_URL is not HTTPS — Telegram will reject webhook")
        logger.info(f"[Bot] Setting webhook to {webhook_url}")
        print("[DEBUG] Awaiting app.bot.set_webhook()...")
        await app.bot.set_webhook(webhook_url, drop_pending_updates=True)
        print("[DEBUG] app.bot.set_webhook() complete.")
        logger.info("[Bot] ✅ Webhook set successfully")
        print("[DEBUG] Bot application fully initialized for webhook mode.")

    except Exception as e:
        print("[DEBUG] Exception in init_bot:", e)
        traceback.print_exc()
        bot_ready = False
        log_and_raise("Bot Init", "initializing Telegram bot", e)