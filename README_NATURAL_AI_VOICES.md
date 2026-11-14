# BRD TV 8 — natural AI voice auditions

The old eSpeak / Piper narration remains available as a fallback, but this experiment uses **OpenAI Realtime 2.1 mini** to generate significantly more natural spoken performances.

The script and underlying town simulation are unchanged. These are voice recordings of previously generated text, **not new LLM-authored dialogue**.

## Quick start

1. Review and merge this PR to main so the manual workflow appears in GitHub Actions.
2. Your existing `OPENAI_API_KEY` GitHub Actions repository secret is reused. No extra service account is needed. API audio output is billed separately; check your usage and leave auto-recharge off if desired.
3. Open Actions → **BRD TV 8 - natural AI voice auditions** → Run workflow.
4. Leave `mode = auditions` and click Run workflow.
5. Download the artifact `brd-tv8-ai-voice-auditions`. It includes seven individual WAVs: anchor, host, weather, Swap Shop, Sam, Harold and Ellen.
6. Listen to them. We can change the voice IDs or delivery instructions before committing to full videos.
7. If you like them, rerun the same workflow with `mode = all12`. It uses the old successful run ID `43644279946` and outputs the original 12 videos with new voices. It **does not** make story-generation API calls or advance the town.

## Voices

| Role | AI voice ID | Intended performance |
|---|---|---|
| Anchor | cedar | Formal 1990s local news |
| Night Line host | echo | Dry and patient |
| Weather | shimmer | Calm and reassuring |
| Swap Shop | coral | Practical local TV |
| Sam | ash | Sincere, slightly nervous |
| Harold | sage | Older, opinionated |
| Ellen | marin | Precise and dry |

Voice profiles are defined in `TownTV_Factory/openai_voice.py` and can be tuned independently.

## Technical notes

- Uses OpenAI `gpt-realtime-2.1-mini` over server-side Realtime WebSockets.
- Script segments are spoken one at a time as 24 kHz PCM and normalized to WAV by FFmpeg.
- Audio transcripts are compared to source dialogue and serious rewriting is treated as a failure.
- Callers have mild telephone-bandwidth EQ; voices are **not pitch-shifted robotically**.
- The long-form `all12` mode can consume more API audio credits than the quick auditions. Each call is billed; don't run repeatedly unnecessarily.
- New renderer code is isolated from the town's saved `town_state.json` and `cryptid_trial_state.json`.
- For public distribution, clearly disclose that speech uses AI-generated voices, not human speakers.

The older `gpt-4o-mini-tts` Speech endpoint is scheduled to shut down in January 2027. This feature intentionally uses the new Realtime model instead.

The Realtime voices are generated from an exact-read prompt, but pronunciation, timing and precise verbatim delivery can still differ. Audition first.
