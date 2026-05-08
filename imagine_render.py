cat > imagine_render.py << 'ENDOFFILE'
"""
imagine_render.py
Sends the Goon source image to OpenAI gpt-image-1 for cinematic villain render.
"""

import os
import logging
import base64
from pathlib import Path
from openai import OpenAI

log = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

RENDER_PROMPT_TEMPLATE = (
    "Transform this character into a cinematic 3D villain render. "
    "Maintain the character exact proportions, design, and color palette. "
    "Render in volumetric 3D form with PBR shaders, subsurface scattering on skin, "
    "subtle cel shading outlines preserved. Teal alien skin texture, "
    "magenta mouth and ear details, purple space armor with magenta trim. "
    "Keep exaggerated cartoon proportions. Dramatic space nebula background, "
    "cinematic lighting with rim light, high detail character portrait. "
    "{class_label} class operative, sinister outer rim villain. "
    "Vertical 9:16 portrait composition."
)


def render_goon_image(source_image: Path, name_data: dict, attributes: dict, output_path: Path):
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")

    prompt = RENDER_PROMPT_TEMPLATE.format(
        class_label=name_data["class_label"],
    )

    log.info(f"  Sending to OpenAI gpt-image-1: {source_image.name}")
    log.info(f"  Prompt: {prompt[:80]}...")

    client = OpenAI(api_key=OPENAI_API_KEY)

    with open(source_image, "rb") as img_file:
        result = client.images.edit(
            model="gpt-image-1",
            image=img_file,
            prompt=prompt,
            size="1024x1536",
            quality="high",
        )

    image_b64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_b64)
    output_path.write_bytes(image_bytes)
    log.info(f"  Render saved: {output_path} ({len(image_bytes) // 1024}KB)")
ENDOFFILE