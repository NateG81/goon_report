"""
video_generator.py
Generates background video via fal.ai Seedance 2.0 image-to-video API.
"""
import os
import logging
import requests
import fal_client
from pathlib import Path

log = logging.getLogger(__name__)

FAL_API_KEY = os.environ.get("FAL_API_KEY", "")

VIDEO_PROMPT_TEMPLATE = (
    "{name} the {class_label} class operative stands in a classified outer rim "
    "space station briefing room, dramatic slow camera push in, amber emergency "
    "lighting, holographic displays flickering, subtle atmospheric smoke, "
    "cinematic sci-fi, 9:16 vertical portrait"
)


def generate_runway_video(render_image: Path, name_data: dict, attributes: dict, output_path: Path):
    os.environ["FAL_KEY"] = FAL_API_KEY

    prompt = VIDEO_PROMPT_TEMPLATE.format(
        name        = name_data["full_name"],
        class_label = name_data["class_label"],
    )

    log.info(f"  Uploading render to fal.ai...")
    image_url = fal_client.upload_file(str(render_image))
    log.info(f"  Image URL: {image_url}")

    log.info(f"  Submitting to Seedance 2.0...")
    log.info(f"  Prompt: {prompt[:80]}...")

    result = fal_client.subscribe(
        "bytedance/seedance-2.0/fast/image-to-video",
        arguments={
            "prompt":         prompt,
            "image_url":      image_url,
            "resolution":     "720p",
            "duration":       "5",
            "aspect_ratio":   "9:16",
            "generate_audio": False,
        },
    )

    video_url = result["video"]["url"]
    log.info(f"  Downloading video from fal...")
    video_resp = requests.get(video_url, timeout=120)
    output_path.write_bytes(video_resp.content)
    log.info(f"  Video saved: {output_path}")