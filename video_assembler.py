"""
video_assembler.py
Assembles the final 9:16 MP4 using FFmpeg.

Structure:
  [TRANSMISSION BOOT]  3 sec — static burst + military lower-thirds, no narration
  [MID-SENTENCE SNAP]  narration starts, Runway video begins
  [THE BRIEFING]       full narration plays over Runway background + render overlay
  [SIGNAL LOST OUTRO]  hard cut to static + SIGNAL LOST text, 2.5 sec

SFX files expected in assets/:
  transmission_open.m4a  — static burst / comms open sound
  signal_lost.m4a        — static wash for the outro
  (both auto-converted to .wav on first run)
"""

import os
import logging
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

FFMPEG = "ffmpeg"
FONT   = "assets/fonts/ShareTechMono-Regular.ttf"  # monospace military font

# Military green-amber palette
TEXT_COLOR  = "0xFFB300"   # amber
SCAN_COLOR  = "0x00FF41"   # matrix green (for SIGNAL LOST)
BG_COLOR    = "0x000000"   # black


def _convert_sfx(m4a_path: Path) -> Path:
    """Convert M4A to WAV once, cache the result."""
    wav_path = m4a_path.with_suffix(".wav")
    if not wav_path.exists():
        log.info(f"  Converting {m4a_path.name} → WAV...")
        subprocess.run([
            FFMPEG, "-y", "-i", str(m4a_path),
            "-ar", "44100", "-ac", "2",
            str(wav_path)
        ], check=True, capture_output=True)
    return wav_path


def _make_subtitle_srt(subtitle_lines: list, narration_duration: float, output_path: Path):
    """Generate a simple SRT file from script lines."""
    # Distribute lines evenly across narration duration (rough approximation)
    n = len(subtitle_lines)
    segment = narration_duration / n
    with open(output_path, "w") as f:
        for i, line in enumerate(subtitle_lines):
            start = i * segment
            end   = (i + 1) * segment
            f.write(f"{i+1}\n")
            f.write(f"{_ts(start)} --> {_ts(end)}\n")
            f.write(f"{line}\n\n")


def _ts(seconds: float) -> str:
    """Convert seconds to SRT timestamp format."""
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def _get_duration(path: Path) -> float:
    """Get media duration in seconds via ffprobe."""
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ], capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def assemble_final_video(
    runway_clip:    Path,
    narration:      Path,
    render_image:   Path,
    subtitle_lines: list,
    assets_dir:     Path,
    output_path:    Path,
    edition:        int,
    name_data:      dict,
):
    narration_dur = _get_duration(narration)
    total_dur     = narration_dur + 3.0 + 2.5  # boot(3) + narration + outro(2.5)

    log.info(f"  Narration: {narration_dur:.1f}s | Total target: {total_dur:.1f}s")

    # Convert SFX from M4A → WAV
    sfx_open   = _convert_sfx(assets_dir / "transmission_open.m4a")
    sfx_lost   = _convert_sfx(assets_dir / "signal_lost.m4a")

    # Subtitle SRT
    srt_path = output_path.with_suffix(".srt")
    _make_subtitle_srt(subtitle_lines, narration_dur, srt_path)

    briefing_header = name_data["briefing_header"].upper()
    class_label     = name_data["class_label"].upper()

    # ── Build FFmpeg filter graph ────────────────────────────────────────────
    # Inputs:
    #   [0] runway_clip       background video (looped to fill narration duration)
    #   [1] narration         ElevenLabs MP3
    #   [2] sfx_open          transmission open WAV (3s)
    #   [3] sfx_lost          signal lost WAV (2.5s)
    #   [4] render_image      Goon render PNG (shown as overlay in corner)

    filter_complex = f"""
    [0:v]scale=1080:1920:force_original_aspect_ratio=increase,
         crop=1080:1920,
         loop=loop=-1:size=250:start=0,
         trim=duration={total_dur},
         setpts=PTS-STARTPTS,
         format=yuv420p
    [bg];

    [4:v]scale=320:320,
         format=rgba,
         colorchannelmixer=aa=0.85
    [render_overlay];

    [bg][render_overlay]overlay=W-w-20:H-h-120:enable='between(t,3,{3+narration_dur})'
    [bg_with_render];

    [bg_with_render]
    drawtext=fontfile={FONT}:
             text='INCOMING TRANSMISSION':
             fontsize=28:fontcolor={TEXT_COLOR}:
             x=(w-text_w)/2:y=180:
             enable='between(t,0.5,3)':
             box=1:boxcolor=black@0.6:boxborderw=8,

    drawtext=fontfile={FONT}:
             text='CLASSIFICATION\\: EYES ONLY':
             fontsize=22:fontcolor={TEXT_COLOR}:
             x=(w-text_w)/2:y=230:
             enable='between(t,1.0,3)':
             box=1:boxcolor=black@0.6:boxborderw=6,

    drawtext=fontfile={FONT}:
             text='SECTOR 7 · OUTER RIM COMMAND':
             fontsize=18:fontcolor={TEXT_COLOR}@0.8:
             x=(w-text_w)/2:y=268:
             enable='between(t,1.5,3)':
             box=1:boxcolor=black@0.5:boxborderw=4,

    drawtext=fontfile={FONT}:
             text='DECRYPTING... ████████ 100\\%':
             fontsize=18:fontcolor={TEXT_COLOR}@0.7:
             x=(w-text_w)/2:y=306:
             enable='between(t,2.0,3)':
             box=1:boxcolor=black@0.5:boxborderw=4,

    drawtext=fontfile={FONT}:
             text='{briefing_header}':
             fontsize=22:fontcolor={TEXT_COLOR}:
             x=30:y=H-130:
             enable='between(t,3,{3+narration_dur})':
             box=1:boxcolor=black@0.7:boxborderw=6,

    drawtext=fontfile={FONT}:
             text='● LIVE TRANSMISSION':
             fontsize=18:fontcolor=red@0.9:
             x=30:y=H-90:
             enable='between(t,3,{3+narration_dur})',

    drawtext=fontfile={FONT}:
             text='[ SIGNAL LOST ]':
             fontsize=52:fontcolor={SCAN_COLOR}:
             x=(w-text_w)/2:y=(h-text_h)/2-40:
             enable='between(t,{3+narration_dur},{total_dur})',

    drawtext=fontfile={FONT}:
             text='TRANSMISSION TERMINATED — CAUSE\\: UNKNOWN':
             fontsize=22:fontcolor={SCAN_COLOR}@0.8:
             x=(w-text_w)/2:y=(h-text_h)/2+40:
             enable='between(t,{3+narration_dur+0.3},{total_dur})',

    subtitles={srt_path}:force_style='FontName=Share Tech Mono,FontSize=20,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2,Alignment=2,MarginV=60'

    [vout];

    [2:a]atrim=duration=3,asetpts=PTS-STARTPTS[sfx_intro];
    [1:a]adelay=3000|3000[narr_delayed];
    [3:a]adelay={int((3+narration_dur)*1000)}|{int((3+narration_dur)*1000)},
         atrim=duration=2.5,asetpts=PTS-STARTPTS[sfx_outro_delayed];

    [sfx_intro][narr_delayed][sfx_outro_delayed]
    amix=inputs=3:duration=longest:normalize=0
    [aout]
    """.replace("\n", "").replace("    ", "")

    cmd = [
        FFMPEG, "-y",
        "-i",          str(runway_clip),     # [0] video
        "-i",          str(narration),       # [1] narration
        "-i",          str(sfx_open),        # [2] transmission open sfx
        "-i",          str(sfx_lost),        # [3] signal lost sfx
        "-i",          str(render_image),    # [4] goon render PNG
        "-filter_complex", filter_complex,
        "-map",        "[vout]",
        "-map",        "[aout]",
        "-c:v",        "libx264",
        "-preset",     "fast",
        "-crf",        "23",
        "-c:a",        "aac",
        "-b:a",        "192k",
        "-t",          str(total_dur),
        "-movflags",   "+faststart",
        str(output_path),
    ]

    log.info("  Running FFmpeg assembly...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        log.error(f"FFmpeg stderr:\n{result.stderr[-3000:]}")
        raise RuntimeError(f"FFmpeg failed with code {result.returncode}")

    log.info(f"  ✓ Final video assembled: {output_path}")
