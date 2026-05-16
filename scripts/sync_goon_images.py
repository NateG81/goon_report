"""
scripts/sync_goon_images.py
Downloads Goon images + individual JSON metadata from Dropbox vault.
Uses refresh token to auto-generate fresh access tokens.
Only downloads the next unprocessed image each run.
"""

import os
import re
import json
import requests
from pathlib import Path

DROPBOX_REFRESH_TOKEN = os.environ.get("DROPBOX_REFRESH_TOKEN", "")
DROPBOX_APP_KEY       = os.environ.get("DROPBOX_APP_KEY", "")
DROPBOX_APP_SECRET    = os.environ.get("DROPBOX_APP_SECRET", "")
DROPBOX_FOLDER        = os.environ.get("DROPBOX_GOONS_PATH", "/Vault/GoonGalaxy/GoonGalaxyGenerator/create-10k-nft-collection-2.0.0/build/images")
DROPBOX_JSON_FOLDER   = os.environ.get("DROPBOX_JSON_PATH", "/Vault/GoonGalaxy/GoonGalaxyGenerator/create-10k-nft-collection-2.0.0/build/json")
LOCAL_DIR             = Path("./goons")
LOCAL_DIR.mkdir(exist_ok=True)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
TIMESTAMP        = "2022_09_25 16_46_17 UTC"

_DROPBOX_TOKEN = None


def get_access_token() -> str:
    resp = requests.post(
        "https://api.dropbox.com/oauth2/token",
        data={
            "grant_type":    "refresh_token",
            "refresh_token": DROPBOX_REFRESH_TOKEN,
            "client_id":     DROPBOX_APP_KEY,
            "client_secret": DROPBOX_APP_SECRET,
        },
    )
    if not resp.ok:
        print(f"  Token refresh error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    return resp.json()["access_token"]


def get_headers() -> dict:
    global _DROPBOX_TOKEN
    if not _DROPBOX_TOKEN:
        _DROPBOX_TOKEN = get_access_token()
    return {"Authorization": f"Bearer {_DROPBOX_TOKEN}"}


def extract_edition_number(filename: str):
    match = re.match(r'^(\d+)', filename)
    return int(match.group(1)) if match else None


def dropbox_list_folder(path: str) -> list:
    all_entries = []
    headers = get_headers()
    resp = requests.post(
        "https://api.dropboxapi.com/2/files/list_folder",
        headers={**headers, "Content-Type": "application/json"},
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
            headers={**headers, "Content-Type": "application/json"},
            json={"cursor": data["cursor"]},
        )
        if not resp.ok:
            print(f"  Dropbox pagination error {resp.status_code}: {resp.text}")
            resp.raise_for_status()
        data = resp.json()
        all_entries.extend(data.get("entries", []))

    return all_entries


def dropbox_download(path: str, dest: Path):
    headers = get_headers()
    resp = requests.post(
        "https://content.dropboxapi.com/2/files/download",
        headers={**headers, "Dropbox-API-Arg": json.dumps({"path": path})},
    )
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def dropbox_upload(local_path: Path, dropbox_path: str):
    headers = get_headers()
    with open(local_path, "rb") as f:
        resp = requests.post(
            "https://content.dropboxapi.com/2/files/upload",
            headers={
                **headers,
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

    log_path = LOCAL_DIR / "goons_log.json"
    posted = set()
    if log_path.exists():
        with open(log_path) as f:
            posted = set(int(k) for k in json.load(f).get("posted", {}).keys())

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

    image_entries.sort(key=lambda x: x[0])

    if not image_entries:
        print("  No unprocessed images found!")
        return

    edition, entry = image_entries[0]
    filename = entry["name"]
    ext = Path(filename).suffix.lower()
    clean_name = f"{edition}{ext}"
    dest = LOCAL_DIR / clean_name

    if not dest.exists():
        print(f"  Downloading image: {filename} -> {clean_name}")
        dropbox_download(entry["path_display"], dest)
    else:
        print(f"  Image already exists: {clean_name}")

    print(f"  Ready to process edition #{edition}")

    json_filename = f"{edition} ({TIMESTAMP}).json"
    json_dest = LOCAL_DIR / f"{edition}.json"
    if not json_dest.exists():
        print(f"  Downloading metadata: {json_filename}")
        dropbox_download(
            f"{DROPBOX_JSON_FOLDER}/{json_filename}",
            json_dest
        )
        print(f"  Metadata downloaded")
    else:
        print(f"  Metadata already exists: {edition}.json")

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
    print(f"  goons_log.json synced to Dropbox")


def archive_to_dropbox(local_video: Path, edition: int, goon_name: str):
    safe_name = goon_name.replace('"', '').replace(' ', '_')
    archive_folder = f"/Vault/GeneralV/prepared/{edition}_{safe_name}"

    if local_video.exists():
        dropbox_upload(local_video, f"{archive_folder}/{local_video.name}")
        print(f"  Video archived to Dropbox")

    for ext in IMAGE_EXTENSIONS:
        candidate = LOCAL_DIR / f"{edition}{ext}"
        if candidate.exists():
            dropbox_upload(candidate, f"{archive_folder}/{candidate.name}")
            print(f"  Source image archived to Dropbox")
            break

    print(f"  Goon #{edition} fully archived")


if __name__ == "__main__":
    sync_from_dropbox()