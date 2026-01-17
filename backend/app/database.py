from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# SQLite connection settings for better concurrent access
connect_args = {
    "check_same_thread": False,  # Needed for SQLite with multiple threads
    "timeout": 60,  # Wait up to 60 seconds for locks to clear (increased)
}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_size=20,       # Increase baseline connections
    max_overflow=30,    # Allow bursts of connections
    pool_timeout=60,    # Wait longer for a connection from the pool
)

# Enable WAL mode and set busy timeout for better concurrent access
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=60000")  # 60 seconds
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

