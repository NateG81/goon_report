"""
voice_generator.py
Generates General V's narration via ElevenLabs TTS API.
"""

import os
import logging
import requests
from pathlib import Path

log = logging.getLogger(__name__)

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID           = os.environ.get("ELEVENLABS_VOICE_ID", "")  # General V's voice ID from ElevenLabs
BASE_URL           = "https://api.elevenlabs.io/v1"

VOICE_SETTINGS = {
    "stability":         0.45,   # Slight instability = more character/unhinged energy
    "similarity_boost":  0.85,
    "style":             0.30,   # Style exaggeration — bump up for more dramatic delivery
    "use_speaker_boost": True,
}


def generate_narration(script_text: str, output_path: Path):
    """
    Send script text to ElevenLabs and save as MP3.
    Converts M4A SFX assets are handled separately in video_assembler.py.
    """
    log.info(f"  Sending {len(script_text)} chars to ElevenLabs (voice: {VOICE_ID})...")

    url = f"{BASE_URL}/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key":   ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept":       "audio/mpeg",
    }
    payload = {
        "text":           script_text,
        "model_id":       "eleven_multilingual_v2",
        "voice_settings": VOICE_SETTINGS,
    }

    response = requests.post(url, json=payload, headers=headers, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(
            f"ElevenLabs error {response.status_code}: {response.text}"
        )

    output_path.write_bytes(response.content)
    log.info(f"  ✓ Narration saved: {output_path} ({len(response.content) // 1024}KB)")
