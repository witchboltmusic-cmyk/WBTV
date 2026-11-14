# Briar Glen — Broadcast Upgrade v2

This is a **patch** for your existing WBTV GitHub repository, not a replacement project.
It upgrades the sound and graphics and very slightly increases the surreal details.
**Do not replace `TownTV_Factory/town_state.json`: that file contains your town’s history.**

## Install into existing repository

1. Unzip this upgrade package.
2. In GitHub, open your WBTV repository and upload the folders `.github` and `TownTV_Factory` to the **repository root**, replacing same-named files. Do not upload an enclosing `Briar_Glen_Upgrade` folder.
3. Confirm these files were updated: `.github/workflows/generate-town-tv.yml`, `TownTV_Factory/generate.py`, `TownTV_Factory/town_engine.py`; and `TownTV_Factory/voiceover.py` was added.
4. Run **Actions → Briar Glen - generate town broadcasts → Run workflow**.
5. When the run finishes, download artifact **briar-glen-broadcasts** and view the four new MP4s.

Your existing Witch Bolt TV APK and S3 videos are untouched; the broadcasts still require manual scheduling/upload if you want them on air.

## What's improved

- **Piper narration** (`john` for announcer/host, `kristin` for caller): natural-sounding offline voices with no per-minute API fee. The GitHub workflow downloads two voice models at runtime. On a computer without Piper, `--voice auto` falls back to eSpeak. `--voice piper` insists on Piper and fails if unavailable.
- **Audio mastering**: gentle high/low pass and dynamic compression, telephone EQ for the caller.
- **Graphics**: 960×540, 8-fps film-ready classic county TV aesthetic, varied news/weather/classified/call-in layouts, scrolling community ticker, low-key animated radar, retro colors and type.
- **5% more uncanny in tone**, not constant horror: subtly anomalous administrative updates added to the event pool; default minor oddities adjusted from 0.16 to 0.17 probability on days without an active mystery event. Existing custom probabilities remain unchanged.
- **Town continuity**: save file remains intact; a one-time upgrade adjusts only the previous default 0.16 probability. The serialized event history and resident statuses remain unchanged.

## Narration licensing and distribution

Piper software and its voice model rights are separate. This setup uses the `en_US-john-medium` and `en_US-kristin-medium` models. Their available model cards identify public-domain LibriVox training recordings. Before using a generated channel commercially, review the specific copies' model cards and your distribution plan. The model files are downloaded at runtime and are NOT included in this ZIP.

## Optional use on your own PC

```
python -m pip install -r TownTV_Factory/requirements.txt
# For natural narration, also install Piper and voice models:
python -m pip install piper-tts
python -m piper.download_voices en_US-john-medium --data-dir TownTV_Factory/voices
python -m piper.download_voices en_US-kristin-medium --data-dir TownTV_Factory/voices
python TownTV_Factory/generate.py --voice piper
```

To render with the old fallback instead, install ffmpeg and espeak and run `python TownTV_Factory/generate.py --voice espeak`.

The generator defaults to adding exactly **one fictional day per run**. Existing GitHub permissions must allow write access to persist the state.
