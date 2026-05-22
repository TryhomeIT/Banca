import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from pdf2image import convert_from_path, pdfinfo_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError
from PIL import Image

from ..config import settings

def generate_thumbnail(pdf_path: str, output_filename: str) -> Tuple[Optional[str], int]:
    """
    Generate a thumbnail from the first page of a PDF.
    Returns tuple of (thumbnail_path, page_count).
    """
    try:
        # Convert first page to image
        images = convert_from_path(
            pdf_path,
            first_page=1,
            last_page=1,
            dpi=150,
            fmt='jpeg'
        )
        
        if not images:
            return None, 0
        
        # Get page count using pdfinfo instead of extracting all pages
        info = pdfinfo_from_path(pdf_path)
        page_count = info.get("Pages", 1)
        
        # Process thumbnail
        thumbnail = images[0]
        
        # Resize to reasonable thumbnail size while maintaining aspect ratio
        max_size = (400, 566)  # Roughly A4 proportions
        thumbnail.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save thumbnail
        thumb_filename = f"{output_filename}.jpg"
        thumbnail_path = settings.THUMBNAIL_DIR / thumb_filename
        thumbnail.save(str(thumbnail_path), "JPEG", quality=85)
        
        # Store relative to THUMBNAIL_DIR or use absolute path but handle in router
        return str(thumbnail_path), page_count
        
    except (PDFInfoNotInstalledError, PDFPageCountError) as e:
        print(f"PDF processing error: {e}")
        return None, 0
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return None, 0

def get_page_count(pdf_path: str) -> int:
    """Get the number of pages in a PDF."""
    try:
        info = pdfinfo_from_path(pdf_path)
        return info.get("Pages", 0)
    except Exception:
        return 0

def save_uploaded_file(file_content: bytes, original_filename: str) -> Tuple[str, str]:
    """
    Save uploaded file to uploads directory.
    Returns tuple of (saved_filename, file_path).
    """
    # Generate unique filename
    file_ext = Path(original_filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = settings.UPLOAD_DIR / unique_filename
    
    # Write file
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    return unique_filename, str(file_path)

def delete_publication_files(filename: str, thumbnail_path: Optional[str] = None):
    """Delete publication file and its thumbnail."""
    try:
        # Delete PDF
        pdf_path = settings.UPLOAD_DIR / filename
        if pdf_path.exists():
            pdf_path.unlink()
        
        # Delete thumbnail
        if thumbnail_path and Path(thumbnail_path).exists():
            Path(thumbnail_path).unlink()
    except Exception as e:
        print(f"Error deleting files: {e}")
