"""
File Watcher Service for Telegram Bot Integration

This service monitors folders where the Telegram bot saves downloaded PDFs
and automatically imports them into the Jornais web app database.
"""

import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import shutil
import unicodedata
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from ..config import settings
from ..database import SessionLocal
from ..models import Publication
from .pdf_service import generate_thumbnail
from .convex_service import convex_service

logger = logging.getLogger(__name__)

# Global lock to prevent concurrent scans
_scan_lock = asyncio.Lock()

# Folder paths for telegram bot downloads - use settings
DATA_DIR = settings.TELEGRAM_DATA_DIR
JORNAIS_FOLDER = os.path.join(DATA_DIR, 'Jornais')
REVISTAS_FOLDER = os.path.join(DATA_DIR, 'Revistas')
OTHERS_FOLDER = os.path.join(DATA_DIR, 'Others')
THUMBNAILS_FOLDER = os.path.join(DATA_DIR, 'thumbnails')

# Track already processed files
processed_files_cache: Dict[str, datetime] = {}

def ensure_folders_exist():
    """Create category folders if they don't exist."""
    for folder in [JORNAIS_FOLDER, REVISTAS_FOLDER, OTHERS_FOLDER]:
        os.makedirs(folder, exist_ok=True)

def get_category_from_folder(folder_path: str) -> str:
    """Get category name from folder path."""
    folder_name = os.path.basename(folder_path)
    return folder_name.lower()

def parse_publication_date(filename: str) -> Optional[datetime]:
    """
    Extract publication date from filename.
    Expected formats:
    - Publication - dd-mm-yyyy.pdf
    - (yyyymmdd-PT) Publication.pdf
    - Publication _ dd _ Month _ YYYY.pdf (Italian/Spanish formats)
    """
    import re
    
    # Format: Publication - dd-mm-yyyy.pdf
    match = re.search(r'(\d{2})-(\d{2})-(\d{4})\.pdf$', filename, re.IGNORECASE)
    if match:
        day, month, year = match.groups()
        try:
            return datetime(int(year), int(month), int(day))
        except ValueError:
            pass
    
    # Format: (yyyymmdd-PT) Publication.pdf
    match = re.search(r'\((\d{8})-PT\)', filename)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            pass

    # Custom parsing for Italian/Spanish/English/Portuguese months
    italian_months = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']
    spanish_months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    english_months = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
    portuguese_months = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    
    all_months_list = italian_months + spanish_months + english_months + portuguese_months
    all_months_pattern = '|'.join(all_months_list)

    # Pattern: _DD_Month_YYYY or _-_Month_YYYY
    match = re.search(rf'[_\s-]*(\d{{1,2}})[_\s]+({all_months_pattern})[_\s]+(\d{{4}})\.pdf$', filename, re.IGNORECASE)
    if match:
        day, month_name, year = match.groups()
        month_name = month_name.lower()
        
        # Find month index (1-based)
        month = 0
        if month_name in italian_months: month = italian_months.index(month_name) + 1
        elif month_name in spanish_months: month = spanish_months.index(month_name) + 1
        elif month_name in english_months: month = english_months.index(month_name) + 1
        elif month_name in portuguese_months: month = portuguese_months.index(month_name) + 1
        
        if month > 0:
            try:
                return datetime(int(year), month, int(day))
            except ValueError:
                pass
    
    return None

def extract_publication_name(filename: str) -> str:
    """
    Extract clean publication name from filename using improved regex patterns.
    """
    import re
    
    # Remove extension
    name = filename.replace('.pdf', '').replace('.PDF', '')
    
    # Remove Telegram downloader prefix like (20240101-PT)
    name = re.sub(r'^\(\d{8}-PT\)\s*!?\s*', '', name)
    
    # Remove date prefixes like DD-MM-YY- or DD-MM-YYYY-
    name = re.sub(r'^\d{2}-\d{2}-\d{2,4}-\s*', '', name)
    
    # Split by common separators to get the base name
    parts = name.split(' - ')
    if len(parts) >= 2:
        name = parts[0].strip()
    else:
        name = name.strip()
    
    # Replace separators with spaces for normalization (common in bot downloads)
    name = name.replace('_', ' ').replace('-', ' ')
    
    # Define month names in multiple languages
    italian_months = 'Gennaio|Febbraio|Marzo|Aprile|Maggio|Giugno|Luglio|Agosto|Settembre|Ottobre|Novembre|Dicembre'
    spanish_months = 'Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre'
    english_months = 'January|February|March|April|May|June|July|August|September|October|November|December'
    portuguese_months = 'Janeiro|Fevereiro|Março|Abril|Maio|Junho|Julho|Agosto|Setembro|Outubro|Novembro|Dezembro'
    
    # Add abbreviations
    abbreviations = 'ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic|gen|mag|set|ott|dez'
    
    all_months = f'{italian_months}|{spanish_months}|{english_months}|{portuguese_months}|{abbreviations}'
    
    # Remove date patterns (handles various formats at the end):
    # DD Month YYYY, Month YYYY, (MM.YY)
    name = re.sub(rf'[_\s-]*\d{{1,2}}[_\s]+({all_months})[_\s]+\d{{4}}$', '', name, flags=re.IGNORECASE)
    name = re.sub(rf'[_\s-]+({all_months})[_\s]+\d{{4}}$', '', name, flags=re.IGNORECASE)
    
    # Handle the case with abbreviations like "11-ene" or "11 ene"
    name = re.sub(rf'[_\s-]*\d{{1,2}}[_\s-]+({abbreviations})[_\s-]*$', '', name, flags=re.IGNORECASE)
    
    # Also handle patterns like (01.26) for months
    name = re.sub(r'\s*\(\d{2}\.\d{2}\)\s*$', '', name)
    
    # Remove trailing separators and extra whitespace
    name = re.sub(r'[_\s-]+$', '', name)
    
    # Normalize to NFC
    name = unicodedata.normalize('NFC', name)
    
    return name.strip() or filename

def import_pdf_to_database(file_path: str, category: str) -> Optional[Publication]:
    """Import a single PDF file into the database."""
    db = SessionLocal()
    try:
        filename = os.path.basename(file_path)
        import uuid
        
        # Check if already in database by original filename
        # We also check if the category matches to handle files moving between folders
        existing = db.query(Publication).filter(
            Publication.original_filename == filename
        ).first()
        
        if existing:
            needs_update = False
            
            # 1. If category changed (e.g. moved from Others to Jornais), update it
            if existing.category != category:
                logger.info(f"🔄 Updating category for {filename}: {existing.category} -> {category}")
                existing.category = category
                needs_update = True
                
            # 2. Check if PDF file exists in uploads, if not try to restore it
            if not os.path.exists(existing.file_path):
                logger.info(f"⚠️ PDF missing from uploads: {existing.filename}. Restoring...")
                os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
                try:
                    shutil.copy2(file_path, existing.file_path)
                except Exception as e:
                    logger.error(f"Failed to restore PDF: {e}")
            
            # 3. Check if thumbnail exists, if not, try to regenerate
            if not existing.thumbnail_path or not os.path.exists(existing.thumbnail_path):
                if os.path.exists(existing.file_path):
                    logger.info(f"🔄 Regenerating missing thumbnail for: {filename}")
                    try:
                        thumbnail_path, page_count = generate_thumbnail(
                            existing.file_path,
                            existing.filename.rsplit('.', 1)[0]
                        )
                        if thumbnail_path:
                            existing.thumbnail_path = thumbnail_path
                            if page_count > 0:
                                existing.page_count = page_count
                            needs_update = True
                    except Exception as e:
                        logger.error(f"Failed to regenerate thumbnail: {e}")
            
            if needs_update:
                db.commit()
                db.refresh(existing)
            
            # Sync to Convex (always sync to ensure metadata like title/category is correct)
            try:
                convex_service.sync_publication({
                    "title": existing.title,
                    "filename": existing.filename,
                    "original_filename": existing.original_filename,
                    "thumbnail_path": existing.thumbnail_path,
                    "file_path": existing.file_path,
                    "page_count": existing.page_count,
                    "file_size": existing.file_size,
                    "category": existing.category,
                    "publication_date": existing.publication_date.isoformat() if existing.publication_date else None,
                    "external_id": existing.id
                })
            except Exception as e:
                logger.error(f"⚠️ Convex sync failed for existing file: {e}")

            return existing
        
        # Extract publication info
        title = extract_publication_name(filename)
        pub_date = parse_publication_date(filename)
        file_size = os.path.getsize(file_path)
        
        # Copy to uploads folder - Use UUID for absolute uniqueness
        unique_suffix = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"{timestamp}_{unique_suffix}_{filename}"
        dest_path = settings.UPLOAD_DIR / unique_filename
        
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        shutil.copy2(file_path, dest_path)
        
        # Generate thumbnail
        thumbnail_path, page_count = generate_thumbnail(
            str(dest_path), 
            unique_filename.rsplit('.', 1)[0]
        )
        
        # Create publication record
        publication = Publication(
            title=title,
            filename=unique_filename,
            original_filename=filename,
            thumbnail_path=thumbnail_path,
            file_path=str(dest_path),
            page_count=page_count,
            file_size=file_size,
            category=category,
            publication_date=pub_date
        )
        
        db.add(publication)
        db.commit()
        db.refresh(publication)
        
        # Sync to Convex
        try:
            convex_service.sync_publication({
                "title": publication.title,
                "filename": publication.filename,
                "original_filename": publication.original_filename,
                "thumbnail_path": publication.thumbnail_path,
                "file_path": publication.file_path,
                "page_count": publication.page_count,
                "file_size": publication.file_size,
                "category": publication.category,
                "publication_date": publication.publication_date.isoformat() if publication.publication_date else None,
                "external_id": publication.id
            })
        except Exception as e:
            logger.error(f"⚠️ Convex sync failed: {e}")

        logger.info(f"✅ Imported: {title} ({category}) - {page_count} pages")
        return publication
        
    except Exception as e:
        logger.error(f"❌ Error importing {file_path}: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def scan_folder(folder_path: str, category: str) -> int:
    """Scan a folder and import all PDF files."""
    if not os.path.exists(folder_path):
        return 0
    
    imported = 0
    for filename in os.listdir(folder_path):
        if not filename.lower().endswith('.pdf'):
            continue
        
        file_path = os.path.join(folder_path, filename)
        
        # Skip if already processed recently
        if file_path in processed_files_cache:
            continue
        
        result = import_pdf_to_database(file_path, category)
        if result:
            imported += 1
            processed_files_cache[file_path] = datetime.now()
    
    return imported

def scan_all_folders(force: bool = False) -> Dict[str, int]:
    """Scan all category folders and import new PDFs."""
    if force:
        logger.info("♻️ Force scan requested: Clearing memory cache")
        processed_files_cache.clear()
        
    ensure_folders_exist()
    
    results = {
        'jornais': scan_folder(JORNAIS_FOLDER, 'newspaper'),
        'revistas': scan_folder(REVISTAS_FOLDER, 'magazine'),
        'others': scan_folder(OTHERS_FOLDER, 'others')
    }
    
    total = sum(results.values())
    logger.info(f"📚 Scan complete. Imported {total} new items.")
    
    return results

async def watch_folders(interval_seconds: int = 30):
    """
    Background task that periodically scans folders for new files.
    Run this as a background task in the FastAPI app.
    """
    logger.info(f"👀 Starting folder watcher (interval: {interval_seconds}s)")
    
    while True:
        try:
            async with _scan_lock:
                await asyncio.to_thread(scan_all_folders)
        except Exception as e:
            logger.error(f"Error in folder watcher: {e}")
        
        await asyncio.sleep(interval_seconds)

def get_folder_stats() -> Dict[str, Any]:
    """Get statistics about the watched folders."""
    ensure_folders_exist()
    
    stats = {}
    for folder, name in [(JORNAIS_FOLDER, 'jornais'), (REVISTAS_FOLDER, 'revistas'), (OTHERS_FOLDER, 'others')]:
        if os.path.exists(folder):
            files = [f for f in os.listdir(folder) if f.lower().endswith('.pdf')]
            total_size = sum(os.path.getsize(os.path.join(folder, f)) for f in files)
            stats[name] = {
                'count': len(files),
                'size_mb': round(total_size / (1024 * 1024), 2),
                'path': folder
            }
        else:
            stats[name] = {'count': 0, 'size_mb': 0, 'path': folder}
    
    return stats
