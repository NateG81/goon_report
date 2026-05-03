"""
imagine_render.py
Sends the Goon's source image to Imagine.art Image Remix API
and downloads the cinematic villain render.
API docs: https://docs.imagine.art
"""

import os
import time
import logging
import requests
from pathlib import Path

log = logging.getLogger(__name__)

IMAGINE_API_KEY  = os.environ["IMAGINE_API_KEY"]
IMAGINE_BASE_URL = "https://api.vyro.ai/v2"

# Style prompt template — tuned for General V's aesthetic
# Derived from: source NFT → Midjourney volumetric 3D render test
# Key findings: subsurface scattering sells the alien skin; cel shading must be
# explicitly named to survive the 3D conversion; exaggerated proportions
# need reinforcing or the model normalises them toward realism.
RENDER_PROMPT_TEMPLATE = (
    "maintain character proportions and design exactly, "
    "render in volumetric 3D form, PBR shaders with subsurface scattering on skin, "
    "subtle cel shading outlines preserved, "
    "teal alien skin texture, magenta mouth and ear details, "
    "purple space armor with magenta trim, "
    "keep exaggerated cartoon proportions, "
    "dramatic space nebula background, "
    "cinematic lighting with rim light, "
    "high detail character portrait, "
    "{class_label} class operative, sinister outer rim villain"
)

ASPECT_RATIO = "9:16"  # Vertical for Reels/TikTok


def render_goon_image(source_image: Path, name_data: dict, attributes: dict, output_path: Path):
    """
    Remix the source Goon image into a cinematic villain render via Imagine.art.
    Saves result PNG to output_path.
    """
    prompt = RENDER_PROMPT_TEMPLATE.format(
        class_label=name_data["class_label"],
        variant=name_data["variant"],
        nickname=name_data["nickname"],
    )

    log.info(f"  Sending to Imagine.art: {source_image.name}")
    log.info(f"  Prompt: {prompt[:80]}...")

    headers = {
        "Authorization": f"Bearer {IMAGINE_API_KEY}",
    }

    with open(source_image, "rb") as img_file:
        files  = {"image": (source_image.name, img_file, "image/png")}
        data   = {
            "prompt":       prompt,
            "aspect_ratio": ASPECT_RATIO,
            "strength":     "0.7",   # 0=preserve original, 1=ignore. 0.7 confirmed working in test render
            # style_id omitted — prompt alone produces correct comic book output
        }
        response = requests.post(
            f"{IMAGINE_BASE_URL}/image/remix",
            headers=headers,
            files=files,
            data=data,
            timeout=120,
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Imagine.art API error {response.status_code}: {response.text}"
        )

    # Response is binary image data
    output_path.write_bytes(response.content)
    log.info(f"  ✓ Render saved: {output_path} ({len(response.content) // 1024}KB)")
