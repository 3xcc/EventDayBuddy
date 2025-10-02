import os
import asyncio
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from telegram import Update

from config.logger import logger
from config.envs import LOG_LEVEL, TELEGRAM_TOKEN
from bot.handlers import init_bot, application
from db.init import close_engine

# ===== Global State =====
# Remove this duplicate declaration:
# bot_ready = False  # ❌ DELETE THIS LINE

# Instead, import from handlers where it's properly managed
from bot.handlers import bot_ready

# ===== Port and CORS =====
PORT = int(os.getenv("PORT", 8000))
ALLOWED_ORIGINS = (
    ["*"] if os.getenv("ENV", "dev") == "dev"
    else os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
)

# ===== FastAPI App =====
app = FastAPI(title="EventDayBuddy API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Startup Hook =====
@app.on_event("startup")
async def startup_event():
    # No need to declare global here since we're importing from handlers
    logger.info("[Web] FastAPI startup — initializing bot...")
    for attempt in range(3):
        try:
            print(f"[DEBUG] init_bot() attempt {attempt+1}")
            await init_bot()
            # The bot_ready flag is now set within init_bot() in handlers.py
            logger.info("[Startup] ✅ Bot initialized successfully.")
            break
        except Exception as e:
            logger.error(f"[Startup] ❌ Bot init failed (attempt {attempt+1}): {e}", exc_info=True)
            await asyncio.sleep(2 * attempt)
    else:
        logger.critical("[Startup] ❌ Bot failed to initialize after retries.")

# ===== Shutdown Hook =====
@app.on_event("shutdown")
async def shutdown_event():
    from bot.handlers import bot_ready, application
    bot_ready = False
    logger.info("[Web] FastAPI shutdown — cleaning up bot and DB...")
    try:
        if application:
            # Proper shutdown for webhook mode
            await application.stop()
            await application.shutdown()
            logger.info("[Shutdown] ✅ Bot application stopped cleanly.")
        else:
            logger.warning("[Shutdown] ⚠️ Bot application was not initialized.")
    except Exception as e:
        logger.error(f"[Shutdown] ❌ Bot shutdown failed: {e}", exc_info=True)
    finally:
        close_engine()
        
# ===== Health Check =====
@app.get("/", tags=["Health"])
def health_check():
    from bot.handlers import bot_ready  # Import current value
    logger.info("[Web] Health check endpoint called.")
    return {
        "status": "ok",
        "message": "EventDayBuddy is running",
        "bot_ready": bot_ready
    }

# ===== Telegram Webhook =====
@app.post(f"/{TELEGRAM_TOKEN}")
async def telegram_webhook(request: Request):
    try:
        from bot.handlers import bot_ready, application
        
        if not bot_ready or not application:
            logger.warning("[Webhook] Update dropped — bot not ready")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"ok": False, "dropped": True}
            )

        data = await request.json()
        logger.info(f"[Webhook] 📩 Incoming update from {request.client.host}")

        update = Update.de_json(data, application.bot)
        
        # ✅ CRITICAL: Use application.process_update() instead of putting in queue
        await application.process_update(update)

        return JSONResponse(status_code=status.HTTP_200_OK, content={"ok": True})

    except Exception as e:
        logger.exception("[Webhook] ❌ Failed to process update")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"ok": False, "error": str(e)},
        )