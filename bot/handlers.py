import asyncio
from io import BytesIO
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config.logger import logger, log_and_raise
from config.envs import TELEGRAM_TOKEN, PUBLIC_URL  # PUBLIC_URL = your Render HTTPS URL

# Core commands
from bot.admin import cpe, boatready, checkinmode, editseats
from bot.bookings import newbooking
from bot.checkin import checkin_by_id, checkin_by_phone, register_checkin_handlers
from bot.departure import departed
from drive.manifest import generate_manifest_pdf

# Global application instance so FastAPI route can access it
application = None

# ===== Command Handlers =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    """
    Dynamic /start command — shows role-based help menu.
    """
    try:
        user_id = str(update.effective_user.id)

        with get_db() as db:
            user = db.query(User).filter(User.chat_id == user_id).first()
            role = user.role if user else "viewer"

        logger.info(f"[Bot] /start used by {user_id} ({role})")

        if role == "admin":
            help_text = (
                "👋 Welcome, Admin!\n\n"
                "Here are your available commands:\n"
                "• /cpe — Set active event\n"
                "• /boatready — Start boarding session\n"
                "• /checkinmode — Enable check-in mode\n"
                "• /editseats — Adjust boat capacity\n"
                "• /departed — Mark boat departed\n"
                "• /newbooking — Add a booking\n"
                "• /i — Check-in by ID\n"
                "• /p — Check-in by phone\n"
                "• /transfer — Transfer ticket\n"
                "• /newbookings — Bulk import\n"
                "• /start — Show this help menu"
            )
        elif role in ["checkin_staff", "booking_staff"]:
            help_text = (
                "👋 Welcome, Event Staff!\n\n"
                "Here are your available commands:\n"
                "• /newbooking — Add a booking\n"
                "• /i — Check-in by ID\n"
                "• /p — Check-in by phone\n"
                "• /start — Show this help menu"
            )
        else:
            help_text = (
                "👋 Welcome to EventDayBuddy!\n\n"
                "This bot helps manage event check-ins and boat boarding.\n"
                "If you're an event staff member, ask your admin to register you.\n"
                "Use /start anytime to see your available commands."
            )

        await update.message.reply_text(help_text)

    except Exception as e:
        log_and_raise("Bot", "handling /start command", e)


# ===== Export PDF Callback =====
async def export_pdf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle export button after /departed — generate and send manifest PDF."""
    try:
        query = update.callback_query
        await query.answer()

        if not query.data or ":" not in query.data:
            await query.edit_message_text("⚠️ Invalid export request.")
            logger.warning("[Callback] Received malformed exportpdf callback data.")
            return

        boat_number = query.data.split(":")[1]

        # Generate PDF bytes
        pdf_bytes = generate_manifest_pdf(boat_number)

        if not pdf_bytes:
            await query.edit_message_text(f"❌ Failed to generate manifest PDF for Boat {boat_number}.")
            logger.error(f"[Callback] No PDF bytes generated for Boat {boat_number}")
            return

        # Send PDF as Telegram document
        pdf_stream = BytesIO(pdf_bytes)
        pdf_stream.name = f"Boat_{boat_number}_Manifest.pdf"

        await query.message.reply_document(
            document=pdf_stream,
            caption=f"📄 Manifest PDF for Boat {boat_number}"
        )

        logger.info(f"[Callback] Manifest PDF sent for Boat {boat_number}")

    except Exception as e:
        log_and_raise("Callback", "handling exportpdf", e)

# ===== Bot Initializer for Webhook Mode =====
async def init_bot():
    """Initialize the Telegram bot application and set webhook."""
    global application
    try:
        logger.info("[Bot] Initializing Telegram bot application...")
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
        

        # Register callbacks
        register_checkin_handlers(app)
        app.add_handler(CallbackQueryHandler(export_pdf_callback, pattern=r"^exportpdf:\d+$"))
        app.add_handler(CallbackQueryHandler(unregister_callback, pattern=r"^unreg:.+"))

        # Build webhook URL safely
        webhook_url = f"{PUBLIC_URL.rstrip('/')}/{TELEGRAM_TOKEN}"
        logger.info(f"[Bot] Setting webhook to {webhook_url}")
        await app.bot.set_webhook(webhook_url)

        # ✅ Start the bot so update_queue is active
        await app.initialize()
        await app.start()

        application = app
        logger.info("[Bot] ✅ Webhook set and bot initialized.")

    except Exception as e:
        log_and_raise("Bot Init", "initializing Telegram bot", e)