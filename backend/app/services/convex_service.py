import os
import logging
from typing import Dict, Any, Optional
from convex import ConvexClient
from dotenv import load_dotenv
from pathlib import Path

# Explicitly load .env from the backend root
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Try to load from frontend/.env.local if not set
if not os.getenv("CONVEX_URL"):
    frontend_env = Path(__file__).parent.parent.parent.parent / 'frontend' / '.env.local'
    if frontend_env.exists():
        load_dotenv(dotenv_path=frontend_env)

from ..database import SessionLocal
from .settings import settings_service

# Use the existing app logger if possible, else root
logger = logging.getLogger("app.services.convex_service")

CONVEX_URL = os.getenv("CONVEX_URL") or "https://sensible-dalmatian-949.convex.cloud"

class ConvexService:
    def __init__(self):
        self.client = None
        if CONVEX_URL:
            try:
                self.client = ConvexClient(CONVEX_URL)
                deploy_key = os.getenv("CONVEX_DEPLOY_KEY")
                auth_status = "✅ Authenticated" if deploy_key else "⚠️ No Deploy Key (Read-only?)"
                logger.info(f"✅ Convex client initialized. {auth_status}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Convex client: {e}")

    def _is_enabled(self) -> bool:
        """Check if Convex sync is enabled in system settings."""
        db = SessionLocal()
        try:
            val = settings_service.get_setting(db, "USE_CONVEX", "false")
            return val.lower() == "true"
        except Exception:
            return False
        finally:
            db.close()

    def sync_publication(self, publication_data: Dict[str, Any]):
        """Sync a publication to Convex."""
        if not self.client or not self._is_enabled():
            return

        try:
            clean_data = {k: v for k, v in publication_data.items() if v is not None}
            self.client.mutation("publications:add", clean_data)
            logger.info(f"🚀 Synced to Convex: {publication_data.get('title')}")
        except Exception as e:
            logger.error(f"❌ Error syncing to Convex: {e}")

    def clear_all(self):
        """Clear all publications from Convex."""
        if not self.client or not self._is_enabled():
            return
        try:
            self.client.mutation("publications:clearAll", {})
            logger.info(f"✅ Cleared records from Convex")
        except Exception as e:
            logger.error(f"❌ Error clearing Convex: {e}")

    def update_system_status(self, is_processing: bool, current_task: Optional[str] = None):
        """Update system status in Convex."""
        if not self.client or not self._is_enabled():
            return
        try:
            from datetime import datetime
            self.client.mutation("system_status:update", {
                "is_processing": is_processing,
                "current_task": current_task,
                "last_update": datetime.now().isoformat()
            })
        except Exception as e:
            pass # Silent fail for status updates

# Global instance
convex_service = ConvexService()
