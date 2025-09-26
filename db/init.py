import time
from sqlalchemy import create_engine, text   # ✅ import text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from config.logger import logger, log_and_raise
from config.envs import DB_URL, LOG_LEVEL
from db.models import Base


# ===== Engine creation with retry/backoff =====
def init_engine_with_retry(url: str, retries: int = 5, backoff: int = 2):
    """Create SQLAlchemy engine with retry/backoff for transient DB errors."""
    attempt = 0
    while True:
        try:
            engine = create_engine(
                url,
                pool_size=5,        # keep under Supabase free-tier pooler cap
                max_overflow=0,     # don’t burst beyond pool_size
                pool_pre_ping=True, # validate connections before using
                echo=(LOG_LEVEL == "DEBUG"),
            )
            # ✅ test connection immediately using SQLAlchemy 2.0 style
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("[DB] ✅ Connected to database.")
            return engine
        except Exception as e:
            attempt += 1
            if attempt >= retries:
                log_and_raise("DB Init", f"failed after {retries} attempts", e)
            wait = backoff ** attempt
            logger.warning(f"[DB] Connection failed (attempt {attempt}), retrying in {wait}s...")
            time.sleep(wait)


# ===== Create engine and session factory =====
engine = init_engine_with_retry(DB_URL)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # ✅ keep attributes after commit
)


# ===== Initialize tables =====
def init_db():
    """Create all tables if they do not exist."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("[DB] ✅ Tables created or verified.")
    except Exception as e:
        log_and_raise("DB Init", "creating tables", e)


# ===== Context manager for DB sessions =====
@contextmanager
def get_db():
    """
    Provide a transactional scope around a series of operations.
    Ensures commit on success, rollback on failure, and session close.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()        # ✅ commit if no exception
    except Exception as e:
        db.rollback()      # ✅ rollback on error
        logger.error(f"[DB] ❌ Transaction rolled back due to error: {e}", exc_info=True)
        raise
    finally:
        db.close()