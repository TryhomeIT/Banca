"""
Admin API endpoints for managing the Telegram bot integration.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..models import User
from ..services import (
    get_current_active_user, 
    scan_all_folders, 
    get_folder_stats,
    start_telegram_bot,
    stop_telegram_bot,
    is_bot_running
)
from ..config import settings
from ..services.settings import settings_service
from ..database import SessionLocal, get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# Path to publications.json (Telegram bot configuration)
PUBLICATIONS_CONFIG = Path(settings.TELEGRAM_DATA_DIR) / 'publications.json'
SCAN_REQUEST_FILE = Path(settings.TELEGRAM_DATA_DIR) / 'scan_request.json'

class ScanResponse(BaseModel):
    jornais: int
    revistas: int
    others: int
    total: int

class FolderStats(BaseModel):
    count: int
    size_mb: float
    path: str

class FolderStatsResponse(BaseModel):
    jornais: FolderStats
    revistas: FolderStats
    others: FolderStats

class OthersFile(BaseModel):
    filename: str
    size: int
    modified: str
    extracted_name: str

class PublicationsConfig(BaseModel):
    jornais: List[str]
    revistas: List[str]
    keywords: List[str]
    topics: List[str]
    ignored: List[str] = []
    others: List[OthersFile] = []

class AddItemRequest(BaseModel):
    category: str  # 'jornais', 'revistas', 'keywords', 'topics', 'ignored'
    item: str

class RemoveItemRequest(BaseModel):
    category: str
    item: str
    permanent: bool = False

class MoveItemRequest(BaseModel):
    item: str
    from_category: str  # 'jornais' or 'revistas'
    to_category: str    # 'jornais' or 'revistas'

class RestoreItemRequest(BaseModel):
    item: str
    target_category: str  # 'jornais', 'revistas', 'keywords', 'topics'

class RecategorizeRequest(BaseModel):
    filename: str
    target_category: str # 'jornais' or 'revistas'

class DeleteOthersRequest(BaseModel):
    filename: str

class SystemSettingsRequest(BaseModel):
    settings: Dict[str, Any]

def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role for access."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def load_publications_config() -> Dict[str, Any]:
    """Load the publications configuration."""
    try:
        if PUBLICATIONS_CONFIG.exists():
            with open(PUBLICATIONS_CONFIG, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading publications config: {e}")
    return {"jornais": [], "revistas": [], "keywords": [], "topics": [], "ignored": []}

def save_publications_config(config: Dict[str, Any]):
    """Save the publications configuration with NFC normalization."""
    import unicodedata
    def normalize_list(l):
        if not l: return []
        # Normalize to NFC and remove duplicates
        return sorted(list(set(unicodedata.normalize('NFC', str(x)) for x in l)))
    
    if 'jornais' in config: config['jornais'] = normalize_list(config['jornais'])
    if 'revistas' in config: config['revistas'] = normalize_list(config['revistas'])
    if 'keywords' in config: config['keywords'] = normalize_list(config['keywords'])
    if 'topics' in config: config['topics'] = normalize_list(config['topics'])
    if 'ignored' in config: config['ignored'] = normalize_list(config['ignored'])
    
    PUBLICATIONS_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with open(PUBLICATIONS_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

# ================== Task Tracking for Persistent Loading States ==================
RUNNING_TASKS_FILE = Path(settings.TELEGRAM_DATA_DIR) / 'running_tasks.json'

def load_running_tasks() -> Dict[str, Any]:
    """Load running tasks from file."""
    try:
        if RUNNING_TASKS_FILE.exists():
            with open(RUNNING_TASKS_FILE, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
                # Clean up stale tasks (older than 30 minutes)
                current_time = datetime.now().timestamp()
                cleaned = {}
                for task_name, task_data in tasks.items():
                    if current_time - task_data.get('started_at', 0) < 1800:  # 30 min
                        cleaned[task_name] = task_data
                if len(cleaned) != len(tasks):
                    save_running_tasks(cleaned)
                return cleaned
    except Exception as e:
        print(f"Error loading running tasks: {e}")
    return {}

def save_running_tasks(tasks: Dict[str, Any]):
    """Save running tasks to file."""
    try:
        RUNNING_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(RUNNING_TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, indent=2)
    except Exception as e:
        print(f"Error saving running tasks: {e}")

def start_task(task_name: str):
    """Mark a task as started."""
    tasks = load_running_tasks()
    tasks[task_name] = {
        'started_at': datetime.now().timestamp(),
        'started_at_iso': datetime.now().isoformat(),
        'status': 'running'
    }
    save_running_tasks(tasks)

def complete_task(task_name: str, result: str = 'completed'):
    """Mark a task as completed."""
    tasks = load_running_tasks()
    if task_name in tasks:
        del tasks[task_name]
        save_running_tasks(tasks)

def is_task_running(task_name: str) -> bool:
    """Check if a task is currently running."""
    tasks = load_running_tasks()
    return task_name in tasks

@router.get("/tasks/status")
async def get_running_tasks(current_user: User = Depends(require_admin)):
    """Get all currently running tasks."""
    tasks = load_running_tasks()
    return {"running_tasks": tasks}


@router.post("/scan", response_model=ScanResponse)
async def trigger_folder_scan(current_user: User = Depends(require_admin)):
    """
    Manually trigger a scan of the Telegram bot download folders.
    Imports any new PDFs into the database.
    """
    results = scan_all_folders()
    return ScanResponse(
        jornais=results['jornais'],
        revistas=results['revistas'],
        others=results['others'],
        total=results['jornais'] + results['revistas'] + results['others']
    )

@router.get("/folders", response_model=FolderStatsResponse)
async def get_folders_statistics(current_user: User = Depends(require_admin)):
    """Get statistics about the Telegram bot download folders."""
    stats = get_folder_stats()
    return FolderStatsResponse(
        jornais=FolderStats(**stats['jornais']),
        revistas=FolderStats(**stats['revistas']),
        others=FolderStats(**stats['others'])
    )

@router.get("/publications/config", response_model=PublicationsConfig)
async def get_publications_configuration(current_user: User = Depends(require_admin)):
    """Get the Telegram bot publications configuration."""
    config = load_publications_config()
    from ..services.file_watcher import OTHERS_FOLDER, extract_publication_name
    
    others_files = []
    if os.path.exists(OTHERS_FOLDER):
        for filename in os.listdir(OTHERS_FOLDER):
            if filename.lower().endswith('.pdf'):
                path = os.path.join(OTHERS_FOLDER, filename)
                stat = os.stat(path)
                others_files.append(OthersFile(
                    filename=filename,
                    size=stat.st_size,
                    modified=str(datetime.fromtimestamp(stat.st_mtime)),
                    extracted_name=extract_publication_name(filename)
                ))

    return PublicationsConfig(
        jornais=config.get('jornais', []),
        revistas=config.get('revistas', []),
        keywords=config.get('keywords', []),
        topics=config.get('topics', []),
        ignored=config.get('ignored', []),
        others=others_files
    )

@router.post("/publications/add")
async def add_publication_item(
    request: AddItemRequest,
    current_user: User = Depends(require_admin)
):
    """Add an item to the publications configuration."""
    if request.category not in ['jornais', 'revistas', 'keywords', 'topics', 'ignored']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category. Must be: jornais, revistas, keywords, topics, or ignored"
        )
    
    config = load_publications_config()
    
    # If adding to an active category, remove from ignored if it's there
    if request.category != 'ignored' and 'ignored' in config and request.item in config['ignored']:
        config['ignored'].remove(request.item)
    
    if request.category not in config:
        config[request.category] = []
    
    if request.item not in config[request.category]:
        config[request.category].append(request.item)
        save_publications_config(config)
        return {"message": f"Added '{request.item}' to {request.category}"}
    else:
        return {"message": f"'{request.item}' already exists in {request.category}"}

@router.post("/publications/remove")
async def remove_publication_item(
    request: RemoveItemRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Remove an item from the publications configuration and delete associated files."""
    from ..services.file_watcher import JORNAIS_FOLDER, REVISTAS_FOLDER, extract_publication_name
    from ..models import Publication
    import unicodedata
    
    if request.category not in ['jornais', 'revistas', 'keywords', 'topics', 'ignored']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category. Must be: jornais, revistas, keywords, topics, or ignored"
        )
    
    config = load_publications_config()
    files_deleted = 0
    db_deleted = 0
    
    if request.category in config and request.item in config[request.category]:
        config[request.category].remove(request.item)
        
        # Delete associated files for jornais/revistas
        if request.category in ['jornais', 'revistas']:
            folder = JORNAIS_FOLDER if request.category == 'jornais' else REVISTAS_FOLDER
            norm_item = unicodedata.normalize('NFC', request.item)
            
            if os.path.exists(folder):
                for filename in os.listdir(folder):
                    if filename.lower().endswith('.pdf'):
                        pub_name = extract_publication_name(filename)
                        norm_pub_name = unicodedata.normalize('NFC', pub_name)
                        if norm_pub_name == norm_item:
                            try:
                                os.remove(os.path.join(folder, filename))
                                files_deleted += 1
                            except Exception as e:
                                logger.warning(f"Failed to delete {filename}: {e}")
            
            # Delete from database
            db_deleted = db.query(Publication).filter(
                Publication.title == norm_item
            ).delete(synchronize_session=False)
            db.commit()
            
            # Delete thumbnails
            from ..config import settings
            thumbnail_dir = settings.THUMBNAIL_DIR
            if os.path.exists(thumbnail_dir):
                for thumb_file in os.listdir(thumbnail_dir):
                    # Thumbnails are named like: timestamp_filename.jpg
                    if norm_item.replace(' ', '_') in thumb_file or request.item.replace(' ', '_') in thumb_file:
                        try:
                            os.remove(os.path.join(thumbnail_dir, thumb_file))
                            logger.info(f"🖼️ Deleted thumbnail: {thumb_file}")
                        except Exception as e:
                            logger.warning(f"Failed to delete thumbnail {thumb_file}: {e}")
        
        # If not already ignored and not a permanent delete, add to ignored list
        if not request.permanent and request.category != 'ignored':
            if 'ignored' not in config:
                config['ignored'] = []
            if request.item not in config['ignored']:
                config['ignored'].append(request.item)
                
        save_publications_config(config)
        
        msg = f"Removed '{request.item}' from {request.category}"
        if files_deleted > 0:
            msg += f", deleted {files_deleted} files"
        if db_deleted > 0:
            msg += f", removed {db_deleted} database entries"
        if not request.permanent and request.category != 'ignored':
            msg += " (moved to ignored)"
        return {"message": msg, "files_deleted": files_deleted, "db_deleted": db_deleted}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{request.item}' not found in {request.category}"
        )

@router.post("/publications/restore")
async def restore_publication_item(
    request: RestoreItemRequest,
    current_user: User = Depends(require_admin)
):
    """Restore an item from the ignored list back to an active category."""
    if request.target_category not in ['jornais', 'revistas', 'keywords', 'topics']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid target category"
        )
        
    config = load_publications_config()
    
    if 'ignored' in config and request.item in config['ignored']:
        config['ignored'].remove(request.item)
        if request.target_category not in config:
            config[request.target_category] = []
        if request.item not in config[request.target_category]:
            config[request.target_category].append(request.item)
        
        save_publications_config(config)
        return {"message": f"Restored '{request.item}' to {request.target_category}"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{request.item}' not found in ignored list"
        )

@router.post("/publications/move")
async def move_publication_category(
    request: MoveItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Move a publication from one category to another, moving files and syncing Convex."""
    from ..models import Publication
    from ..services.file_watcher import JORNAIS_FOLDER, REVISTAS_FOLDER, extract_publication_name
    from ..services.convex_service import convex_service
    import shutil
    import unicodedata
    
    valid_categories = ['jornais', 'revistas']
    if request.from_category not in valid_categories or request.to_category not in valid_categories:
        raise HTTPException(status_code=400, detail="Invalid categories")
    
    # 1. Update publications.json
    config = load_publications_config()
    if request.from_category not in config or request.item not in config[request.from_category]:
        raise HTTPException(status_code=404, detail="Item not found in source category")
    
    config[request.from_category].remove(request.item)
    if request.to_category not in config: config[request.to_category] = []
    if request.item not in config[request.to_category]: config[request.to_category].append(request.item)
    save_publications_config(config)
    
    # 2. Preparation
    category_map = {'jornais': 'newspaper', 'revistas': 'magazine'}
    folder_map = {'jornais': JORNAIS_FOLDER, 'revistas': REVISTAS_FOLDER}
    new_category = category_map[request.to_category]
    source_folder = folder_map[request.from_category]
    target_folder = folder_map[request.to_category]
    norm_item = unicodedata.normalize('NFC', request.item)
    
    # 3. Move Physical Source Files (The ones in Jornais/Revistas)
    files_moved = 0
    if os.path.exists(source_folder):
        os.makedirs(target_folder, exist_ok=True)
        for filename in os.listdir(source_folder):
            if filename.lower().endswith('.pdf'):
                pub_name = extract_publication_name(filename)
                if unicodedata.normalize('NFC', pub_name) == norm_item:
                    try:
                        shutil.move(os.path.join(source_folder, filename), os.path.join(target_folder, filename))
                        files_moved += 1
                    except Exception as e:
                        logger.warning(f"File move failed: {e}")

    # 4. Update DB Records & Sync to Convex
    # We find by both normalized and original title to be safe
    publications = db.query(Publication).filter(
        (Publication.title == norm_item) | (Publication.title == request.item)
    ).all()
    
    updated_count = 0
    for pub in publications:
        pub.category = new_category
        pub.title = norm_item # Standardize title to NFC
        
        # If the file path in DB pointed to the old category folder (not common but possible), update it
        if source_folder in pub.file_path:
            pub.file_path = pub.file_path.replace(source_folder, target_folder)
            
        try:
            convex_service.sync_publication({
                "title": pub.title,
                "filename": pub.filename,
                "original_filename": pub.original_filename,
                "thumbnail_path": pub.thumbnail_path,
                "file_path": pub.file_path,
                "page_count": pub.page_count,
                "file_size": pub.file_size,
                "category": pub.category,
                "publication_date": pub.publication_date.isoformat() if pub.publication_date else None,
                "external_id": pub.id
            })
            updated_count += 1
        except: pass
        
    db.commit()
    
    return {
        "message": f"Moved '{request.item}' to {request.to_category}",
        "files_moved": files_moved,
        "records_synced": updated_count
    }


@router.post("/publications/reorganize")
async def reorganize_all_publications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Scan all PDFs and reorganize them.
    """
    from ..models import Publication
    from ..services.file_watcher import JORNAIS_FOLDER, REVISTAS_FOLDER, OTHERS_FOLDER, extract_publication_name, scan_all_folders
    import shutil
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Start task tracking
    start_task('reorganize')
    
    try:
        # Force a full import scan first
        logger.info("Step 0: Triggering full folder import...")
        scan_all_folders(force=True)
        
        config = load_publications_config()
        ai_categorized = 0
        db_updated = 0
        import unicodedata
        
        # Pre-normalize config names for faster matching
        jornais_names = {unicodedata.normalize('NFC', name) for name in config.get('jornais', [])}
        revistas_names = {unicodedata.normalize('NFC', name) for name in config.get('revistas', [])}
        
        moved_to_jornais = 0
        moved_to_revistas = 0
        ai_categorized = 0
        db_updated = 0
        errors = []
        others_files = []
        
        # Step 0: Fix 'other' category entries in database by re-scanning names
        logger.info("🔍 Step 0: Checking database for 'other' category entries...")
        other_publications = db.query(Publication).filter(Publication.category == 'others').all()
        for pub in other_publications:
            # Use original filename to extract a better name
            better_name = extract_publication_name(pub.original_filename or pub.filename)
            norm_better_name = unicodedata.normalize('NFC', better_name)
            
            # Check if it matches any rules
            target_category = None
            if norm_better_name in jornais_names:
                target_category = 'newspaper'
            elif norm_better_name in revistas_names:
                target_category = 'magazine'
            
            if target_category:
                logger.info(f"✨ Found match for 'other' entry ID {pub.id}: '{better_name}' as {target_category}")
                pub.category = target_category
                pub.title = better_name
                db_updated += 1
                
                # If the file is still in Others, we should move it too (if not handled by later steps)
                if pub.file_path and ('Outros' in pub.file_path or 'Others' in pub.file_path) and os.path.exists(pub.file_path):
                    target_folder = JORNAIS_FOLDER if target_category == 'newspaper' else REVISTAS_FOLDER
                    os.makedirs(target_folder, exist_ok=True)
                    new_filename = os.path.basename(pub.file_path)
                    new_path = os.path.join(target_folder, new_filename)
                    try:
                        shutil.move(pub.file_path, new_path)
                        pub.file_path = new_path
                        logger.info(f"📁 Moved file to {target_category} folder: {new_filename}")
                    except Exception as e:
                        logger.error(f"Failed to move file for DB entry {pub.id}: {e}")

        # Step 1: Move misplaced files between Jornais/Revistas based on rules
        if os.path.exists(REVISTAS_FOLDER):
            for filename in os.listdir(REVISTAS_FOLDER):
                if not filename.lower().endswith('.pdf'):
                    continue
                pub_name = extract_publication_name(filename)
                norm_pub_name = unicodedata.normalize('NFC', pub_name)
                if norm_pub_name in jornais_names:
                    source = os.path.join(REVISTAS_FOLDER, filename)
                    target = os.path.join(JORNAIS_FOLDER, filename)
                    try:
                        os.makedirs(JORNAIS_FOLDER, exist_ok=True)
                        shutil.move(source, target)
                        moved_to_jornais += 1
                        logger.info(f"📁 Moved {filename} from Revistas to Jornais")
                        
                        # Update DB path
                        db.query(Publication).filter(
                            Publication.original_filename == filename
                        ).update({"file_path": target, "category": "newspaper"}, synchronize_session=False)
                    except Exception as e:
                        errors.append(f"Failed to move {filename}: {e}")
        
        if os.path.exists(JORNAIS_FOLDER):
            for filename in os.listdir(JORNAIS_FOLDER):
                if not filename.lower().endswith('.pdf'):
                    continue
                pub_name = extract_publication_name(filename)
                norm_pub_name = unicodedata.normalize('NFC', pub_name)
                if norm_pub_name in revistas_names:
                    source = os.path.join(JORNAIS_FOLDER, filename)
                    target = os.path.join(REVISTAS_FOLDER, filename)
                    try:
                        os.makedirs(REVISTAS_FOLDER, exist_ok=True)
                        shutil.move(source, target)
                        moved_to_revistas += 1
                        logger.info(f"📁 Moved {filename} from Jornais to Revistas")
                        
                        # Update DB path
                        db.query(Publication).filter(
                            Publication.original_filename == filename
                        ).update({"file_path": target, "category": "magazine"}, synchronize_session=False)
                    except Exception as e:
                        errors.append(f"Failed to move {filename}: {e}")
        
        # Step 2: Use AI to categorize files in Others folder
        if os.path.exists(OTHERS_FOLDER):
            for filename in os.listdir(OTHERS_FOLDER):
                if filename.lower().endswith('.pdf'):
                    pub_name = extract_publication_name(filename)
                    norm_pub_name = unicodedata.normalize('NFC', pub_name)
                    if norm_pub_name not in jornais_names and norm_pub_name not in revistas_names and norm_pub_name not in config.get('ignored', []):
                        others_files.append({
                            'filename': filename,
                            'pub_name': pub_name,
                            'filepath': os.path.join(OTHERS_FOLDER, filename)
                        })
        
        if others_files:
            unique_pub_names = list(set(f['pub_name'] for f in others_files))
            ai_results = {}
            
            try:
                gemini_key = settings_service.get_setting(db, "GEMINI_API_KEY")
                
                if gemini_key:
                    from google import genai
                    
                    cache_file = Path(settings.TELEGRAM_DATA_DIR) / 'ai_cache.json'
                    cache = {}
                    if cache_file.exists():
                        try:
                            with open(cache_file, 'r') as f:
                                cache = json.load(f)
                        except:
                            pass
                    
                    uncached = [name for name in unique_pub_names if name.lower() not in cache]
                    
                    for name in unique_pub_names:
                        if name.lower() in cache:
                            ai_results[name] = cache[name.lower()]
                            logger.info(f"💾 Using cached category for '{name}': {cache[name.lower()]}")
                    
                    if uncached:
                        logger.info(f"🤖 Calling AI to categorize {len(uncached)} publications in batch...")
                        
                        publications_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(uncached)])
                        
                        prompt = f"""Classify these Portuguese publications as jornal or revista:

{publications_list}

Rules:
- Jornal (newspaper): daily news, sports, regional news
- Revista (magazine): weekly/monthly, specialized topics, lifestyle

Respond ONLY with numbered list:
1. jornal
2. revista"""
                        
                        client = genai.Client(api_key=gemini_key)
                        response = client.models.generate_content(
                            model="gemini-2.0-flash-lite",
                            contents=prompt
                        )
                        
                        lines = response.text.strip().split('\n')
                        for i, line in enumerate(lines):
                            if i >= len(uncached):
                                break
                            category = line.split('.')[-1].strip().lower()
                            if category in ['jornal', 'revista']:
                                name = uncached[i]
                                ai_results[name] = category
                                cache[name.lower()] = category
                                logger.info(f"🤖 AI categorized '{name}' as: {category}")
                        
                        cache_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(cache_file, 'w') as f:
                            json.dump(cache, f, indent=2, ensure_ascii=False)
                        
                        logger.info(f"✅ AI batch categorization complete: {len(ai_results)} results")
                else:
                    logger.warning("⚠️ GEMINI_API_KEY not configured, skipping AI categorization")
                    
            except Exception as e:
                logger.error(f"Error in AI categorization: {e}")
                errors.append(f"AI error: {str(e)}")
            
            for file_info in others_files:
                pub_name = file_info['pub_name']
                if pub_name in ai_results:
                    category = ai_results[pub_name]
                    target_folder = JORNAIS_FOLDER if category == 'jornal' else REVISTAS_FOLDER
                    category_key = 'jornais' if category == 'jornal' else 'revistas'
                    db_category = 'newspaper' if category == 'jornal' else 'magazine'
                    
                    try:
                        os.makedirs(target_folder, exist_ok=True)
                        target_path = os.path.join(target_folder, file_info['filename'])
                        shutil.move(file_info['filepath'], target_path)
                        
                        if pub_name not in config.get(category_key, []):
                            if category_key not in config:
                                config[category_key] = []
                            config[category_key].append(pub_name)
                        
                        ai_categorized += 1
                        if category == 'jornal':
                            moved_to_jornais += 1
                        else:
                            moved_to_revistas += 1
                        
                        # Update DB entry if created during Others scan
                        db.query(Publication).filter(
                            Publication.original_filename == file_info['filename']
                        ).update({"file_path": target_path, "category": db_category, "title": pub_name}, synchronize_session=False)

                        logger.info(f"📁 AI moved {file_info['filename']} to {category_key.capitalize()}")
                        
                    except Exception as e:
                        errors.append(f"Failed to move {file_info['filename']}: {e}")
            
            if ai_categorized > 0:
                save_publications_config(config)
        
        # Step 3: Update database records (ensuring NFC normalization in titles)
        for name in config.get('jornais', []):
            norm_name = unicodedata.normalize('NFC', name)
            # Update by matching both original and normalized name if they differ
            count = db.query(Publication).filter(
                (Publication.title == norm_name) | (Publication.title == name),
                Publication.category != 'newspaper'
            ).update({"category": "newspaper", "title": norm_name}, synchronize_session=False)
            db_updated += count
        
        for name in config.get('revistas', []):
            norm_name = unicodedata.normalize('NFC', name)
            count = db.query(Publication).filter(
                (Publication.title == norm_name) | (Publication.title == name),
                Publication.category != 'magazine'
            ).update({"category": "magazine", "title": norm_name}, synchronize_session=False)
            db_updated += count
        
        db.commit()
        
        return {
            "message": "Reorganization complete",
            "files_moved_to_jornais": moved_to_jornais,
            "files_moved_to_revistas": moved_to_revistas,
            "ai_categorized": ai_categorized,
            "database_records_updated": db_updated,
            "others_remaining": len(others_files) - ai_categorized if others_files else 0,
            "errors": errors
        }
    finally:
        complete_task('reorganize')

@router.post("/publications/recategorize")
async def recategorize_publication(
    request: RecategorizeRequest,
    current_user: User = Depends(require_admin)
):
    """Move a file from Others to a specific category and update rules."""
    from ..services.file_watcher import (
        OTHERS_FOLDER, JORNAIS_FOLDER, REVISTAS_FOLDER, extract_publication_name
    )
    from ..models import Publication
    from ..config import settings
    import shutil
    
    source_path = os.path.join(OTHERS_FOLDER, request.filename)
    if not os.path.exists(source_path):
        raise HTTPException(status_code=404, detail="File not found in Others")
        
    # Determine target folder and category name
    db_category = 'newspaper' if request.target_category == 'jornais' else 'magazine'
    target_folder = JORNAIS_FOLDER if request.target_category == 'jornais' else REVISTAS_FOLDER
    
    # 1. Add to publications.json
    clean_name = extract_publication_name(request.filename)
    config = load_publications_config()
    
    if request.target_category not in config:
        config[request.target_category] = []
        
    if clean_name not in config[request.target_category]:
        config[request.target_category].append(clean_name)
        save_publications_config(config)
    
    # 2. Move the physical file first
    os.makedirs(target_folder, exist_ok=True)
    dest_path = os.path.join(target_folder, request.filename)
    shutil.move(source_path, dest_path)
    
    # 3. Update or create DB record
    db = SessionLocal()
    try:
        # Try to find by original_filename or filename
        pub = db.query(Publication).filter(
            (Publication.original_filename == request.filename) | 
            (Publication.filename.contains(request.filename))
        ).first()
        
        if pub:
            # Update existing record
            pub.category = db_category
            pub.file_path = dest_path
            db.commit()
            logger.info(f"Updated database record for {request.filename}")
        else:
            # Create new record - let the file watcher handle it on next scan
            logger.info(f"No database record found for {request.filename}, will be picked up on next scan")
    finally:
        db.close()
    
    # 4. Move thumbnail if exists (search for thumbnails containing the filename)
    thumbnail_dir = settings.THUMBNAIL_DIR
    if os.path.exists(thumbnail_dir):
        base_filename = request.filename.replace('.pdf', '').replace('.PDF', '')
        for thumb_file in os.listdir(thumbnail_dir):
            if base_filename in thumb_file:
                # Thumbnails don't need to be moved, they can stay where they are
                # as they're referenced by their full path in the database
                logger.info(f"Found existing thumbnail: {thumb_file}")
                break
    
    return {"message": f"Successfully moved to {request.target_category} and updated rules"}

@router.post("/publications/others/delete")
async def delete_others_publication(
    request: DeleteOthersRequest,
    current_user: User = Depends(require_admin)
):
    """Delete a file from the Others folder."""
    from ..services.file_watcher import OTHERS_FOLDER
    
    source_path = os.path.join(OTHERS_FOLDER, request.filename)
    if not os.path.exists(source_path):
        raise HTTPException(status_code=404, detail="File not found in Others")
    
    try:
        os.remove(source_path)
        return {"message": f"Successfully deleted {request.filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

@router.get("/status")
async def get_system_status(current_user: User = Depends(require_admin)):
    """Get overall system status."""
    from ..database import SessionLocal
    from ..models import Publication, User as UserModel
    from ..services.telegram_bot import get_bot_status
    
    db = SessionLocal()
    try:
        total_publications = db.query(Publication).count()
        total_users = db.query(UserModel).count()
        
        # Count by category
        categories = {}
        for cat in ['newspaper', 'magazine', 'others']:
            categories[cat] = db.query(Publication).filter(
                Publication.category == cat
            ).count()
        
        folder_stats = get_folder_stats()
        bot_status = get_bot_status()
        
        return {
            "database": {
                "total_publications": total_publications,
                "total_users": total_users,
                "by_category": categories
            },
            "folders": folder_stats,
            "telegram_bot": bot_status,
            "telegram_bot_configured": PUBLICATIONS_CONFIG.exists()
        }
    finally:
        db.close()

@router.post("/telegram/test")
async def test_telegram_config(
    config: Dict[str, Any],
    current_user: User = Depends(require_admin)
):
    """Test Telegram configuration without starting the full bot."""
    from ..services.telegram_bot import test_telegram_connection
    
    api_id = config.get("TELEGRAM_API_ID")
    api_hash = config.get("TELEGRAM_API_HASH")
    channel_id = config.get("TELEGRAM_CHANNEL_ID")
    
    if not api_id or not api_hash:
        return {"success": False, "message": "API ID and Hash are required for testing"}
        
    try:
        success, message = await test_telegram_connection(api_id, api_hash, channel_id)
        return {"success": success, "message": message}
    except Exception as e:
        return {"success": False, "message": str(e)}

@router.post("/telegram/login/request")
async def request_telegram_login(
    config: Dict[str, Any],
    current_user: User = Depends(require_admin)
):
    """Request a login code from Telegram."""
    from ..services.telegram_bot import request_login_code, get_bot_status
    
    # Ensure bot is stopped before requesting code (shared session file lock)
    status = get_bot_status()
    if status["is_running"]:
        raise HTTPException(status_code=400, detail="Please stop the Telegram bot before requesting a login code.")

    phone = config.get("phone")
    api_id = config.get("api_id")
    api_hash = config.get("api_hash")
    
    if not phone or not api_id or not api_hash:
        raise HTTPException(status_code=400, detail="Phone, API ID and API Hash are required")
        
    try:
        success, message = await request_login_code(api_id, api_hash, phone)
        if not success:
            raise HTTPException(status_code=500, detail=message)
        return {"success": True, "message": message}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/telegram/login/verify")
async def verify_telegram_login(
    config: Dict[str, Any],
    current_user: User = Depends(require_admin)
):
    """Verify the login code from Telegram."""
    from ..services.telegram_bot import submit_login_code
    
    phone = config.get("phone")
    code = config.get("code")
    password = config.get("password") # 2FA
    
    if not phone or not code:
        raise HTTPException(status_code=400, detail="Phone and code are required")
        
    try:
        success, message = await submit_login_code(phone, code, password)
        if not success:
            raise HTTPException(status_code=500, detail=message)
        return {"success": True, "message": message}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/telegram/start")
async def trigger_telegram_start(current_user: User = Depends(require_admin)):
    """Start the Telegram bot."""
    if is_bot_running():
        return {"message": "Bot is already running"}
    try:
        await start_telegram_bot()
        return {"message": "Bot started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/telegram/stop")
async def trigger_telegram_stop(current_user: User = Depends(require_admin)):
    """Stop the Telegram bot."""
    if not is_bot_running():
        return {"message": "Bot is not running"}
    try:
        await stop_telegram_bot()
        return {"message": "Bot stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/telegram/scan")
async def trigger_telegram_scan(
    limit: int = 100,
    current_user: User = Depends(require_admin)
):
    """Trigger a quick scan of the last N messages."""
    from ..services.telegram_bot import scan_channel_history
    try:
        await scan_channel_history(limit)
        return {"message": "Scan started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/telegram/scan/days")
async def trigger_telegram_scan_by_date(
    days: int = 7,
    current_user: User = Depends(require_admin)
):
    """Trigger a scan of the last N days."""
    from ..services.telegram_bot import scan_channel_history_by_date
    try:
        await scan_channel_history_by_date(days)
        return {"message": f"Scan for last {days} days started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/telegram/scan/others")
async def scan_telegram_others(current_user: User = Depends(require_admin)):
    """Trigger a scan of the Others folder to reclassify files using AI."""
    try:
        with open(SCAN_REQUEST_FILE, 'w') as f:
            json.dump({"type": "others", "timestamp": str(datetime.now())}, f)
        return {"message": "Scan request sent to bot.", "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/telegram/ai-categorize")
async def trigger_ai_categorization_manual(current_user: User = Depends(require_admin)):
    """Trigger manual AI categorization for pending files."""
    from ..services.telegram_bot import trigger_ai_categorization
    try:
        await trigger_ai_categorization()
        return {"message": "AI categorization request sent to bot.", "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

@router.post("/scan/corrupt")
async def scan_and_remove_corrupt_files(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin)
):
    """
    Start a background task to scan and remove corrupt files.
    """
    if is_task_running('scan_corrupt'):
        return {"message": "Scan already in progress"}

    background_tasks.add_task(run_corrupt_file_scan)
    return {"message": "Corrupt file scan started in background"}

def run_corrupt_file_scan():
    """
    The actual heavy lifting function for scanning files.
    """
    from pdf2image import convert_from_path
    from ..services.file_watcher import JORNAIS_FOLDER, REVISTAS_FOLDER, OTHERS_FOLDER
    
    start_task('scan_corrupt')
    logger = logging.getLogger(__name__)
    deleted_count = 0
    errors = []
    
    try:
        logger.info("🔍 Starting background corrupt file scan...")
        folders = [JORNAIS_FOLDER, REVISTAS_FOLDER, OTHERS_FOLDER, settings.UPLOAD_DIR]
        
        for folder in folders:
            if not os.path.exists(folder):
                continue
                
            for filename in os.listdir(folder):
                if not filename.lower().endswith('.pdf'):
                    continue
                    
                filepath = os.path.join(folder, filename)
                is_corrupt = False
                reason = ""
                
                # 1. Check size
                try:
                    if os.path.getsize(filepath) < 1024:
                        is_corrupt = True
                        reason = "Too small (<1KB)"
                except OSError:
                    continue

                # 2. Check PDF validity by attempting to render first page
                if not is_corrupt:
                    try:
                        convert_from_path(filepath, first_page=1, last_page=1)
                    except Exception as e:
                        is_corrupt = True
                        reason = f"Render Failed: {str(e)[:50]}..."
                
                if is_corrupt:
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                        logger.warning(f"🗑️ Deleted corrupt file ({reason}): {filename}")
                    except Exception as e:
                        errors.append(f"Failed to delete {filename}: {e}")
        
        logger.info(f"✅ Corrupt file scan completed. Deleted: {deleted_count}")
        
    except Exception as e:
        logger.error(f"Error during corrupt file scan: {e}")
    finally:
        complete_task('scan_corrupt')

@router.post("/telegram/cleanup")
async def trigger_telegram_cleanup(current_user: User = Depends(require_admin)):
    """Trigger a cleanup of duplicate and old files."""
    try:
        with open(SCAN_REQUEST_FILE, 'w') as f:
            json.dump({"type": "cleanup", "timestamp": str(datetime.now())}, f)
        return {"message": "Cleanup requested"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users")
async def get_users(current_user: User = Depends(require_admin)):
    """List all users."""
    from ..models import User as UserModel
    from ..schemas.schemas import UserResponse
    db = SessionLocal()
    try:
        users = db.query(UserModel).all()
        return [UserResponse.model_validate(u) for u in users]
    finally:
        db.close()

class UserCreateRequest(BaseModel):
    username: str
    email: str
    password: str
    is_admin: bool = False

@router.post("/users")
async def create_new_user(
    user_data: UserCreateRequest,
    current_user: User = Depends(require_admin)
):
    """Create a new user."""
    from ..models import User as UserModel
    from ..services import get_password_hash
    from ..schemas.schemas import UserResponse
    
    db = SessionLocal()
    try:
        existing = db.query(UserModel).filter(UserModel.username == user_data.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
            
        new_user = UserModel(
            username=user_data.username,
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            is_admin=user_data.is_admin
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return UserResponse.model_validate(new_user)
    finally:
        db.close()

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin)
):
    """Delete a user."""
    from ..models import User as UserModel
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
        
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        db.delete(user)
        db.commit()
        return {"message": "User deleted"}
    finally:
        db.close()

@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: Dict[str, Any],
    current_user: User = Depends(require_admin)
):
    """Update a user."""
    from ..models import User as UserModel
    from ..services import get_password_hash
    from ..schemas.schemas import UserResponse
    
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        if 'is_admin' in user_data and user_id != current_user.id:
            user.is_admin = user_data['is_admin']
            
        if 'password' in user_data and user_data['password']:
            user.hashed_password = get_password_hash(user_data['password'])
            
        if 'email' in user_data:
            user.email = user_data['email']
            
        db.commit()
        db.refresh(user)
        return UserResponse.model_validate(user)
    finally:
        db.close()

@router.get("/logs")
async def get_logs(
    type: str = "app", 
    lines: int = 500,
    current_user: User = Depends(get_current_active_user)
):
    """Get the latest log entries."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    log_file = settings.LOGS_DIR / f"{type}.log"
    
    if not log_file.exists():
        return {"logs": f"Log file {type}.log not found."}
        
    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.readlines()
            return {
                "logs": "".join(content[-lines:]),
                "type": type,
                "total_lines": len(content)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")

@router.get("/settings")
async def get_system_settings(
    category: str = None,
    current_user: User = Depends(require_admin)
):
    """Get all system settings or settings by category."""
    db = SessionLocal()
    try:
        if category:
            return settings_service.get_settings_by_category(db, category)
        return settings_service.get_all_settings(db)
    finally:
        db.close()

@router.post("/settings")
async def update_system_settings(
    request: SystemSettingsRequest,
    current_user: User = Depends(require_admin)
):
    """Update system settings."""
    db = SessionLocal()
    try:
        updated = []
        for key, value in request.settings.items():
            category = "general"
            if key.startswith("TELEGRAM_"):
                category = "telegram"
            elif key.startswith("GEMINI_"):
                category = "ai"
            
            settings_service.set_setting(db, key, str(value), category=category)
            updated.append(key)
        
        telegram_updated = any(k.startswith("TELEGRAM_") for k in updated)
        if telegram_updated:
            try:
                if is_bot_running():
                    await stop_telegram_bot()
                    await start_telegram_bot()
            except Exception as e:
                print(f"Error restarting bot: {e}")

        return {"message": f"Updated settings: {', '.join(updated)}", "updated": updated}
    finally:
        db.close()

@router.post("/telegram/sync-convex")
async def sync_convex_manual(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Wipe Convex and re-upload all local database records.
    Fixes shifted IDs and thumbnail mismatches.
    """
    from ..models import Publication
    from ..services.convex_service import convex_service
    from ..services.pdf_service import generate_thumbnail
    import logging
    
    logger = logging.getLogger(__name__)
    start_task('sync_convex')
    
    try:
        # 1. Wipe Convex
        logger.warning("Wiping Convex for manual sync...")
        try:
            convex_service.clear_all()
        except Exception as e:
            logger.error(f"Wipe failed (might be empty): {e}")
        
        # 2. Fetch all local records
        publications = db.query(Publication).all()
        logger.info(f"Uploading {len(publications)} records to Convex...")
        
        count = 0
        for pub in publications:
            try:
                # INTEGRITY CHECK: Ensure thumbnail exists, if not, try to regenerate
                if not pub.thumbnail_path or not os.path.exists(pub.thumbnail_path):
                    if pub.file_path and os.path.exists(pub.file_path):
                        logger.info(f"🖼️ Regenerating thumbnail for {pub.title}")
                        new_thumb, pages = generate_thumbnail(pub.file_path, pub.filename.rsplit('.', 1)[0])
                        if new_thumb:
                            pub.thumbnail_path = new_thumb
                            if pages > 0: pub.page_count = pages
                            db.commit()

                convex_service.sync_publication({
                    "title": pub.title,
                    "filename": pub.filename,
                    "original_filename": pub.original_filename,
                    "thumbnail_path": pub.thumbnail_path,
                    "file_path": pub.file_path,
                    "page_count": pub.page_count,
                    "file_size": pub.file_size,
                    "category": pub.category,
                    "publication_date": pub.publication_date.isoformat() if pub.publication_date else None,
                    "external_id": pub.id
                })
                count += 1
            except Exception as e:
                logger.error(f"Failed to sync record {pub.id}: {e}")
        
        return {
            "message": "Convex sync complete",
            "records_synced": count
        }
    finally:
        complete_task('sync_convex')

@router.post("/reset")
async def reset_system(
    days: int = 7,
    delete_downloads: bool = False,
    current_user: User = Depends(require_admin)
):
    """
    NUCLEAR OPTION: Reset the system state.
    """
    import shutil
    import traceback
    from ..models import Publication, ReadingProgress
    from ..services.file_watcher import scan_all_folders
    from ..services.telegram_bot import stop_telegram_bot, start_telegram_bot, is_bot_running
    from ..services.convex_service import convex_service
    
    logger = logging.getLogger(__name__)
    logger.warning(f"☢️ SYSTEM RESET INITIATED by {current_user.username}")
    
    try:
        # 1. Stop Bot to release file locks
        if is_bot_running():
            logger.info("Stopping Telegram bot...")
            try:
                await stop_telegram_bot()
            except Exception as e:
                logger.error(f"Error stopping bot (continuing): {e}")

        # 1.5 Wipe Convex Data (Cloud)
        logger.info("Wiping Convex data...")
        try:
            convex_service.clear_all()
        except Exception as e:
            logger.error(f"Error wiping Convex: {e}")

        # 2. Wipe Database Tables
        logger.info("Wiping database tables...")
        db = SessionLocal()
        try:
            db.query(ReadingProgress).delete()
            db.query(Publication).delete()
            db.commit()
            logger.info("✅ Database tables wiped")
        except Exception as e:
            logger.error(f"Error wiping database: {e}")
            db.rollback()
        finally:
            db.close()

        # 3. Clear Generated Files (Uploads/Thumbnails)
        logger.info("Clearing generated files...")
        for folder in [settings.UPLOAD_DIR, settings.THUMBNAIL_DIR]:
            if folder.exists():
                try:
                    for item in folder.iterdir():
                        try:
                            if item.is_file() or item.is_symlink():
                                item.unlink()
                            elif item.is_dir():
                                shutil.rmtree(item)
                        except Exception as e:
                            logger.warning(f"Failed to delete {item}: {e}")
                    logger.info(f"✅ Cleared {folder}")
                except Exception as e:
                    logger.error(f"Error accessing folder {folder}: {e}")

        # 4. Optional: Delete Downloaded Files
        if delete_downloads:
            logger.info("Deleting downloaded files...")
            for folder_name in ['Jornais', 'Revistas', 'Others']:
                folder_path = Path(settings.TELEGRAM_DATA_DIR) / folder_name
                if folder_path.exists():
                    try:
                        for item in folder_path.iterdir():
                            try:
                                if item.is_file() or item.is_symlink():
                                    item.unlink()
                                elif item.is_dir():
                                    shutil.rmtree(item)
                            except Exception as e:
                                logger.warning(f"Failed to delete {item}: {e}")
                        logger.info(f"✅ Cleared {folder_name}")
                    except Exception as e:
                        logger.error(f"Error accessing {folder_name}: {e}")

        # 5. Reset Bot Memory
        logger.info("Resetting bot memory...")
        processed_log = Path(settings.TELEGRAM_DATA_DIR) / 'processed_files.json'
        try:
            if processed_log.exists():
                with open(processed_log, 'w') as f:
                    json.dump({}, f)
                logger.info("✅ Reset processed_files.json")
        except Exception as e:
            logger.error(f"Error resetting log file: {e}")

        # 6. Re-scan Local Folders
        logger.info("Re-scanning local folders...")
        try:
            scan_all_folders()
            logger.info("✅ Local scan complete")
        except Exception as e:
            logger.error(f"Error scanning folders: {e}")

        # 7. Trigger Telegram History Scan
        logger.info(f"Triggering Telegram scan for {days} days...")
        try:
            with open(SCAN_REQUEST_FILE, 'w') as f:
                json.dump({
                    "type": "keywords", 
                    "days": days,
                    "timestamp": str(datetime.now())
                }, f)
            logger.info("✅ Scan request queued")
            
            # Restart Bot
            await start_telegram_bot()
            logger.info("✅ Bot restarted")
            
        except Exception as e:
            logger.error(f"Error restarting bot: {e}")

        return {
            "message": "System reset complete. Rescan in progress.",
            "details": f"Database wiped, history reset, scanning last {days} days."
        }

    except Exception as e:
        logger.critical(f"🔥 CRITICAL ERROR DURING RESET: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")
