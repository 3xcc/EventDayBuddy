from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.logger import logger, log_and_raise
from config.envs import DB_URL
from db.models import Base

# ===== Create engine and session =====
try:
    engine = create_engine(DB_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("[DB] ✅ Connected to database.")
except Exception as e:
    log_and_raise("DB Init", "connecting to database", e)

# ===== Initialize tables =====
def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("[DB] ✅ Tables created or verified.")
    except Exception as e:
        log_and_raise("DB Init", "creating tables", e)