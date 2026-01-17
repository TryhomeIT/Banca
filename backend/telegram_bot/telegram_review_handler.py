"""
Telegram-based file review handler for managing "Others" files.
Handles sending files to Telegram for user review and processing responses.
Uses Gemini AI to automatically categorize publications.
"""

import asyncio
import os
import re
import json
import shutil
import logging
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from google import genai
from komga_integration import schedule_komga_scan

logger = logging.getLogger(__name__)

# Configuration
# Use the same destination as the file uploads (Jornais Tugas group)
# This will be resolved from dialogs at runtime
REVIEW_CHAT_NAME = "Jornais Tugas"  # Used to find the chat in dialogs
REVIEW_CHAT = None  # Will be set at runtime after resolving from dialogs
DATA_FOLDER = os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), 'app', 'data'))
PENDING_REVIEWS_FILE = os.path.join(DATA_FOLDER, 'pending_reviews.json')
OTHERS_FOLDER = os.path.join(DATA_FOLDER, 'Others')
PUBLICATIONS_FILE = os.path.join(DATA_FOLDER, 'publications.json')

# AI Queue for hourly batch processing (max 1 API call per hour)
AI_QUEUE_FILE = os.path.join(DATA_FOLDER, 'ai_queue.json')

# Rate limiting kept for fallback, but now we use hourly batching
AI_RATE_LIMIT = 10  # requests per minute (kept for compatibility)
AI_REQUEST_INTERVAL = 60.0 / AI_RATE_LIMIT  # 6 seconds between requests
last_ai_request_time = 0

# Cache for AI categorization results to avoid duplicate calls
categorization_cache = {}
CACHE_FILE = os.path.join(DATA_FOLDER, 'ai_cache.json')

def load_ai_cache():
    """Load AI categorization cache from file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading AI cache: {e}")
    return {}

def save_ai_cache(cache):
    """Save AI categorization cache to file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving AI cache: {e}")

# Load cache on startup
categorization_cache = load_ai_cache()

# AI Queue management for hourly batch processing
def load_ai_queue():
    """Load pending AI categorization queue from file"""
    try:
        os.makedirs(os.path.dirname(AI_QUEUE_FILE), exist_ok=True)
        if os.path.exists(AI_QUEUE_FILE):
            with open(AI_QUEUE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading AI queue: {e}")
    return {"pending": []}

def save_ai_queue(queue):
    """Save AI categorization queue to file"""
    try:
        os.makedirs(os.path.dirname(AI_QUEUE_FILE), exist_ok=True)
        with open(AI_QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving AI queue: {e}")

def add_to_ai_queue(publication_name, filepath, filename):
    """Add a publication to the AI categorization queue for hourly processing"""
    queue = load_ai_queue()
    
    # Check if already in queue
    for item in queue["pending"]:
        if item["filepath"] == filepath:
            logger.debug(f"📋 Already in AI queue: {publication_name}")
            return
    
    queue["pending"].append({
        "publication_name": publication_name,
        "filepath": filepath,
        "filename": filename,
        "added_at": datetime.now().isoformat()
    })
    save_ai_queue(queue)
    logger.debug(f"📋 Added to AI queue: {publication_name} (queue size: {len(queue['pending'])})")

# Initialize Gemini AI
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini AI initialized successfully")
else:
    gemini_client = None
    logger.warning("⚠️ GEMINI_API_KEY not found. AI categorization will be disabled.")

def set_review_chat(chat_id):
    """Set the REVIEW_CHAT global variable at runtime"""
    global REVIEW_CHAT
    REVIEW_CHAT = chat_id
    logger.info(f"✅ REVIEW_CHAT set to: {chat_id}")

def load_pending_reviews():
    """Load pending file reviews from JSON"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(PENDING_REVIEWS_FILE), exist_ok=True)
        
        if os.path.exists(PENDING_REVIEWS_FILE):
            with open(PENDING_REVIEWS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading pending reviews: {e}")
    return {}

def save_pending_reviews(reviews):
    """Save pending file reviews to JSON"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(PENDING_REVIEWS_FILE), exist_ok=True)
        
        with open(PENDING_REVIEWS_FILE, 'w', encoding='utf-8') as f:
            json.dump(reviews, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving pending reviews: {e}")

def extract_publication_name(filename: str) -> str:
    """
    Extract clean publication name from filename using improved regex patterns.
    """
    import re
    import unicodedata
    
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
    
    return name.strip()

def add_pending_review(filepath, message_id):
    """Add a file to pending reviews"""
    try:
        reviews = load_pending_reviews()
        filename = os.path.basename(filepath)
        publication_name = extract_publication_name(filename)
        
        reviews[str(message_id)] = {
            'filepath': str(filepath),
            'filename': filename,
            'publication_name': publication_name,
            'message_id': message_id,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'pending'
        }
        
        save_pending_reviews(reviews)
        logger.info(f"📝 Added to pending reviews: {filename} (Message ID: {message_id})")
        return True
    except Exception as e:
        logger.error(f"Error adding pending review: {e}")
        return False

def remove_pending_review(message_id):
    """Remove a file from pending reviews"""
    try:
        reviews = load_pending_reviews()
        if str(message_id) in reviews:
            del reviews[str(message_id)]
            save_pending_reviews(reviews)
            return True
    except Exception as e:
        logger.error(f"Error removing pending review: {e}")
    return False

def get_pending_review(message_id):
    """Get pending review by message ID"""
    try:
        reviews = load_pending_reviews()
        return reviews.get(str(message_id))
    except Exception as e:
        logger.error(f"Error getting pending review: {e}")
    return None

def move_file_to_category(filepath, category):
    """Move file from Others to the appropriate category folder"""
    try:
        category_folder = Path(DATA_FOLDER) / category
        category_folder.mkdir(parents=True, exist_ok=True)
        
        destination = category_folder / Path(filepath).name
        
        if destination.exists():
            logger.warning(f"⚠️ File already exists in {category}: {destination.name}")
            # Still move, but log the overwrite
            os.remove(destination)
        
        shutil.move(str(filepath), str(destination))
        logger.info(f"📁 Moved file to {category}/{Path(filepath).name}")
        # Trigger Komga library scan (debounced)
        schedule_komga_scan(category.lower())
        return True
    except Exception as e:
        logger.error(f"Error moving file: {e}")
        return False

def load_publications_config():
    """Load publications configuration from JSON file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(PUBLICATIONS_FILE), exist_ok=True)
        
        if os.path.exists(PUBLICATIONS_FILE):
            with open(PUBLICATIONS_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Ensure all expected keys exist
                if "topics" not in config:
                    config["topics"] = []
                if "keywords" not in config:
                    config["keywords"] = []
                if "jornais" not in config:
                    config["jornais"] = []
                if "revistas" not in config:
                    config["revistas"] = []
                return config
    except Exception as e:
        logger.error(f"Error loading publications.json: {e}")
    return {"jornais": [], "revistas": [], "keywords": [], "topics": []}

def save_publications_config(config):
    """Save publications configuration to JSON file"""
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(PUBLICATIONS_FILE), exist_ok=True)
        
        # Remove duplicates and sort alphabetically
        if "jornais" in config:
            config["jornais"] = sorted(list(set(config["jornais"])))
        if "revistas" in config:
            config["revistas"] = sorted(list(set(config["revistas"])))
        if "keywords" in config:
            # Keep keywords lowercase and unique
            config["keywords"] = sorted(list(set([k.lower() for k in config["keywords"]])))
        if "topics" in config:
            # Keep topics lowercase and unique
            config["topics"] = sorted(list(set([unicodedata.normalize('NFC', t.lower()) for t in config["topics"]])))
        
        # Normalize all strings in jornais and revistas
        if "jornais" in config:
            config["jornais"] = sorted(list(set([unicodedata.normalize('NFC', n) for n in config["jornais"]])))
        if "revistas" in config:
            config["revistas"] = sorted(list(set([unicodedata.normalize('NFC', n) for n in config["revistas"]])))
        
        with open(PUBLICATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info("✅ Saved publications.json")
        return True
    except Exception as e:
        logger.error(f"Error saving publications.json: {e}")
        return False

def add_keyword(keyword, config):
    """Add keyword to the config"""
    if "keywords" not in config:
        config["keywords"] = []
    
    keyword_lower = keyword.lower()
    
    if keyword_lower in [k.lower() for k in config["keywords"]]:
        logger.info(f"ℹ️ Keyword '{keyword}' already exists")
        return False
    
    config["keywords"].append(keyword_lower)
    config["keywords"] = sorted(config["keywords"])
    logger.info(f"✅ Added keyword '{keyword_lower}'")
    return True

def remove_keyword(keyword, config):
    """Remove keyword from the config"""
    if "keywords" not in config:
        config["keywords"] = []
        return False
    
    keyword_lower = keyword.lower()
    original_count = len(config["keywords"])
    
    # Remove the keyword (case-insensitive)
    config["keywords"] = [k for k in config["keywords"] if k.lower() != keyword_lower]
    
    removed = len(config["keywords"]) < original_count
    if removed:
        logger.info(f"✅ Removed keyword '{keyword_lower}'")
    else:
        logger.info(f"ℹ️ Keyword '{keyword}' not found")
    
    return removed

def get_keywords(config):
    """Get list of all keywords"""
    return config.get("keywords", [])

def add_topic(topic, config):
    """Add topic to the config"""
    if "topics" not in config:
        config["topics"] = []
    
    topic_lower = topic.lower()
    
    if topic_lower in config["topics"]:
        logger.info(f"ℹ️ Topic '{topic_lower}' already exists")
        return False
    
    config["topics"].append(topic_lower)
    config["topics"] = sorted(config["topics"])
    logger.info(f"✅ Added topic '{topic_lower}'")
    return True

def remove_topic(topic, config):
    """Remove topic from the config"""
    if "topics" not in config:
        config["topics"] = []
        return False
    
    topic_lower = topic.lower()
    original_count = len(config["topics"])
    
    config["topics"] = [t for t in config["topics"] if t.lower() != topic_lower]
    
    removed = len(config["topics"]) < original_count
    if removed:
        logger.info(f"✅ Removed topic '{topic_lower}'")
    else:
        logger.info(f"ℹ️ Topic '{topic}' not found")
    
    return removed

def get_topics(config):
    """Get list of all topics"""
    return config.get("topics", [])

async def categorize_with_ai(publication_name):
    """Use Gemini AI to categorize a publication as jornal or revista"""
    global last_ai_request_time, categorization_cache
    
    if not gemini_client:
        logger.warning("Gemini AI not available, skipping AI categorization")
        return None
    
    # Check cache first
    cache_key = unicodedata.normalize('NFC', publication_name.lower())
    if cache_key in categorization_cache:
        cached_result = categorization_cache[cache_key]
        logger.info(f"💾 Using cached categorization for '{publication_name}': {cached_result}")
        return cached_result
    
    # Rate limiting: wait if needed to respect 10 requests/minute
    current_time = time.time()
    time_since_last_request = current_time - last_ai_request_time
    
    if time_since_last_request < AI_REQUEST_INTERVAL:
        wait_time = AI_REQUEST_INTERVAL - time_since_last_request
        logger.info(f"⏱️ Rate limiting: waiting {wait_time:.1f}s before AI request")
        await asyncio.sleep(wait_time)
    
    try:
        # Shorter, more efficient prompt
        prompt = f"""Classify this Portuguese publication:

"{publication_name}"

Jornal (newspaper): daily news, contains "Jornal", "Diário", "Notícias"
Revista (magazine): periodic, contains "Revista", "Magazine", specialized topics

Respond ONLY: jornal OR revista"""
        
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt
        )
        last_ai_request_time = time.time()  # Update last request time
        category = response.text.strip().lower()
        
        if category in ['jornal', 'revista']:
            logger.info(f"🤖 AI categorized '{publication_name}' as: {category}")
            # Cache the result
            categorization_cache[cache_key] = category
            save_ai_cache(categorization_cache)
            return category
        else:
            logger.warning(f"⚠️ AI returned unexpected category: {category}")
            return None
            
    except Exception as e:
        logger.error(f"Error using AI to categorize: {e}")
        return None

async def batch_categorize_with_ai(publication_names):
    """Batch categorize multiple publications in ONE AI call to save RPM"""
    global last_ai_request_time, categorization_cache
    
    if not gemini_client or not publication_names:
        return {}
    
    # Filter out already cached items
    uncached_names = [name for name in publication_names if name.lower() not in categorization_cache]
    
    if not uncached_names:
        # All cached, return from cache
        return {name: categorization_cache[name.lower()] for name in publication_names}
    
    results = {}
    
    # Return cached results first
    for name in publication_names:
        cache_key = unicodedata.normalize('NFC', name.lower())
        if cache_key in categorization_cache:
            results[name] = categorization_cache[cache_key]
    
    # Safety: Use a larger batch size for single-call processing
    MAX_BATCH_SIZE = 200
    if len(uncached_names) > MAX_BATCH_SIZE:
        logger.info(f"⚠️ Very large batch detected ({len(uncached_names)} items), processing in chunks of {MAX_BATCH_SIZE}...")
        for i in range(0, len(uncached_names), MAX_BATCH_SIZE):
            chunk = uncached_names[i:i + MAX_BATCH_SIZE]
            chunk_results = await batch_categorize_with_ai(chunk)
            results.update(chunk_results)
        return results
    
    # Rate limiting
    current_time = time.time()
    time_since_last_request = current_time - last_ai_request_time
    
    if time_since_last_request < AI_REQUEST_INTERVAL:
        wait_time = AI_REQUEST_INTERVAL - time_since_last_request
        logger.info(f"⏱️ Rate limiting: waiting {wait_time:.1f}s before batch AI request")
        await asyncio.sleep(wait_time)
    
    try:
        # Create batch prompt - all publications in ONE request
        publications_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(uncached_names)])
        
        prompt = f"""Classify these Portuguese publications as 'jornal' or 'revista':

{publications_list}

Rules:
- Jornal: daily news, contains "Jornal", "Diário", "Notícias"
- Revista: periodic, contains "Revista", "Magazine", specialized

Respond ONLY with the numbered list. No preamble, no explanation.
Format:
1. jornal
2. revista
..."""
        
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt
        )
        last_ai_request_time = time.time()
        
        raw_text = response.text.strip()
        logger.debug(f"🤖 Raw AI response:\n{raw_text}")
        
        # Parse response using regex to handle bolding (e.g., **jornal**) or varying prefixes
        import re
        
        # Strategy 1: Look for numbered lines (preferred)
        # Matches "1. jornal" or "1: **jornal**" or just "1. Revista"
        numbered_pattern = re.compile(r'(\d+)[\.:\s]+([^\n]+)', re.IGNORECASE)
        numbered_matches = numbered_pattern.findall(raw_text)
        
        indexed_results = {}
        for idx_str, content in numbered_matches:
            try:
                idx = int(idx_str) - 1 # 0-indexed
                cat_match = re.search(r'\b(jornal|revista)\b', content.lower())
                if cat_match:
                    indexed_results[idx] = cat_match.group(1)
            except:
                continue
        
        # Strategy 2: Fallback to line-by-line if numbered list fails
        lines = [line.lower() for line in raw_text.split('\n') if re.search(r'\b(jornal|revista)\b', line.lower())]
        
        for i, name in enumerate(uncached_names):
            category = None
            
            # Use indexed result if available
            if i in indexed_results:
                category = indexed_results[i]
            # Fallback to line index if we have enough lines with categories
            elif i < len(lines):
                match = re.search(r'\b(jornal|revista)\b', lines[i])
                if match:
                    category = match.group(1)
            
            if category:
                results[name] = category
                # Cache it
                categorization_cache[name.lower()] = category
            else:
                logger.warning(f"⚠️ Could not parse category for '{name}' from AI response")
        
        # Save updated cache
        save_ai_cache(categorization_cache)
        logger.info(f"🤖 Batch categorized {len(results)}/{len(uncached_names)} publications in one request")
        
    except Exception as e:
        logger.error(f"Error in batch AI categorization: {e}")
    
    return results

async def process_ai_queue(client=None):
    """Process all queued publications in a single batch API call (runs hourly)"""
    global categorization_cache
    
    queue = load_ai_queue()
    pending = queue.get("pending", [])
    
    if not pending:
        logger.info("📋 AI queue is empty, nothing to process")
        return 0
    
    logger.info(f"⏰ Processing AI queue: {len(pending)} items")
    
    # Get unique publication names (some might be duplicates)
    pub_names = list(set(item["publication_name"] for item in pending))
    
    # Filter out already cached ones
    uncached = [name for name in pub_names if name.lower() not in categorization_cache]
    
    if uncached:
        # Make single batch API call for all uncached items
        try:
            logger.info(f"🤖 Making single batch AI request for {len(uncached)} publications")
            results = await batch_categorize_with_ai(uncached)
            logger.info(f"🤖 Batch AI categorization complete: {len(results)} results")
        except Exception as e:
            logger.error(f"Error in batch AI call: {e}")
            results = {}
    else:
        results = {}
        logger.info("💾 All publications found in cache")
    
    # Combine cached and new results
    all_results = {}
    for name in pub_names:
        if name.lower() in categorization_cache:
            all_results[name] = categorization_cache[name.lower()]
        elif name in results:
            all_results[name] = results[name]
    
    # Process each item in the queue
    processed = 0
    config = load_publications_config()
    
    for item in pending:
        pub_name = item["publication_name"]
        filepath = item["filepath"]
        filename = item["filename"]
        
        if pub_name not in all_results:
            logger.warning(f"⚠️ No category for {pub_name}, keeping in Outros")
            continue
        
        category = all_results[pub_name]
        folder_name = "Jornais" if category == "jornal" else "Revistas"
        target_folder = os.path.join(DATA_FOLDER, folder_name)
        os.makedirs(target_folder, exist_ok=True)
        
        # Move file if it exists
        if os.path.exists(filepath):
            target_path = os.path.join(target_folder, os.path.basename(filepath))
            try:
                shutil.move(filepath, target_path)
                logger.info(f"📁 Moved {pub_name} to {folder_name}/")
                # Trigger Komga library scan (debounced)
                schedule_komga_scan(folder_name.lower())
                
                # Add to publications config
                category_key = "jornais" if category == "jornal" else "revistas"
                if pub_name not in config.get(category_key, []):
                    if category_key not in config:
                        config[category_key] = []
                    config[category_key].append(pub_name)
                    config[category_key].sort()
                
                processed += 1
            except Exception as e:
                logger.error(f"Error moving file: {e}")
        else:
            logger.warning(f"⚠️ File not found: {filepath}")
            processed += 1  # Count as processed to remove from queue
    
    # Save updated config
    save_publications_config(config)
    
    # Clear the queue
    queue["pending"] = []
    save_ai_queue(queue)
    
    logger.info(f"✅ Processed {processed} items from AI queue")
    
    # Send notification if client available
    if client and REVIEW_CHAT and processed > 0:
        try:
            await client.send_message(
                REVIEW_CHAT,
                f"⏰ **Hourly AI Batch Complete**\n\n"
                f"Processed {processed} publication(s) from queue."
            )
        except Exception as e:
            logger.warning(f"Could not send queue notification: {e}")
    
    return processed

def add_to_category(publication_name, category, config):
    """Add publication to a category in the config"""
    if category not in config:
        config[category] = []
    
    if publication_name in config[category]:
        logger.info(f"ℹ️ '{publication_name}' already exists in {category}")
        return False
    
    config[category].append(unicodedata.normalize('NFC', publication_name))
    config[category] = sorted(list(set(config[category])))
    logger.info(f"✅ Added '{publication_name}' to {category}")
    return True

async def send_file_for_review(client, filepath):
    """Send file to user for review with AI categorization via hourly queue"""
    try:
        filename = os.path.basename(filepath)
        publication_name = extract_publication_name(filename)
        norm_pub_name = unicodedata.normalize('NFC', publication_name)
        config = load_publications_config()
        
        # Check if publication is in the ignored list
        if norm_pub_name in config.get('ignored', []):
            logger.info(f"🚫 '{publication_name}' is in ignored list, staying in Others for manual review")
            return None
        
        # Check cache first - if cached, auto-process immediately
        cache_key = publication_name.lower()
        if cache_key in categorization_cache:
            ai_category = categorization_cache[cache_key]
            logger.info(f"💾 Using cached categorization for '{publication_name}': {ai_category}")
            
            # Auto-process with cached category
            category_folder = 'Jornais' if ai_category == 'jornal' else 'Revistas'
            
            if move_file_to_category(filepath, category_folder):
                category_key = 'jornais' if ai_category == 'jornal' else 'revistas'
                if add_to_category(publication_name, category_key, config):
                    save_publications_config(config)
                
                category_emoji = "📰" if ai_category == "jornal" else "📑"
                notification = f"💾 **Cached categorization**\n\n{category_emoji} **{publication_name}**\n📁 Category: {category_folder}\n\n✅ File moved automatically"
                await client.send_message(REVIEW_CHAT, notification)
                logger.info(f"✅ Auto-categorized {publication_name} from cache as {ai_category}")
                return None
        
        # Not cached - add to AI queue for hourly batch processing
        add_to_ai_queue(publication_name, filepath, filename)
        logger.debug(f"📋 '{publication_name}' queued for hourly AI batch processing")
        
        # Send notification about queued file
        try:
            queue = load_ai_queue()
            queue_size = len(queue.get("pending", []))
            notification = f"📋 **Queued for AI categorization**\n\n📄 **{publication_name}**\n⏰ Queue size: {queue_size}\n\n_Will be processed at the start of next hour_"
            await client.send_message(REVIEW_CHAT, notification)
        except Exception as e:
            logger.warning(f"Could not send queue notification: {e}")
        
        return None  # No manual review needed now - will be processed hourly
    
    except Exception as e:
        logger.error(f"Error in send_file_for_review: {e}")
        return None

async def process_approval(client, message_id, category):
    """Process file approval and move it to the appropriate folder"""
    try:
        review = get_pending_review(message_id)
        if not review:
            logger.error(f"Review not found for message ID: {message_id}")
            return False
        
        filepath = review['filepath']
        publication_name = review['publication_name']
        filename = review['filename']
        
        # Check if file still exists
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            remove_pending_review(message_id)
            return False
        
        # Move file to category folder
        category_map = {
            'jornal': 'Jornais',
            'revista': 'Revistas'
        }
        folder_name = category_map.get(category, category)
        
        if not move_file_to_category(filepath, folder_name):
            logger.error(f"Failed to move file: {filepath}")
            return False
        
        # Update publications.json
        config = load_publications_config()
        if add_to_category(publication_name, category + 's', config):
            save_publications_config(config)
        
        # Update pending review status
        remove_pending_review(message_id)
        
        # Edit message to show confirmation
        category_emoji = "📰" if category == "jornal" else "📑"
        confirmation_text = f"""✅ **File Categorized Successfully!**

📰 **Publication Name:** {publication_name}
📁 **Filename:** {filename}
📂 **Category:** {category_emoji} {folder_name}
⏰ **Processed at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        try:
            await client.edit_message_text(REVIEW_CHAT, message_id, confirmation_text)
        except Exception as e:
            logger.warning(f"Could not edit message: {e}")
        
        logger.info(f"✅ File approved and moved to {folder_name}: {filename}")
        return True
    
    except Exception as e:
        logger.error(f"Error processing approval: {e}")
        return False

async def process_delete(client, message_id):
    """Process file deletion from Others folder"""
    try:
        review = get_pending_review(message_id)
        if not review:
            logger.error(f"Review not found for message ID: {message_id}")
            return False
        
        filepath = review['filepath']
        publication_name = review['publication_name']
        filename = review['filename']
        
        # Delete the file if it exists
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"🗑️ Deleted file: {filepath}")
        else:
            logger.warning(f"File already deleted or not found: {filepath}")
        
        # Remove from pending reviews
        remove_pending_review(message_id)
        
        # Edit message to show deletion confirmation
        confirmation_text = f"""🗑️ **File Deleted**

📄 **{publication_name}**
📁 `{filename}`
⏰ **Deleted at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        try:
            await client.edit_message_text(REVIEW_CHAT, message_id, confirmation_text)
        except Exception as e:
            logger.warning(f"Could not edit message: {e}")
        
        logger.info(f"🗑️ File deleted: {filename}")
        return True
    
    except Exception as e:
        logger.error(f"Error processing delete: {e}")
        return False

async def handle_callback(client, callback_query):
    """Handle inline button callbacks from Telegram (Pyrogram)"""
    try:
        # Pyrogram: get message ID from callback_query.message.id
        message_id = callback_query.message.id
        
        # Pyrogram: data is already a string, no need to decode
        callback_data = callback_query.data
        
        # Parse the new compact format: j_123, r_123, d_123
        if '_' in callback_data:
            parts = callback_data.split('_', 1)
            action = parts[0]
            # The message ID in callback should match callback_query.message.id
        else:
            action = callback_data
        
        # Map short codes to full category names
        action_map = {
            'j': 'jornal',
            'r': 'revista',
            'd': 'delete',
            # Legacy support
            'jornal': 'jornal',
            'revista': 'revista'
        }
        
        category = action_map.get(action)
        
        if not category:
            await callback_query.answer("❌ Invalid action", show_alert=True)
            return
        
        # Handle delete action
        if category == 'delete':
            success = await process_delete(client, message_id)
            if success:
                await callback_query.answer("🗑️ File deleted", show_alert=False)
            else:
                await callback_query.answer("❌ Error deleting file", show_alert=True)
            return
        
        # Process the approval for jornal/revista
        success = await process_approval(client, message_id, category)
        
        if success:
            category_emoji = "📰" if category == "jornal" else "📑"
            await callback_query.answer(f"✅ Moved to {category_emoji}", show_alert=False)
        else:
            await callback_query.answer("❌ Error processing file", show_alert=True)
    
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        await callback_query.answer("❌ Error processing request", show_alert=True)

async def scan_existing_others_files(client):
    """Scan Others folder for existing files and send them to Telegram for review"""
    try:
        others_path = Path(OTHERS_FOLDER)
        
        if not others_path.exists():
            logger.info(f"📂 Others folder not found: {OTHERS_FOLDER}")
            return 0
        
        # Get all PDF files in Others folder
        pdf_files = list(others_path.glob("*.pdf")) + list(others_path.glob("*.PDF"))
        
        if not pdf_files:
            logger.info("✨ No existing files found in Others folder")
            return 0
        
        logger.info(f"🔍 Found {len(pdf_files)} existing file(s) in Others folder")
        
        logger.info(f"📋 Processing {len(pdf_files)} file(s) from Others")
        
        # Clear pending reviews on startup
        logger.info("🧹 Clearing pending reviews to resend all files")
        save_pending_reviews({})
        
        # OPTIMIZATION: Batch process files using AI
        # Extract unique publication names for AI, but keep track of all files
        unique_publication_names = set()
        file_list = [] # List of (filename, publication_name, filepath)
        
        for filepath in sorted(pdf_files):
            filename = filepath.name
            publication_name = extract_publication_name(filename)
            unique_publication_names.add(publication_name)
            file_list.append((filename, publication_name, str(filepath)))
        
        # Batch categorize all UNIQUE publications in ONE AI call
        logger.info(f"🤖 Batch categorizing {len(unique_publication_names)} unique publications...")
        categorization_results = await batch_categorize_with_ai(list(unique_publication_names))
        
        sent_count = 0
        auto_processed = 0
        
        # Collect auto-categorized files for consolidated notification
        auto_jornais = []
        auto_revistas = []
        
        for filename, publication_name, filepath_str in file_list:
            try:
                # Check if AI already categorized this one
                ai_category = categorization_results.get(publication_name)
                
                if ai_category:
                    # Auto-process using cached/batch result
                    logger.info(f"🤖 Auto-categorizing '{publication_name}' as {ai_category}")
                    
                    config = load_publications_config()
                    category_folder = 'Jornais' if ai_category == 'jornal' else 'Revistas'
                    
                    if move_file_to_category(filepath_str, category_folder):
                        category_key = 'jornais' if ai_category == 'jornal' else 'revistas'
                        if add_to_category(publication_name, category_key, config):
                            save_publications_config(config)
                        
                        # Collect for consolidated notification
                        if ai_category == 'jornal':
                            auto_jornais.append(publication_name)
                        else:
                            auto_revistas.append(publication_name)
                        auto_processed += 1
                else:
                    # Send for manual review
                    logger.debug(f"📤 Sending '{publication_name}' for manual review")
                    await send_file_for_review(client, filepath_str)
                    sent_count += 1
                    # Small delay to avoid Telegram flood limits when sending many files
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ Error processing file: {publication_name} - {e}")
        
        # Send consolidated notification for auto-categorized files
        if auto_processed > 0:
            summary_parts = [f"🤖 **Batch Auto-categorized {auto_processed} file(s)**\n"]
            
            if auto_jornais:
                jornais_list = ", ".join(auto_jornais[:10])
                if len(auto_jornais) > 10:
                    jornais_list += f" (+{len(auto_jornais) - 10} more)"
                summary_parts.append(f"\n📰 **Jornais ({len(auto_jornais)}):**\n{jornais_list}")
            
            if auto_revistas:
                revistas_list = ", ".join(auto_revistas[:10])
                if len(auto_revistas) > 10:
                    revistas_list += f" (+{len(auto_revistas) - 10} more)"
                summary_parts.append(f"\n📑 **Revistas ({len(auto_revistas)}):**\n{revistas_list}")
            
            await client.send_message(REVIEW_CHAT, "".join(summary_parts))
        
        logger.info(f"✅ Startup scan complete: {auto_processed} auto-categorized, {sent_count} sent for review")
        
        return sent_count + auto_processed
    
    except Exception as e:
        logger.error(f"Error scanning existing files: {e}")
        return 0

def setup_callback_handlers(client):
    """Setup callback handler for inline buttons and command handlers"""
    @client.on_callback_query(filters.chat(REVIEW_CHAT))
    async def callback_handler(client, callback_query):
        await handle_callback(client, callback_query)
    
    @client.on_message(filters.chat(REVIEW_CHAT) & filters.command(["addkeyword", "removekeyword", "keywords", "addtopic", "removetopic", "topics", "scan", "help", "rescan", "status", "publications"]))
    async def command_handler(client, message):
        await handle_command(client, message)
    
    @client.on_message(filters.chat(REVIEW_CHAT) & filters.reply)
    async def reply_handler(client, message):
        await handle_reply(client, message)
    
    logger.info("✅ Callback and command handlers registered")


async def handle_command(client, message):
    """Handle text commands from Telegram (Pyrogram)"""
    try:
        message_text = message.text.strip()
        parts = message_text.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        config = load_publications_config()
        
        # /addkeyword <keyword>
        if command == "/addkeyword":
            if not args:
                await message.reply("❌ Usage: /addkeyword <keyword>\n\nExample: /addkeyword magazine")
                return
            
            keyword = args.strip()
            if add_keyword(keyword, config):
                save_publications_config(config)
                await message.reply(f"✅ Keyword added: **{keyword.lower()}**\n\n"
                                f"Files containing this keyword will now be downloaded.")
            else:
                await message.reply(f"ℹ️ Keyword **{keyword.lower()}** already exists.")
        
        # /removekeyword <keyword>
        elif command == "/removekeyword":
            if not args:
                await message.reply("❌ Usage: /removekeyword <keyword>\n\nExample: /removekeyword magazine")
                return
            
            keyword = args.strip()
            if remove_keyword(keyword, config):
                save_publications_config(config)
                await message.reply(f"✅ Keyword removed: **{keyword.lower()}**")
            else:
                await message.reply(f"❌ Keyword **{keyword.lower()}** not found.")
        
        # /keywords - list all keywords
        elif command == "/keywords":
            keywords = get_keywords(config)
            if keywords:
                keywords_list = "\n".join([f"• {k}" for k in keywords])
                await message.reply(f"📋 **Current Keywords** ({len(keywords)}):\n\n{keywords_list}\n\n"
                                f"Use /addkeyword or /removekeyword to manage.")
            else:
                await message.reply("📋 No keywords configured.\n\n"
                                f"Use /addkeyword <keyword> to add one.")
        
        # /addtopic <topic>
        elif command == "/addtopic":
            if not args:
                await message.reply("❌ Usage: /addtopic <topic>\n\nExample: /addtopic bikes")
                return
            
            topic = args.strip()
            if add_topic(topic, config):
                save_publications_config(config)
                await message.reply(f"✅ Topic added: **{topic.lower()}**\n\n"
                                f"English language files related to this topic will now be downloaded.")
            else:
                await message.reply(f"ℹ️ Topic **{topic.lower()}** already exists.")
        
        # /removetopic <topic>
        elif command == "/removetopic":
            if not args:
                await message.reply("❌ Usage: /removetopic <topic>\n\nExample: /removetopic bikes")
                return
            
            topic = args.strip()
            if remove_topic(topic, config):
                save_publications_config(config)
                await message.reply(f"✅ Topic removed: **{topic.lower()}**")
            else:
                await message.reply(f"❌ Topic **{topic.lower()}** not found.")
        
        # /topics - list all topics
        elif command == "/topics":
            topics = get_topics(config)
            if topics:
                topics_list = "\n".join([f"• {t}" for t in topics])
                await message.reply(f"🎯 **Current Topics** ({len(topics)}):\n\n{topics_list}\n\n"
                                f"English language files matching these topics will be downloaded.\n"
                                f"Use /addtopic or /removetopic to manage.")
            else:
                await message.reply("🎯 No topics configured.\n\n"
                                f"Use /addtopic <topic> to add one.\n\n"
                                f"Example: /addtopic bikes")
        
        # /categorize <publication_name> <jornal|revista> - categorize a pending file
        elif command == "/categorize":
            if not args:
                await message.reply("❌ Usage: /categorize <publication_name> <jornal|revista>\n\n"
                                "Example: /categorize Público jornal")
                return
            
            parts = args.rsplit(maxsplit=1)
            if len(parts) != 2:
                await message.reply("❌ Usage: /categorize <publication_name> <jornal|revista>")
                return
            
            publication_name = parts[0].strip()
            category = parts[1].strip().lower()
            
            if category not in ['jornal', 'revista']:
                await message.reply("❌ Category must be 'jornal' or 'revista'")
                return
            
            # Find the pending review for this publication
            pending_reviews = load_pending_reviews()
            found_review = None
            
            for msg_id, review in pending_reviews.items():
                if review.get('publication_name', '').lower() == publication_name.lower():
                    found_review = (msg_id, review)
                    break
            
            if not found_review:
                await message.reply(f"❌ No pending file found for publication: {publication_name}")
                return
            
            msg_id, review = found_review
            
            # Process the categorization
            success = await process_approval(client, int(msg_id), category)
            
            if success:
                category_emoji = "📰" if category == "jornal" else "📑"
                await message.reply(f"✅ File categorized as {category_emoji} **{category}**\n\n"
                                f"Publication **{publication_name}** added to {category}s list.")
            else:
                await message.reply(f"❌ Error categorizing file for {publication_name}")
        
        # /scan - trigger channel scan
        elif command == "/scan":
            await message.reply("🔍 Starting channel scan...\n\n"
                            "This will search for files matching current keywords and PT pattern.")
            
            # Trigger a scan by importing and calling the scan function
            try:
                from telegram_downloader import scan_channel_for_keywords
                count = await scan_channel_for_keywords(client, message)
                await message.reply(f"✅ Scan complete!\n\n"
                                f"Processed {count} message(s).")
            except Exception as e:
                logger.error(f"Error during scan: {e}")
                await message.reply(f"❌ Error during scan: {str(e)}")
        
        # /scan_others - scan Others folder and send files for review
        elif command == "/scan_others":
            await message.reply("🔍 Scanning Others folder...\n\n"
                            "Finding uncategorized files for review.")
            
            try:
                data_path = Path(DATA_FOLDER)
                others_path = Path(OTHERS_FOLDER)
                
                logger.info(f"📂 DATA_FOLDER: {DATA_FOLDER}")
                logger.info(f"📂 OTHERS_FOLDER: {OTHERS_FOLDER}")
                logger.info(f"📂 DATA_FOLDER exists: {data_path.exists()}")
                logger.info(f"📂 OTHERS_FOLDER exists: {others_path.exists()}")
                
                # List all contents of DATA_FOLDER for debugging
                if data_path.exists():
                    contents = list(data_path.iterdir())
                    logger.info(f"📂 Contents of {DATA_FOLDER}: {[p.name for p in contents]}")
                
                if not others_path.exists():
                    msg = f"📂 Others folder not found at: {OTHERS_FOLDER}\n\n"
                    msg += f"📂 DATA_FOLDER: {DATA_FOLDER}\n"
                    msg += f"📂 DATA_FOLDER exists: {data_path.exists()}"
                    logger.warning(msg)
                    await message.reply(msg)
                    return
                
                # Get all PDF files in Others folder (case-insensitive)
                pdf_files = [f for f in others_path.iterdir() if f.suffix.lower() == '.pdf']
                logger.info(f"📂 Found {len(pdf_files)} PDF file(s) in Others folder")
                
                # Also list all files (not just PDF)
                all_files = list(others_path.iterdir())
                logger.info(f"📂 All files in Others: {[p.name for p in all_files]}")
                
                if not pdf_files:
                    msg = f"✨ No PDF files found in Others folder"
                    if all_files:
                        msg += f"\n\n📁 Files found: {[p.name for p in all_files[:10]]}"
                    await message.reply(msg)
                    return
                
                logger.info(f"🔍 Found {len(pdf_files)} file(s) in Others folder for review")
                
                sent_count = 0
                for filepath in sorted(pdf_files):
                    filename = filepath.name
                    try:
                        # Send file for review
                        await send_file_for_review(client, str(filepath))
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Error sending {filename} for review: {e}")
                
                await message.reply(f"✅ Scan complete!\n\n"
                                f"📤 Sent {sent_count} file(s) for categorization.")
                logger.info(f"📤 Sent {sent_count} files from Others folder for review")
                
            except Exception as e:
                logger.error(f"Error scanning Others folder: {e}", exc_info=True)
                await message.reply(f"❌ Error scanning Others folder: {str(e)}")
        
        # /clearcache - clear AI categorization cache
        elif command == "/clearcache":
            global categorization_cache
            cache_size = len(categorization_cache)
            categorization_cache = {}
            save_ai_cache(categorization_cache)
            await message.reply(f"✅ AI cache cleared!\n\n"
                            f"Removed {cache_size} cached categorization(s).\n"
                            f"Next categorizations will use fresh AI calls.")
            logger.info(f"🗑️ AI cache cleared by user command ({cache_size} entries)")
        
        # /cachestats - show cache statistics
        elif command == "/cachestats":
            cache_size = len(categorization_cache)
            await message.reply(f"📊 **AI Cache Statistics**\n\n"
                            f"Cached publications: {cache_size}\n"
                            f"Cache file: `ai_cache.json`\n\n"
                            f"Cached results avoid duplicate AI calls and save RPM.\n"
                            f"Use /clearcache to reset if needed.")
        
        # /help - show available commands
        elif command == "/help":
            help_text = """📚 **Available Commands:**

**Keyword Management:**
• `/addkeyword <word>` - Add a new keyword
• `/removekeyword <word>` - Remove a keyword
• `/keywords` - List all keywords

**Topic Management (English files):**
• `/addtopic <topic>` - Add topic filter (e.g. bikes, tech)
• `/removetopic <topic>` - Remove a topic
• `/topics` - List all topics

**File Management:**
• `/categorize <name> <jornal|revista>` - Categorize pending file
• `/scan` - Scan channel for new files
• `/scan_others` - Scan Others folder and send for review

**AI Cache:**
• `/cachestats` - Show AI cache statistics
• `/clearcache` - Clear AI categorization cache

**Other:**
• `/help` - Show this help message

**Examples:**
```
/addkeyword magazine
/addtopic bikes
/scan_others
/categorize Público jornal
```

**Notes:**
• AI results are cached to save RPM (10 req/min limit)
• Batch processing used when possible
• Topics match ONLY English language files"""
            
            await message.reply(help_text)
        
        else:
            await message.reply(f"❌ Unknown command: {command}\n\n"
                            f"Use /help to see available commands.")
    
    except Exception as e:
        logger.error(f"Error handling command: {e}")
        await message.reply(f"❌ Error processing command: {str(e)}")


async def handle_reply(client, message):
    """Handle simple text replies to categorization messages (Pyrogram)"""
    try:
        # Skip if it's a command
        if message.text.startswith('/'):
            return
        
        # Check if this is a reply to another message
        if not message.reply_to_message_id:
            return
        
        text = message.text.strip().lower()
        
        # Check if the reply is "jornal" or "revista"
        if text not in ['jornal', 'revista', 'jornais', 'revistas']:
            return
        
        # Normalize to singular form
        category = 'jornal' if text in ['jornal', 'jornais'] else 'revista'
        
        # Get the message being replied to
        reply_to_msg_id = message.reply_to_message_id
        
        # Check if this message ID is in pending reviews
        review = get_pending_review(reply_to_msg_id)
        if not review:
            # Not a pending review message
            return
        
        logger.info(f"📝 Reply categorization: {category} for message {reply_to_msg_id}")
        
        # Process the approval
        success = await process_approval(client, reply_to_msg_id, category)
        
        if success:
            category_emoji = "📰" if category == "jornal" else "📑"
            await message.reply(f"✅ Categorized as {category_emoji} **{category}**")
        else:
            await message.reply(f"❌ Error categorizing file")
    
    except Exception as e:
        logger.error(f"Error handling reply: {e}")


