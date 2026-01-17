#!/usr/bin/env python3
import os
import hashlib
from pathlib import Path

def get_file_hash(filepath, chunk_size=8192):
    """Calculate MD5 hash of file"""
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)
    return md5.hexdigest()

def find_duplicates():
    folders = ['data/Jornais', 'data/Revistas', 'data/Outros']
    files_by_hash = {}
    files_by_name_size = {}
    
    for folder in folders:
        if not os.path.exists(folder):
            continue
        
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            if not os.path.isfile(filepath) or not filename.endswith('.pdf'):
                continue
            
            size = os.path.getsize(filepath)
            name_size_key = (filename, size)
            
            # Track by name+size
            if name_size_key not in files_by_name_size:
                files_by_name_size[name_size_key] = []
            files_by_name_size[name_size_key].append(filepath)
    
    # Find duplicates by name and size
    print("=== Duplicates by Name + Size ===")
    duplicates_found = False
    for (name, size), paths in files_by_name_size.items():
        if len(paths) > 1:
            duplicates_found = True
            print(f"\n{name} ({size} bytes):")
            for path in paths:
                print(f"  - {path}")
            
            # Verify with hash
            hashes = {}
            for path in paths:
                h = get_file_hash(path)
                if h not in hashes:
                    hashes[h] = []
                hashes[h].append(path)
            
            if len(hashes) > 1:
                print(f"  ⚠️  WARNING: Same name/size but DIFFERENT content!")
            else:
                print(f"  ✓ Confirmed identical content (hash: {list(hashes.keys())[0][:8]}...)")
    
    if not duplicates_found:
        print("No duplicates found!")

if __name__ == '__main__':
    find_duplicates()
