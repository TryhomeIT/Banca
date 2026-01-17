#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/administrator/Documents/Development/Tryhomeit/Jornais/backend')

from app.database import SessionLocal
from app.models import Publication
from sqlalchemy import func
from collections import defaultdict

db = SessionLocal()

# Find duplicate titles
print("=== Checking for duplicate publications in database ===\n")

# Group by title and category
duplicates = db.query(
    Publication.title,
    Publication.category,
    func.count(Publication.id).label('count')
).group_by(Publication.title, Publication.category).having(func.count(Publication.id) > 1).all()

if duplicates:
    print(f"Found {len(duplicates)} duplicate title+category combinations:\n")
    for title, category, count in duplicates:
        print(f"  {title} ({category}): {count} entries")
        
        # Show details
        pubs = db.query(Publication).filter(
            Publication.title == title,
            Publication.category == category
        ).all()
        
        for pub in pubs:
            print(f"    - ID: {pub.id}, File: {pub.filename}, Date: {pub.publication_date}")
        print()
else:
    print("No duplicate title+category combinations found in database.")

# Check for duplicate filenames
print("\n=== Checking for duplicate filenames ===\n")
filename_duplicates = db.query(
    Publication.filename,
    func.count(Publication.id).label('count')
).group_by(Publication.filename).having(func.count(Publication.id) > 1).all()

if filename_duplicates:
    print(f"Found {len(filename_duplicates)} duplicate filenames:\n")
    for filename, count in filename_duplicates:
        print(f"  {filename}: {count} entries")
        pubs = db.query(Publication).filter(Publication.filename == filename).all()
        for pub in pubs:
            print(f"    - ID: {pub.id}, Title: {pub.title}, Category: {pub.category}")
        print()
else:
    print("No duplicate filenames found in database.")

db.close()
