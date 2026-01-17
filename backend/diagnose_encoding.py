import os
import sys
import unicodedata
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup DB connection directly
DATABASE_URL = "sqlite:////app/storage/banca.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def to_hex(s):
    return ":".join("{:04x}".format(ord(c)) for c in s)

def scan_dir(path):
    print(f"\n📂 Scanning {path}...")
    if not os.path.exists(path):
        print("  [MISSING]")
        return
        
    for root, dirs, files in os.walk(path):
        for name in files:
            full_path = os.path.join(root, name)
            # relative = os.path.relpath(full_path, path)
            print(f"  📄 {name}")
            print(f"     Hex: {to_hex(name)}")
            print(f"     Norm NFC: {to_hex(unicodedata.normalize('NFC', name))}")
            print(f"     Norm NFD: {to_hex(unicodedata.normalize('NFD', name))}")

def check_db():
    print("\n🗄️ Checking Database Records...")
    session = SessionLocal()
    try:
        results = session.execute(text("SELECT id, title, file_path, thumbnail_path FROM publications LIMIT 10")).fetchall()
        for row in results:
            print(f"\n  🆔 ID: {row[0]}")
            print(f"     Title: {row[1]}")
            
            fpath = row[2]
            fname = os.path.basename(fpath)
            print(f"     File Path: {fpath}")
            print(f"     Filename Hex: {to_hex(fname)}")
            
            exists = os.path.exists(fpath)
            print(f"     Exists on disk? {'✅ YES' if exists else '❌ NO'}")
            
            if not exists:
                # Try to find it manually in Jornais/Revistas
                print("     Trying to locate...")
                found = False
                for folder in ['/app/storage/Jornais', '/app/storage/Revistas']:
                    if not os.path.exists(folder): continue
                    for f in os.listdir(folder):
                        if unicodedata.normalize('NFC', f) == unicodedata.normalize('NFC', fname):
                            print(f"     Found matching NFC in {folder}: {f}")
                            found = True
                        elif unicodedata.normalize('NFD', f) == unicodedata.normalize('NFD', fname):
                            print(f"     Found matching NFD in {folder}: {f}")
                            found = True
                if not found:
                    print("     ❌ File seems completely missing from Jornais/Revistas folders.")

    except Exception as e:
        print(f"Error reading DB: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("🔍 DIAGNOSTIC TOOL")
    scan_dir("/app/storage/Jornais")
    scan_dir("/app/storage/Revistas")
    check_db()
