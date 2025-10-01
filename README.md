  # EventDayBuddy

  EventDayBuddy is a modern event management and check-in system for boat-based events, built with FastAPI, SQLAlchemy, Telegram Bot API, and Google Sheets integration. It is designed for reliability, admin control, and seamless staff workflows.

  ## Features
  - Telegram bot for booking, check-in, and admin commands
  - FastAPI web server with health checks and webhook endpoint
  - Google Sheets integration for manifests and exports
  - Role-based access: admin, booking_staff, checkin_staff, viewer
  - Bulk import/export of bookings
  - PDF/ID card generation and storage
  - Admin-only `/runtests` command for CI/CD and safety

  ## Quick Start

  ### 1. Requirements
  - Python 3.12+
  - PostgreSQL (Supabase or local)
  - Google Cloud credentials for Sheets API
  - Telegram Bot Token

  ### 2. Environment Variables
  Set these in your Render dashboard or `.env` (for local dev):
  - `TELEGRAM_TOKEN` (required)
  - `PUBLIC_URL` (required, must be HTTPS for Telegram webhooks)
  - `DB_URL` (Postgres connection string)
  - `GOOGLE_SHEET_ID`, `GOOGLE_CREDS_JSON` (for Sheets)
  - `ADMIN_CHAT_ID` (for admin alerts)
  - ...and others as needed (see `config/envs.py`)

  ### 3. Database Setup
  ```
  alembic upgrade head
  ```

  ### 4. Run Locally
  ```
  python main.py
  ```

  ### 5. Deploy to Render
  - Connect your repo
  - Set all required environment variables
  - Use `python main.py` as the start command

  ## Testing
  - **Local:** Requires all envs set (not recommended for safety)
  - **Production:** Use `/runtests` Telegram command (admin only)
    - Runs all unit tests
    - Cleans up test data after run
    - Returns results as message or file

  ## Admin Commands
  - `/start` — Show help menu
  - `/cpe` — Set/view active event
  - `/boatready` — Start boarding session
  - `/checkinmode` — Enable check-in mode
  - `/editseats` — Adjust boat capacity
  - `/departed` — Mark boat departed
  - `/newbooking` — Add booking
  - `/editbooking` — Edit booking
  - `/newbookings` — Bulk import
  - `/attachphoto` — Attach ID photo
  - `/i` — Check-in by ID
  - `/p` — Check-in by phone
  - `/sleeptime` — Graceful shutdown
  - `/runtests` — Run all tests (admin only)

  ## Architecture
  - `bot/` — Telegram bot logic and handlers
  - `db/` — SQLAlchemy models and DB ops
  - `services/` — Business logic (booking, import)
  - `sheets/` — Google Sheets integration
  - `utils/` — Helpers (PDF, money, storage)
  - `web/` — FastAPI server
  - `tests/` — Unit tests (run via `/runtests`)

  ## Contributing
  Pull requests welcome! Please:
  - Write tests for new features
  - Document public APIs and commands
  - Use clear commit messages

  ## License
  MIT
