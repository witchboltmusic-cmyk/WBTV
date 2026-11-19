# Bramhollow / CH 02: Overhead Town Observation

This is the first working visual prototype of the proposed second TV channel. It is NOT wired into the Chromecast app yet; it creates a video so we can approve the visual design without risking the existing working station.

## What this version does

- Renders a 960x540 MP4 with original, procedural 1990s-style overhead pixel graphics.
- Shows named residents (Sam Evers, Ellen Price, Harold Vale, etc.) walking along mapped streets and following job-based daily routines.
- Simulates a compressed day, around 6 AM to 11 PM, with an on-screen clock and day/night change.
- Uses the broadcast day, stored weather and recorded news headlines from the saved cryptid trial world state.
- Reads established resident statuses and business closures from town state. People who are away or have moved do not appear.
- Uses deterministic routes, no new LLM calls, no TTS, and no paid API.
- Produces an MP4, a PNG still, and a JSON manifest.

## Important limitation

The existing town engine tracks resident status and news events, NOT exact street destinations or encounter logs. Thus job-based schedules and walking paths here are ILLUSTRATIVE ROUTINES. We do not assert that a new meeting happened in the TV storyline, and this tool does not modify any town state.

The next stage is one shared spatial/event ledger so both the news scripts and the map are driven by the same recorded facts, including real encounters.

## See the demo

1. Open the Channel 02 pull request. Its GitHub Actions preview runs automatically on the PR and uploads an artifact called bramhollow-channel-02-overhead-preview.
2. Download the artifact to view the MP4 and still PNG.

After merging the pull request, the workflow can be rerun manually in Actions under "BRD TV 8 - Channel 02 overhead town preview". It reads the latest day already saved in the repository's cryptid trial state; it does not rerun that simulation.

## Local generation

Run from repository root with Pillow and FFmpeg installed:

    python TownTV_Factory/town_map.py --state TownTV_Factory/cryptid_trial_state.json --report TownTV_Factory/output/day_009_cryptid_report.json --seconds 55 --output TownTV_Factory/output/bramhollow_channel_02.mp4 --preview TownTV_Factory/output/bramhollow_channel_02_preview.png

A report file is optional for selecting a particular day. The workflow uses the most recent recorded day WITHOUT advancing it.

## Channel integration plan

After confirming the visual style:
1. Add a second selectable channel to the Android app while retaining the existing single-channel playlist format.
2. Publish Channel 02 MP4s to the same HTTPS storage as the original broadcasts.
3. Record character movements and encounters in one shared world-event ledger so both channels genuinely observe the same simulation.

Nothing in this preview changes the Chromecast app, S3 bucket, playlist, voices, existing videos or persistent town history.
