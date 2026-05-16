"""
video_generator.py
Generates background video via fal.ai Seedance 2.0 image-to-video API.
"""
import os
import time
import logging
import requests
import base64
from pathlib import Path

log = logging.getLogger(__name__)

FAL_API_KEY = os.environ.get("FAL_API_KEY", "")
FAL_BASE    = "https://fal.run"

VIDEO_PROMPT_TEMPLATE = (
    "{name} the {class_label} class operative stands in a classified outer rim "
    "space station briefing room, dramatic camera slow push in, amber emergency "
    "lighting, holographic displays flickering around them, subtle atmospheric "
    "smoke, cinematic sci-fi aesthetic, 9:16 vertical portrait"
)


def upload_image_to_fal(image_path: Path) -> str:
    """Upload image to fal.ai storage and return public URL."""
    with open(image_path, "rb") as f:
        image_data = f.read()

    resp = requests.post(
        "https://fal.run/fal-ai/upload",
        headers={
            "Authorization": f"Key {FAL_API_KEY}",
            "Content-Type": "image/png",
        },
        data=image_data,
        timeout=60,
    )
    if not resp.ok:
        raise RuntimeError(f"fal upload error {resp.status_code}: {resp.text}")
    return resp.json()["url"]


def generate_runway_video(render_image: Path, name_data: dict, attributes: dict, output_path: Path):
    """
    Generate video via fal.ai Seedance 2.0 image-to-video.
    """
    prompt = VIDEO_PROMPT_TEMPLATE.format(
        name        = name_data["full_name"],
        class_label = name_data["class_label"],
    )

    log.info(f"  Uploading render to fal.ai...")
    image_url = upload_image_to_fal(render_image)
    log.info(f"  Image URL: {image_url}")

    log.info(f"  Submitting to Seedance 2.0...")
    log.info(f"  Prompt: {prompt[:80]}...")

    headers = {
        "Authorization": f"Key {FAL_API_KEY}",
        "Content-Type":  "application/json",
    }

    payload = {
        "prompt":         prompt,
        "image_url":      image_url,
        "resolution":     "720p",
        "duration":       "5",
        "aspect_ratio":   "9:16",
        "generate_audio": False,
    }

    resp = requests.post(
        f"{FAL_BASE}/bytedance/seedance-2.0/fast/image-to-video",
        json=payload,
        headers=headers,
        timeout=60,
    )

    if not resp.ok:
        raise RuntimeError(f"fal submit error {resp.status_code}: {resp.text}")

    result = resp.json()
    log.info(f"  fal response: {result}")

    video_url = result["video"]["url"]
    log.info(f"  Downloading video from fal...")
    video_resp = requests.get(video_url, timeout=120)
    output_path.write_bytes(video_resp.content)
    log.info(f"  Video saved: {output_path}")