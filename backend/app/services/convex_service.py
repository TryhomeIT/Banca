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

# Use the existing app logger if possible, else root
logger = logging.getLogger("app.services.convex_service")

CONVEX_URL = os.getenv("CONVEX_URL") or "https://sensible-dalmatian-949.convex.cloud"

class ConvexService:
    def __init__(self):
        self.client = None
        if CONVEX_URL:
            try:
                # The ConvexClient automatically looks for CONVEX_DEPLOY_KEY in env
                self.client = ConvexClient(CONVEX_URL)
                
                # Log status
                deploy_key = os.getenv("CONVEX_DEPLOY_KEY")
                auth_status = "✅ Authenticated (Key found)" if deploy_key else "⚠️ No Deploy Key found (Read-only?)"
                
                print(f"✅ Convex client initialized with URL: {CONVEX_URL}")
                print(f"   Status: {auth_status}")
                logger.info(f"✅ Convex client initialized. {auth_status}")
            except Exception as e:
                print(f"❌ Failed to initialize Convex client: {e}")
                logger.error(f"❌ Failed to initialize Convex client: {e}")
        else:
            logger.warning("⚠️ CONVEX_URL not found")

    def sync_publication(self, publication_data: Dict[str, Any]):
        """Sync a publication to Convex."""
        if not self.client:
            return

        try:
            # Filter out None values to respect v.optional()
            # sending 'null' can sometimes fail if not explicitly handled as v.union(v.string(), v.null())
            clean_data = {k: v for k, v in publication_data.items() if v is not None}
            
            # Log the payload for debugging
            logger.info(f"📤 Syncing payload: {clean_data}")

            # Map Python/SQLAlchemy model data to Convex schema
            # publication_data should be a dict
            self.client.mutation("publications:add", clean_data)
            logger.info(f"🚀 Synced to Convex: {publication_data.get('title')}")
        except Exception as e:
            logger.error(f"❌ Error syncing to Convex: {e}")

    def clear_all(self):
        """Clear all publications from Convex."""
        if not self.client:
            return
        try:
            logger.warning("☢️ Clearing all data from Convex...")
            count = self.client.mutation("publications:clearAll", {})
            logger.info(f"✅ Cleared {count} records from Convex")
        except Exception as e:
            logger.error(f"❌ Error clearing Convex data: {e}")

    def update_system_status(self, is_processing: bool, current_task: Optional[str] = None):
        """Update system status in Convex for real-time frontend monitoring."""
        if not self.client:
            return

        try:
            from datetime import datetime
            self.client.mutation("system_status:update", {
                "is_processing": is_processing,
                "current_task": current_task,
                "last_update": datetime.now().isoformat()
            })
        except Exception as e:
            # We might not have defined system_status:update yet, but that's okay for now
            logger.error(f"❌ Error updating system status in Convex: {e}")

# Global instance
convex_service = ConvexService()
