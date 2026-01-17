import json
import unicodedata
import os
from pathlib import Path
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import Publication

def normalize(s):
    if not s: return s
    return unicodedata.normalize('NFC', s)

def run_normalization():
    print("🚀 Starting Database and Config Normalization...")
    
    # 1. Normalize publications.json
    config_path = Path('/home/administrator/Documents/Development/Tryhomeit/Jornais/backend/storage/data/publications.json')
    if config_path.exists():
        print(f"📄 Normalizing {config_path}...")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        for key in ['jornais', 'revistas', 'keywords', 'topics']:
            if key in config:
                config[key] = sorted(list(set(normalize(name) for name in config[key])))
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print("✅ Config file normalized.")
    else:
        print("⚠️ publications.json not found.")

    # 2. Normalize Database Records
    db = SessionLocal()
    try:
        # Load normalized config for categorization
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        jornais = set(config.get('jornais', []))
        revistas = set(config.get('revistas', []))
        
        pubs = db.query(Publication).all()
        print(f"🗄️ Processing {len(pubs)} database records...")
        
        updated_count = 0
        recategorized_count = 0
        
        for p in pubs:
            original_title = p.title
            normalized_title = normalize(p.title)
            original_category = p.category
            
            # Update title if needed
            if original_title != normalized_title:
                p.title = normalized_title
                updated_count += 1
            
            # Re-check categorization for 'other'
            if p.category == 'other':
                if normalized_title in jornais:
                    p.category = 'newspaper'
                    recategorized_count += 1
                elif normalized_title in revistas:
                    p.category = 'magazine'
                    recategorized_count += 1
            
        if updated_count > 0 or recategorized_count > 0:
            db.commit()
            print(f"✨ Success: {updated_count} titles normalized, {recategorized_count} publications recategorized.")
        else:
            print("ℹ️ No changes needed in database.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_normalization()
