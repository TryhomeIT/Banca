"""
Admin API endpoints for managing the Telegram bot integration and system settings.
"""

import os
import json
import logging
import shutil
import traceback
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..models import User, Publication, ReadingProgress
from ..services import (
    get_current_active_user, 
    scan_all_folders, 
    get_folder_stats,
    start_telegram_bot,
    stop_telegram_bot,
    is_bot_running,
    get_password_hash
)
from ..config import settings
from ..services.settings import settings_service
from ..services.convex_service import convex_service
from ..services.pdf_service import generate_thumbnail
from ..database import SessionLocal, get_db
from ..schemas.schemas import UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])

# Constants
PUBLICATIONS_CONFIG = Path(settings.TELEGRAM_DATA_DIR) / 'publications.json'
SCAN_REQUEST_FILE = Path(settings.TELEGRAM_DATA_DIR) / 'scan_request.json'
RUNNING_TASKS_FILE = Path(settings.TELEGRAM_DATA_DIR) / 'running_tasks.json'

# --- Pydantic Models ---

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
    category: str
    item: str

class RemoveItemRequest(BaseModel):
    category: str
    item: str
    permanent: bool = False

class MoveItemRequest(BaseModel):
    item: str
    from_category: str
    to_category: str

class RestoreItemRequest(BaseModel):
    item: str
    target_category: str

class RecategorizeRequest(BaseModel):
    filename: str
    target_category: str

class DeleteOthersRequest(BaseModel):
    filename: str

class SystemSettingsRequest(BaseModel):
    settings: Dict[str, Any]

class UserCreateRequest(BaseModel):
    username: str
    email: str
    password: str
    is_admin: bool = False

class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    is_admin: Optional[bool] = None

# --- Helper Functions ---

def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

def load_publications_config() -> Dict[str, Any]:
    defaults = {"jornais": [], "revistas": [], "keywords": [], "topics": [], "ignored": []}
    try:
        if PUBLICATIONS_CONFIG.exists():
            with open(PUBLICATIONS_CONFIG, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for k, v in defaults.items():
                    if k not in data:
                        data[k] = v
                return data
    except: pass
    return defaults

def save_publications_config(config: Dict[str, Any]):
    def normalize_list(l):
        if not l: return []
        return sorted(list(set(unicodedata.normalize('NFC', str(x)) for x in l)))
    
    for key in ['jornais', 'revistas', 'keywords', 'topics', 'ignored']:
        if key in config: config[key] = normalize_list(config[key])
    
    PUBLICATIONS_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with open(PUBLICATIONS_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def load_running_tasks() -> Dict[str, Any]:
    try:
        if RUNNING_TASKS_FILE.exists():
            with open(RUNNING_TASKS_FILE, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
                now = datetime.now().timestamp()
                return {k: v for k, v in tasks.items() if now - v.get('started_at', 0) < 1800}
    except: pass
    return {}

def save_running_tasks(tasks: Dict[str, Any]):
    try:
        RUNNING_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(RUNNING_TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, indent=2)
    except: pass

def start_task(task_name: str):
    tasks = load_running_tasks()
    tasks[task_name] = {'started_at': datetime.now().timestamp(), 'status': 'running'}
    save_running_tasks(tasks)

def complete_task(task_name: str):
    tasks = load_running_tasks()
    if task_name in tasks:
        del tasks[task_name]
        save_running_tasks(tasks)

def is_task_running(task_name: str) -> bool:
    return task_name in load_running_tasks()

# --- Endpoints ---

@router.get("/tasks/status")
async def get_running_tasks(current_user: User = Depends(require_admin)):
    return {"running_tasks": load_running_tasks()}

@router.post("/scan", response_model=ScanResponse)
async def trigger_folder_scan(force: bool = Query(False), current_user: User = Depends(require_admin)):
    results = scan_all_folders(force=force)
    return ScanResponse(
        jornais=results['jornais'], revistas=results['revistas'], others=results['others'],
        total=sum(results.values())
    )

@router.get("/folders", response_model=FolderStatsResponse)
async def get_folders_statistics(current_user: User = Depends(require_admin)):
    stats = get_folder_stats()
    return FolderStatsResponse(
        jornais=FolderStats(**stats['jornais']),
        revistas=FolderStats(**stats['revistas']),
        others=FolderStats(**stats['others'])
    )

@router.get("/publications/config", response_model=PublicationsConfig)
async def get_publications_configuration(current_user: User = Depends(require_admin)):
    config = load_publications_config()
    from ..services.file_watcher import OTHERS_FOLDER, extract_publication_name
    others_files = []
    if os.path.exists(OTHERS_FOLDER):
        for filename in os.listdir(OTHERS_FOLDER):
            if filename.lower().endswith('.pdf'):
                path = os.path.join(OTHERS_FOLDER, filename)
                stat = os.stat(path)
                others_files.append(OthersFile(
                    filename=filename, size=stat.st_size,
                    modified=str(datetime.fromtimestamp(stat.st_mtime)),
                    extracted_name=extract_publication_name(filename)
                ))
    return PublicationsConfig(**config, others=others_files)

@router.post("/publications/add")
async def add_publication_item(request: AddItemRequest, current_user: User = Depends(require_admin)):
    config = load_publications_config()
    if request.category not in config: config[request.category] = []
    if request.item not in config[request.category]:
        config[request.category].append(request.item)
        if request.category != 'ignored' and request.item in config.get('ignored', []):
            config['ignored'].remove(request.item)
        save_publications_config(config)
    return {"message": "Success"}

@router.post("/publications/remove")
async def remove_publication_item(request: RemoveItemRequest, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    config = load_publications_config()
    if request.category in config and request.item in config[request.category]:
        config[request.category].remove(request.item)
        if not request.permanent and request.category != 'ignored':
            if request.item not in config['ignored']: config['ignored'].append(request.item)
        save_publications_config(config)
    return {"message": "Success"}

@router.post("/publications/move")
async def move_publication_category(request: MoveItemRequest, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    from ..services.file_watcher import JORNAIS_FOLDER, REVISTAS_FOLDER, extract_publication_name
    config = load_publications_config()
    if request.from_category in config and request.item in config[request.from_category]:
        config[request.from_category].remove(request.item)
        if request.to_category not in config: config[request.to_category] = []
        config[request.to_category].append(request.item)
        save_publications_config(config)
        
        new_cat = 'newspaper' if request.to_category == 'jornais' else 'magazine'
        target_dir = JORNAIS_FOLDER if new_cat == 'newspaper' else REVISTAS_FOLDER
        source_dir = REVISTAS_FOLDER if new_cat == 'newspaper' else JORNAIS_FOLDER
        
        # Move files & sync
        norm_item = unicodedata.normalize('NFC', request.item)
        pubs = db.query(Publication).filter((Publication.title == norm_item) | (Publication.title == request.item)).all()
        for pub in pubs:
            pub.category = new_cat
            if source_dir in pub.file_path:
                new_path = pub.file_path.replace(source_dir, target_dir)
                if os.path.exists(pub.file_path):
                    os.makedirs(target_dir, exist_ok=True)
                    shutil.move(pub.file_path, new_path)
                    pub.file_path = new_path
            convex_service.sync_publication({
                "title": pub.title, "filename": pub.filename, "original_filename": pub.original_filename,
                "thumbnail_path": pub.thumbnail_path, "file_path": pub.file_path, "page_count": pub.page_count,
                "file_size": pub.file_size, "category": pub.category, 
                "publication_date": pub.publication_date.isoformat() if pub.publication_date else None,
                "external_id": pub.id
            })
        db.commit()
    return {"message": "Success"}

@router.post("/publications/restore")
async def restore_publication_item(request: RestoreItemRequest, current_user: User = Depends(require_admin)):
    config = load_publications_config()
    if request.item in config.get('ignored', []):
        config['ignored'].remove(request.item)
    if request.target_category not in config: config[request.target_category] = []
    if request.item not in config[request.target_category]:
        config[request.target_category].append(request.item)
    save_publications_config(config)
    return {"message": "Restored"}

@router.post("/publications/recategorize")
async def recategorize_file(request: RecategorizeRequest, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    from ..services.file_watcher import import_pdf_to_database, OTHERS_FOLDER, extract_publication_name
    
    # 1. Add keyword to config
    config = load_publications_config()
    clean_name = extract_publication_name(request.filename)
    if request.target_category not in config: config[request.target_category] = []
    
    # Avoid duplicates
    if clean_name not in config[request.target_category]:
        config[request.target_category].append(clean_name)
        save_publications_config(config)
    
    # 2. Re-import file
    file_path = os.path.join(OTHERS_FOLDER, request.filename)
    if os.path.exists(file_path):
        new_cat_name = 'newspaper' if request.target_category == 'jornais' else 'magazine'
        import_pdf_to_database(file_path, new_cat_name)
        return {"message": "Recategorized"}
    
    raise HTTPException(status_code=404, detail="File not found")

@router.post("/publications/others/delete")
async def delete_others_file(request: DeleteOthersRequest, current_user: User = Depends(require_admin)):
    from ..services.file_watcher import OTHERS_FOLDER
    file_path = os.path.join(OTHERS_FOLDER, request.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": "Deleted"}
    raise HTTPException(status_code=404, detail="File not found")

@router.post("/publications/reorganize")
async def reorganize_all_publications(current_user: User = Depends(require_admin)):
    start_task('reorganize')
    try:
        from ..services.file_watcher import scan_all_folders
        scan_all_folders(force=True)
    finally:
        complete_task('reorganize')
    return {"message": "Success"}

@router.get("/status")
async def get_system_status(current_user: User = Depends(require_admin)):
    from ..services.telegram_bot import get_bot_status
    db = SessionLocal()
    try:
        return {
            "database": {
                "total_publications": db.query(Publication).count(),
                "total_users": db.query(User).count(),
                "by_category": {cat: db.query(Publication).filter(Publication.category == cat).count() for cat in ['newspaper', 'magazine', 'others']}
            },
            "folders": get_folder_stats(),
            "telegram_bot": get_bot_status(),
            "telegram_bot_configured": PUBLICATIONS_CONFIG.exists()
        }
    finally: db.close()

@router.post("/telegram/login/request")
async def request_telegram_login(config: Dict[str, Any], current_user: User = Depends(require_admin)):
    from ..services.telegram_bot import request_login_code, get_bot_status
    if get_bot_status()["is_running"]: raise HTTPException(status_code=400, detail="Stop bot first")
    success, msg = await request_login_code(config.get("api_id"), config.get("api_hash"), config.get("phone"))
    if not success: raise HTTPException(status_code=500, detail=msg)
    return {"message": msg}

@router.post("/telegram/login/verify")
async def verify_telegram_login(config: Dict[str, Any], current_user: User = Depends(require_admin)):
    from ..services.telegram_bot import submit_login_code
    success, msg = await submit_login_code(config.get("phone"), config.get("code"), config.get("password"))
    if not success: raise HTTPException(status_code=500, detail=msg)
    return {"message": msg}

@router.post("/telegram/start")
async def trigger_telegram_start(current_user: User = Depends(require_admin)):
    await start_telegram_bot()
    return {"message": "Started"}

@router.post("/telegram/stop")
async def trigger_telegram_stop(current_user: User = Depends(require_admin)):
    await stop_telegram_bot()
    return {"message": "Stopped"}

@router.post("/telegram/scan/days")
async def trigger_telegram_scan_by_date(days: int = 7, current_user: User = Depends(require_admin)):
    from ..services.telegram_bot import scan_channel_history_by_date
    await scan_channel_history_by_date(days)
    return {"message": "Queued"}

@router.post("/telegram/ai-categorize")
async def trigger_ai_categorization_endpoint(current_user: User = Depends(require_admin)):
    from ..services.telegram_bot import trigger_ai_categorization
    await trigger_ai_categorization()
    return {"message": "AI Categorization Queued"}

@router.post("/telegram/scan/outros")
async def trigger_outros_scan(current_user: User = Depends(require_admin)):
    from ..services.telegram_bot import trigger_ai_categorization
    # Re-using AI categorize logic as it scans 'Others' folder
    await trigger_ai_categorization()
    return {"message": "Outros Scan Queued"}

@router.post("/telegram/cleanup")
async def cleanup_telegram_files(current_user: User = Depends(require_admin)):
    """
    Full cleanup: Delete ALL records, files, and re-download from last 7 days.
    """
    start_task('cleanup')
    try:
        logger.info("🧹 Starting full cleanup...")
        
        # 1. Stop the bot first
        if is_bot_running(): 
            logger.info("Stopping bot...")
            await stop_telegram_bot()
        
        # 2. Clear processed files history
        processed_file = Path(settings.TELEGRAM_DATA_DIR) / 'processed_files.json'
        with open(processed_file, 'w') as f: json.dump({}, f)
        logger.info("✅ Cleared processed files history")
            
        # 3. Delete all downloaded files
        for cat in ['Jornais', 'Revistas', 'Others', 'downloads']:
            p = Path(settings.TELEGRAM_DATA_DIR) / cat
            if p.exists():
                for item in p.iterdir():
                    if item.is_file(): item.unlink()
                    elif item.is_dir(): shutil.rmtree(item)
        logger.info("✅ Deleted all downloaded files")
        
        # 4. Clear database records
        db = SessionLocal()
        try:
            db.query(ReadingProgress).delete()
            db.query(Publication).delete()
            db.commit()
            logger.info("✅ Cleared all database records")
        finally:
            db.close()
        
        # 5. Clear uploads and thumbnails
        for folder in [settings.UPLOAD_DIR, settings.THUMBNAIL_DIR]:
            if folder.exists():
                for item in folder.iterdir():
                    if item.is_file(): item.unlink()
                    elif item.is_dir(): shutil.rmtree(item)
        logger.info("✅ Cleared uploads and thumbnails")
        
        # 6. Clear file watcher in-memory cache and Convex cloud data
        logger.info("♻️ Clearing file watcher cache...")
        from ..services.file_watcher import scan_all_folders
        scan_all_folders(force=True)
        
        try:
            convex_service.clear_all()
            logger.info("✅ Cleared Convex cloud data")
        except Exception as e:
            logger.warning(f"Convex clear skipped: {e}")
        
        # 7. Start bot & Trigger 7-day scan
        await start_telegram_bot()
        
        # Write scan request for 7 days
        with open(SCAN_REQUEST_FILE, 'w') as f:
            json.dump({"type": "keywords", "days": 7, "timestamp": str(datetime.now())}, f)
        logger.info("✅ Started bot and queued 7-day scan")
            
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        complete_task('cleanup')
        
    return {"message": "Cleanup complete. All records and files removed. 7-day re-scan started."}

@router.post("/telegram/sync-convex")
async def sync_convex_manual(wipe: bool = Query(False), db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    start_task('sync_convex')
    try:
        if wipe: convex_service.clear_all()
        pubs = db.query(Publication).all()
        for pub in pubs:
            if not pub.thumbnail_path or not os.path.exists(pub.thumbnail_path):
                if pub.file_path and os.path.exists(pub.file_path):
                    thumb, pages = generate_thumbnail(pub.file_path, pub.filename.rsplit('.', 1)[0])
                    if thumb: 
                        pub.thumbnail_path = thumb
                        if pages > 0: pub.page_count = pages
                        db.commit()
            convex_service.sync_publication({
                "title": pub.title, "filename": pub.filename, "original_filename": pub.original_filename,
                "thumbnail_path": pub.thumbnail_path, "file_path": pub.file_path, "page_count": pub.page_count,
                "file_size": pub.file_size, "category": pub.category,
                "publication_date": pub.publication_date.isoformat() if pub.publication_date else None,
                "external_id": pub.id
            })
    finally: complete_task('sync_convex')
    return {"message": "Success"}

@router.post("/scan/corrupt")
async def scan_and_remove_corrupt_files(background_tasks: BackgroundTasks, current_user: User = Depends(require_admin)):
    if is_task_running('scan_corrupt'): return {"message": "Already running"}
    background_tasks.add_task(run_corrupt_file_scan)
    return {"message": "Started"}

def run_corrupt_file_scan():
    from ..services.file_watcher import JORNAIS_FOLDER, REVISTAS_FOLDER, OTHERS_FOLDER
    start_task('scan_corrupt')
    try:
        for folder in [JORNAIS_FOLDER, REVISTAS_FOLDER, OTHERS_FOLDER, settings.UPLOAD_DIR]:
            if not os.path.exists(folder): continue
            for filename in os.listdir(folder):
                if not filename.lower().endswith('.pdf'): continue
                path = os.path.join(folder, filename)
                try:
                    if os.path.getsize(path) < 1024: os.remove(path)
                    else: convert_from_path(path, first_page=1, last_page=1)
                except:
                    try: os.remove(path)
                    except: pass
    finally: complete_task('scan_corrupt')

@router.get("/users")
async def get_users(current_user: User = Depends(require_admin)):
    db = SessionLocal()
    try: return [UserResponse.model_validate(u) for u in db.query(User).all()]
    finally: db.close()

@router.post("/users")
async def create_new_user(data: UserCreateRequest, current_user: User = Depends(require_admin)):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == data.username).first(): raise HTTPException(status_code=400, detail="Exists")
        new_user = User(username=data.username, email=data.email, hashed_password=get_password_hash(data.password), is_admin=data.is_admin)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return UserResponse.model_validate(new_user)
    finally: db.close()

@router.put("/users/{user_id}")
async def update_user(user_id: int, data: UserUpdateRequest, current_user: User = Depends(require_admin)):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: raise HTTPException(status_code=404, detail="User not found")
        if data.email is not None: user.email = data.email
        if data.is_admin is not None and user_id != current_user.id: user.is_admin = data.is_admin
        if data.password: user.hashed_password = get_password_hash(data.password)
        db.commit()
        return {"message": "User updated"}
    finally: db.close()

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user: User = Depends(require_admin)):
    if user_id == current_user.id: raise HTTPException(status_code=400, detail="Self")
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user_id).first()
        if u: db.delete(u); db.commit()
        return {"message": "Deleted"}
    finally: db.close()

from fastapi.responses import FileResponse

@router.get("/logs/download")
async def download_logs(type: str = "telegram_bot", current_user: User = Depends(require_admin)):
    log_file = settings.LOGS_DIR / f"{type}.log"
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{type}_{timestamp}.log"
    
    return FileResponse(
        path=log_file, 
        filename=filename, 
        media_type='text/plain'
    )

@router.get("/logs")
async def get_logs(type: str = "app", lines: int = 500, current_user: User = Depends(require_admin)):
    log_file = settings.LOGS_DIR / f"{type}.log"
    if not log_file.exists(): return {"logs": "Not found"}
    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.readlines()
            return {"logs": "".join(content[-lines:]), "type": type}
    except: raise HTTPException(status_code=500, detail="Error")

@router.get("/settings")
async def get_system_settings(category: str = None, current_user: User = Depends(require_admin)):
    db = SessionLocal()
    try: return settings_service.get_settings_by_category(db, category) if category else settings_service.get_all_settings(db)
    finally: db.close()

@router.post("/settings")
async def update_system_settings(request: SystemSettingsRequest, current_user: User = Depends(require_admin)):
    db = SessionLocal()
    try:
        updated = []
        for k, v in request.settings.items():
            cat = "telegram" if k.startswith("TELEGRAM_") else "ai" if k.startswith("GEMINI_") else "general"
            settings_service.set_setting(db, k, str(v), category=cat)
            updated.append(k)
        if any(k.startswith("TELEGRAM_") for k in updated) and is_bot_running():
            await stop_telegram_bot(); await start_telegram_bot()
        return {"message": "Updated", "updated": updated}
    finally: db.close()

@router.post("/reset")
async def reset_system(days: int = 7, delete_downloads: bool = False, current_user: User = Depends(require_admin)):
    try:
        if is_bot_running(): await stop_telegram_bot()
        convex_service.clear_all()
        db = SessionLocal()
        try:
            db.query(ReadingProgress).delete()
            db.query(Publication).delete()
            db.commit()
        finally: db.close()
        for f in [settings.UPLOAD_DIR, settings.THUMBNAIL_DIR]:
            if f.exists():
                for item in f.iterdir():
                    if item.is_file(): item.unlink()
                    elif item.is_dir(): shutil.rmtree(item)
        if delete_downloads:
            for cat in ['Jornais', 'Revistas', 'Others']:
                p = Path(settings.TELEGRAM_DATA_DIR) / cat
                if p.exists():
                    for item in p.iterdir():
                        if item.is_file(): item.unlink()
                        elif item.is_dir(): shutil.rmtree(item)
        with open(Path(settings.TELEGRAM_DATA_DIR) / 'processed_files.json', 'w') as f: json.dump({}, f)
        scan_all_folders()
        with open(SCAN_REQUEST_FILE, 'w') as f: json.dump({"type": "keywords", "days": days, "timestamp": str(datetime.now())}, f)
        await start_telegram_bot()
        return {"message": "Reset complete"}
    except Exception as e:
        logger.critical(f"Reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))