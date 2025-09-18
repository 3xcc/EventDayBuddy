import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.logger import logger
from config.envs import LOG_LEVEL

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

# ===== Routes =====
@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
def health_check():
    """Basic health check endpoint for uptime monitoring."""
    logger.info("[Web] Health check endpoint called.")
    return {"status": "ok", "message": "EventDayBuddy is running"}
