import os
import logging
from typing import List, Optional
from datetime import datetime, date, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, case

from ..database import get_db
from ..models import User, Publication, ReadingProgress, UserFavorite
from ..schemas import (
    PublicationResponse,
    PublicationWithProgress,
    ReadingProgressUpdate,
    ReadingProgressResponse
)
from ..services import (
    get_current_active_user,
    generate_thumbnail,
    save_uploaded_file,
    delete_publication_files,
    enforce_retention_policies,
)
from ..config import settings

import unicodedata

logger = logging.getLogger(__name__)

def build_publication_response_dict(publication: Publication) -> dict:
    pub_dict = PublicationResponse.model_validate(publication).model_dump()
    if not pub_dict.get("publication_date"):
        pub_dict["publication_date"] = publication.created_at
    return pub_dict

def check_path_exists_unicode(path_str: str) -> Optional[str]:
    """
    Check if path exists, trying different unicode normalizations.
    Returns the actual existing path or None.
    """
    if not path_str:
        return None
        
    path = Path(path_str)
    if path.exists():
        return str(path)
        
    # Try normalization on the filename part
    directory = path.parent
    filename = path.name
    
    # Common normalizations
    forms = ['NFC', 'NFD', 'NFKC', 'NFKD']
    
    for form in forms:
        normalized_name = unicodedata.normalize(form, filename)
        candidate = directory / normalized_name
        if candidate.exists():
            return str(candidate)
            
    return None

router = APIRouter(prefix="/api/publications", tags=["Publications"])

@router.get("/", response_model=List[PublicationWithProgress])
async def get_publications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
    category: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all publications with reading progress for current user. Favorites from today appear first."""
    enforce_retention_policies(db)
    query = db.query(Publication)
    
    if category:
        query = query.filter(Publication.category == category)
    
    if search:
        query = query.filter(Publication.title.ilike(f"%{search}%"))
    
    # Get the latest publication date for EACH title in the database
    # This ensures we know if a pub is the "latest" version of that magazine/newspaper
    latest_dates_query = db.query(
        Publication.title, 
        func.max(Publication.publication_date).label("max_date")
    ).group_by(Publication.title).all()
    latest_dates = {row.title: row.max_date for row in latest_dates_query}

    # Get user's favorite titles
    user_favorites = db.query(UserFavorite.publication_title).filter(
        UserFavorite.user_id == current_user.id
    ).all()
    favorite_titles = {f[0] for f in user_favorites}
    
    # Get all publications matching filters
    publications = query.order_by(
        desc(Publication.publication_date)
    ).all()
    
    # Sort: 
    # 1. Latest issue of a Favorite title -> Top
    # 2. Everything else -> By Date
    def sort_key(pub):
        is_favorite = pub.title in favorite_titles
        is_latest = pub.publication_date == latest_dates.get(pub.title)
        
        # Priority 0: Favorite + Latest
        # Priority 1: Everything else
        priority = 0 if (is_favorite and is_latest) else 1
        
        # Sort by: Priority (0 first), then Date (newest first)
        date_sort = -(pub.publication_date.timestamp() if pub.publication_date else 0)
        
        return (priority, date_sort)
    
    publications_sorted = sorted(publications, key=sort_key)
    
    # Apply pagination manually after sorting
    paginated_pubs = publications_sorted[skip : skip + limit]
    
    # Get reading progress for each publication
    result = []
    for pub in paginated_pubs:
        progress = db.query(ReadingProgress).filter(
            ReadingProgress.user_id == current_user.id,
            ReadingProgress.publication_id == pub.id
        ).first()
        
        pub_dict = build_publication_response_dict(pub)
        pub_dict["current_page"] = progress.current_page if progress else 1
        pub_dict["last_read_at"] = progress.last_read_at if progress else None
        pub_dict["is_favorite"] = pub.title in favorite_titles
        result.append(PublicationWithProgress(**pub_dict))
    
    return result


@router.get("/recent", response_model=List[PublicationWithProgress])
async def get_recent_publications(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get recently read publications for current user."""
    enforce_retention_policies(db)
    progress_list = db.query(ReadingProgress).filter(
        ReadingProgress.user_id == current_user.id
    ).order_by(desc(ReadingProgress.last_read_at)).limit(limit).all()
    
    # Get user's favorite titles
    user_favorites = db.query(UserFavorite.publication_title).filter(
        UserFavorite.user_id == current_user.id
    ).all()
    favorite_titles = {f[0] for f in user_favorites}
    
    result = []
    for progress in progress_list:
        pub = progress.publication
        pub_dict = build_publication_response_dict(pub)
        pub_dict["current_page"] = progress.current_page
        pub_dict["last_read_at"] = progress.last_read_at
        pub_dict["is_favorite"] = pub.title in favorite_titles
        result.append(PublicationWithProgress(**pub_dict))
    
    return result

@router.get("/categories")
async def get_categories(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all unique categories."""
    enforce_retention_policies(db)
    categories = db.query(Publication.category).distinct().filter(
        Publication.category.isnot(None)
    ).all()
    return [cat[0] for cat in categories if cat[0]]

@router.get("/{publication_id}", response_model=PublicationWithProgress)
async def get_publication(
    publication_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a single publication with reading progress."""
    enforce_retention_policies(db)
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")
    
    progress = db.query(ReadingProgress).filter(
        ReadingProgress.user_id == current_user.id,
        ReadingProgress.publication_id == publication_id
    ).first()

    is_favorite = db.query(UserFavorite).filter(
        UserFavorite.user_id == current_user.id,
        UserFavorite.publication_title == publication.title
    ).first() is not None
    
    pub_dict = build_publication_response_dict(publication)
    pub_dict["current_page"] = progress.current_page if progress else 1
    pub_dict["last_read_at"] = progress.last_read_at if progress else None
    pub_dict["is_favorite"] = is_favorite
    
    return PublicationWithProgress(**pub_dict)

@router.post("/", response_model=PublicationResponse)
async def upload_publication(
    file: UploadFile = File(...),
    title: str = Form(...),
    category: Optional[str] = Form(None),
    publication_date: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a new publication."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Save file
    file_content = await file.read()
    filename, file_path = save_uploaded_file(file_content, file.filename)
    
    # Generate thumbnail and get page count
    thumbnail_path, page_count = generate_thumbnail(file_path, filename.rsplit('.', 1)[0])
    
    # Parse publication date if provided
    pub_date = None
    if publication_date:
        try:
            pub_date = datetime.fromisoformat(publication_date)
        except ValueError:
            pass
    if pub_date is None:
        pub_date = datetime.utcnow()
    
    # Create publication record
    publication = Publication(
        title=title,
        filename=filename,
        original_filename=file.filename,
        thumbnail_path=thumbnail_path,
        file_path=file_path,
        page_count=page_count,
        file_size=len(file_content),
        category=category,
        publication_date=pub_date
    )
    
    db.add(publication)
    db.commit()
    db.refresh(publication)
    


    return publication

@router.delete("/{publication_id}")
async def delete_publication(
    publication_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a publication (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete publications"
        )
    
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")
    
    # Delete files
    delete_publication_files(publication.filename, publication.thumbnail_path)
    
    # Delete reading progress
    db.query(ReadingProgress).filter(ReadingProgress.publication_id == publication_id).delete()
    
    # Delete publication
    db.delete(publication)
    db.commit()
    
    return {"message": "Publication deleted successfully"}

@router.get("/{publication_id}/pdf")
async def get_publication_pdf(
    publication_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get the PDF file for a publication."""
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")
    
    # Try to find the file with unicode handling
    file_path = check_path_exists_unicode(publication.file_path)
    
    if not file_path:
        unique_name = publication.file_path.replace('\\', '/').split('/')[-1]
        orig_name = publication.original_filename
        logger.warning(f"🚨 File not found at primary path: {publication.file_path}. Searching for {unique_name}...")
        
        # Build exhaustive list of possible paths
        search_paths = []
        # 1. Check in uploads (using unique name)
        search_paths.append(str(settings.UPLOAD_DIR / unique_name))
        
        # 2. Check in Telegram folders (try both capitalized and lower, and both unique/orig names)
        data_dir = Path(settings.TELEGRAM_DATA_DIR)
        for folder in ["Jornais", "jornais", "Revistas", "revistas", "Outros", "outros", "data"]:
            folder_path = data_dir / folder
            search_paths.append(str(folder_path / unique_name))
            if orig_name:
                search_paths.append(str(folder_path / orig_name))
        
        found = False
        for alt in search_paths:
            resolved_alt = check_path_exists_unicode(alt)
            if resolved_alt:
                logger.info(f"✨ Found PDF at alternate path: {resolved_alt}")
                file_path = resolved_alt
                found = True
                break
        
        if not found:
            logger.error(f"❌ PDF not found after searching {len(search_paths)} locations")
            logger.error(f"   Checked: {[str(p) for p in search_paths]}")
            raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=publication.original_filename
    )

@router.get("/{publication_id}/thumbnail")
async def get_publication_thumbnail(
    publication_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get the thumbnail for a publication."""
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")
    
    # Check primary path with unicode support
    thumb_path = check_path_exists_unicode(publication.thumbnail_path)
    
    if not thumb_path:
        # Try to resolve based on filename if absolute path is wrong (common when moving from local to docker)
        resolved_thumb = None
        if publication.filename:
            # Extract name without extension
            base_name = publication.filename.rsplit('.', 1)[0]
            alt_path = settings.THUMBNAIL_DIR / f"{base_name}.jpg"
            resolved_thumb = check_path_exists_unicode(str(alt_path))
            
            if not resolved_thumb and publication.thumbnail_path:
                # Last resort: try checking the filename itself in thumbnails (handle both / and \ separators)
                filename_only = publication.thumbnail_path.replace('\\', '/').split('/')[-1]
                fallback_path = settings.THUMBNAIL_DIR / filename_only
                resolved_thumb = check_path_exists_unicode(str(fallback_path))
        
        if resolved_thumb:
            thumb_path = resolved_thumb
        else:
            # If still not found, try to GENERATE it on-the-fly if we have the PDF
            # Use the robust PDF finder logic again (copy-paste logic, or rely on get_publication_pdf logic but internal)
            # Simplified: Use primary path or check uploads/telegram
            file_path = check_path_exists_unicode(publication.file_path)
            
            if not file_path:
                unique_name = publication.file_path.replace('\\', '/').split('/')[-1]
                orig_name = publication.original_filename
                
                search_paths = [str(settings.UPLOAD_DIR / unique_name)]
                data_dir = Path(settings.TELEGRAM_DATA_DIR)
                for folder in ["Jornais", "jornais", "Revistas", "revistas", "Outros", "outros", "data"]:
                    fp = data_dir / folder
                    search_paths.append(str(fp / unique_name))
                    if orig_name:
                        search_paths.append(str(fp / orig_name))
                
                for alt in search_paths:
                    resolved = check_path_exists_unicode(alt)
                    if resolved:
                        file_path = resolved
                        break
            
            if file_path:
                try:
                    # We have the PDF, try to generate thumbnail
                    new_thumb, page_count = generate_thumbnail(
                        file_path, 
                        (publication.filename or "thumb").rsplit('.', 1)[0]
                    )
                    if new_thumb:
                        publication.thumbnail_path = new_thumb
                        if page_count > 0:
                            publication.page_count = page_count
                        db.commit()
                        thumb_path = new_thumb
                except Exception as e:
                    logger.error(f"Failed to generate on-the-fly thumbnail: {e}")
            
            # If still nothing, 404
            if not thumb_path or not os.path.exists(thumb_path):
                logger.error(f"❌ Thumbnail not found for ID {publication_id}")
                logger.error(f"   Primary path: {publication.thumbnail_path}")
                logger.error(f"   Search attempts failed in: {[str(p) for p in search_paths] if 'search_paths' in locals() else 'Standard paths'}")
                raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    return FileResponse(thumb_path, media_type="image/jpeg")

@router.put("/{publication_id}/progress", response_model=ReadingProgressResponse)
async def update_reading_progress(
    publication_id: int,
    progress: ReadingProgressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update reading progress for a publication."""
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")
    
    # Validate page number
    if progress.current_page < 1 or progress.current_page > publication.page_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page number must be between 1 and {publication.page_count}"
        )
    
    # Get or create reading progress
    reading_progress = db.query(ReadingProgress).filter(
        ReadingProgress.user_id == current_user.id,
        ReadingProgress.publication_id == publication_id
    ).first()
    
    if reading_progress:
        reading_progress.current_page = progress.current_page
        reading_progress.last_read_at = datetime.utcnow()
    else:
        reading_progress = ReadingProgress(
            user_id=current_user.id,
            publication_id=publication_id,
            current_page=progress.current_page
        )
        db.add(reading_progress)
    
    db.commit()
    db.refresh(reading_progress)
    
    return reading_progress
@router.delete("/{publication_id}/progress")
async def delete_reading_progress(
    publication_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete reading progress for a publication (remove from Continue Reading)."""
    db.query(ReadingProgress).filter(
        ReadingProgress.user_id == current_user.id,
        ReadingProgress.publication_id == publication_id
    ).delete()
    db.commit()
    return {"message": "Reading progress removed"}


# ========================================
# FAVORITES ENDPOINTS
# ========================================

@router.get("/favorites/titles")
async def get_unique_publication_titles(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get unique publication titles for the favorites management page.
    Returns each unique title with its most recent publication's thumbnail.
    """
    # Build base query for publications
    query = db.query(Publication)
    
    if category:
        query = query.filter(Publication.category == category)
    else:
        # Exclude 'others' category by default
        query = query.filter(Publication.category.in_(['newspaper', 'magazine']))
    
    # Get all publications ordered by date (newest first)
    publications = query.order_by(desc(Publication.publication_date)).all()
    
    # Get user's favorites
    user_favorites = db.query(UserFavorite.publication_title).filter(
        UserFavorite.user_id == current_user.id
    ).all()
    favorite_titles = {f[0] for f in user_favorites}
    
    # Group by title, keeping only the most recent for each
    seen_titles = {}
    for pub in publications:
        if pub.title not in seen_titles:
            seen_titles[pub.title] = {
                "title": pub.title,
                "category": pub.category,
                "thumbnail_id": pub.id,  # Use the most recent publication's ID for thumbnail
                "is_favorite": pub.title in favorite_titles
            }
    
    # Sort: favorites first, then alphabetically
    result = list(seen_titles.values())
    result.sort(key=lambda x: (not x["is_favorite"], x["title"].lower()))
    
    return result


@router.get("/favorites/list")
async def get_user_favorites(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get the current user's favorite publication titles."""
    favorites = db.query(UserFavorite).filter(
        UserFavorite.user_id == current_user.id
    ).all()
    return [f.publication_title for f in favorites]


@router.post("/favorites/{title:path}")
async def add_favorite(
    title: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a publication title to user's favorites."""
    # Check if already exists
    existing = db.query(UserFavorite).filter(
        UserFavorite.user_id == current_user.id,
        UserFavorite.publication_title == title
    ).first()
    
    if existing:
        return {"message": "Already a favorite", "title": title}
    
    favorite = UserFavorite(user_id=current_user.id, publication_title=title)
    db.add(favorite)
    db.commit()
    
    return {"message": "Added to favorites", "title": title}


@router.delete("/favorites/{title:path}")
async def remove_favorite(
    title: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove a publication title from user's favorites."""
    db.query(UserFavorite).filter(
        UserFavorite.user_id == current_user.id,
        UserFavorite.publication_title == title
    ).delete()
    db.commit()
    
    return {"message": "Removed from favorites", "title": title}
