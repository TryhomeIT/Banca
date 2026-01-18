import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import engine, Base, SessionLocal
from .routers import auth_router, publications_router, admin_router
from .config import settings
from .services.file_watcher import watch_folders, scan_all_folders
from .services.telegram_bot import bot_watchdog_loop
import logging
from logging.handlers import RotatingFileHandler

# ... (logging config)

# Background task references
watcher_task = None
bot_watchdog_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    global watcher_task, bot_watchdog_task
    
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
    async def start_background_tasks():
        await asyncio.sleep(2)
        # 1. Folder Watcher
        asyncio.create_task(watch_folders(interval_seconds=60))
        # 2. Telegram Bot Watchdog
        asyncio.create_task(bot_watchdog_loop(interval_seconds=60))

    watcher_task = asyncio.create_task(start_background_tasks())
    logger.info("👀 Background tasks scheduled (starts in 2s)")
    
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
