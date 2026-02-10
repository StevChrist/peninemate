import re
from typing import List, Dict, Optional


def extract_sequel_number(title: str) -> Optional[int]:
    """
    Extract sequel number from title (Iron Man 2 -> 2)
    """
    match = re.search(r'\b(\d+)\b$', title)
    return int(match.group(1)) if match else None


def detect_invalid_sequel(
    query: str,
    search_results: List[Dict]
) -> Optional[Dict]:
    """
    Detect if user asks for a sequel that does not exist

    Returns:
        None → valid or not a sequel
        Dict → invalid sequel info
    """
    match = re.search(r'(.+?)\s(\d+)$', query.strip())
    if not match:
        return None

    base_title = match.group(1).lower()
    requested_num = int(match.group(2))

    existing_numbers = []

    for movie in search_results:
        title = movie.get("title", "").lower()
        if base_title in title:
            num = extract_sequel_number(title)
            if num is not None:
                existing_numbers.append(num)

    if not existing_numbers:
        return None

    max_existing = max(existing_numbers)

    if requested_num > max_existing:
        return {
            "base_title": match.group(1),
            "requested": requested_num,
            "max_existing": max_existing,
            "existing_titles": [
                m["title"] for m in search_results
                if base_title in m.get("title", "").lower()
            ]
        }

    return None
