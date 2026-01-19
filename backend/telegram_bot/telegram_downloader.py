import asyncio
import os
import json
import re
import shutil
import logging
import sys
import hashlib
import time as time_module
import sqlite3
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# ================== CRITICAL: Patch SQLite to prevent "database is locked" errors ==================
_original_sqlite_connect = sqlite3.connect

def _patched_sqlite_connect(*args, **kwargs):
    if 'timeout' not in kwargs:
        kwargs['timeout'] = 60.0
    conn = _original_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=60000")
    except:
        pass
    return conn

sqlite3.connect = _patched_sqlite_connect
# ================== End SQLite patch ==================

from pyrogram import Client, filters
from pyrogram.errors import FloodWait, RPCError
from pdf2image import convert_from_path
from telegram_review_handler import send_file_for_review, setup_callback_handlers, scan_existing_others_files, extract_publication_name, process_ai_queue
from komga_integration import schedule_komga_scan

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Constants
CONNECTION_CHECK_INTERVAL = 300

# Directory Setup
DATA_DIR = os.getenv('DATA_DIR', '/app/storage')
DOWNLOADS_DIR = os.getenv('DOWNLOADS_DIR', '/app/storage/downloads')

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

PROCESSED_FILES_LOG = os.path.join(DATA_DIR, 'processed_files.json')
SCAN_REQUEST_FILE = os.path.join(DATA_DIR, 'scan_request.json')
ACTIVITY_LOG_FILE = os.path.join(DATA_DIR, 'activity_log.json')
PID_LOCK_FILE = os.path.join(DATA_DIR, 'telegram_bot.pid')

# Global instances
app = None
RAW_SOURCE_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# API Credentials
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
PHONE = os.getenv('TELEGRAM_PHONE')

# Initialize global app
if API_ID and API_HASH:
    session_name = os.getenv('SESSION_NAME', 'session_name')
    logger.info(f"📂 Workdir: {DATA_DIR} | Session: {session_name}")
    app = Client(
        name=session_name,
        api_id=int(API_ID),
        api_hash=API_HASH,
        phone_number=PHONE,
        workdir=DATA_DIR
    )

# --- Helper Functions ---

def check_single_instance():
    if os.path.exists(PID_LOCK_FILE):
        try:
            with open(PID_LOCK_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            try:
                os.kill(old_pid, 0)
                logger.error(f"❌ Another bot instance is running (PID: {old_pid})")
                sys.exit(1)
            except OSError:
                logger.info(f"🔓 Removing stale lock file")
        except: pass
    with open(PID_LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))

def cleanup_pid_file():
    try:
        if os.path.exists(PID_LOCK_FILE): os.remove(PID_LOCK_FILE)
    except: pass

def load_processed_files():
    try:
        if os.path.exists(PROCESSED_FILES_LOG):
            with open(PROCESSED_FILES_LOG, 'r', encoding='utf-8') as f: return json.load(f)
    except: pass
    return {}

def save_processed_files(processed_files):
    try:
        with open(PROCESSED_FILES_LOG, 'w', encoding='utf-8') as f:
            json.dump(processed_files, f, indent=2, ensure_ascii=False)
    except: pass

def is_file_already_processed(filename, file_size, date_str=None):
    files = load_processed_files()
    h = hashlib.md5(f"{filename}_{file_size}_{date_str}".encode()).hexdigest()
    return h in files

def mark_file_as_processed(filename, file_size, date_str=None, action="processed"):
    files = load_processed_files()
    h = hashlib.md5(f"{filename}_{file_size}_{date_str}".encode()).hexdigest()
    files[h] = {
        'filename': filename, 'size': file_size, 'date': date_str,
        'ts': datetime.now().isoformat(), 'action': action
    }
    save_processed_files(files)

def load_publications_config():
    try:
        p_file = os.path.join(DATA_DIR, 'publications.json')
        with open(p_file, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {"jornais": [], "revistas": [], "keywords": [], "topics": []}

def get_publication_category(name, config):
    if name in config.get("jornais", []): return "Jornais"
    if name in config.get("revistas", []): return "Revistas"
    return None

def parse_filename(filename):
    if not filename: return None, None
    from urllib.parse import unquote
    match = re.match(r'\((\d{8})-PT\)[\s%20]*(.+)\.pdf$', unquote(filename), re.IGNORECASE)
    if match:
        d, n = match.group(1), match.group(2).split('_')[0]
        return unicodedata.normalize('NFC', n), f"{d[6:8]}-{d[4:6]}-{d[0:4]}"
    return None, None

def log_activity(filename, category):
    try:
        logs = []
        if os.path.exists(ACTIVITY_LOG_FILE):
            with open(ACTIVITY_LOG_FILE, 'r', encoding='utf-8') as f: logs = json.load(f)
        logs.append({"timestamp": datetime.now().isoformat(), "filename": filename, "category": category})
        with open(ACTIVITY_LOG_FILE, 'w', encoding='utf-8') as f: json.dump(logs[-1000:], f, indent=2)
    except: pass

async def resolve_source_chat():
    """Robustly resolve the source channel ID or username."""
    if not RAW_SOURCE_ID:
        logger.error("❌ TELEGRAM_CHANNEL_ID not set")
        return None
        
    logger.info(f"🔎 Resolving source: {RAW_SOURCE_ID}")
    
    # 1. Try direct resolve
    try:
        chat = await app.get_chat(RAW_SOURCE_ID)
        logger.info(f"✅ Resolved directly: {chat.title} ({chat.id})")
        return chat.id
    except Exception:
        pass
        
    # 2. Search dialogs
    logger.info("🕵️ Channel not cached. Searching all dialogs...")
    async for dialog in app.get_dialogs():
        chat = dialog.chat
        # Check ID match (handling string vs int and -100 prefix)
        if str(chat.id) == str(RAW_SOURCE_ID) or \
           str(chat.id).replace("-100", "") == str(RAW_SOURCE_ID).replace("-100", "") or \
           (chat.username and chat.username.lower() == str(RAW_SOURCE_ID).lower().replace("@", "")):
            logger.info(f"✅ Found in dialogs: {chat.title} ({chat.id})")
            return chat.id
            
    logger.error(f"❌ Could not find channel {RAW_SOURCE_ID} in your chat list!")
    return None

async def process_message(message, client, config=None):
    """Processes a single message from Telegram."""
    if not message.document: return "skipped"
    if message.document.mime_type != 'application/pdf': return "skipped"
    
    if config is None:
        config = load_publications_config()
    
    fname = message.document.file_name or "unnamed.pdf"
    fsize = message.document.file_size
    caption = message.caption or ""
    
    # Log every PDF found for transparency
    logger.info(f"🧐 Found PDF: {fname} ({fsize} bytes)")
    if caption: logger.info(f"   Caption: {caption[:100]}...")
    
    # 1. Try standard parsing (format: (YYYYMMDD-PT) Name.pdf)
    pub_name, date_fmt = parse_filename(fname)
    is_keyword_match = False
    
    # 2. If not standard, try Keyword matching (Flexible)
    if not pub_name:
        # Create a clean string for matching: replace underscores, dots, hyphens with spaces
        search_target = f"{fname} {caption}".lower()
        search_target_clean = search_target.replace('_', ' ').replace('.', ' ').replace('-', ' ')
        
        for kw in config.get('keywords', []):
            kw_clean = kw.lower().strip()
            kw_no_spaces = kw_clean.replace(" ", "")
            
            # We match against both raw and cleaned name to be safe
            # Also check if the keyword without spaces exists (e.g. "Auto Express" matching "AutoExpress")
            if (kw_clean in search_target or 
                kw_clean in search_target_clean or 
                kw_no_spaces in search_target or 
                kw_no_spaces in search_target_clean):
                
                pub_name = unicodedata.normalize('NFC', kw)
                is_keyword_match = True
                logger.info(f"✨ Match found via keyword '{kw}': {fname}")
                break
    
    # 3. Handle No Match
    if not pub_name:
        logger.info(f"⏭️ No match for: {fname}")
        return "skipped"

    # 4. Check if already processed
    if is_file_already_processed(fname, fsize, date_fmt):
        logger.info(f"⏭️ Already processed: {fname}")
        return "skipped"

    # 5. Download and Process
    download_path = os.path.join(DOWNLOADS_DIR, fname)
    try:
        logger.info(f"📥 Downloading: {fname}")
        
        # Handle FloodWait with automatic retry
        try:
            await client.download_media(message, file_name=download_path)
        except FloodWait as e:
            wait_time = e.value
            logger.warning(f"⏳ FloodWait: Telegram requires a {wait_time}s wait. Sleeping...")
            await asyncio.sleep(wait_time + 5)  # Add buffer
            logger.info(f"🔄 Retrying download: {fname}")
            await client.download_media(message, file_name=download_path)
        
        # Add small delay between downloads to prevent rate limiting
        await asyncio.sleep(2)
        
        # Verify PDF integrity
        try: 
            convert_from_path(download_path, first_page=1, last_page=1)
        except Exception as e: 
            logger.error(f"❌ Corrupt PDF skipped: {fname} - {e}")
            return "error"

        # Determine Category
        cat = get_publication_category(pub_name, config)
        if cat:
            dest = os.path.join(DATA_DIR, cat)
            os.makedirs(dest, exist_ok=True)
            # Use cleaner name if we have a date
            final_name = f"{pub_name} - {date_fmt}.pdf" if date_fmt else fname
            shutil.copy2(download_path, os.path.join(dest, final_name))
            mark_file_as_processed(fname, fsize, date_fmt, "saved")
            log_activity(final_name, cat)
            logger.info(f"✅ Saved to {cat}: {final_name}")
            return "saved_cat"
        elif is_keyword_match:
            dest = os.path.join(DATA_DIR, 'Others')
            os.makedirs(dest, exist_ok=True)
            shutil.copy2(download_path, os.path.join(dest, fname))
            mark_file_as_processed(fname, fsize, date_fmt, "saved_via_keyword")
            log_activity(fname, "Others")
            logger.info(f"✅ Keyword match '{pub_name}', saved to Others: {fname}")
            return "saved_keyword"
        else:
            # Fallback to Others
            dest = os.path.join(DATA_DIR, 'Others')
            os.makedirs(dest, exist_ok=True)
            shutil.copy2(download_path, os.path.join(dest, fname))
            # Optional: Send to bot for interactive review if logic is present
            try:
                await send_file_for_review(client, os.path.join(dest, fname))
                mark_file_as_processed(fname, fsize, date_fmt, "sent_to_review")
                return "sent_to_review"
            except:
                mark_file_as_processed(fname, fsize, date_fmt, "saved_to_others")
                return "saved_others"
            
            log_activity(fname, "Others")
            logger.info(f"📂 Category unknown, saved to 'Others': {fname}")
            
    except FloodWait as e:
        # If we still get FloodWait after retry, log and skip this file for now
        logger.error(f"⏳ FloodWait persists for {fname}. Skipping. Wait required: {e.value}s")
        return "flood_wait"
    except Exception as e:
        logger.error(f"❌ Download failed for {fname}: {e}")
        return "error"
    finally:
        if os.path.exists(download_path): 
            try: os.unlink(download_path)
            except: pass

# --- Main Logic ---

async def check_scan_requests():
    if not os.path.exists(SCAN_REQUEST_FILE): return
    try:
        with open(SCAN_REQUEST_FILE, 'r') as f: req = json.load(f)
        os.remove(SCAN_REQUEST_FILE)
        
        target_id = await resolve_source_chat()
        if not target_id: return
        
        config = load_publications_config()
        
        if req.get('type') == 'keywords':
            days = req.get('days', 7)
            logger.info(f"🔍 HISTORY SCAN: {days} days on {target_id}")
            logger.info(f"⚙️ Loaded Config: {len(config.get('jornais', []))} Newspapers, {len(config.get('revistas', []))} Magazines")
            logger.info(f"🔑 Active Keywords ({len(config.get('keywords', []))}): {', '.join(config.get('keywords', []))}")
            
            cutoff = datetime.now() - timedelta(days=days)
            stats = {"checked": 0, "saved": 0, "keyword": 0, "review": 0, "skipped": 0, "error": 0}
            
            async for msg in app.get_chat_history(target_id, limit=30000):
                if msg.date < cutoff: break
                status = await process_message(msg, app, config=config)
                stats["checked"] += 1
                
                if status == "saved_cat": stats["saved"] += 1
                elif status == "saved_keyword": stats["keyword"] += 1
                elif status == "sent_to_review": stats["review"] += 1
                elif status == "skipped": stats["skipped"] += 1
                elif status == "error": stats["error"] += 1
            
            logger.info(f"✅ Scan complete. Checked {stats['checked']} messages.")
            logger.info(f"📊 Summary: {stats['saved']} matched publications, {stats['keyword']} keyword matches, {stats['review']} sent to review. ({stats['skipped']} skipped)")
            
        elif req.get('type') == 'ai_categorize': await process_ai_queue(app)
        elif req.get('type') == 'others': await scan_existing_others_files(app)
    except Exception as e: logger.error(f"Scan Error: {e}")

async def main():
    logger.info("🚀 Bot Connecting...")
    try:
        await app.start()
    except FloodWait as e:
        logger.error(f"⏳ FloodWait: {e.value}s")
        await asyncio.sleep(e.value); return
    except RPCError as e:
        logger.error(f"❌ Auth Error: {e}"); await asyncio.sleep(3600); return

    # Resolve ID once on startup to cache it
    source_id = await resolve_source_chat()
    
    # Live listener
    @app.on_message(filters.chat(source_id) if source_id else filters.private)
    async def msg_handler(client, message):
        # Reload config for live messages to ensure latest keywords are used
        config = load_publications_config()
        await process_message(message, client, config=config)

    setup_callback_handlers(app)
    asyncio.create_task(maintenance_loop())
    
    logger.info("👂 Bot ready and listening.")
    while True:
        await asyncio.sleep(300)
        await app.get_me()

async def maintenance_loop():
    while True:
        try:
            if app.is_connected: await check_scan_requests()
        except: pass
        await asyncio.sleep(10)

async def run():
    check_single_instance()
    import atexit
    atexit.register(cleanup_pid_file)
    while True:
        try:
            s_name = os.getenv('SESSION_NAME', 'session_name')
            for ext in ['-journal', '-wal', '-shm']:
                try: os.remove(os.path.join(DATA_DIR, f"{s_name}.session{ext}"))
                except: pass
            await main()
        except Exception as e:
            logger.error(f"Crash: {e}")
            await asyncio.sleep(30)

if __name__ == '__main__':
    asyncio.run(run())