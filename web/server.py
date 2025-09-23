import os
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from config.logger import logger
from config.envs import LOG_LEVEL, TELEGRAM_TOKEN
from bot.handlers import init_bot
from telegram import Update

# Render sets PORT automatically; default to 8000 for local dev
PORT = int(os.getenv("PORT", 8000))

app = FastAPI(title="EventDayBuddy API", version="1.0.0")

# ===== Middleware =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for stricter security in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Startup Hook =====
@app.on_event("startup")
async def startup_event():
    logger.info("[Web] FastAPI startup — initializing bot...")
    try:
        await init_bot()
    except Exception as e:
        logger.error(f"[Startup] Bot init failed: {e}", exc_info=True)

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
