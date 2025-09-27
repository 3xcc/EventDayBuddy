import os
import sys
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from config.logger import logger
from config.envs import LOG_LEVEL, TELEGRAM_TOKEN
from bot.handlers import init_bot
from telegram import Update

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
    import traceback
    try:
        print("[DEBUG] Calling init_bot()...")
        await init_bot()
        logger.info("[Startup] Bot initialized successfully.")
        print("[DEBUG] init_bot() completed successfully.")
    except Exception as e:
        logger.error(f"[Startup] Bot init failed: {e}", exc_info=True)
        print("[DEBUG] Exception in startup_event:", e)
        traceback.print_exc()
        # sys.exit(1)

# ===== Shutdown Hook =====
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("[Web] FastAPI shutdown — cleaning up bot...")
    try:
        from bot.handlers import application
        if application:
            await application.shutdown()
            await application.stop()
            logger.info("[Shutdown] Bot application shut down cleanly.")
    except Exception as e:
        logger.error(f"[Shutdown] Bot shutdown failed: {e}", exc_info=True)


# ===== Routes =====
@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
def health_check():
    """Basic health check endpoint for uptime monitoring."""
    logger.info("[Web] Health check endpoint called.")
    return {"status": "ok", "message": "EventDayBuddy is running"}

# ===== Telegram Webhook =====
@app.post(f"/{TELEGRAM_TOKEN}")
async def telegram_webhook(request: Request):
    """Endpoint for Telegram to POST updates to."""
    try:
        from bot.handlers import application

        if application is None:
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