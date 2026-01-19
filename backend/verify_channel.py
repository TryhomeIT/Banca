
import asyncio
import os
import sys

# Add the parent directory to sys.path to allow importing from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.services.settings import settings_service
from app.services.telegram_bot import test_telegram_connection

async def verify():
    db = SessionLocal()
    try:
        print("--- Checking Telegram Configuration ---")
        settings = settings_service.get_all_settings(db)
        
        api_id = settings.get('TELEGRAM_API_ID')
        api_hash = settings.get('TELEGRAM_API_HASH')
        channel_id = settings.get('TELEGRAM_CHANNEL_ID')
        
        print(f"API ID: {api_id}")
        # Mask API Hash for security
        masked_hash = f"{api_hash[:4]}...{api_hash[-4:]}" if api_hash and len(api_hash) > 8 else "Not Set"
        print(f"API Hash: {masked_hash}")
        print(f"Channel ID/Username: {channel_id}")
        
        if not api_id or not api_hash:
            print("\n❌ Error: TELEGRAM_API_ID or TELEGRAM_API_HASH is missing.")
            return

        if not channel_id:
            print("\n⚠️ Warning: TELEGRAM_CHANNEL_ID is not set.")
            
        print("\n--- Testing Connection ---")
        success, message = await test_telegram_connection(api_id, api_hash, channel_id)
        
        print(message)
        
        if success:
            print("\n✅ Verification Successful!")
        else:
            print("\n❌ Verification Failed.")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(verify())
