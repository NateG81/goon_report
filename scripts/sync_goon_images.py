"""
scripts/sync_goon_images.py
Downloads Goon images + metadata from Dropbox vault to local ./goons/ folder
so the GitHub Actions runner has access to them.

Dropbox folder structure:
  /Vault/GoonGalaxy/GoonGalaxyGenerator/create-10k-nft-collection-2.0.0/build/images
  /Vault/GoonGalaxy/GoonGalaxyGenerator/create-10k-nft-collection-2.0.0/build/json
"""

import os
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


def dropbox_list_folder(path: str) -> list:
    resp = requests.post(
        "https://api.dropboxapi.com/2/files/list_folder",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"path": path, "recursive": False},
    )
    resp.raise_for_status()
    return resp.json().get("entries", [])


def dropbox_download(path: str, dest: Path):
    resp = requests.post(
        "https://content.dropboxapi.com/2/files/download",
        headers={
            **HEADERS,
            "Dropbox-API-Arg": json.dumps({"path": path}),
        },
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
    print(f"Found {len(entries)} entries in images folder")

    for entry in entries:
        if entry[".tag"] != "file":
            continue
        filename = entry["name"]
        dest     = LOCAL_DIR / filename
        ext      = Path(filename).suffix.lower()

        if ext in IMAGE_EXTENSIONS:
            if not dest.exists():
                print(f"  Downloading image: {filename}")
                dropbox_download(entry["path_display"], dest)
            else:
                print(f"  Already exists: {filename}")

    # Pull _metadata_.json from json folder
    print(f"Syncing metadata from: {DROPBOX_JSON_FOLDER}")
    metadata_dest = LOCAL_DIR / "_metadata_.json"
    if not metadata_dest.exists():
        print(f"  Downloading _metadata_.json...")
        dropbox_download(f"{DROPBOX_JSON_FOLDER}/_metadata_.json", metadata_dest)
    else:
        print(f"  _metadata_.json already exists")

    # Pull goons_log.json if it exists
    try:
        log_dest = LOCAL_DIR / "goons_log.json"
        if not log_dest.exists():
            dropbox_download(f"{DROPBOX_FOLDER}/goons_log.json", log_dest)
            print(f"  Downloaded goons_log.json")
    except Exception:
        print(f"  No existing goons_log.json (first run)")

    print("Sync complete.")


def push_log_to_dropbox():
    local_log = LOCAL_DIR / "goons_log.json"
    if not local_log.exists():
        print("  No goons_log.json to push")
        return
    dropbox_path = f"{DROPBOX_FOLDER}/goons_log.json"
    print(f"  Pushing goons_log.json to Dropbox...")
    dropbox_upload(local_log, dropbox_path)
    print(f"  ✓ goons_log.json synced to Dropbox")


def archive_to_dropbox(local_video: Path, edition: int, goon_name: str):
    safe_name      = goon_name.replace('"', '').replace(' ', '_')
    archive_folder = f"{DROPBOX_FOLDER}/posted/{edition}_{safe_name}"

    if local_video.exists():
        dropbox_upload(local_video, f"{archive_folder}/{local_video.name}")
        print(f"  ✓ Video archived to Dropbox")

    for ext in IMAGE_EXTENSIONS:
        for candidate in [LOCAL_DIR / f"{str(edition).zfill(4)}{ext}", LOCAL_DIR / f"{edition}{ext}"]:
            if candidate.exists():
                dropbox_upload(candidate, f"{archive_folder}/{candidate.name}")
                print(f"  ✓ Source image archived to Dropbox")
                break

    print(f"  ✓ Goon #{edition} fully archived")


if __name__ == "__main__":
    sync_from_dropbox()
