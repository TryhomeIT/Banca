"""
Telegram Bot Service - Process Manager

This module manages the external Telegram Downloader script (telegram_downloader.py)
as a subprocess. This prevents database locking issues (since only one process
uses the session file) and ensures full feature parity including interactive reviews.
"""

import os
import sys
import json
import logging
import asyncio
import subprocess
import signal
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from ..config import settings

logger = logging.getLogger(__name__)

# Config
SCRIPT_PATH = settings.BASE_DIR / 'telegram_bot' / 'telegram_downloader.py'
DATA_DIR = Path(settings.TELEGRAM_DATA_DIR)
SCAN_REQUEST_FILE = DATA_DIR / 'scan_request.json'
PROCESSED_FILES_LOG = DATA_DIR / 'processed_files.json'

# Global process handle
bot_process: Optional[subprocess.Popen] = None

def get_bot_status() -> Dict[str, Any]:
    """Get the status of the bot process."""
    global bot_process
    
    is_running = False
    pid = None
    
    # Check if our managed process is running
    if bot_process:
        if bot_process.poll() is None:
            is_running = True
            pid = bot_process.pid
        else:
            # Process has ended
            bot_process = None
            
    # Note: We only track processes we started. If container was restarted,
    # the bot needs to be started from the UI again.

    # Load stats from file if possible (since we can't share memory)
    # The external bot writes to processed_files.json
    processed_count = 0
    if PROCESSED_FILES_LOG.exists():
        try:
            with open(PROCESSED_FILES_LOG, 'r') as f:
                data = json.load(f)
                processed_count = len(data)
        except:
            pass

    return {
        "is_running": is_running,
        "pid": pid,
        "script_path": str(SCRIPT_PATH),
        "status": "running" if is_running else "stopped",
        "processed_files_count": processed_count,
        "files_downloaded": processed_count, # Alias for frontend compatibility
        "notes": "Managed as external process"
    }

async def start_telegram_bot():
    """Start the Telegram bot as a subprocess."""
    global bot_process
    
    status = get_bot_status()
    if status["is_running"]:
        logger.info(f"Bot already running (PID: {status['pid']})")
        return
    
    if not SCRIPT_PATH.exists():
        logger.error(f"Bot script not found at: {SCRIPT_PATH}")
        raise FileNotFoundError(f"Bot script not found at {SCRIPT_PATH}")
        
    logger.info(f"🚀 Starting bot script: {SCRIPT_PATH}")
    
    # AGGRESSIVE CLEANUP: Ensure no stale instances or locks exist
    try:
        # 1. Kill any existing instances not tracked by this process
        subprocess.run("pkill -f 'python.*telegram_downloader.py'", shell=True)
        
        # 2. Remove stale PID file if it exists
        pid_file = DATA_DIR / 'telegram_bot.pid'
        if pid_file.exists():
            try:
                os.remove(pid_file)
                logger.info("🧹 Removed stale PID lock file during startup")
            except Exception as e:
                logger.warning(f"Could not remove stale PID file: {e}")
                
        # 3. Clear session locks if they exist (optional, but helps with 'database locked')
        session_path = DATA_DIR / 'session_name'
        for ext in ['.session-journal', '.session-wal', '.session-shm']:
            lock = Path(f"{session_path}{ext}")
            if lock.exists():
                try:
                    os.remove(lock)
                except: pass
                
    except Exception as e:
        logger.warning(f"Cleanup warning during startup: {e}")
    
    try:
        # Spawn process
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['DATA_DIR'] = str(DATA_DIR)
        env['DOWNLOADS_DIR'] = str(DATA_DIR / 'downloads')
        
        # Load settings from database
        from ..database import SessionLocal
        from .settings import settings_service
        db = SessionLocal()
        try:
            db_settings = settings_service.get_all_settings(db)
            env['GEMINI_API_KEY'] = db_settings.get('GEMINI_API_KEY', settings.GEMINI_API_KEY)
            env['TELEGRAM_API_ID'] = db_settings.get('TELEGRAM_API_ID', '')
            env['TELEGRAM_API_HASH'] = db_settings.get('TELEGRAM_API_HASH', '')
            env['TELEGRAM_PHONE'] = db_settings.get('TELEGRAM_PHONE', '')
            env['TELEGRAM_CHANNEL_ID'] = db_settings.get('TELEGRAM_CHANNEL_ID', '')
        finally:
            db.close()
        
        # Consistent session name
        env['SESSION_NAME'] = 'session_name'
        
        # Open log file for the bot
        log_file = open(settings.LOGS_DIR / "telegram_bot.log", "a")
        log_file.write(f"\n--- Bot start at {datetime.now()} ---\n")
        log_file.flush()
        
        bot_process = subprocess.Popen(
            [sys.executable, str(SCRIPT_PATH)],
            cwd=str(SCRIPT_PATH.parent),
            env=env,
            stdout=log_file,
            stderr=log_file,
        )
        
        logger.info(f"✅ Bot process started with PID: {bot_process.pid} (logging to telegram_bot.log)")
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot process: {e}")
        raise

async def stop_telegram_bot():
    """Stop the Telegram bot process."""
    global bot_process
    
    # Check managed process
    if bot_process:
        logger.info(f"🛑 Stopping bot process {bot_process.pid}...")
        bot_process.terminate()
        try:
            bot_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            bot_process.kill()
        bot_process = None
        
    # Also Force Kill any lingering instances via pkill
    try:
        subprocess.run("pkill -f 'python.*telegram_downloader.py'", shell=True)
    except:
        pass
        
    logger.info("✅ Bot stopped")

async def bot_watchdog_loop(interval_seconds: int = 60):
    """
    Background task to ensure the bot is always running if configured.
    Restarts the bot if it crashes.
    """
    logger.info(f"🐕 Starting Telegram Bot Watchdog (interval: {interval_seconds}s)")
    
    while True:
        try:
            # 1. Check configuration
            from ..database import SessionLocal
            from .settings import settings_service
            db = SessionLocal()
            try:
                db_settings = settings_service.get_all_settings(db)
                is_configured = (
                    db_settings.get('TELEGRAM_API_ID') and 
                    db_settings.get('TELEGRAM_API_HASH') and 
                    db_settings.get('TELEGRAM_PHONE')
                )
            finally:
                db.close()

            # 2. Check current status
            status = get_bot_status()
            
            if is_configured:
                if not status["is_running"]:
                    logger.info("🤖 Bot configured but not running. Starting...")
                    try:
                        await start_telegram_bot()
                    except Exception as e:
                        logger.error(f"Failed to start bot in watchdog: {e}")
            else:
                if status["is_running"]:
                    logger.info("⚠️ Bot running but configuration removed. Stopping...")
                    await stop_telegram_bot()
                    
        except Exception as e:
            logger.error(f"Error in Bot Watchdog loop: {e}")
            
        await asyncio.sleep(interval_seconds)

# Variables for compatibility with admin.py imports
bot_running = False # This property is a bit tricky now, admin.py uses it.
# We need to make bot_running a property or update admin.py.
# But admin.py imports 'bot_running' directly. 
# Changing it to a function call in admin.py is best, OR we monkey patch it.

# Update: In admin.py line 204: `if bot_running:`
# Code in admin.py imports `bot_running` variable.
# If I change this module, admin.py will import the initial value (False) and it won't update.
# I MUST update admin.py to call `get_bot_status()['is_running']` or similar.
# Or I can use a module-level getattr? No.

# Plan: Update admin.py to NOT import bot_running, but call a function `is_bot_running()`.

def is_bot_running():
    return get_bot_status()["is_running"]

# Scan functions wrapper
async def scan_channel_history(limit: int = 100):
    """Trigger scan via file request (Quick Scan)."""
    if not is_bot_running():
        raise Exception("Bot is not running")
        
    # Map limit to days approximately? Or just use days=1 for quick scan
    days = 1
    
    req = {
        "type": "keywords",
        "days": days,
        "timestamp": str(datetime.now())
    }
    
    with open(SCAN_REQUEST_FILE, 'w') as f:
        json.dump(req, f)
        
    logger.info("Queued scan request for bot")
    return limit # Dummy return

async def scan_channel_history_by_date(days: int = 7):
    """Trigger scan via file request."""
    if not is_bot_running():
        raise Exception("Bot is not running")
        
    req = {
        "type": "keywords",
        "days": days,
        "timestamp": str(datetime.now())
    }
    
    with open(SCAN_REQUEST_FILE, 'w') as f:
        json.dump(req, f)
        
    logger.info(f"Queued {days}-day scan request for bot")
    return {"message": f"{days}-day scan queued"}

async def trigger_ai_categorization():
    """Trigger manual AI categorization via file request."""
    if not is_bot_running():
        raise Exception("Bot is not running")
        
    req = {
        "type": "ai_categorize",
        "timestamp": str(datetime.now())
    }
    
    with open(SCAN_REQUEST_FILE, 'w') as f:
        json.dump(req, f)
        
    logger.info("Queued manual AI categorization request for bot")
    return {"message": "AI categorization queued"}

async def test_telegram_connection(api_id: str, api_hash: str, channel_id: str = None) -> tuple[bool, str]:
    """
    Test Telegram API credentials and optionally channel access.
    Uses the persistent session if available.
    Returns (success, message).
    """
    from pyrogram import Client
    import asyncio
    
    try:
        # Try to clean up stale lock files before testing
        session_path = str(DATA_DIR / 'session_name')
        for ext in ['-journal', '-wal', '-shm']:
            try:
                os.remove(f"{session_path}.session{ext}")
            except:
                pass

        test_client = Client(
            name=session_path,
            api_id=int(api_id),
            api_hash=api_hash,
            sleep_threshold=10, # Don't wait too long on flood limits
        )
        
        await test_client.connect()
        
        # Check if we're logged in
        try:
            me = await test_client.get_me()
            auth_status = f" (Logged in as {me.first_name})"
            is_logged_in = True
        except Exception as e:
            auth_status = " (Not logged in yet)"
            is_logged_in = False
        
        if channel_id and is_logged_in:
            # Convert channel_id to int if numeric
            try:
                target_id = int(channel_id)
            except ValueError:
                target_id = channel_id  # Keep as string for @usernames
            
            # First try direct access
            try:
                chat = await test_client.get_chat(target_id)
                await test_client.disconnect()
                return True, f"✅ Connected to channel '{chat.title}'!{auth_status}"
            except Exception:
                pass  # Try searching dialogs
            
            # For private channels, search through dialogs
            logger.info(f"Searching dialogs for channel {target_id}...")
            found_channel = None
            
            async for dialog in test_client.get_dialogs():
                chat = dialog.chat
                chat_id = chat.id
                
                # Check various ID formats
                if isinstance(target_id, int):
                    raw_id = abs(chat_id) % 10000000000  # Extract raw ID without -100 prefix
                    if raw_id == target_id or chat_id == target_id or chat_id == -int(f"100{target_id}"):
                        found_channel = chat
                        break
                elif isinstance(target_id, str):
                    if chat.username and chat.username.lower() == target_id.lstrip('@').lower():
                        found_channel = chat
                        break
            
            if found_channel:
                await test_client.disconnect()
                return True, f"✅ Found channel '{found_channel.title}' (ID: {found_channel.id})!{auth_status}"
            else:
                await test_client.disconnect()
                return False, f"❌ Channel not found. Make sure you are a member of the channel with ID {channel_id}.{auth_status}"
                
        elif channel_id and not is_logged_in:
            await test_client.disconnect()
            return True, f"✅ API credentials valid. Please log in first to access private channels.{auth_status}"
        
        await test_client.disconnect()
        return True, f"✅ API credentials are valid!{auth_status}"
        
    except ValueError:
        return False, "❌ Invalid API ID: Must be a number"
    except Exception as e:
        logger.error(f"Telegram test failed: {e}")
        return False, f"❌ Connection failed: {str(e)}"

# Store pending login state
_pending_login_client = None
_pending_phone_code_hash = None

async def request_login_code(api_id: str, api_hash: str, phone: str) -> tuple[bool, str]:
    """
    Request a login code from Telegram. Returns (success, message).
    The code will be sent to the user's phone.
    """
    global _pending_login_client, _pending_phone_code_hash
    from pyrogram import Client
    
    try:
        # Create a persistent session in the data directory
        session_path = str(DATA_DIR / 'session_name')
        
        _pending_login_client = Client(
            name=session_path,
            api_id=int(api_id),
            api_hash=api_hash,
        )
        
        await _pending_login_client.connect()
        
        # Send code request
        sent_code = await _pending_login_client.send_code(phone)
        _pending_phone_code_hash = sent_code.phone_code_hash
        
        logger.info(f"Login code sent to {phone}")
        return True, f"✅ Login code sent to {phone}. Please enter the code you received."
        
    except Exception as e:
        logger.error(f"Failed to request login code: {e}")
        _pending_login_client = None
        _pending_phone_code_hash = None
        return False, f"❌ Failed to send code: {str(e)}"

async def submit_login_code(phone: str, code: str, password: str = None) -> tuple[bool, str]:
    """
    Submit the login code received on the phone. Returns (success, message).
    If 2FA is enabled, password may be required.
    """
    global _pending_login_client, _pending_phone_code_hash
    
    if not _pending_login_client or not _pending_phone_code_hash:
        return False, "❌ No pending login. Please request a code first."
    
    try:
        # Sign in with the code
        await _pending_login_client.sign_in(
            phone_number=phone,
            phone_code_hash=_pending_phone_code_hash,
            phone_code=code
        )
        
        # Get user info to confirm login
        me = await _pending_login_client.get_me()
        await _pending_login_client.disconnect()
        
        # Clear pending state
        _pending_login_client = None
        _pending_phone_code_hash = None
        
        logger.info(f"Successfully logged in as {me.first_name}")
        return True, f"✅ Successfully logged in as {me.first_name}! You can now start the bot."
        
    except Exception as e:
        error_str = str(e)
        
        # Check if 2FA password is required
        if "PASSWORD_HASH_INVALID" in error_str or "SESSION_PASSWORD_NEEDED" in error_str:
            if password:
                try:
                    await _pending_login_client.check_password(password)
                    me = await _pending_login_client.get_me()
                    await _pending_login_client.disconnect()
                    _pending_login_client = None
                    _pending_phone_code_hash = None
                    return True, f"✅ Successfully logged in as {me.first_name}!"
                except Exception as pw_e:
                    return False, f"❌ 2FA password incorrect: {str(pw_e)}"
            else:
                return False, "🔐 Two-factor authentication is enabled. Please enter your 2FA password."
        
        logger.error(f"Failed to sign in: {e}")
        return False, f"❌ Sign in failed: {str(e)}"

async def check_login_status(api_id: str, api_hash: str) -> tuple[bool, str]:
    """Check if the session is already logged in."""
    from pyrogram import Client
    
    try:
        session_path = str(DATA_DIR / 'session_name')
        
        client = Client(
            name=session_path,
            api_id=int(api_id),
            api_hash=api_hash,
        )
        
        await client.connect()
        
        try:
            me = await client.get_me()
            await client.disconnect()
            return True, f"✅ Logged in as {me.first_name} (@{me.username or 'no username'})"
        except Exception:
            await client.disconnect()
            return False, "Not logged in"
            
    except Exception as e:
        return False, f"❌ Error checking status: {str(e)}"
