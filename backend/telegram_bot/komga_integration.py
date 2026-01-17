"""
Komga integration for triggering library scans after file downloads.
Uses debouncing to avoid triggering multiple scans for batch downloads.
"""

import asyncio
import aiohttp
import logging
import time
from typing import Set

logger = logging.getLogger(__name__)

# Komga Configuration
KOMGA_API_KEY = "49e8c61b024345438466dd7a46491b02"
KOMGA_BASE_URL = "https://jornais.local.tryhomeit.com"

# Library endpoints
KOMGA_LIBRARIES = {
    "jornais": f"{KOMGA_BASE_URL}/api/v1/libraries/0NZWA3HS14353/scan?deep=false",
    "revistas": f"{KOMGA_BASE_URL}/api/v1/libraries/0NZWA7ZT149XT/scan?deep=false"
}

# Debounce settings
SCAN_DELAY_SECONDS = 30  # Wait 30 seconds before triggering scan
_pending_scans: Set[str] = set()  # Libraries waiting to be scanned
_scan_task: asyncio.Task = None
_last_scan_time: dict = {"jornais": 0, "revistas": 0}
MIN_SCAN_INTERVAL = 60  # Minimum 60 seconds between scans for same library


async def _trigger_komga_scan(library: str) -> bool:
    """Actually trigger the Komga scan for a library"""
    if library not in KOMGA_LIBRARIES:
        logger.warning(f"⚠️ Unknown Komga library: {library}")
        return False
    
    url = KOMGA_LIBRARIES[library]
    headers = {
        "X-API-Key": KOMGA_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        # Use SSL verification disabled for local certs (common in homelab)
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, headers=headers) as response:
                if response.status in [200, 202, 204]:
                    logger.info(f"📚 Komga scan triggered for {library} library")
                    return True
                else:
                    text = await response.text()
                    logger.warning(f"⚠️ Komga scan failed for {library}: {response.status} - {text}")
                    return False
    except Exception as e:
        logger.error(f"❌ Error triggering Komga scan for {library}: {e}")
        return False


async def _process_pending_scans():
    """Process all pending scans after the debounce delay"""
    global _pending_scans, _last_scan_time
    
    await asyncio.sleep(SCAN_DELAY_SECONDS)
    
    # Copy and clear pending scans
    libraries_to_scan = _pending_scans.copy()
    _pending_scans.clear()
    
    if not libraries_to_scan:
        return
    
    current_time = time.time()
    
    for library in libraries_to_scan:
        # Check if we scanned recently
        time_since_last = current_time - _last_scan_time.get(library, 0)
        if time_since_last < MIN_SCAN_INTERVAL:
            logger.info(f"⏳ Skipping Komga scan for {library} (scanned {time_since_last:.0f}s ago)")
            continue
        
        success = await _trigger_komga_scan(library)
        if success:
            _last_scan_time[library] = current_time


def schedule_komga_scan(library: str):
    """
    Schedule a Komga library scan with debouncing.
    Multiple calls within SCAN_DELAY_SECONDS will result in only one scan.
    
    Args:
        library: 'jornais' or 'revistas'
    """
    global _pending_scans, _scan_task
    
    library = library.lower()
    if library not in KOMGA_LIBRARIES:
        logger.warning(f"⚠️ Unknown library for Komga scan: {library}")
        return
    
    # Add to pending scans
    _pending_scans.add(library)
    logger.debug(f"📋 Queued Komga scan for {library} (pending: {_pending_scans})")
    
    # Cancel existing task if any and start new one
    if _scan_task and not _scan_task.done():
        _scan_task.cancel()
    
    # Schedule the scan
    try:
        loop = asyncio.get_event_loop()
        _scan_task = loop.create_task(_process_pending_scans())
    except RuntimeError:
        # No event loop running yet, will be handled later
        pass


async def trigger_immediate_scan(library: str):
    """Trigger an immediate scan without debouncing (for manual triggers)"""
    global _last_scan_time
    
    library = library.lower()
    current_time = time.time()
    
    # Check rate limit
    time_since_last = current_time - _last_scan_time.get(library, 0)
    if time_since_last < MIN_SCAN_INTERVAL:
        logger.info(f"⏳ Rate limited: Komga {library} scan (wait {MIN_SCAN_INTERVAL - time_since_last:.0f}s)")
        return False
    
    success = await _trigger_komga_scan(library)
    if success:
        _last_scan_time[library] = current_time
    return success


async def trigger_all_scans():
    """Trigger scans for all libraries (useful for startup or manual refresh)"""
    results = {}
    for library in KOMGA_LIBRARIES.keys():
        results[library] = await trigger_immediate_scan(library)
    return results
