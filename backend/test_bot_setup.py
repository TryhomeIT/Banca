import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path('/home/administrator/Documents/Development/Tryhomeit/Jornais/backend')
sys.path.append(str(backend_path))

from app.services.telegram_bot import get_bot_status, start_telegram_bot
from app.config import settings

async def check():
    print(f"Settings LOGS_DIR: {settings.LOGS_DIR}")
    print(f"Log file path: {settings.LOGS_DIR / 'telegram_bot.log'}")
    print(f"Status: {get_bot_status()}")
    
    # Try creating the file manually
    try:
        log_path = settings.LOGS_DIR / "telegram_bot.log"
        with open(log_path, "a") as f:
            f.write("Test log entry\n")
        print(f"Successfully wrote to {log_path}")
    except Exception as e:
        print(f"Failed to write to log file: {e}")

if __name__ == "__main__":
    asyncio.run(check())
