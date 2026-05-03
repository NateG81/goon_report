"""
goon_namer.py
Generates a deterministic three-part operative name from NFT traits + DNA hash.
Format: {First} "{Nickname}" {Last}
  e.g.  Nurble "The Hole Poker" Staarbyington
"""

import hashlib


# ── First name tables (by Body class) ─────────────────────────────────────────
FIRST_NAMES = {
    "Infiltrator":    ["Blumph", "Nurble", "Dobbix", "Flantz", "Glumph", "Squibble", "Wormsby", "Gruntle"],
    "Gunner":         ["Kraggo", "Bludge", "Wumbo",  "Dorko",  "Torff",  "Blasto",   "Kaboodle","Spronk"],
    "Brawler":        ["Grunk",  "Smudge", "Brolly", "Rumpf",  "Thwump", "Bonko",    "Wallop",  "Clonk"],
    "Raid Master":    ["Pilf",   "Skagg",  "Razzle", "Vobb",   "Plonk",  "Snatch",   "Grabbo",  "Lurcho"],
    "Toxic Don":      ["Mould",  "Phlurb", "Slurge", "Nurk",   "Drebb",  "Oozer",    "Seepworth","Drippo"],
    "Exo Dark":       ["Nullb",  "Wexle",  "Crypt",  "Shlorb", "Obvix",  "Darko",    "Skulko",  "Vexle"],
    "Engineer Pink":  ["Sprintz","Clonk",  "Duzzle", "Prink",  "Mekko",  "Bolty",    "Cogsworth","Fizbit"],
    "Engineer Orange":["Klink",  "Wrencho","Boltie",  "Fizbit", "Sprockett","Gearby", "Clank",   "Ratchet"],
    "Security":       ["Warde",  "Bludgeon","Stalko", "Vigg",   "Krubb",  "Thump",    "Blocko",  "Stopper"],
    "DEFAULT":        ["Zoggle", "Blarg",  "Skrunt", "Nulbo",  "Wurple", "Floob",    "Gruntle", "Slobbo"],
}

# ── Nickname tables (by Mouth, then Nose as fallback) ─────────────────────────
NICKNAMES = {
    # Mouth-based
    "Furnacemouth": ["The Scorcher",   "Hot Gob",       "Throat of Doom",  "The Burner",    "Char Breath"],
    "Sphincter":    ["The Closer",     "No Entry",       "The Seal",        "Door Policy",   "The Pucker"],
    "Nasty":        ["The Unpleasant", "Bad Vibes",      "Foul Regards",    "The Wretched",  "Off-Putting"],
    "Wide grin":    ["Grin Reaper",    "Too Many Teeth", "The Smiler",      "Perpetual",     "Dental Issue"],
    "MuzzleLip":    ["The Muzzle",     "Snout Life",     "Lip Service",     "The Jowl",      "Face First"],
    "Bubbs":        ["The Blubber",    "Glob",           "Burp Master",     "The Splat",     "Wet Regards"],
    "Tude":         ["The Attitude",   "Sass Master",    "Chronic Snark",   "The Eyeroll",   "Difficult"],
    # Nose-based fallbacks
    "Tubes":        ["The Nostril",    "Pipe Dream",     "Intake",          "The Sniffer",   "Tube Life"],
    "Vamp":         ["The Biter",      "Two Points",     "The Puncture",    "Fang Adjacent", "Light Snack"],
    "Beaker":       ["The Chemist",    "Beaky",          "Lab Results",     "The Specimen",  "Erlenmeyer"],
    "Broad":        ["The Wide One",   "Panoramic",      "Big Sniff",       "Generous",      "Broad Strokes"],
    "Trislit":      ["Triple Threat",  "The Trident",    "Slit Decision",   "Three Way",     "Nostrils³"],
    "Shnoodle":     ["The Noodle",     "Bendy",          "The Shnook",      "Wobbly",        "Flexible"],
    "FurnaceNose":  ["Hot Intake",     "Nasal Inferno",  "The Singed",      "Smoke Nose",    "The Sniffer"],
    "DEFAULT":      ["The Mysterious", "Various Crimes", "The One",         "Pending",       "Unknown Reasons"],
}

# ── Last name tables (by Eyes) ─────────────────────────────────────────────────
LAST_NAMES = {
    "MadEye":      ["Skaggsworth",    "Glarkinson",      "Oglebury",        "Staarbyington",  "Crakkleflap"],
    "Spider":      ["Webbington",     "Kraalsworth",     "Skeezibottom",    "Lurkorgan",      "Vennflap"],
    "Psycho":      ["Spazzington",    "Kraznikworth",    "Bonkington",      "Frenkelbottom",  "Rixbyflap"],
    "Gecko":       ["Licklesworth",   "Slitherbottom",   "Kleekington",     "Zeelyorgan",     "Grippington"],
    "Addict":      ["Slurpington",    "Fiendsworth",     "Jonesybottom",    "Cravensburyflap","Hunklington"],
    "Vengeful":    ["Grudgelington",  "Wrothsworth",     "Vengington",      "Spitebottom",    "Rakorflap"],
    "OG Beadyz":   ["Beadsworth",     "Orbington",       "Globnikflap",     "Gawkinsbottom",  "Peerlington"],
    "GreyGoogle":  ["Googlington",    "Lensibottom",     "Starebumworth",   "Visorbyflap",    "Optikington"],
    "Void":        ["Nullsworth",     "Abyssington",     "Blankobottom",    "Vaaklington",    "Nothinflap"],
    "Doe":         ["Blinkington",    "Daazworth",       "Wunnibottom",     "Softleflap",     "Meldington"],
    "DEFAULT":     ["Skaggsworth",    "Blargington",     "Skornbottom",     "Vuzzleflap",     "Plonkington"],
}


def _dna_pick(options: list, seed_string: str) -> str:
    """Pick deterministically from a list using a seed string."""
    h = int(hashlib.md5(seed_string.encode()).hexdigest(), 16)
    return options[h % len(options)]


def generate_goon_name(edition: int, attributes: dict, dna: str) -> dict:
    """
    Generate a full operative name deterministically from edition + traits + DNA.

    Returns dict with keys:
        first, nickname, last, full_name,
        class_label, variant, signature,
        briefing_header
    """
    body      = attributes.get("Body", "DEFAULT").strip()
    eyes      = attributes.get("Eyes", "DEFAULT").strip()
    mouth     = attributes.get("Mouth", "DEFAULT").strip()
    nose      = attributes.get("Nose", "DEFAULT").strip()
    accessory = attributes.get("Head_Accessory", "None").strip()

    # First name — seeded from DNA + body
    first_pool = FIRST_NAMES.get(body, FIRST_NAMES["DEFAULT"])
    first = _dna_pick(first_pool, f"{dna}:first:{body}")

    # Nickname — mouth first, nose as fallback
    if mouth in NICKNAMES:
        nick_pool = NICKNAMES[mouth]
        nick_seed = f"{dna}:nick:{mouth}"
    elif nose in NICKNAMES:
        nick_pool = NICKNAMES[nose]
        nick_seed = f"{dna}:nick:{nose}"
    else:
        nick_pool = NICKNAMES["DEFAULT"]
        nick_seed = f"{dna}:nick:default"
    nickname = _dna_pick(nick_pool, nick_seed)

    # Last name — seeded from DNA + eyes + edition
    last_pool = LAST_NAMES.get(eyes, LAST_NAMES["DEFAULT"])
    last = _dna_pick(last_pool, f"{dna}:last:{eyes}:{edition}")

    full_name      = f'{first} "{nickname}" {last}'
    signature      = accessory if accessory.lower() != "none" else "No Accessory"
    briefing_header = f"Goon #{edition} — {full_name}, {body} Class"

    return {
        "first":           first,
        "nickname":        nickname,
        "last":            last,
        "full_name":       full_name,
        "class_label":     body,
        "variant":         eyes,
        "signature":       signature,
        "edition":         edition,
        "briefing_header": briefing_header,
    }


if __name__ == "__main__":
    # Quick test with Goon #1 from the metadata example
    test_attrs = {
        "Body": "Infiltrator", "Eyes": "MadEye", "Mouth": "Nasty",
        "Nose": "Tubes", "Head_Accessory": "The Do Teal",
    }
    result = generate_goon_name(1, test_attrs, "eb5df823242bd15e8e93310749a6ad7972269a3a")
    print(result["briefing_header"])
    print(result["full_name"])
