"""
video_assembler.py
Assembles final 9:16 MP4:
  - Background video (fal.ai Seedance) looped
  - Goon render overlaid large (top portion)
  - Military text overlays (top + bottom)
  - SIGNAL LOST outro
  - Narration audio + SFX bookends
"""

import os
import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

FFMPEG = "ffmpeg"
FONT   = "assets/fonts/ShareTechMono-Regular.ttf"

TEXT_COLOR = "0xFFB300"
SCAN_COLOR = "0x00FF41"


def _ensure_wav(assets_dir: Path, stem: str) -> Path:
    wav_path = assets_dir / f"{stem}.wav"
    m4a_path = assets_dir / f"{stem}.m4a"
    if wav_path.exists():
        return wav_path
    if not m4a_path.exists():
        raise FileNotFoundError(f"Missing audio asset: {m4a_path}")
    log.info(f"  Converting {m4a_path.name} to WAV...")
    subprocess.run([
        FFMPEG, "-y", "-i", str(m4a_path),
        "-ar", "44100", "-ac", "2", str(wav_path)
    ], check=True, capture_output=True)
    return wav_path


def assemble_final_video(
    runway_clip: Path,
    narration: Path,
    render_image: Path,
    subtitle_lines: list,
    assets_dir: Path,
    output_path: Path,
    edition: int,
    name_data: dict,
):
    sfx_open = _ensure_wav(assets_dir, "transmission_open")
    sfx_lost = _ensure_wav(assets_dir, "signal_lost")

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", str(narration)],
        capture_output=True, text=True
    )
    narration_dur = float(json.loads(probe.stdout)["streams"][0]["duration"])
    total_dur = narration_dur + 3 + 2.5

    log.info(f"  Narration: {narration_dur:.1f}s | Total target: {total_dur:.1f}s")

    briefing_header = name_data.get("briefing_header", f"GOON #{edition}").upper()

    filter_complex = f"""
    [0:v]scale=1080:1920:force_original_aspect_ratio=increase,
         crop=1080:1920,
         loop=loop=-1:size=250:start=0,
         trim=duration={total_dur},
         setpts=PTS-STARTPTS,
         format=yuv420p
    [bg];
    [4:v]scale=900:-1,
         format=rgba,
         colorchannelmixer=aa=1.0
    [render_overlay];
    [bg][render_overlay]overlay=(W-w)/2:40:enable='between(t,3,{3+narration_dur})'
    [bg_with_render];
    [bg_with_render]
    drawtext=fontfile={FONT}:
             text='INCOMING TRANSMISSION':
             fontsize=28:fontcolor={TEXT_COLOR}: