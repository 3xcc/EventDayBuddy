from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from config.logger import logger, log_and_raise
from config.envs import DB_URL, LOG_LEVEL
from db.models import Base

# ===== Create engine and session =====
try:
    engine = create_engine(
        DB_URL,
        pool_pre_ping=True,
        echo=(LOG_LEVEL == "DEBUG")  # Show SQL in debug mode
    )
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False   # ✅ keep attributes after commit
    )
    logger.info("[DB] ✅ Connected to database.")
except Exception as e:
    log_and_raise("DB Init", "connecting to database", e)

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
    Ensures the session is closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()