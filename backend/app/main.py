import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import engine, Base, SessionLocal
from .routers import auth_router, publications_router, admin_router
from .config import settings
from .services.file_watcher import watch_folders, scan_all_folders
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_file = settings.LOGS_DIR / "app.log"

# Main handler
file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Stream handler for console
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)
stream_handler.setLevel(logging.INFO)

# Root logger setup
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(stream_handler)

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Background task reference
watcher_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    global watcher_task
    
    # Startup
    logger.info("🚀 Starting Jornais Digital Newsstand...")
    
    # Enable WAL mode for SQLite to handle concurrent writes better
    from sqlalchemy import text
    db = SessionLocal()
    try:
        db.execute(text("PRAGMA journal_mode=WAL"))
        db.commit()
    except Exception as e:
        logger.warning(f"Could not set WAL mode: {e}")
    finally:
        db.close()
    
    # Start background folder watcher (includes initial scan)
    # Using a small delay to allow uvicorn to finish binding before heavy work starts
    async def start_watcher_with_delay():
        await asyncio.sleep(2)
        await watch_folders(interval_seconds=60)

    watcher_task = asyncio.create_task(start_watcher_with_delay())
    logger.info("👀 Folder watcher scheduled (starts in 2s)")
    
    yield  # Application is running
    
    # Shutdown
    if watcher_task:
        watcher_task.cancel()
    logger.info("👋 Jornais shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description="A digital newsstand for reading newspapers and magazines",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(publications_router)
app.include_router(admin_router)

# Serve static files (thumbnails)
app.mount("/thumbnails", StaticFiles(directory=str(settings.THUMBNAIL_DIR)), name="thumbnails")

@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "description": "Digital Newsstand API",
        "features": [
            "PDF Library Management",
            "Telegram Bot Integration",
            "Auto-import from folders"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
