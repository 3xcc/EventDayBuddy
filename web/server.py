import os
from fastapi import FastAPI

PORT = int(os.getenv("PORT", 8000))  # Render sets this automatically

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "ok", "message": "EventDayBuddy is running"}