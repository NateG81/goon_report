"""
scripts/sync_goon_images.py
Downloads Goon images + metadata from Dropbox vault.
Handles filenames like: '1 (2022_09_25 16_46_17 UTC).png'
Only downloads the next unprocessed image each run.
"""

import os
import re
import json
import requests
from pathlib import Path

DROPBOX_TOKEN       = os.environ["DROPBOX_ACCESS_TOKEN"]
DROPBOX_FOLDER      = os.environ.get("DROPBOX_GOONS_PATH", "/Vault/GoonGalaxy/GoonGalaxyGenerator/create-10k-nft-collection-2.0.0/build/images")
DROPBOX_JSON_FOLDER = os.environ.get("DROPBOX_JSON_PATH", "/Vault/GoonGalaxy/GoonGalaxyGenerator/create-10k-nft-collection-2.0.0/build/json")
LOCAL_DIR           = Path("./goons")
LOCAL_DIR.mkdir(exist_ok=True)

HEADERS = {"Authorization": f"Bearer {DROPBOX_TOKEN}"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def extract_edition_number(filename: str):
    """Extract edition number from '1 (2022_09_25 16_46_17 UTC).png' -> 1"""
    match = re.match(r'^(\d+)', filename)
    return int(match.group(1)) if match else None


def dropbox_list_folder(path: str) -> list:
    """List all files, handling pagination for 10k+ files."""
    all_entries = []
    resp = requests.post(
        "https://api.dropboxapi.com/2/files/list_folder",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"path": path, "recursive": False, "limit": 2000},
    )
    if not resp.ok:
        print(f"  Dropbox error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    data = resp.json()
    all_entries.extend(data.get("entries", []))

    while data.get("has_more"):
        print(f"  Paginating... ({len(all_entries)} so far)")
        resp = requests.post(
            "https://api.dropboxapi.com/2/files/list_folder/continue",
            headers={**HEADERS, "Content-Type": "application/json"},
            json={"cursor": data["cursor"]},
        )
        if not resp.ok:
            print(f"  Dropbox pagination error {resp.status_code}: {resp.text}")
            resp.raise_for_status()
        data = resp.json()
        all_entries.extend(data.get("entries", []))

    return all_entries


def dropbox_download(path: str, dest: Path):
    resp = requests.post(
        "https://content.dropboxapi.com/2/files/download",
        headers={**HEADERS, "Dropbox-API-Arg": json.dumps({"path": path})},
    )
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def dropbox_upload(local_path: Path, dropbox_path: str):
    with open(local_path, "rb") as f:
        resp = requests.post(
            "https://content.dropboxapi.com/2/files/upload",
            headers={
                **HEADERS,
                "Content-Type": "application/octet-stream",
                "Dropbox-API-Arg": json.dumps({
                    "path": dropbox_path,
                    "mode": "overwrite",
                    "autorename": False,
                }),
            },
            data=f,
        )
    resp.raise_for_status()
    return resp.json()


def sync_from_dropbox():
    print(f"Syncing images from Dropbox: {DROPBOX_FOLDER}")
    entries = dropbox_list_folder(DROPBOX_FOLDER)
    print(f"Found {len(entries)} total entries")

    # Load existing log to know which editions are already posted
    log_path = LOCAL_DIR / "goons_log.json"
    posted = set()
    if log_path.exists():
        with open(log_path) as f:
            posted = set(int(k) for k in json.load(f).get("posted", {}).keys())

    # Build sorted list of unprocessed image entries
    image_entries = []
    for entry in entries:
        if entry[".tag"] != "file":
            continue
        filename = entry["name"]
        ext = Path(filename).suffix.lower()
        if ext not in IMAGE_EXTENSIONS:
            continue
        edition = extract_edition_number(filename)
        if edition is not None and edition not in posted:
            image_entries.append((edition, entry))

    # Sort by edition number ascending
    image_entries.sort(key=lambda x: x[0])

    if not image_entries:
        print("  No unprocessed images found!")
        return

    # Download ONLY the next unprocessed image
    edition, entry = image_entries[0]
    filename = entry["name"]
    ext = Path(filename).suffix.lower()
    clean_name = f"{edition}{ext}"
    dest = LOCAL_DIR / clean_name

    if not dest.exists():
        print(f"  Downloading: {filename} -> {clean_name}")
        dropbox_download(entry["path_display"], dest)
    else:
        print(f"  Already exists: {clean_name}")

    print(f"  Ready to process edition #{edition}")

    # Pull _metadata_.json from json folder
    metadata_dest = LOCAL_DIR / "_metadata_.json"
    if not metadata_dest.exists():
        print(f"  Downloading _metadata_.json...")
        dropbox_download(f"{DROPBOX_JSON_FOLDER}/_metadata_ (2022_09_25 16_46_17 UTC).json", metadata_dest)
    else:
        print(f"  _metadata_.json already exists")

    # Pull goons_log.json if it exists in Dropbox
    try:
        if not log_path.exists():
            dropbox_download(f"{DROPBOX_FOLDER}/goons_log.json", log_path)
            print(f"  Downloaded goons_log.json")
    except Exception:
        print(f"  No existing goons_log.json (first run)")

    print("Sync complete.")


def push_log_to_dropbox():
    local_log = LOCAL_DIR / "goons_log.json"
    if not local_log.exists():
        print("  No goons_log.json to push")
        return
    dropbox_upload(local_log, f"{DROPBOX_FOLDER}/goons_log.json")
    print(f"  ✓ goons_log.json synced to Dropbox")


def archive_to_dropbox(local_video: Path, edition: int, goon_name: str):
    safe_name = goon_name.replace('"', '').replace(' ', '_')
    archive_folder = f"{DROPBOX_FOLDER}/posted/{edition}_{safe_name}"

    if local_video.exists():
        dropbox_upload(local_video, f"{archive_folder}/{local_video.name}")
        print(f"  ✓ Video archived to Dropbox")

    for ext in IMAGE_EXTENSIONS:
        candidate = LOCAL_DIR / f"{edition}{ext}"
        if candidate.exists():
            dropbox_upload(candidate, f"{archive_folder}/{candidate.name}")
            print(f"  ✓ Source image archived to Dropbox")
            break

    print(f"  ✓ Goon #{edition} fully archived")


if __name__ == "__main__":
    sync_from_dropbox()
