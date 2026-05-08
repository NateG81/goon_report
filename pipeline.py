"""
General V — Galactic Goon Content Pipeline
"""

import os
import sys
import json
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime

print("PIPELINE STARTING", flush=True)

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

OBSIDIAN_GOONS_PATH = Path(os.environ["OBSIDIAN_GOONS_PATH"]).expanduser()
OUTPUT_DIR          = Path("output")
ASSETS_DIR          = Path("assets")
OUTPUT_DIR.mkdir(exist_ok=True)
DRY_RUN             = os.environ.get("DRY_RUN", "false").lower() == "true"


def run():
    log.info("General V Pipeline Starting")
    if DRY_RUN:
        log.info("DRY RUN MODE")

    log.info("Stage 1: Picking next unprocessed Goon...")
    goon_image_path, edition_number = get_next_goon(OBSIDIAN_GOONS_PATH)
    if not goon_image_path:
        log.error("No unprocessed Goons found.")
        sys.exit(1)
    log.info(f"Selected: {goon_image_path.name} Edition {edition_number}")

    log.info("Stage 2: Loading NFT metadata...")
    goon_json_path = OBSIDIAN_GOONS_PATH / f"{edition_number}.json"
    if not goon_json_path.exists():
        log.error(f"No metadata JSON found: {goon_json_path}")
        sys.exit(1)
    with open(goon_json_path) as f:
        metadata = json.load(f)

    attributes = {a["trait_type"]: a["value"].strip() for a in metadata.get("attributes", [])}
    log.info(f"Traits loaded: {attributes}")

    log.info("Stage 3: Generating operative name...")
    dna = metadata.get("custom_fields", {}).get("dna", "")
    name_data = generate_goon_name(edition_number, attributes, dna)
    log.info(f"Name: {name_data['briefing_header']}")

    log.info("Stage 4: Rendering via OpenAI...")
    render_path = OUTPUT_DIR / f"goon_{edition_number}_render.png"
    render_goon_image(goon_image_path, name_data, attributes, render_path)
    log.info(f"Render saved: {render_path}")

    log.info("Stage 5: Generating briefing script...")
    script_data = generate_briefing_script(name_data, attributes, dna, edition_number)
    script_path = OUTPUT_DIR / f"goon_{edition_number}_script.json"
    with open(script_path, "w") as f:
        json.dump(script_data, f, indent=2)
    log.info(f"Script saved: {script_path}")

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
    log.info(f"Narration saved: {narration_path}")

    log.info("Stage 7: Generating Runway background video...")
    runway_path = OUTPUT_DIR / f"goon_{edition_number}_runway.mp4"
    generate_runway_video(render_path, name_data, attributes, runway_path)
    log.info(f"Runway clip saved: {runway_path}")

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
    log.info(f"Final video: {final_path}")

    caption = script_data.get("caption", f"{name_data['briefing_header']} #GoonGalaxy #GeneralV")

    if DRY_RUN:
        log.info("Stage 9: DRY RUN - skipping social posting")
    else:
        log.info("Stage 9a: Posting to Instagram...")
        post_to_instagram(final_path, caption)
        log.info("Stage 9b: Posting to TikTok...")
        post_to_tiktok(final_path, caption)

    mark_goon_posted(OBSIDIAN_GOONS_PATH, edition_number, name_data["full_name"])

    log.info("Stage 10: Archiving to Dropbox...")
    from scripts.sync_goon_images import archive_to_dropbox, push_log_to_dropbox
    archive_to_dropbox(final_path, edition_number, name_data["full_name"])
    push_log_to_dropbox()

    log.info(f"Pipeline complete: {name_data['full_name']} posted")


if __name__ == "__main__":
    run()
