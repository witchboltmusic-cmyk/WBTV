# BRD TV 8 — Cryptid naming experiment

This is a **separate pilot**. It uses the existing town engine, news graphics, weather graphics and voices without changing the normal generator, existing `town_state.json`, S3, or Chromecast app.

## Scenario

- Day one: Sam Evers says he saw an unfamiliar tall animal by Reservoir Road. Sam chooses a name. The *name proposal* is the headline.
- Day two: Harold Vale (hardware-store owner) and Ellen Price (librarian) each propose a rival name. Neither actually saw the animal.
- Day three: the naming argument becomes a minor community issue. People keep disagreeing, even though the sighting is unconfirmed.
- All four outputs — news, weather, Swap Shop and Night Line — mention the controversy appropriately. The LLM writes the names and words; they are **not pre-scripted**.
- Each resident has persistent beliefs, eyewitness status, nominations and recent dialogue.

## Setup (once)

1. Merge the pull request for this pilot into `main`; GitHub manual workflows must exist on the default branch to appear in the Actions picker.
2. Create an OpenAI API key at https://platform.openai.com/api-keys. API usage is separately billed; review its spend controls.
3. Open this repository's **Settings → Secrets and variables → Actions → New repository secret** and create `OPENAI_API_KEY` with the key's value. **Do not put an API key in code, an issue, or chat.**
4. Open **Actions → BRD TV 8 - cryptid naming trial → Run workflow**.
5. Download the `brd-tv8-cryptid-pilot` artifact from the completed run. The ZIP contains MP4s, reports and scripts.

The workflow uses the supported API model ID `gpt-6-luna`, a text-only Responses API call with strict JSON output, plus the existing free eSpeak voices. Named callers receive different stable pitch/rate/EQ profiles. For more natural voices we can move to Piper or a cloud TTS provider later.

## State and safety

- The normal town simulator's `TownTV_Factory/town_state.json` is never written by this workflow.
- The trial writes only `TownTV_Factory/cryptid_trial_state.json` (a separate invented-town history).
- The workflow is **manual**: it doesn't automatically publish video or change S3.
- One API request per fictional day: three requests for the standard run. If the API request or continuity validation fails, the workflow fails rather than substituting canned dialogue.
- API usage requires working credits/limits; I cannot verify the API key or billable inference until the workflow is run.
- The trial uses eSpeak by default for reliability. Its distinct processed voices aren't independent recorded actors.
- Rerunning the workflow continues the pilot for another three days rather than resetting its state.

## Technical entry point

```bash
python -m pip install -r TownTV_Factory/requirements.txt 'openai>=2,<4'
python TownTV_Factory/cryptid_trial.py --days 3 --voice espeak
```

Requires FFmpeg, eSpeak, and `OPENAI_API_KEY` set in the environment. To create scripts without MP4s: `--no-video`. Run offline tests with `python -m unittest discover -s TownTV_Factory/tests -v`.

The generator writes `TownTV_Factory/output/day_###_cryptid_scripts.txt`, `day_###_cryptid_report.json`, the four `day_###_*.mp4` videos, and `cryptid_trial_manifest.json`.
