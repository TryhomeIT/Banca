import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..config import settings

WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
WIKIDATA_ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{entity_id}.json"
WIKIDATA_CACHE_FILE = Path(settings.DATA_DIR) / "wikidata_publication_cache.json"
WIKIDATA_USER_AGENT = "BancaDiscover/1.0 (Wikidata weekly enrichment)"
WIKIDATA_REFRESH_DAYS = 7


def normalize_wikidata_text(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFC", value).lower()
    normalized = normalized.replace("_", " ").replace(".", " ").replace("-", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def load_wikidata_cache() -> Dict[str, Any]:
    try:
        if WIKIDATA_CACHE_FILE.exists():
            with open(WIKIDATA_CACHE_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, dict):
                    data.setdefault("meta", {})
                    data.setdefault("entries", {})
                    return data
    except Exception:
        pass
    return {"meta": {}, "entries": {}}


def save_wikidata_cache(cache: Dict[str, Any]):
    WIKIDATA_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WIKIDATA_CACHE_FILE, "w", encoding="utf-8") as handle:
        json.dump(cache, handle, indent=2, ensure_ascii=False)


def get_cached_wikidata_metadata(title: str) -> Optional[Dict[str, Any]]:
    cache = load_wikidata_cache()
    return cache.get("entries", {}).get(normalize_wikidata_text(title))


def refresh_wikidata_cache_for_titles(titles: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    cache = load_wikidata_cache()
    now = datetime.now(timezone.utc)
    last_scan_raw = cache.get("meta", {}).get("last_scan_at")
    last_scan = None
    if last_scan_raw:
        try:
            last_scan = datetime.fromisoformat(last_scan_raw)
        except ValueError:
            last_scan = None

    if last_scan and now - last_scan < timedelta(days=WIKIDATA_REFRESH_DAYS):
        return cache.get("entries", {})

    changed = False
    entries = cache.setdefault("entries", {})

    for title in sorted({title for title in titles if title and title.strip()}):
        normalized_title = normalize_wikidata_text(title)
        if not normalized_title:
            continue

        try:
            entries[normalized_title] = lookup_title_on_wikidata(title)
        except Exception:
            entries[normalized_title] = {
                "country": "Unknown",
                "suggested_category": None,
                "country_source": "wikidata_error",
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        changed = True

    if changed:
        cache.setdefault("meta", {})["last_scan_at"] = now.isoformat()
        save_wikidata_cache(cache)

    return entries


def lookup_title_on_wikidata(title: str) -> Dict[str, Any]:
    try:
        search_results = wikidata_api_request(
            {
                "action": "wbsearchentities",
                "search": title,
                "language": "en",
                "limit": 5,
                "format": "json",
            }
        ).get("search", [])
    except Exception:
        return {
            "country": "Unknown",
            "suggested_category": None,
            "country_source": "wikidata_error",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    normalized_title = normalize_wikidata_text(title)
    selected_result = None

    for result in search_results:
        label = normalize_wikidata_text(result.get("label", ""))
        description = normalize_wikidata_text(result.get("description", ""))
        if label == normalized_title:
            selected_result = result
            break
        if label and (label in normalized_title or normalized_title in label):
            selected_result = result
            break
        if any(token in description for token in ["newspaper", "magazine", "periodical", "journal"]):
            selected_result = result
            break

    if selected_result is None and search_results:
        selected_result = search_results[0]

    if selected_result is None:
        return {
            "country": "Unknown",
            "suggested_category": None,
            "country_source": "wikidata_unresolved",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    entity_id = selected_result.get("id")
    try:
        entity_payload = wikidata_entity_request(entity_id)
    except Exception:
        return {
            "country": "Unknown",
            "suggested_category": None,
            "country_source": "wikidata_error",
            "wikidata_id": entity_id,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    entity = entity_payload.get("entities", {}).get(entity_id, {})
    claims = entity.get("claims", {})

    related_ids = []
    related_ids.extend(extract_entity_ids(claims.get("P17", [])))
    related_ids.extend(extract_entity_ids(claims.get("P495", [])))
    related_ids.extend(extract_entity_ids(claims.get("P31", [])))
    labels_by_id = fetch_entity_labels(related_ids)

    country = "Unknown"
    for property_id in ("P17", "P495"):
        entity_ids = extract_entity_ids(claims.get(property_id, []))
        if entity_ids:
            country = labels_by_id.get(entity_ids[0], "Unknown")
            if country:
                break

    suggested_category = None
    instance_labels = [labels_by_id.get(entity_id, "") for entity_id in extract_entity_ids(claims.get("P31", []))]
    for label in instance_labels:
        normalized_label = normalize_wikidata_text(label)
        if "newspaper" in normalized_label:
            suggested_category = "newspaper"
            break
        if any(token in normalized_label for token in ["magazine", "periodical", "journal"]):
            suggested_category = "magazine"
            break

    return {
        "country": country or "Unknown",
        "suggested_category": suggested_category,
        "country_source": "wikidata",
        "wikidata_id": entity_id,
        "wikidata_label": selected_result.get("label"),
        "wikidata_description": selected_result.get("description"),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def extract_entity_ids(claims: Iterable[Dict[str, Any]]) -> list[str]:
    entity_ids: list[str] = []
    for claim in claims or []:
        try:
            entity_id = claim["mainsnak"]["datavalue"]["value"]["id"]
        except Exception:
            continue
        if entity_id:
            entity_ids.append(entity_id)
    return entity_ids


def fetch_entity_labels(entity_ids: Iterable[str]) -> Dict[str, str]:
    unique_ids = sorted({entity_id for entity_id in entity_ids if entity_id})
    if not unique_ids:
        return {}

    payload = wikidata_api_request(
        {
            "action": "wbgetentities",
            "ids": "|".join(unique_ids),
            "props": "labels",
            "languages": "en",
            "format": "json",
        }
    )
    entities = payload.get("entities", {})
    labels: Dict[str, str] = {}
    for entity_id in unique_ids:
        labels[entity_id] = entities.get(entity_id, {}).get("labels", {}).get("en", {}).get("value", "")
    return labels


def wikidata_api_request(params: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{WIKIDATA_API_URL}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def wikidata_entity_request(entity_id: str) -> Dict[str, Any]:
    url = WIKIDATA_ENTITY_URL.format(entity_id=entity_id)
    request = Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))