#!/usr/bin/env python3
"""BRD TV 8 isolated cryptid pilot: 3 days of unscripted, stateful local television.

One LLM call per simulated day. Python controls objective facts, memory, and
which residents have witnessed events. The model writes names and dialogue.
The regular town_state.json, normal generator workflow, S3, and TV app are untouched.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import datetime as dt
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import wave

from openai import OpenAI
import generate as tv
from town_engine import initial_state, upgrade_state, advance
from voiceover import active_voice_engine, _write_speech, _run

ROOT = Path(__file__).resolve().parent
TRIAL_STATE = ROOT / "cryptid_trial_state.json"
PEOPLE = {
    "sam": {"name": "Sam Evers", "role": "Bus driver",
            "personality": "Earnest, cautious; proud to be the only witness."},
    "harold": {"name": "Harold Vale", "role": "Hardware store owner",
               "personality": "Opinionated and practical; skeptical of Sam's identification."},
    "ellen": {"name": "Ellen Price", "role": "Librarian",
              "personality": "Precise, dry, opinionated about terminology; wants evidence."},
}
# Dedicated Piper voice models give the residents genuinely different voices.
# The rate/pitch settings below are small finishing adjustments, not the identity.
VOICES = {
    "anchor": ("en_US-john-medium", 1.00, 1.00, False),
    "host": ("en_US-john-medium", 0.98, 0.95, False),
    "weather": ("en_US-kristin-medium", 1.00, 0.98, False),
    "swap_host": ("en_US-kristin-medium", 0.96, 1.00, False),
    "sam": ("en_US-joe-medium", 1.00, 1.02, True),
    "harold": ("en_US-mike-medium", 0.94, 0.92, True),
    "ellen": ("en_US-amy-medium", 1.02, 1.00, True),
}
_PILOT_VOICES = {}

def write_pilot_speech(text, speaker, destination, engine):
    model_name = VOICES[speaker][0]
    if engine == "piper":
        from piper import PiperVoice
        model = ROOT / "voices" / (model_name + ".onnx")
        config = ROOT / "voices" / (model_name + ".onnx.json")
        if not model.exists() or not config.exists():
            raise RuntimeError(f"Missing required Piper model/config: {model_name}")
        if model_name not in _PILOT_VOICES:
            _PILOT_VOICES[model_name] = PiperVoice.load(str(model))
        with wave.open(str(destination), "wb") as out:
            _PILOT_VOICES[model_name].synthesize_wav(text, out)
    else:
        # Retain old speech solely as an explicit local testing fallback.
        legacy = "caller" if speaker in ("ellen", "weather", "swap_host") else "host"
        _write_speech(text, legacy, destination, engine)

def speak(segments, dest, voice_choice="auto"):
    """Reuse installed Piper/eSpeak voices, with stable individual rate/pitch/EQ."""
    engine = active_voice_engine(voice_choice)
    if voice_choice == "piper" and engine != "piper":
        raise RuntimeError("Piper required: do not silently use eSpeak")
    with tempfile.TemporaryDirectory() as tmp:
        frames = []
        rate = 44100
        for i, (speaker, content) in enumerate(segments):
            if speaker not in VOICES:
                raise ValueError("Unknown speaker: " + str(speaker))
            model, pitch, speed, phone = VOICES[speaker]
            raw = Path(tmp) / f"{i:03d}_raw.wav"
            done = Path(tmp) / f"{i:03d}_done.wav"
            write_pilot_speech(content, speaker, raw, engine)
            # Only pitch-shift the two underlying Piper voices. eSpeak already
            # has its own voice variations; tempo adjustments remain gentle.
            shift = pitch if engine == "piper" else 1.0
            tempo = speed / shift
            eq = ("highpass=f=230,lowpass=f=3200" if phone else
                  "highpass=f=90,lowpass=f=10500")
            filters = (f"aresample=44100,asetrate={round(rate * shift)},"
                       f"aresample=44100,atempo={tempo:.5f},{eq}")
            _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i",
                  str(raw), "-af", filters, "-ar", str(rate), "-ac", "1",
                  "-c:a", "pcm_s16le", str(done)])
            with wave.open(str(done), "rb") as item:
                if (item.getnchannels(), item.getsampwidth(), item.getframerate()) != (1, 2, rate):
                    raise ValueError("Unexpected normalized WAV parameters")
                frames.append(item.readframes(item.getnframes()))
        with wave.open(str(dest), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(rate)
            for i, frame in enumerate(frames):
                if i:
                    out.writeframes(b"\x00" * int(rate * 0.34) * 2)
                out.writeframes(frame)
        duration = sum(map(len, frames)) / (rate * 2) + max(0, len(frames) - 1) * 0.34
        return duration, engine

def schema_obj(**properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}

STRING = {"type": "string"}
NOMINATION = schema_obj(
    resident_id={"type": "string", "enum": list(PEOPLE)},
    name=STRING,
)
OPINION = schema_obj(
    resident_id={"type": "string", "enum": list(PEOPLE)},
    belief=STRING,
    stance=STRING,
)
TURN = schema_obj(
    speaker_id={"type": "string", "enum": ["host", *PEOPLE]},
    text=STRING,
)
SCHEMA = schema_obj(
    nominations={"type": "array", "items": NOMINATION},
    opinions={"type": "array", "items": OPINION},
    shows=schema_obj(
        news=schema_obj(narration=STRING),
        weather=schema_obj(narration=STRING, footnote=STRING),
        swap_shop=schema_obj(narration=STRING, listing=STRING),
        night_line=schema_obj(turns={"type": "array", "items": TURN}),
    ),
)
INSTRUCTIONS = """Write an original, low-key, sometimes absurd series of BRD TV 8 local
television broadcasts from October 1996. The station is serious, municipal,
underfunded, and vaguely uncanny. The animal is not the sensational headline.
The headline is that bus driver SAM EVERS proposed a name, and two other
residents are obsessed with choosing a better name.

The town engine establishes facts. Do not invent new sightings, witnesses,
evidence, attacks, deaths, magic, named residents, or physical facts.
Sam alone saw an unidentified tall shape near Reservoir Road in poor visibility.
Harold and Ellen have NEVER seen it. They are competing in a naming dispute
over something they do not know exists.

Use character personalities, carried-forward beliefs, and previously proposed
names. NO recycling earlier scripted dialogue. Let the humor emerge through
earnest nitpicking over the names and procedural etiquette, not jokes or horror.
Residents may be confidently wrong and can misinterpret rumors. They must
never become omniscient.

On day phase 1, nominate exactly one distinctive, speakable name from Sam.
On day phase 2, nominate exactly two OTHER names, one from Harold and Ellen.
After that, nominate no new names. Keep names and rationale consistent.
Write opinions for Sam, Harold and Ellen each day.
News narration: 75-130 words, naming proposal/disagreement as LEAD and one
normal community news story using supplied events.
Weather: 55-90 words; use ONLY supplied weather, with at most a subtle
reservoir reference. Supply a short weather footnote.
Swap Shop: 35-65 words, mundane listing with a weak link to the naming issue.
Night Line: 8-14 conversational turns, short natural dialogue featuring the
host and ALL THREE people; people should argue over names on their own.
Return JSON conforming exactly to schema. No stage directions or markdown."""

def context_for(state, daily):
    c = state.setdefault("cryptid_trial", {
        "first_day": daily["day"],
        "names": {},
        "minds": {key: {"witnessed": key == "sam", "belief": "",
                        "stance": ""} for key in PEOPLE},
        "public_record": [],
        "recent_dialogue": [],
        "creature_private": {
            "exists": True,
            "habitat": "wooded drainage near reservoir",
            "behavior": "avoids lit areas; mostly nocturnal",
        },
    })
    phase = daily["day"] - c["first_day"] + 1
    evidence = ("Sam says he saw a tall shape beside Reservoir Road after his bus route."
                if phase == 1 else
                "Only Sam claims a sighting; neither Harold nor Ellen has seen it.")
    return {
        "day": daily["day"], "phase": phase, "air_date": daily["air_date"],
        "public_evidence": evidence,
        "weather": deepcopy(daily["weather"]),
        "ordinary_news": [{"headline": e["headline"], "text": e["text"]}
                          for e in daily["events"] if not e.get("surreal")][:3],
        "residents": deepcopy(PEOPLE),
        "private_beliefs": deepcopy(c["minds"]),
        "established_names": deepcopy(c["names"]),
        "previous_news": deepcopy(c["public_record"][-3:]),
        "previous_dialogue": deepcopy(c["recent_dialogue"][-2:]),
    }

def ask_model(client, model, context):
    result = client.responses.create(
        model=model,
        instructions=INSTRUCTIONS,
        input=json.dumps(context, ensure_ascii=False),
        text={"format": {"type": "json_schema", "name": "brd_tv8_cryptid",
                         "schema": SCHEMA, "strict": True}},
        store=False,
        max_output_tokens=5500,
    )
    if getattr(result, "status", "completed") != "completed" or not result.output_text:
        raise RuntimeError("Incomplete model response; trial history not saved")
    return json.loads(result.output_text)

def apply_response(state, daily, context, data):
    """Validate structured facts before committing subjective opinions and dialogue."""
    c = state["cryptid_trial"]
    phase = context["phase"]
    expected = {"sam"} if phase == 1 else ({"harold", "ellen"} if phase == 2 else set())
    proposals = {}
    for item in data["nominations"]:
        who = item["resident_id"]
        name = " ".join(item["name"].split())
        if who not in PEOPLE or who in proposals or not 2 <= len(name) <= 38:
            raise ValueError("Invalid name proposal")
        proposals[who] = name
    if set(proposals) != expected:
        raise ValueError("Unexpected nominations or missing nominated name")
    if len(set([*c["names"].values(), *proposals.values()])) != len(c["names"]) + len(proposals):
        raise ValueError("Different residents must propose distinct names")
    opinions = data["opinions"]
    if sorted(item["resident_id"] for item in opinions) != sorted(PEOPLE):
        raise ValueError("One opinion is required from each named resident")
    shows = data["shows"]
    turns = shows["night_line"]["turns"]
    if not 8 <= len(turns) <= 14 or not {"host", *PEOPLE}.issubset(
        {item["speaker_id"] for item in turns}
    ):
        raise ValueError("Night Line needs host and all three speakers")
    if sum(len(item["text"]) for item in turns) > 4800:
        raise ValueError("Night Line is too long")
    for key in ("news", "weather", "swap_shop"):
        if not 25 <= len(shows[key]["narration"]) <= 2800:
            raise ValueError("Invalid " + key + " script length")
    c["names"].update(proposals)
    for item in opinions:
        who = item["resident_id"]
        c["minds"][who]["belief"] = item["belief"][:220]
        c["minds"][who]["stance"] = item["stance"][:220]
    # Preserve the difference between witnessed evidence and hearsay.
    c["minds"]["sam"]["witnessed"] = True
    c["minds"]["harold"]["witnessed"] = False
    c["minds"]["ellen"]["witnessed"] = False
    if phase == 1:
        headline = f'Sam Evers proposes "{c["names"]["sam"]}" as name for reservoir animal'
    elif phase == 2:
        headline = "Harold Vale and Ellen Price dispute Sam Evers' proposed name"
    else:
        headline = "Reservoir animal naming debate draws community comment"
    normal = next((e["headline"] for e in daily["events"]
                   if e.get("category") == "community"), "Local community bulletins")
    story = {"day": daily["day"], "headline": headline,
             "text": "Unconfirmed Reservoir Road animal report; residents debate names.",
             "category": "community", "surreal": False, "thread": "cryptid_naming"}
    daily["events"].insert(0, story)
    state["history"].append(story)
    state["history"] = state["history"][-800:]
    c["public_record"].append({"day": daily["day"], "headline": headline,
                               "names": deepcopy(c["names"])})
    c["recent_dialogue"].append({"day": daily["day"], "turns": turns})
    c["recent_dialogue"] = c["recent_dialogue"][-5:]
    daily["weather"]["footnote"] = shows["weather"]["footnote"][:190]
    daily["swap"] = shows["swap_shop"]["listing"][:200]
    daily["call"] = {"caller": "Sam / Harold / Ellen",
                     "caller_text": "Bramhollow debates reservoir animal names",
                     "host_text": ""}
    daily["cryptid"] = {"phase": phase, "headline": headline,
                        "name_proposals": deepcopy(c["names"])}
    def single(name, who, script, display, second):
        return {"name": name, "segments": [(who, script)],
                "narration": script, "display": display,
                "second": second, "events": [headline]}
    scripts = [
        single("News", "anchor", shows["news"]["narration"], headline, normal),
        single("Weather", "weather", shows["weather"]["narration"],
               daily["weather"]["label"], daily["weather"]["forecast"]),
        single("Swap Shop", "swap_host", shows["swap_shop"]["narration"],
               daily["swap"], "County classifieds"),
    ]
    scripts.append({
        "name": "Night Line",
        "segments": [(turn["speaker_id"], turn["text"]) for turn in turns],
        "narration": " ".join(turn["text"] for turn in turns),
        "display": daily["call"]["caller_text"],
        "second": "Open telephone lines", "events": [headline],
    })
    return scripts

def main():
    p = argparse.ArgumentParser(description="BRD TV 8 isolated LLM cryptid trial")
    p.add_argument("--days", type=int, default=3)
    p.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-6-luna"))
    p.add_argument("--voice", choices=("auto", "espeak", "piper"), default="auto")
    p.add_argument("--no-video", action="store_true")
    p.add_argument("--state", type=Path, default=TRIAL_STATE)
    args = p.parse_args()
    if not 1 <= args.days <= 10:
        p.error("Choose 1-10 days")
    if not os.getenv("OPENAI_API_KEY"):
        p.error("OPENAI_API_KEY missing; refusing to fabricate generated conversation")
    client = OpenAI(timeout=100.0, max_retries=2)
    if not args.no_video:
        if not shutil.which("ffmpeg"):
            p.error("ffmpeg is required to render")
        active_voice_engine(args.voice)
        tv.synthesize = speak  # confine the voice extension to this pilot process
    state = (upgrade_state(json.loads(args.state.read_text("utf-8")))
             if args.state.exists() else initial_state())
    state["town"], state["station"] = "Bramhollow", "BRD TV 8"
    tv.OUT.mkdir(parents=True, exist_ok=True)
    reports = []
    for _ in range(args.days):
        day = advance(state)
        context = context_for(state, day)
        response = ask_model(client, args.model, context)
        programs = apply_response(state, day, context, response)
        prefix = f'day_{day["day"]:03d}'
        (tv.OUT / (prefix + "_cryptid_scripts.txt")).write_text(
            "\n\n".join(f'[{x["name"]}]\n{x["narration"]}' for x in programs) + "\n",
            encoding="utf-8")
        (tv.OUT / (prefix + "_cryptid_report.json")).write_text(
            json.dumps({"day": day, "nominations": state["cryptid_trial"]["names"],
                        "programs": [x["name"] for x in programs]}, indent=2) + "\n",
            encoding="utf-8")
        generated = []
        if not args.no_video:
            tv.TEMP.mkdir(parents=True, exist_ok=True)
            try:
                for program in programs:
                    generated.append(tv.render_program(program, day, state, args.voice))
            finally:
                shutil.rmtree(tv.TEMP, ignore_errors=True)
        reports.append({"day": day["day"], "date": day["air_date"],
                        "clips": generated, "headline": day["cryptid"]["headline"]})
        # Save only after successful model generation and rendering.
        args.state.parent.mkdir(parents=True, exist_ok=True)
        args.state.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        print(prefix, ":", day["cryptid"]["headline"])
    (tv.OUT / "cryptid_trial_manifest.json").write_text(
        json.dumps({"station": "BRD TV 8", "reports": reports}, indent=2) + "\n",
        encoding="utf-8")

if __name__ == "__main__":
    main()
