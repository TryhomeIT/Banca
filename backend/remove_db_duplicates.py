#!/usr/bin/env python3
"""
Remove duplicate publication entries from the database.
Keeps the oldest entry (lowest ID) for each unique combination of title, category, and publication_date.
"""
import sys
sys.path.insert(0, '/home/administrator/Documents/Development/Tryhomeit/Jornais/backend')

from app.database import SessionLocal
from app.models import Publication, ReadingProgress
from sqlalchemy import func
import os

db = SessionLocal()

print("=== Removing duplicate publications from database ===\n")

# Find all duplicate groups (same title, category, and publication_date)
duplicates = db.query(
    Publication.title,
    Publication.category,
    Publication.publication_date,
    func.count(Publication.id).label('count')
).group_by(
    Publication.title, 
    Publication.category,
    Publication.publication_date
).having(func.count(Publication.id) > 1).all()

total_removed = 0
total_size_freed = 0

for title, category, pub_date, count in duplicates:
    print(f"Processing: {title} ({category}) - {pub_date} [{count} duplicates]")
    
    # Get all publications with this combination
    pubs = db.query(Publication).filter(
        Publication.title == title,
        Publication.category == category,
        Publication.publication_date == pub_date
    ).order_by(Publication.id).all()
    
    # Keep the first one (oldest/lowest ID), remove the rest
    keep = pubs[0]
    to_remove = pubs[1:]
    
    print(f"  Keeping ID {keep.id}: {keep.filename}")
    
    for pub in to_remove:
        print(f"  Removing ID {pub.id}: {pub.filename}")
        
        # Delete associated reading progress
        db.query(ReadingProgress).filter(
            ReadingProgress.publication_id == pub.id
        ).delete()
        
        # Delete the file if it exists
        if os.path.exists(pub.file_path):
            try:
                file_size = os.path.getsize(pub.file_path)
                os.remove(pub.file_path)
                total_size_freed += file_size
                print(f"    Deleted file: {pub.file_path}")
            except Exception as e:
                print(f"    Error deleting file: {e}")
        
        # Delete thumbnail if it exists
        if pub.thumbnail_path and os.path.exists(pub.thumbnail_path):
            try:
                os.remove(pub.thumbnail_path)
                print(f"    Deleted thumbnail: {pub.thumbnail_path}")
            except Exception as e:
                print(f"    Error deleting thumbnail: {e}")
        
        # Delete the database entry
        db.delete(pub)
        total_removed += 1
    
    print()

# Commit all changes
db.commit()
db.close()

print(f"\n✅ Cleanup complete!")
print(f"   Removed {total_removed} duplicate database entries")
print(f"   Freed {total_size_freed / (1024*1024):.2f} MB of disk space")
