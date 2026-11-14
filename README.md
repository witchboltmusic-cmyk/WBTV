# BRIAR GLEN — A Town That Broadcasts Itself

An experimental **fictional town simulation** that automatically makes local television. No AI-generated video, actors, online text-generation API, or paid text-to-speech service is needed.

This is an upgrade to the first Town TV Factory prototype, built as a **separate addition** to your working Witch Bolt TV app. It **does not change the Android app or your existing S3 playlist**.

## How it works

Every time the generator runs:

1. Loads `TownTV_Factory/town_state.json` — the town's persistent memory.
2. Advances one fictional day (starting October 1, 1996).
3. Simulates everyday local events, residents, shop openings/repairs, town weather, and occasionally a mysterious event.
4. Progresses existing mysteries in stages over several days; completed stages cannot be repeated.
5. Generates four connected programs from that day's shared facts:
   - **Evening News:** a primitive computer-animated news anchor.
   - **County Weather:** moving fictional radar graphics.
   - **Swap Shop:** classified ads, occasionally related to news.
   - **The Night Line:** a two-voice robotic call-in show.
6. Synthesizes all spoken lines offline with eSpeak and builds H.264/AAC MP4s using FFmpeg.
7. Saves new stories, resident/shop statuses, and mystery progress to `town_state.json` for the following day.

**Vibe setting:** `"surreal_chance": 0.16` in `town_state.json` controls the chance of a *standalone* oddity on days without a main story beat. Storyline events can still be uncanny. A setting of `0.05` is gentler; `0.30` is more surreal.

This is a **rules-based procedural simulation**. It makes new combinations and carries forward meaningful state without repeating the exact original five-day storyline. Its prose comes from curated templates and finite mystery arcs; it is not unlimited AI storytelling. For truly unrestricted evolving plots, we'd add a text-only writing model later (optional and potentially billable).

## Quick start with your existing GitHub WBTV repository

1. Download and unzip this package on your computer.
2. Upload the **contents** of the ZIP to the **root** of your `WBTV` repository, not into an additional enclosing folder. You'll have `TownTV_Factory/` and `.github/workflows/generate-town-tv.yml` at the repository root. If replacing old generator files, overwrite them. **Do not overwrite the existing `build-apk.yml` workflow or `WitchBoltTV_GoogleTV` folder.**
3. In your repository choose **Settings → Actions → General → Workflow permissions → Read and write permissions** and save. This allows the town's changes to persist in GitHub. Repository-level protections can also restrict pushes.
4. Choose **Actions → Briar Glen - generate town broadcasts → Run workflow**.
5. When the run finishes, download the `briar-glen-broadcasts` artifact. It contains four MP4 videos, today's scripts, a report and a program manifest.
6. Run it again to advance to the following fictional day. You will see different events that remember what happened previously.

**For automatic daily runs:** In `.github/workflows/generate-town-tv.yml`, uncomment the two `schedule` lines. The example runs at 13:00 UTC (7 AM standard / 8 AM daylight time in US Central). GitHub's scheduled runs are best effort; they may be delayed. A manually triggered run advances one day regardless of the real date.

## Your own music

Drop an original track named `theme.mp3`, `theme.wav`, or `theme.ogg` into `TownTV_Factory/music/`. It will be mixed quietly under the narration during video generation. If the repo is public, whatever you upload there is publicly accessible.

## Adjusting the town

- `TownTV_Factory/town_state.json` — settings, town name, population, active mysteries, businesses and complete recent history. **Do not delete after you begin running it.**
- `TownTV_Factory/town_engine.py` — event pools, mystery arcs, weather transitions, who moves in, which shops open, and character continuity.
- `TownTV_Factory/generate.py` — the look of the programs, voice style, and music volume.
- `TownTV_Factory/tests/test_engine.py` — continuity tests over 120 town days.

### Run it on your own computer (optional)

Requires Python 3, `pip install -r TownTV_Factory/requirements.txt`, `espeak` and `ffmpeg`:

```bash
cd TownTV_Factory
python generate.py                  # advance 1 day, render 4 MP4s
python generate.py --days 7 --no-video   # simulate 7 days quickly, render none
python -m unittest discover -s tests -v
```

`--days 7` creates TV for the **last** simulated day, unless you also use `--no-video`. Copies of your `town_state.json` are recommended before experimenting; every successful run advances history.

## Connecting to your Chromecast TV channel

Right now, this generator writes videos to a GitHub Actions artifact, **not S3**. That's intentional: we haven't authorized any cloud upload automation, and the existing Tallowman playlist remains untouched. You can manually upload the new MP4s to S3 today.

The next technical step is a separate S3 publisher using securely scoped credentials, plus a playlist update/refresh mechanism. Once those are in place, generated shows can appear automatically in your TV's rotation. The current Google TV app typically reloads its playlist when restarted, not continuously while open.

## Important

All locations, residents, news and warnings are fictional. If you publish a public channel, make its fictional nature clear in the app information and don't mimic real emergency alerts in a way that might cause confusion. Confirm commercial rights for any outside footage and music used.
