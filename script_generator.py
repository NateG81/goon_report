"""
script_generator.py
Calls Claude API to generate General V's villain briefing script.
Returns structured JSON with all script segments + caption.
"""

import os
import json
import logging
import anthropic

log = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

SYSTEM_PROMPT = """
You are the scriptwriter for General V, commander of the Galactic Goon forces.
General V delivers classified operative briefings about his Goons to assembled troops.
He is completely serious at all times. He never breaks character or acknowledges anything is funny.
The comedy comes entirely from the absurdity of what he describes, delivered with total military authority.

SCRIPT STRUCTURE — follow exactly:
1. open_fragment: A mid-sentence fragment implying the transmission joined mid-briefing.
   e.g. "—which is why Sector 4 no longer has a Tuesday."
   Must start with an em dash. 1-2 sentences max.

2. intro: Formal introduction of the operative. Full name (first, nickname in quotes, last),
   class, variant, signature accessory. Reference traits naturally and absurdly.
   2-3 sentences.

3. act_1: First documented act of galactic villainy. Absurd but specific.
   Include fake coordinates, dates, unit designations. Petty-to-weird scale.
   3-4 sentences.

4. act_2: Second act. Escalates in scale or weirdness. 3-4 sentences.

5. act_3: Third act. Most unhinged. Builds directly to the cutoff_line. 3-4 sentences.

6. cutoff_line: The final complete sentence General V speaks before the transmission cuts.
   This is the funniest, most unhinged line in the entire script.
   Must be a complete sentence. The hard signal cut happens immediately after.
   1 sentence only.

7. caption: Instagram/TikTok post caption. Include the full operative name and class.
   Tone: deadpan military, slightly unhinged. End with hashtags:
   #GoonGalaxy #GeneralV #OuterRim #GalacticGoons #ClassifiedBriefing #Villain

RULES:
- Never use the words "hilarious", "funny", "joke", or acknowledge comedy in any way.
- Always cite specific fake details: coordinates, stardate, unit names, planet names.
- Acts escalate: petty → weird → completely unhinged.
- Total read time when voiced: 15–20 seconds at normal speaking pace. Extremely tight and punchy — maximum impact, minimum words. Think movie trailer not documentary.
- General V refers to himself in third person occasionally: "This command considers..."
- DNA hash can be referenced as the operative's "biometric signature" or "trace code."

Return ONLY valid JSON. No markdown fences. No preamble. Keys:
open_fragment, intro, act_1, act_2, act_3, cutoff_line, caption
""".strip()

USER_PROMPT_TEMPLATE = """
Generate a General V briefing for this operative:

NAME: {full_name}
CLASS: {class_label}
VARIANT (eyes): {variant}
SIGNATURE (head accessory): {signature}
EDITION: #{edition}
DNA TRACE: {dna}
MOUTH TRAIT: {mouth}
NOSE TRAIT: {nose}
HEAD TRAIT: {head}
BODY TRAIT: {body}
ALL TRAITS: {traits_formatted}
""".strip()


def generate_briefing_script(name_data: dict, attributes: dict, dna: str, edition: int) -> dict:
    traits_formatted = ", ".join(f"{k}: {v}" for k, v in attributes.items())

    user_prompt = USER_PROMPT_TEMPLATE.format(
        full_name       = name_data["full_name"],
        class_label     = name_data["class_label"],
        variant         = name_data["variant"],
        signature       = name_data["signature"],
        edition         = edition,
        dna             = dna,
        mouth           = attributes.get("Mouth", "Unknown"),
        nose            = attributes.get("Nose", "Unknown"),
        head            = attributes.get("Head", "Unknown"),
        body            = attributes.get("Body", "Unknown"),
        traits_formatted= traits_formatted,
    )

    log.info("  Calling Claude API for briefing script...")
    message = client.messages.create(
        model      = "claude-sonnet-4-5",
        max_tokens = 1000,
        system     = SYSTEM_PROMPT,
        messages   = [{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if present (safety net)
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    for attempt in range(3):
        try:
            script_data = json.loads(raw)
            break
        except json.JSONDecodeError:
            if attempt < 2:
                log.warning(f"JSON parse failed (attempt {attempt+1}), retrying...")
                message = client.messages.create(
                    model      = "claude-sonnet-4-5",
                    max_tokens = 1500,
                    system     = SYSTEM_PROMPT,
                    messages   = [{"role": "user", "content": user_prompt}],
                )
                raw = message.content[0].text.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            else:
                raise
    required_keys = ["open_fragment","intro","act_1","act_2","act_3","cutoff_line","caption"]
    missing = [k for k in required_keys if k not in script_data]
    if missing:
        raise ValueError(f"Script JSON missing keys: {missing}")
    return script_data
