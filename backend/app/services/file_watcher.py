"""
File Watcher Service for Telegram Bot Integration

This service monitors folders where the Telegram bot saves downloaded PDFs
and automatically imports them into the Jornais web app database.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import shutil
import unicodedata
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from ..config import settings
from ..database import SessionLocal
from ..models import Publication, ReadingProgress
from .pdf_service import generate_thumbnail, delete_publication_files
from .settings import settings_service

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

RETENTION_SETTINGS = {
    'newspaper': 'DOWNLOADS_RETENTION_DAYS_JORNAIS',
    'magazine': 'DOWNLOADS_RETENTION_DAYS_REVISTAS',
}

SOURCE_FOLDERS_BY_CATEGORY = {
    'newspaper': ['Jornais', 'jornais'],
    'magazine': ['Revistas', 'revistas'],
}

def ensure_folders_exist():
    """Create category folders if they don't exist."""
    for folder in [JORNAIS_FOLDER, REVISTAS_FOLDER, OTHERS_FOLDER]:
        os.makedirs(folder, exist_ok=True)

def delete_source_publication_file(original_filename: str, category: str):
    """Delete the original downloaded file from the source category folder if it still exists."""
    if not original_filename:
        return

    for folder_name in SOURCE_FOLDERS_BY_CATEGORY.get(category, []):
        candidate = Path(DATA_DIR) / folder_name / original_filename
        if candidate.exists():
            try:
                candidate.unlink()
            except Exception as exc:
                logger.warning(f"Failed to delete source file {candidate}: {exc}")

def get_publication_reference_date(publication: Publication) -> Optional[datetime]:
    """Return the best available date for retention comparisons."""
    return publication.publication_date or publication.created_at

def derive_publication_date(file_path: str) -> datetime:
    """Use the file modification time as fallback when the filename has no embedded date."""
    try:
        return datetime.fromtimestamp(os.path.getmtime(file_path))
    except OSError:
        return datetime.utcnow()

def enforce_retention_policies(db=None) -> int:
    """Remove expired publications and files based on configured retention days.

    The newest issue for each title is always preserved, even if it falls outside
    the configured retention window.
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()

    removed_count = 0

    try:
        now = datetime.utcnow()

        for category, setting_key in RETENTION_SETTINGS.items():
            raw_days = settings_service.get_setting(db, setting_key)
            try:
                retention_days = int(raw_days)
            except (TypeError, ValueError):
                continue

            cutoff = now - timedelta(days=retention_days)
            publications = db.query(Publication).filter(Publication.category == category).all()

            latest_publication_ids_by_title = {}
            for publication in publications:
                title = publication.title or ''
                current_latest = latest_publication_ids_by_title.get(title)
                publication_key = (
                    get_publication_reference_date(publication) or datetime.min,
                    publication.created_at or datetime.min,
                    publication.id,
                )

                if current_latest is None or publication_key > current_latest[0]:
                    latest_publication_ids_by_title[title] = (publication_key, publication.id)

            protected_ids = {
                publication_id for _, publication_id in latest_publication_ids_by_title.values()
            }

            for publication in publications:
                reference_date = get_publication_reference_date(publication)
                if reference_date is None or reference_date >= cutoff:
                    continue
                if publication.id in protected_ids:
                    continue

                try:
                    db.query(ReadingProgress).filter(
                        ReadingProgress.publication_id == publication.id
                    ).delete(synchronize_session=False)
                    delete_publication_files(publication.filename, publication.thumbnail_path)
                    delete_source_publication_file(publication.original_filename, category)
                    db.delete(publication)
                    db.commit()
                    removed_count += 1
                except Exception as exc:
                    db.rollback()
                    logger.error(f"Failed to prune expired publication {publication.id}: {exc}")

        if removed_count:
            logger.info(f"🧹 Retention cleanup removed {removed_count} expired publications")

        return removed_count
    finally:
        if own_session:
            db.close()

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
            fallback_date = derive_publication_date(file_path)
            
            # 1. If category changed (e.g. moved from Others to Jornais), update it
            if existing.category != category:
                logger.info(f"🔄 Updating category for {filename}: {existing.category} -> {category}")
                existing.category = category
                needs_update = True

            # 1b. Backfill missing publication dates using the download/import timestamp.
            if not existing.publication_date:
                existing.publication_date = fallback_date
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
            
            return existing
        
        # Extract publication info
        title = extract_publication_name(filename)
        pub_date = parse_publication_date(filename) or derive_publication_date(file_path)
        file_size = os.path.getsize(file_path)
        
        # Extract collection name for books if present
        import re
        collection_name = None
        if category == 'book':
            match = re.search(r'\{([^}]+)\}', filename)
            if match:
                collection_name = match.group(1).strip()
                title = re.sub(r'\{[^}]+\}', '', title).strip()
        
        # Copy to uploads folder - Use UUID for absolute uniqueness
        unique_suffix = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        from .comic_converter import is_comic_archive, convert_comic_to_pdf
        is_comic = is_comic_archive(filename)
        
        dest_filename = filename
        if is_comic:
            dest_filename = filename.rsplit('.', 1)[0] + '.pdf'
            
        unique_filename = f"{timestamp}_{unique_suffix}_{dest_filename}"
        dest_path = settings.UPLOAD_DIR / unique_filename
        
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        if is_comic:
            success = convert_comic_to_pdf(file_path, str(dest_path))
            if not success:
                logger.error(f"Failed to convert comic {filename} to PDF")
                return None
            # Re-read file size after conversion
            file_size = os.path.getsize(dest_path)
        else:
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
            collection_name=collection_name,
            publication_date=pub_date
        )
        
        db.add(publication)
        db.commit()
        db.refresh(publication)
        
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
        ext = filename.lower()
        if not (ext.endswith('.pdf') or ext.endswith('.cbz') or ext.endswith('.cbr') or ext.endswith('.zip') or ext.endswith('.rar')):
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
    enforce_retention_policies()
    
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
            files = [f for f in os.listdir(folder) if f.lower().endswith(('.pdf', '.cbz', '.cbr', '.zip', '.rar'))]
            total_size = sum(os.path.getsize(os.path.join(folder, f)) for f in files)
            stats[name] = {
                'count': len(files),
                'size_mb': round(total_size / (1024 * 1024), 2),
                'path': folder
            }
        else:
            stats[name] = {'count': 0, 'size_mb': 0, 'path': folder}
    
    return stats
