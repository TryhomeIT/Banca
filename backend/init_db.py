"""
Database initialization script
Creates default admin user if database is empty
"""
import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.models import Base, User, SystemSettings
from app.services.auth import get_password_hash

def init_database():
    """Initialize database with default admin user if needed"""
    
    database_url = settings.DATABASE_URL
    
    # Create engine with SQLite settings for concurrent access
    engine = create_engine(
        database_url, 
        connect_args={
            "check_same_thread": False,
            "timeout": 30
        }
    )
    
    # Enable WAL mode for better concurrent access
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Check if database is empty (no users)
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        
        if user_count == 0:
            print("📝 Database is empty. Creating default admin user...")
            
            # Create default admin user
            admin_user = User(
                username="admin",
                email="admin@banca.com",
                hashed_password=get_password_hash("changeme"),
                is_admin=True
            )
            
            db.add(admin_user)
            db.commit()
            
            print("✅ Default admin user created:")
            print("   Username: admin")
            print("   Password: changeme")
            print("   ⚠️  Please change this password after first login!")
            
            # Initialize default system settings
            print("⚙️  Initializing default system settings...")
            default_settings = [
                ("TELEGRAM_API_ID", "", "Telegram API ID", "telegram"),
                ("TELEGRAM_API_HASH", "", "Telegram API Hash", "telegram"),
                ("TELEGRAM_PHONE", "", "Telegram Phone Number", "telegram"),
                ("TELEGRAM_CHANNEL_ID", "", "Source Channel ID (Numeric or @username)", "telegram"),
                ("USE_CONVEX", "false", "Enable Cloud Sync (Convex)", "general"),
                ("GEMINI_API_KEY", "", "Gemini AI API Key", "ai"),
                ("DOWNLOADS_RETENTION_DAYS_JORNAIS", "7", "Days to keep newspaper files", "general"),
                ("DOWNLOADS_RETENTION_DAYS_REVISTAS", "90", "Days to keep magazine files", "general"),
            ]
            
            for key, value, desc, cat in default_settings:
                setting = SystemSettings(key=key, value=value, description=desc, category=cat)
                db.add(setting)
            
            db.commit()
            print("✅ System settings initialized.")
            
            # Create default publications.json
            import json
            data_dir = str(settings.DATA_DIR)
            os.makedirs(data_dir, exist_ok=True)
            publications_file = os.path.join(data_dir, 'publications.json')
            if not os.path.exists(publications_file):
                default_publications = {
                    "jornais": [],
                    "revistas": [],
                    "keywords": [],
                    "topics": []
                }
                with open(publications_file, 'w', encoding='utf-8') as f:
                    json.dump(default_publications, f, indent=2, ensure_ascii=False)
                print("✅ Default publications.json created.")
        else:
            print(f"✅ Database already initialized ({user_count} users)")
            
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
