"""
video_generator.py
Generates a background video clip via Runway Gen-3 API.
Uses the Imagine.art render as the seed image.
"""

import os
import time
import logging
import requests
from pathlib import Path
import base64

log = logging.getLogger(__name__)

RUNWAY_API_KEY = os.environ["RUNWAY_API_KEY"]
RUNWAY_BASE    = "https://api.dev.runwayml.com/v1"

VIDEO_PROMPT_TEMPLATE = (
    "Classified military briefing, outer rim space station interior, "
    "slow dramatic camera push toward {name}, {class_label} class operative, "
    "amber emergency lighting, holographic displays flickering, "
    "subtle smoke in atmosphere, cinematic villain aesthetic, "
    "ominous and authoritative, 9:16 vertical"
)

POLL_INTERVAL = 10   # seconds between status checks
MAX_WAIT      = 600  # 10 minutes max


def generate_runway_video(render_image: Path, name_data: dict, attributes: dict, output_path: Path):
    """
    Submit image + prompt to Runway Gen-3, poll until complete, download MP4.
    """
    prompt = VIDEO_PROMPT_TEMPLATE.format(
        name        = name_data["full_name"],
        class_label = name_data["class_label"],
    )

    log.info(f"  Submitting to Runway Gen-3...")
    log.info(f"  Prompt: {prompt[:80]}...")

    # Encode image as base64 data URI
    with open(render_image, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    image_uri = f"data:image/png;base64,{img_b64}"

    headers = {
        "Authorization": f"Bearer {RUNWAY_API_KEY}",
        "Content-Type":  "application/json",
        "X-Runway-Version": "2024-11-06",
    }

    payload = {
        "model":        "gen3a_turbo",
        "promptImage":  image_uri,
        "promptText":   prompt,
        "duration":     10,      # seconds — will be looped/trimmed in assembly
        "ratio":        "768:1344",  # 9:16 vertical
        "watermark":    False,
    }

    # Submit task
    resp = requests.post(
        f"{RUNWAY_BASE}/image_to_video",
        json=payload,
        headers=headers,
        timeout=60,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Runway submit error {resp.status_code}: {resp.text}")

    task_id = resp.json()["id"]
    log.info(f"  Runway task submitted: {task_id}")

    # Poll for completion
    elapsed = 0
    while elapsed < MAX_WAIT:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

        status_resp = requests.get(
            f"{RUNWAY_BASE}/tasks/{task_id}",
            headers=headers,
            timeout=30,
        )
        status_data = status_resp.json()
        status = status_data.get("status")
        log.info(f"  Runway status: {status} ({elapsed}s elapsed)")

        if status == "SUCCEEDED":
            video_url = status_data["output"][0]
            log.info(f"  Downloading Runway video...")
            video_resp = requests.get(video_url, timeout=120)
            output_path.write_bytes(video_resp.content)
            log.info(f"  ✓ Runway video saved: {output_path}")
            return

        if status in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Runway task {task_id} failed: {status_data}")

    raise TimeoutError(f"Runway task {task_id} timed out after {MAX_WAIT}s")
