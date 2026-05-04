"""
social_poster.py
Posts the final MP4 to Instagram Reels and TikTok.

Instagram: Meta Graph API (container → publish flow)
TikTok:    Content Posting API v2 (direct post flow)
"""

import os
import time
import logging
import requests
from pathlib import Path

log = logging.getLogger(__name__)

# ── Instagram ──────────────────────────────────────────────────────────────────
IG_USER_ID    = os.environ.get("INSTAGRAM_USER_ID", "")
IG_TOKEN      = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
IG_API_BASE   = "https://graph.facebook.com/v19.0"

# ── TikTok ─────────────────────────────────────────────────────────────────────
TIKTOK_TOKEN  = os.environ.get("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_BASE   = "https://open.tiktokapis.com/v2"

# ── Cloudinary (for video hosting — required by Instagram Graph API) ───────────
CLOUDINARY_URL       = os.environ.get("CLOUDINARY_URL")          # optional fallback
CLOUDINARY_UPLOAD_URL = os.environ.get("CLOUDINARY_UPLOAD_PRESET_URL")  # upload preset URL


def _upload_to_cloudinary(video_path: Path) -> str:
    """
    Upload video to Cloudinary and return public HTTPS URL.
    Instagram Graph API requires a publicly accessible URL for Reels upload.
    """
    log.info("  Uploading to Cloudinary for public URL...")
    with open(video_path, "rb") as f:
        resp = requests.post(
            CLOUDINARY_UPLOAD_URL,
            files={"file": f},
            data={"resource_type": "video"},
            timeout=300,
        )
    if resp.status_code != 200:
        raise RuntimeError(f"Cloudinary upload failed: {resp.text}")
    url = resp.json()["secure_url"]
    log.info(f"  ✓ Cloudinary URL: {url}")
    return url


# ── Instagram ──────────────────────────────────────────────────────────────────

def post_to_instagram(video_path: Path, caption: str):
    """
    Post video as an Instagram Reel using Meta Graph API.
    Requires video to be at a public URL (uploaded to Cloudinary).
    """
    video_url = _upload_to_cloudinary(video_path)

    # Step 1 — Create media container
    log.info("  Creating Instagram Reels container...")
    container_resp = requests.post(
        f"{IG_API_BASE}/{IG_USER_ID}/media",
        params={
            "media_type":   "REELS",
            "video_url":    video_url,
            "caption":      caption,
            "share_to_feed": "true",
            "access_token": IG_TOKEN,
        },
        timeout=60,
    )
    if container_resp.status_code != 200:
        raise RuntimeError(f"IG container error: {container_resp.text}")
    container_id = container_resp.json()["id"]
    log.info(f"  Container ID: {container_id}")

    # Step 2 — Poll until container is ready
    log.info("  Waiting for Instagram to process video...")
    for attempt in range(30):
        time.sleep(10)
        status_resp = requests.get(
            f"{IG_API_BASE}/{container_id}",
            params={
                "fields":       "status_code,status",
                "access_token": IG_TOKEN,
            },
        )
        status = status_resp.json().get("status_code")
        log.info(f"  IG status: {status} (attempt {attempt+1})")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError(f"Instagram processing error: {status_resp.json()}")
    else:
        raise TimeoutError("Instagram video processing timed out")

    # Step 3 — Publish
    log.info("  Publishing Instagram Reel...")
    publish_resp = requests.post(
        f"{IG_API_BASE}/{IG_USER_ID}/media_publish",
        params={
            "creation_id":  container_id,
            "access_token": IG_TOKEN,
        },
        timeout=30,
    )
    if publish_resp.status_code != 200:
        raise RuntimeError(f"IG publish error: {publish_resp.text}")
    post_id = publish_resp.json()["id"]
    log.info(f"  ✓ Instagram Reel posted: {post_id}")


# ── TikTok ─────────────────────────────────────────────────────────────────────

def post_to_tiktok(video_path: Path, caption: str):
    """
    Post video to TikTok using Content Posting API v2.
    Uses FILE_UPLOAD method (direct upload, no public URL needed).
    """
    file_size = video_path.stat().st_size

    # Step 1 — Initialize upload
    log.info("  Initializing TikTok upload...")
    init_resp = requests.post(
        f"{TIKTOK_BASE}/post/publish/video/init/",
        headers={
            "Authorization": f"Bearer {TIKTOK_TOKEN}",
            "Content-Type":  "application/json; charset=UTF-8",
        },
        json={
            "post_info": {
                "title":        caption[:2200],  # TikTok caption limit
                "privacy_level": "SELF_ONLY",    # Change to PUBLIC_TO_EVERYONE when ready
                "disable_duet":  False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source":           "FILE_UPLOAD",
                "video_size":       file_size,
                "chunk_size":       file_size,   # single chunk for files < 64MB
                "total_chunk_count": 1,
            },
        },
        timeout=30,
    )
    if init_resp.status_code != 200:
        raise RuntimeError(f"TikTok init error: {init_resp.text}")

    init_data   = init_resp.json()["data"]
    publish_id  = init_data["publish_id"]
    upload_url  = init_data["upload_url"]
    log.info(f"  TikTok publish ID: {publish_id}")

    # Step 2 — Upload video bytes
    log.info("  Uploading video to TikTok...")
    with open(video_path, "rb") as f:
        video_bytes = f.read()

    upload_resp = requests.put(
        upload_url,
        data=video_bytes,
        headers={
            "Content-Type":   "video/mp4",
            "Content-Length": str(file_size),
            "Content-Range":  f"bytes 0-{file_size-1}/{file_size}",
        },
        timeout=300,
    )
    if upload_resp.status_code not in (200, 201, 206):
        raise RuntimeError(f"TikTok upload error {upload_resp.status_code}: {upload_resp.text}")

    # Step 3 — Poll publish status
    log.info("  Waiting for TikTok to process...")
    for attempt in range(20):
        time.sleep(10)
        status_resp = requests.post(
            f"{TIKTOK_BASE}/post/publish/status/fetch/",
            headers={
                "Authorization": f"Bearer {TIKTOK_TOKEN}",
                "Content-Type":  "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id},
            timeout=30,
        )
        status_data = status_resp.json().get("data", {})
        status = status_data.get("status")
        log.info(f"  TikTok status: {status} (attempt {attempt+1})")
        if status == "PUBLISH_COMPLETE":
            log.info(f"  ✓ TikTok post published: {publish_id}")
            return
        if status in ("FAILED", "SPAM_RISK_TOO_MANY_PENDING_SHARE"):
            raise RuntimeError(f"TikTok failed: {status_data}")

    raise TimeoutError("TikTok publish timed out")
