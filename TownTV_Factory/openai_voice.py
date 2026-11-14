#!/usr/bin/env python3
"""BRD TV 8 AI character voices using OpenAI's current Realtime API.

This module does not generate dialogue. It reads existing scripts verbatim,
one speaker at a time, with separate voice identities and acting directions.
It works with the same synthesize(segments, dest, voice_choice) interface as
the existing town video renderer. API key stays in GitHub Actions Secrets.

Audio is generated via gpt-realtime-2.1-mini WebSocket and saved as WAV.
No AI-generated visuals. No re-simulation or new story text.
"""
from __future__ import annotations

import argparse
import base64
import difflib
import json
import os
from pathlib import Path
import re
import tempfile
import wave

from voiceover import _run

ROOT = Path(__file__).resolve().parent
MODEL = os.environ.get("BRD_VOICE_MODEL", "gpt-realtime-2.1-mini")
PROFILE = {
    "anchor": {
        "voice": "cedar",
        "style": "Mature American local TV news presenter. Grounded, measured, slightly formal. Read copy straight, no theatrical suspense.",
        "telephone": False,
        "sample": "Tonight's leading story: Sam Evers has proposed a name for the animal reported near Reservoir Road. The town has not yet agreed.",
    },
    "host": {
        "voice": "echo",
        "style": "Male 1990s late-night local phone-in host. Relaxed, dry, patient, naturally curious. Let callers finish; never sound like a comedy character.",
        "telephone": False,
        "sample": "Good evening, you're on Night Line. We seem to have several names for an animal that only one person claims to have seen.",
    },
    "weather": {
        "voice": "shimmer",
        "style": "Warm, composed American local weather presenter. Low-key and factual, not exaggerated. Gently reassuring delivery.",
        "telephone": False,
        "sample": "Cloudy skies tonight, with patchy fog expected around the reservoir. Visibility could fall quickly after midnight.",
    },
    "swap_host": {
        "voice": "coral",
        "style": "Cheerful but ordinary rural American public-access classified ads announcer. Practical and approachable, never cartoonish.",
        "telephone": False,
        "sample": "We have a used lawn mower, two jars of canning lids, and a perfectly good folding table available on the north side.",
    },
    "sam": {
        "voice": "ash",
        "style": "Adult working-class American man, bus driver. Sincere, slightly nervous and hesitant. Modest accent, conversational, never spooky or exaggerated.",
        "telephone": True,
        "sample": "I saw something standing by Reservoir Road. I don't know what it was, but I think the Tall One is a perfectly good name.",
    },
    "harold": {
        "voice": "sage",
        "style": "Older American man, gruff dry hardware store owner. Opinionated, practical, slightly irritated, but authentic, not performed as a joke.",
        "telephone": True,
        "sample": "The Tall One is not a useful name. We haven't established how tall it is. Roadside Shape is more accurate.",
    },
    "ellen": {
        "voice": "marin",
        "style": "Adult American woman, librarian. Articulate, precise, dryly amused but extremely serious about terminology. Distinct natural speaking rhythm.",
        "telephone": True,
        "sample": "Neither of you has considered how this animal would appear in a catalogue. Unidentified Tall Shape is clearly more responsible.",
    },
}

def profile_for(speaker):
    try:
        return PROFILE[speaker]
    except KeyError:
        raise ValueError(f"Unrecognized BRD TV 8 speaker: {speaker}") from None

def _normalize(words):
    return re.sub(r"[^a-z0-9]+", " ", words.lower()).strip()

def _generate_pcm(text, profile, model=MODEL):
    """Get one isolated speech-only 24kHz PCM sample from the Realtime API."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY GitHub Actions secret")
    try:
        import websocket
    except ImportError as exc:
        raise RuntimeError("Install websocket-client to enable OpenAI Realtime voices") from exc
    if not text.strip():
        raise ValueError("Empty voice segment")
    if len(text) > 3500:
        raise ValueError("Voice segment exceeds safe 3500-character limit")
    instructions = (
        "You are a professional voice actor making an audio recording for a fictional "
        "1990s regional television station. Read the exact supplied script, word for "
        "word. Do not add or omit words. Do not improvise. Do not introduce the script. "
        "Produce only the voice reading, no sound effects, no music. "
        "Delivery style: " + profile["style"] + "\n\n"
        "READ THIS EXACT SCRIPT:\n" + text
    )
    ws = websocket.create_connection(
        f"wss://api.openai.com/v1/realtime?model={model}",
        header=[f'Authorization: Bearer {os.environ["OPENAI_API_KEY"]}'],
        timeout=150,
    )
    audio_chunks, transcript = [], []
    try:
        ws.send(json.dumps({
            "type": "response.create",
            "response": {
                "conversation": "none",
                "input": [],
                "output_modalities": ["audio"],
                "audio": {
                    "output": {
                        "voice": profile["voice"],
                        "format": {"type": "audio/pcm", "rate": 24000},
                    }
                },
                "instructions": instructions,
            },
        }))
        completed = False
        while not completed:
            event = json.loads(ws.recv())
            kind = event.get("type")
            if kind == "error":
                raise RuntimeError("OpenAI voice error: " + str(event.get("error", {}).get("message", event)))
            if kind == "response.output_audio.delta":
                audio_chunks.append(base64.b64decode(event["delta"]))
            elif kind == "response.output_audio_transcript.delta":
                transcript.append(event.get("delta", ""))
            elif kind == "response.done":
                response = event.get("response", {})
                if response.get("status") != "completed":
                    raise RuntimeError("OpenAI speech was not completed: " + str(response.get("status_details")))
                completed = True
        if not audio_chunks:
            raise RuntimeError("OpenAI did not return speech audio")
        spoken = "".join(transcript)
        # A serious mismatch means the spoken track may not match the town's script.
        # Realtime transcript punctuation is not identical, so allow modest variation.
        if spoken:
            similarity = difflib.SequenceMatcher(None, _normalize(text), _normalize(spoken)).ratio()
            if similarity < 0.80:
                raise RuntimeError(
                    f"Speech substantially changed the original script (similarity {similarity:.2f})"
                )
        return b"".join(audio_chunks)
    finally:
        ws.close()

def _make_wave(text, speaker, destination):
    """Write clean 24kHz mono WAV with no AI voice alteration after generation."""
    profile = profile_for(speaker)
    audio = _generate_pcm(text, profile)
    with wave.open(str(destination), "wb") as dest:
        dest.setnchannels(1)
        dest.setsampwidth(2)
        dest.setframerate(24000)
        dest.writeframes(audio)

def synthesize(segments, dest, voice_choice="realtime"):
    """A drop-in replacement for voiceover.synthesize, returning (seconds, engine)."""
    if voice_choice not in ("realtime", "auto"):
        raise ValueError("Use --voice realtime to enable cloud voices")
    if not segments:
        raise ValueError("Cannot synthesize zero speech segments")
    with tempfile.TemporaryDirectory() as work:
        pieces = []
        for n, (speaker, text) in enumerate(segments):
            original = Path(work) / f"speech_{n:03d}.wav"
            normalized = Path(work) / f"normalized_{n:03d}.wav"
            _make_wave(text, speaker, original)
            # Only telephone equalization for call-in guests; no robotic pitch shifting.
            sound = ("highpass=f=250,lowpass=f=3500"
                     if profile_for(speaker)["telephone"] else
                     "highpass=f=75,lowpass=f=10500")
            _run(["ffmpeg","-y","-hide_banner","-loglevel","error",
                  "-i",str(original),"-af",sound,"-ar","44100","-ac","1",
                  "-c:a","pcm_s16le",str(normalized)])
            with wave.open(str(normalized),"rb") as w:
                if (w.getnchannels(),w.getsampwidth(),w.getframerate()) != (1,2,44100):
                    raise ValueError("Wrong normalized WAV format")
                pieces.append(w.readframes(w.getnframes()))
        gap = int(0.34 * 44100) * 2
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(dest),"wb") as final:
            final.setnchannels(1)
            final.setsampwidth(2)
            final.setframerate(44100)
            for i, piece in enumerate(pieces):
                if i:
                    final.writeframes(b"\x00" * gap)
                final.writeframes(piece)
        duration = (sum(len(a) for a in pieces) + gap * (len(pieces)-1)) / (44100 * 2)
        return duration, "realtime"

def audition(output):
    output.mkdir(parents=True, exist_ok=True)
    for speaker, details in PROFILE.items():
        wav = output / f"{speaker}_{details['voice']}.wav"
        print(f"Generating AI voice audition: {speaker} ({details['voice']})", flush=True)
        synthesize([(speaker, details["sample"])], wav, "realtime")
    (output / "README.txt").write_text(
        "BRD TV 8 — AI VOICE AUDITIONS\n\n"
        "These are synthetic AI-generated voices, not human recordings.\n"
        "These lines are examples for evaluating voices, not scripted broadcast dialogue.\n\n"
        + "\n".join(f"{name}: {info['voice']} — {info['style']}"
                    for name, info in PROFILE.items()) + "\n",
        encoding="utf-8",
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audition", action="store_true", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "voice_auditions")
    args = parser.parse_args()
    audition(args.output)
