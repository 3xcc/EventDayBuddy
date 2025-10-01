import os
import asyncio
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from config.logger import logger
from config.envs import LOG_LEVEL, TELEGRAM_TOKEN
from bot.handlers import init_bot, application, bot_ready
from telegram import Update
from db.init import close_engine

# Render sets PORT automatically; default to 8000 for local dev
PORT = int(os.getenv("PORT", 8000))

# Allow all origins in dev, restrict in prod
ALLOWED_ORIGINS = (
    ["*"] if os.getenv("ENV", "dev") == "dev"
    else os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
)

app = FastAPI(title="EventDayBuddy API", version="1.0.0")

# ===== Middleware =====
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
    logger.info("[Web] FastAPI startup — initializing bot...")
    for attempt in range(3):
        try:
            print(f"[DEBUG] init_bot() attempt {attempt+1}")
            await init_bot()
            logger.info("[Startup] Bot initialized successfully.")
            break
        except Exception as e:
            logger.error(f"[Startup] Bot init failed (attempt {attempt+1}): {e}", exc_info=True)
            await asyncio.sleep(2 * attempt)
    else:
        logger.critical("[Startup] Bot failed to initialize after retries.")

# ===== Shutdown Hook =====
@app.on_event("shutdown")
async def shutdown_event():
    bot_ready = False  # ✅ Mark bot as not ready
    logger.info("[Web] FastAPI shutdown — cleaning up bot and DB...")
    try:
        if application and getattr(application, "running", False):
            await application.stop()
            await application.shutdown()
            logger.info("[Shutdown] ✅ Bot application stopped cleanly.")
        else:
            logger.warning("[Shutdown] ⚠️ Bot was already stopped or not initialized.")
    except Exception as e:
        logger.error(f"[Shutdown] ❌ Bot shutdown failed: {e}", exc_info=True)
    finally:
        close_engine()

# ===== Routes =====
@app.get("/", tags=["Health"])
def health_check():
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
        if not application or not getattr(application, "running", False):
            logger.error("[Webhook] Bot application not initialized — update dropped.")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"ok": False, "error": "Bot not initialized"},
            )

        data = await request.json()
        logger.info(f"[Webhook] Incoming update from {request.client.host}")

        update = Update.de_json(data, application.bot)
        await application.update_queue.put(update)

        return JSONResponse(status_code=status.HTTP_200_OK, content={"ok": True})

    except Exception as e:
        logger.exception("[Webhook] Failed to process update")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"ok": False, "error": str(e)},
        )
