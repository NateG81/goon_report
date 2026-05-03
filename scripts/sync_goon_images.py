"""
scripts/sync_goon_images.py
Downloads Goon images from Cloudinary to the local ./goons/ folder
so the GitHub Actions runner has access to them.

Store your images in Cloudinary under folder: goon-galaxy/goons/
Named by edition number: 0001.png, 0042.png etc.
The _metadata_.json should also be stored there.
"""

import os
import json
import requests
import hashlib
from pathlib import Path

CLOUD_NAME = os.environ["CLOUDINARY_CLOUD_NAME"]
API_KEY    = os.environ["CLOUDINARY_API_KEY"]
API_SECRET = os.environ["CLOUDINARY_API_SECRET"]

GOONS_FOLDER = "goon-galaxy/goons"
LOCAL_DIR    = Path("./goons")
LOCAL_DIR.mkdir(exist_ok=True)


def cloudinary_list_resources(folder: str) -> list:
    """List all resources in a Cloudinary folder."""
    url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/resources/image"
    resp = requests.get(
        url,
        auth=(API_KEY, API_SECRET),
        params={
            "type":        "upload",
            "prefix":      folder,
            "max_results": 500,
        },
    )
    resp.raise_for_status()
    return resp.json().get("resources", [])


def download_file(url: str, dest: Path):
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def main():
    print(f"Syncing from Cloudinary folder: {GOONS_FOLDER}")
    resources = cloudinary_list_resources(GOONS_FOLDER)
    print(f"Found {len(resources)} resources")

    for resource in resources:
        filename = resource["public_id"].split("/")[-1]
        ext      = resource["format"]
        dest     = LOCAL_DIR / f"{filename}.{ext}"

        if not dest.exists():
            print(f"  Downloading: {dest.name}")
            download_file(resource["secure_url"], dest)
        else:
            print(f"  Already exists: {dest.name}")

    # Also download metadata JSON (stored as raw file in Cloudinary)
    metadata_dest = LOCAL_DIR / "_metadata_.json"
    if not metadata_dest.exists():
        meta_url = f"https://res.cloudinary.com/{CLOUD_NAME}/raw/upload/{GOONS_FOLDER}/_metadata_.json"
        print(f"  Downloading _metadata_.json...")
        download_file(meta_url, metadata_dest)

    print("Sync complete.")


if __name__ == "__main__":
    main()
