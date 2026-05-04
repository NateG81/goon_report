"""
General V — Galactic Goon Content Pipeline
==========================================
Stages:
  1. Pick next unprocessed Goon image from Obsidian vault
  2. Load NFT metadata from individual JSON file
  3. Generate operative name (deterministic from traits)
  4. Imagine.art Image Remix → cinematic villain render
  5. Claude API → General V briefing script (JSON)
  6. ElevenLabs → narration MP3
  7. Runway → background video clip
  8. FFmpeg → assemble final 9:16 MP4 with bookends + subtitles
  9. Post to Instagram Reels + TikTok
  10. Archive to Dropbox
"""

import os
import sys
import json
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime

from goon_namer import generate_goon_name
from imagine_render import render_goon_image
from script_generator import generate_briefing_script
from voice_generator import generate_narration
from video_generator import generate_runway_video
from video_assembler import assemble_final_video
from social_poster import post_to_instagram, post_to_tiktok
from goon_log import get_next_goon, mark_goon_posted

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
OBSIDIAN_GOONS_PATH = Path(os.environ["OBSIDIAN_GOONS_PATH"]).expanduser()
OUTPUT_DIR          = Path("output")
ASSETS_DIR          = Path("assets")
OUTPUT_DIR.mkdir(exist_ok=True)
DRY_RUN             = os.environ.get("DRY_RUN", "false").lower() == "true"


def run():
    log.info("═══ General V Pipeline Starting ═══")
    if DRY_RUN:
        log.info("DRY RUN MODE — social posting will be skipped")

    # ── Stage 1: Pick next Goon ──────────────────────────────────────────────
    log.info("Stage 1: Picking next unprocessed Goon...")
    goon_image_path, edition_number = get_next_goon(OBSIDIAN_GOONS_PATH)
    if not goon_image_path:
        log.error("No unprocessed Goons found.")
        sys.exit(1)
    log.info(f"  → Selected: {goon_image_path.name} (Edition #{edition_number})")

    # ── Stage 2: Load metadata ───────────────────────────────────────────────
    log.info("Stage 2: Loading NFT metadata...")
    goon_json_path = OBSIDIAN_GOONS_PATH / f"{edition_number}.json"
    if not goon_json_path.exists():
        log.error(f"No metadata JSON found: {goon_json_path}")
        sys.exit(1)
    with open(goon_json_path) as f:
        metadata = json.load(f)

    attributes = {a["trait_type"]: a["value"].strip() for a in metadata.get("attributes", [])}
    log.info(f"  → Traits loaded: {attributes}")

    # ── Stage 3: Generate operative name ─────────────────────────────────────
    log.info("Stage 3: Generating operative name...")
    dna = metadata.get("custom_fields", {}).get("dna", "")
    name_data = generate_goon_name(edition_number, attributes, dna)
    log.info(f"  → {name_data['briefing_header']}")

    # ── Stage 4: Imagine.art render ──────────────────────────────────────────
    log.info("Stage 4: Rendering via Imagine.art...")
    render_path = OUTPUT_DIR / f"goon_{edition_number}_render.png"
    render_goon_image(goon_image_path, name_data, attributes, render_path)
    log.info(f"  → Render saved: {render_path}")

    # ── Stage 5: Generate briefing script ────────────────────────────────────
    log.info("Stage 5: Generating General V briefing script...")
    script_data = generate_briefing_script(name_data, attributes, dna, edition_number)
    script_path = OUTPUT_DIR / f"goon_{edition_number}_script.json"
    with open(script_path, "w") as f:
        json.dump(script_data, f, indent=2)
    log.info(f"  → Script saved: {script_path}")
    log.info(f"  → Cutoff line: {script_data['cutoff_line']}")

    # ── Stage 6: ElevenLabs narration ────────────────────────────────────────
    log.info("Stage 6: Generating voice narration...")
    narration_path = OUTPUT_DIR / f"goon_{edition_number}_narration.mp3"
    full_script_text = " ".join([
        script_data["open_fragment"],
        script_data["intro"],
        script_data["act_1"],
        script_data["act_2"],
        script_data["act_3"],
        script_data["cutoff_line"],
    ])
    generate_narration(full_script_text, narration_path)
    log.info(f"  → Narration saved: {narration_path}")

    # ── Stage 7: Runway background video ─────────────────────────────────────
    log.info("Stage 7: Generating Runway background video...")
    runway_path = OUTPUT_DIR / f"goon_{edition_number}_runway.mp4"
    generate_runway_video(render_path, name_data, attributes, runway_path)
    log.info(f"  → Runway clip saved: {runway_path}")

    # ── Stage 8: FFmpeg assembly ──────────────────────────────────────────────
    log.info("Stage 8: Assembling final video...")
    final_path = OUTPUT_DIR / f"goon_{edition_number}_final.mp4"
    subtitle_lines = [
        script_data["open_fragment"],
        script_data["intro"],
        script_data["act_1"],
        script_data["act_2"],
        script_data["act_3"],
        script_data["cutoff_line"],
    ]
    assemble_final_video(
        runway_clip=runway_path,
        narration=narration_path,
        render_image=render_path,
        subtitle_lines=subtitle_lines,
        assets_dir=ASSETS_DIR,
        output_path=final_path,
        edition=edition_number,
        name_data=name_data,
    )
    log.info(f"  → Final video: {final_path}")

    # ── Stage 9: Post to social ──────────────────────────────────────
