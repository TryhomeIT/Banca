import os
from pathlib import Path
from app.database import SessionLocal
from app.models.models import Publication

def print_tree(directory, level=0, max_depth=2):
    if level > max_depth: return
    prefix = "  " * level + "├── "
    try:
        if not os.path.exists(directory):
            print(f"{prefix}[MISSING] {directory}")
            return
        
        print(f"{prefix}{os.path.basename(directory)}/")
        for item in os.listdir(directory):
            path = os.path.join(directory, item)
            if os.path.isdir(path):
                print_tree(path, level + 1, max_depth)
            else:
                print(f"{ '  ' * (level + 1)}├── {item}")
    except Exception as e:
        print(f"{prefix}[ERROR] {e}")

def debug_setup():
    print("\n🔍 DEBUG: Storage Directory Structure (/app/storage):")
    print_tree("/app/storage")
    
    print("\n🔍 DEBUG: Database Sample (First 3 Publications):")
    db = SessionLocal()
    try:
        pubs = db.query(Publication).limit(3).all()
        for p in pubs:
            print(f"  ID: {p.id}")
            print(f"  Title: {p.title}")
            print(f"  DB File Path: {p.file_path}")
            print(f"  DB Thumb Path: {p.thumbnail_path}")
            print(f"  Exists (File)? {os.path.exists(p.file_path)}")
            print(f"  Exists (Thumb)? {os.path.exists(p.thumbnail_path) if p.thumbnail_path else 'N/A'}")
            print("-" * 30)
    finally:
        db.close()

if __name__ == "__main__":
    debug_setup()
