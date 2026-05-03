"""
goon_log.py
Tracks which Goon editions have been posted.
Log file: {OBSIDIAN_GOONS_PATH}/goons_log.json
Image files should be named: {edition_number}.png / .jpg / .webp
  e.g.  0001.png, 0042.jpg, 9999.png
"""

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

LOG_FILENAME = "goons_log.json"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _load_log(vault_path: Path) -> dict:
    log_path = vault_path / LOG_FILENAME
    if log_path.exists():
        with open(log_path) as f:
            return json.load(f)
    return {"posted": {}}


def _save_log(vault_path: Path, data: dict):
    log_path = vault_path / LOG_FILENAME
    with open(log_path, "w") as f:
        json.dump(data, f, indent=2)


def get_next_goon(vault_path: Path) -> tuple:
    """
    Returns (image_path, edition_number) for the next unprocessed Goon.
    Images must be named by edition number: 0001.png, 42.jpg etc.
    Returns (None, None) if all are processed.
    """
    log_data = _load_log(vault_path)
    posted_editions = set(int(k) for k in log_data["posted"].keys())

    # Collect all image files, sort by edition number ascending
    images = []
    for ext in IMAGE_EXTENSIONS:
        for img in vault_path.glob(f"*{ext}"):
            try:
                edition = int(img.stem)
                images.append((edition, img))
            except ValueError:
                # Skip files not named as numbers (e.g. _metadata_.json)
                pass

    images.sort(key=lambda x: x[0])

    for edition, img_path in images:
        if edition not in posted_editions:
            return img_path, edition

    return None, None


def mark_goon_posted(vault_path: Path, edition: int, full_name: str):
    """Mark an edition as posted in the log."""
    from datetime import datetime
    log_data = _load_log(vault_path)
    log_data["posted"][str(edition)] = {
        "name": full_name,
        "posted_at": datetime.utcnow().isoformat() + "Z"
    }
    _save_log(vault_path, log_data)
    log.info(f"  → Logged edition #{edition} ({full_name}) as posted")
