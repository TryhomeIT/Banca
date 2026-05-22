import os
import tempfile
import zipfile
import logging
from pathlib import Path
from PIL import Image
import rarfile
from natsort import natsorted

logger = logging.getLogger(__name__)

# Configure rarfile to use the system unar command
rarfile.UNRAR_TOOL = "unar"

def is_comic_archive(filename: str) -> bool:
    """Check if the filename has a supported comic archive extension."""
    ext = filename.lower()
    return ext.endswith('.cbz') or ext.endswith('.cbr') or ext.endswith('.zip') or ext.endswith('.rar')

def extract_archive(archive_path: str, extract_to: str) -> bool:
    """Extract a ZIP/CBZ or RAR/CBR archive to the target directory."""
    ext = archive_path.lower()
    try:
        if ext.endswith('.cbz') or ext.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            return True
        elif ext.endswith('.cbr') or ext.endswith('.rar'):
            with rarfile.RarFile(archive_path, 'r') as rar_ref:
                rar_ref.extractall(extract_to)
            return True
    except Exception as e:
        logger.error(f"Error extracting archive {archive_path}: {e}")
        return False
    return False

def convert_comic_to_pdf(source_path: str, dest_pdf_path: str) -> bool:
    """
    Extracts images from a CBZ or CBR and compiles them sequentially into a PDF.
    Returns True if successful, False otherwise.
    """
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Extracting {source_path} for PDF conversion...")
            if not extract_archive(source_path, temp_dir):
                logger.error(f"Failed to extract {source_path}")
                return False

            # Find all image files in the extracted directory (including subdirectories)
            valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}
            image_paths = []
            
            for root, _, files in os.walk(temp_dir):
                for f in files:
                    if Path(f).suffix.lower() in valid_extensions:
                        # Skip macOS hidden files
                        if not f.startswith('._') and not f == '.DS_Store':
                            image_paths.append(os.path.join(root, f))
            
            if not image_paths:
                logger.error(f"No valid images found in archive {source_path}")
                return False

            # Sort the images naturally (e.g., page 2 comes before page 10)
            image_paths = natsorted(image_paths)
            
            logger.info(f"Found {len(image_paths)} images. Compiling PDF...")
            
            import img2pdf
            
            # Prepare images. img2pdf cannot handle images with alpha channel.
            processed_paths = []
            for p in image_paths:
                try:
                    if p.lower().endswith(('.png', '.webp', '.gif')):
                        with Image.open(p) as img:
                            if img.mode in ('RGBA', 'LA', 'P'):
                                temp_path = p + '.jpg'
                                img.convert('RGB').save(temp_path, 'JPEG', quality=90)
                                processed_paths.append(temp_path)
                            else:
                                processed_paths.append(p)
                    else:
                        processed_paths.append(p)
                except Exception as e:
                    logger.warning(f"Failed to process image {p}: {e}")

            if not processed_paths:
                logger.error(f"Failed to load any images from {source_path}")
                return False
                
            # Convert to PDF in one fast, memoryless step
            with open(dest_pdf_path, "wb") as f:
                f.write(img2pdf.convert(processed_paths))
            
            logger.info(f"Successfully converted {source_path} to {dest_pdf_path}")
            return True
            
    except Exception as e:
        logger.error(f"Error converting comic to PDF {source_path}: {e}")
        return False
