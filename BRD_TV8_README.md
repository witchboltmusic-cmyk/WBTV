# BRD TV 8 — Bramhollow Broadcast Upgrade

This patch upgrades the existing GitHub `WBTV` town generator. It uses the weather icon sheet, 24-second radar clip, and 29-second news-presenter footage supplied for the project. **It does not modify your Google TV app or S3 storage.**

## What changes

- The fictional town is now named **Bramhollow**, and the station is **BRD TV 8**. On first run, the code migrates the *existing* persistent state in place, preserving the resident roster, day number, businesses, mysteries and history.
- Weather: looping supplied radar, fictional town map labels, real uploaded weather-symbol artwork, current conditions, a five-day forecast and county note crawl.
- News: a real clip of the presenter. The *green presentation monitor beside the presenter* is replaced with station headlines; the show cuts to additional title cards so no precise lip sync is required. It doesn't remove or replace the entire studio background.
- Local programs: existing generated Swap Shop and Night Line continue to work with new station branding.
- Audio: the GitHub workflow explicitly downloads Piper voices and generates with `--voice piper`, so the old eSpeak voice will not be silently substituted. If Piper fails to install, the workflow reports an error instead of making misleading audio.
- Tone: the simulator keeps the existing gently surreal events rather than turning every program into overt horror.

## Upgrade your existing GitHub repo

1. Download the ZIP and extract it. **Drag its contents into the main level of your WBTV GitHub repository, not the enclosing ZIP folder.**
2. It includes `TownTV_Factory/` and `.github/workflows/`. On Mac press **Command + Shift + .** to display the hidden `.github` folder while uploading.
3. Existing source files named `generate.py`, `town_engine.py` and `voiceover.py` should be updated; new `render_media.py` and `assets/` are added.
4. **Do not replace or delete `TownTV_Factory/town_state.json`.** It's deliberately **not included** in this patch.
5. Verify `.github/workflows/generate-town-tv.yml` was also replaced (open it in GitHub; the first line should say `name: BRD TV 8 - generate Bramhollow broadcasts`). On some setups uploading hidden `.github` files can be skipped; if that happens, open the YAML file on GitHub and edit it using the version in the ZIP.
6. In GitHub go to **Actions → BRD TV 8 - generate Bramhollow broadcasts → Run workflow**. Download the `brd-tv8-broadcasts` artifact after a successful run.

This patch includes about 19 MB of supplied visual assets for GitHub. The demo ZIP was rendered locally with fallback eSpeak; the GitHub workflow is configured for Piper, whose voice models are downloaded at runtime rather than included here.

## Local testing (optional)

Install Python/Pillow, FFmpeg and eSpeak. From the repo root:

```sh
python -m pip install -r TownTV_Factory/requirements.txt
python TownTV_Factory/generate.py --voice espeak
```

For Piper, install `piper-tts`, download both voice models into `TownTV_Factory/voices`, then run `python TownTV_Factory/generate.py --voice piper`.

## Notes

- Source footage is looped and cut with graphics. The generated narration is not lip-synced to the person in the clip.
- The radar is fictional programming artwork, not a real-world forecast for Bramhollow.
- Review rights/terms for the source material before *commercial* broadcasting. Giving credit or downloading from a freely accessible site alone doesn't automatically establish unrestricted commercial rights.
