# General V — Galactic Goon Content Pipeline

Automated daily content pipeline for General V's classified operative briefings.
Each day: one Goon, one briefing, posted to Instagram Reels + TikTok.

## Pipeline stages

```
Obsidian vault image
      ↓
Imagine.art Image Remix  →  Cinematic villain render
      ↓
Claude API               →  General V briefing script (JSON)
      ↓
ElevenLabs               →  Narration MP3
      ↓
Runway Gen-3             →  Background video clip
      ↓
FFmpeg                   →  Final 9:16 MP4
                              [INCOMING TRANSMISSION boot]
                              [Mid-sentence snap-in]
                              [The briefing]
                              [SIGNAL LOST hard cut]
      ↓
Instagram Reels + TikTok →  Posted
```

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/general-v-pipeline
cd general-v-pipeline
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
# FFmpeg must also be installed on your system
brew install ffmpeg   # macOS
```

### 3. Add your Goon images to Cloudinary
- Upload images to Cloudinary folder: `goon-galaxy/goons/`
- Name each file by edition number: `0001.png`, `0042.jpg`, etc.
- Upload `_metadata_.json` to the same folder (raw file type)

### 4. Add SFX files to assets/
```
assets/
  transmission_open.m4a   ← static burst / comms open sound
  signal_lost.m4a         ← static wash for the outro
  fonts/
    ShareTechMono-Regular.ttf   ← monospace military font
```
Download Share Tech Mono free from Google Fonts.

### 5. Configure environment variables
```bash
cp .env.example .env
# Fill in all values in .env
```

### 6. Set up TikTok auth (one-time)
```bash
export TIKTOK_CLIENT_KEY=your_key
export TIKTOK_CLIENT_SECRET=your_secret
python scripts/tiktok_auth.py
```
Add the printed tokens to `.env` and GitHub Secrets.

### 7. Add all secrets to GitHub
Go to your repo → Settings → Secrets and variables → Actions → New repository secret.
Add every variable from `.env.example`.

### 8. Run locally to test
```bash
source .env
python pipeline.py
```

### 9. Enable GitHub Actions
The workflow runs daily at 18:00 UTC automatically.
You can also trigger it manually from the Actions tab.

## Goon image naming
Images in your Cloudinary folder must be named by edition number:
```
0001.png    ← Edition #1
0042.jpg    ← Edition #42
9999.png    ← Edition #9999
```
The pipeline picks the lowest unprocessed edition each run.
Progress is tracked in `goons/goons_log.json` (committed back automatically).

## Manual trigger
Go to GitHub → Actions → General V Daily Briefing → Run workflow.
Set `dry_run: true` to test the pipeline without posting to social.

## Output artifacts
Each run uploads output files to GitHub Actions artifacts (kept 7 days):
- `goon_{N}_render.png`   — Imagine.art cinematic render
- `goon_{N}_script.json`  — General V briefing script
- `goon_{N}_narration.mp3`— ElevenLabs narration
- `goon_{N}_runway.mp4`   — Runway background clip
- `goon_{N}_final.mp4`    — Final assembled video
