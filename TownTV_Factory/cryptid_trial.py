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
from apocalypse_engine import advance_incident, public_context
from voiceover import active_voice_engine, _write_speech, _run

ROOT = Path(__file__).resolve().parent
TRIAL_STATE = ROOT / "cryptid_trial_state.json"
PEOPLE = {
    "sam": {"name": "Sam Evers", "role": "Bus driver",
            "personality": "Blunt, observant, touchy about being dismissed. Saw the shape himself and gets furious when two non-witnesses lecture him. Speaks in plain, imperfect sentences; humor comes from indignation and specificity."},
    "harold": {"name": "Harold Vale", "role": "Hardware store owner",
               "personality": "Stubborn, loud, slyly insulting, and certain he knows better. Has NOT seen the animal. Keeps trying to make the naming argument a matter of common sense and personal dignity; grudges are petty and specific."},
    "ellen": {"name": "Ellen Price", "role": "Librarian",
              "personality": "Acid-dry, intelligent, ferociously precise, sometimes cutting. Has NOT seen the animal. Uses a calm voice to say surprisingly brutal things, especially when Harold becomes pompous; capable of making things worse on purpose."},
}
# Existing town residents can call; the original trio remains the naming cast.
CALLER_CAST = {
    **PEOPLE,
    "mara": {"name": "Mara Voss", "role": "County clerk",
             "personality": "Exact, exhausted, direct; knows county paperwork."},
    "david": {"name": "David Bell", "role": "Recreation director",
              "personality": "Friendly, increasingly anxious; struggles to sound calm."},
    "oscar": {"name": "Oscar Reed", "role": "Sign painter",
              "personality": "Plainspoken and attentive to concrete physical details."},
    "june": {"name": "June Mercer", "role": "Postal worker",
             "personality": "Dry, matter-of-fact, suspicious of rumors."},
    "violet": {"name": "Violet Dunn", "role": "Retired schoolteacher",
               "personality": "Calm but firm; dislikes empty reassurance."},
    "ernest": {"name": "Ernest Pike", "role": "Garden club president",
               "personality": "Practical and fussy; interrupts when frightened."},
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
    "mara": ("en_US-amy-medium", 0.97, 0.97, True),
    "david": ("en_US-joe-medium", 1.00, 1.00, True),
    "oscar": ("en_US-mike-medium", 1.01, 0.99, True),
    "june": ("en_US-amy-medium", 1.01, 1.02, True),
    "violet": ("en_US-amy-medium", 0.97, 1.00, True),
    "ernest": ("en_US-mike-medium", 1.00, 1.00, True),
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
    speaker_id={"type": "string", "enum": ["host", *CALLER_CAST]},
    text=STRING,
)
SCHEMA = schema_obj(
    lead_headline=STRING,
    nominations={"type": "array", "items": NOMINATION},
    opinions={"type": "array", "items": OPINION},
    shows=schema_obj(
        news=schema_obj(narration=STRING),
        weather=schema_obj(narration=STRING, footnote=STRING),
        swap_shop=schema_obj(narration=STRING, listing=STRING),
        night_line=schema_obj(turns={"type": "array", "items": TURN}),
    ),
)
INSTRUCTIONS = """You write human, gripping, frightening fictional 1996 TV broadcasts from
Bramhollow, a small American town undergoing a real, escalating emergency.
ONE HIDDEN, RULE-DRIVEN SIMULATION controls death, injury, disappearances,
destroyed buildings, official casualty totals, eyewitness limitations and chronology.
The simulation facts arrive in the JSON input under 'public_disaster'; the AI
writes only the words that people speak. Do NOT invent additional confirmed
deaths, sightings, injuries, transmissions, attacks, police statements, rescues,
survivors, locations of entities, or property destruction. No resurrection,
no posthumous live phone calls, no contradictions with resident_status.
People may be mistaken or lie, but label any new claims as unverified anecdotes.

TONE: Genuinely terrifying, concrete, visceral, increasingly catastrophic.
No empty phrases like 'an unexplained occurrence', 'things seem strange',
'residents are concerned' or 'authorities are monitoring the situation'.
Ground fear in the specific dimensions of structures, physical aftermath,
sounds, what responders found, evacuations, damaged roads, bodies, and losses
provided by the county incident reports. Deaths MUST be called deaths when
they are confirmed. Do not soften them into generic 'incidents.'
At least one daily line should be emotionally devastating or specific enough
to stay with the viewer. Let fear change the way people speak.
No cliched analog-horror phrases, no theatrical one-liners, no 'shadows',
'memories', prophecy, or cosmic exposition. Never give the attackers an
origin, theological classification, species name, purpose or grand explanation.
They are not called angels or demons by the station. Do not reveal their rules.
Do not imply that anyone in town already knows what they are.
The TV station must behave like underfunded local television trying to stay
professional under conditions it cannot manage.

HUMAN CHARACTER RULES:
- SAM EVERS: bus driver and original sighting witness. Defensive, blunt.
- HAROLD VALE: hardware-store owner, petty and loud, never saw the original shape.
- ELLEN PRICE: librarian, cutting and precise, never saw the original shape.
- HOST: strained late-night host, may interrupt, panic, lose track of who's on air.
ONLY characters in 'available_speakers' may speak LIVE. DEAD and MISSING
characters never speak. A recorded archival quote, if needed, must be explicitly
identified by a surviving speaker as an old recording, not a live turn.
Characters know only what public officials or their own lived experiences reveal.
Previously established nickname proposals persist but rapidly become less
important as the real emergency unfolds. People can be vulgar when terrified,
sometimes swear, get irrational, cry, say ugly things, and abandon arguments.
Do not make everything a joke; dark humor should become rare after casualties.

OUTPUT:
- lead_headline: 35-105 characters, about TODAY'S VERIFIED EMERGENCY BULLETIN,
  not the old nickname debate. In days with no emergency use the naming dispute.
  Do NOT announce a new unverified event as fact.
- nominations: Sam nominates once on first naming phase; Harold and Ellen in
  second; none after. Follow the phase in the input. Keep past names unchanged.
- opinions: exactly one per LIVING/AVAILABLE original resident; no opinions
  attributed to dead or missing characters.
- News: 130-210 spoken words. Open with the actual reported incident and explicitly
  give confirmed death counts and named casualties when supplied. The female anchor
  reads clear short sentences with punctuation and real breaths. The dead are not
  'unaccounted for'. The missing are not confirmed dead. Briefly mention an ordinary
  local event for contrast only when it feels plausible.
- Weather: 55-110 words. Keep factual supplied conditions and temperature,
  but include one concrete station or infrastructure disruption from the
  public disaster if relevant. Never invent a fresh catastrophe.
- Swap Shop: 40-100 words. Initially mundane, later becomes lost-property,
  shelter, evacuation-related and practical personal announcements. Never casually
  sell household goods while the town is collapsing; never invent confirmed rescues.
- Night Line: usually 12-20 rapid conversational turns, with host and available
  named speakers; 6-12 if fewer than two people remain. Not everyone needs to
  agree. The host can lose composure or be cut off by callers. Use concrete fear,
  sharp argument, faltering attempts to remain normal, specific losses.
  No voices from dead or missing people, no omniscience, no tidy closing speech.
  If nobody from the original trio is available, write a distressed
  station-only emergency broadcast with host turns.
- Return JSON conforming exactly to schema, no stage directions or markdown.
Keep every verified incident fact and causal ambiguity consistent across shows."""

def select_nightline_guest(state, daily):
    """Rotate available town callers and avoid immediate repetition."""
    eligible = sorted(
        key for key in CALLER_CAST
        if state.get("residents", {}).get(key, {}).get("status") == "home"
    )
    if not eligible:
        return None
    previous = state.get("cryptid_trial", {}).get("last_nightline_guest")
    caller = eligible[(int(daily["day"]) - 1) % len(eligible)]
    if caller == previous and len(eligible) > 1:
        caller = eligible[(eligible.index(caller) + 1) % len(eligible)]
    person = state["residents"][caller]
    return {"resident_id": caller, "name": person["name"],
            "job": person.get("job", CALLER_CAST[caller]["role"]),
            "personality": CALLER_CAST[caller]["personality"]}


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
        "previous_dialogue": deepcopy(c["recent_dialogue"][-1:]),
        "call_in_guest": select_nightline_guest(state, daily),
        "public_disaster": public_context(state, daily),
        "available_speakers": [
            k for k in PEOPLE
            if state.get("residents", {}).get(k, {}).get("status", "home")
            not in ("dead", "missing", "moved", "away", "evacuated")
        ],
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
    available = set(context.get("available_speakers", PEOPLE))
    if sorted(item["resident_id"] for item in opinions) != sorted(available):
        raise ValueError("One opinion is required from each available named resident")
    shows = data["shows"]
    turns = shows["night_line"]["turns"]
    speakers = {item["speaker_id"] for item in turns}
    minimum = 14 if len(available) >= 3 else (10 if len(available) == 2 else
              6 if len(available) == 1 else 6)
    if not minimum <= len(turns) <= 20 or not {"host", *available}.issubset(speakers):
        raise ValueError("Night Line needs host and currently available speakers")
    if not speakers.issubset({"host", *available}):
        raise ValueError("Dead, missing, evacuated or otherwise absent resident cannot call live")
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
    headline = (" ".join(daily["horror"]["headline"].split())
                if daily.get("horror") else
                " ".join(data["lead_headline"].split()))
    if not 20 <= len(headline) <= 110:
        raise ValueError("Lead headline length outside permitted broadcast format")
    if not daily.get("horror") and not any(
        token in headline.lower()
        for token in ("sam", "harold", "ellen", "name", "naming",
                      *(n.lower() for n in c["names"].values()))
    ):
        raise ValueError("Lead headline must match the existing naming dispute")
    normal = next((e["headline"] for e in daily["events"]
                   if e.get("category") == "community"), "Local community bulletins")
    story = {"day": daily["day"], "headline": headline,
             "text": "Unconfirmed Reservoir Road animal report; residents debate names.",
             "category": "community", "surreal": False, "thread": "cryptid_naming"}
    daily["events"].insert(0, story)
    state["history"].append(story)
    state["history"] = state["history"][-800:]
    c["public_record"].append({"day": daily["day"], "headline": headline,
                               "names": deepcopy(c["names"]),
                               "confirmed_horror_event": (
                                   daily["horror"]["headline"] if daily.get("horror") else None)})
    c["recent_dialogue"].append({"day": daily["day"], "turns": turns})
    c["recent_dialogue"] = c["recent_dialogue"][-5:]
    daily["weather"]["footnote"] = shows["weather"]["footnote"][:190]
    daily["swap"] = shows["swap_shop"]["listing"][:200]
    daily["call"] = {"caller": " / ".join(PEOPLE[k]["name"] for k in sorted(available))
                               or "Emergency station staff",
                     "caller_text": (daily["horror"]["headline"] if daily.get("horror")
                                     else "Bramhollow debates reservoir animal names"),
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

def configure_voice_renderer(choice):
    """Select verified Realtime speech or explicitly requested offline Piper."""
    if choice == "realtime":
        import openai_voice
        tv.synthesize = openai_voice.synthesize
        return "realtime"
    engine = active_voice_engine(choice)
    tv.synthesize = speak
    return engine


def main():
    p = argparse.ArgumentParser(description="BRD TV 8 isolated LLM cryptid trial")
    p.add_argument("--days", type=int, default=3)
    p.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-6-luna"))
    p.add_argument("--voice", choices=("auto", "espeak", "piper", "realtime"), default="realtime")
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
        selected = configure_voice_renderer(args.voice)
        print("BRD TV 8 voice engine:", selected, flush=True)
    state = (upgrade_state(json.loads(args.state.read_text("utf-8")))
             if args.state.exists() else initial_state())
    state["town"], state["station"] = "Bramhollow", "BRD TV 8"
    tv.OUT.mkdir(parents=True, exist_ok=True)
    reports = []
    for _ in range(args.days):
        day = advance(state)
        advance_incident(state, day)
        context = context_for(state, day)
        response = ask_model(client, args.model, context)
        programs = apply_response(state, day, context, response)
        prefix = f'day_{day["day"]:03d}'
        (tv.OUT / (prefix + "_cryptid_scripts.txt")).write_text(
            "\n\n".join(f'[{x["name"]}]\n{x["narration"]}' for x in programs) + "\n",
            encoding="utf-8")
        (tv.OUT / (prefix + "_cryptid_report.json")).write_text(
            json.dumps({"day": day, "nominations": state["cryptid_trial"]["names"],
                        "programs": [x["name"] for x in programs],
                        "disaster_public_facts": public_context(state, day)}, indent=2) + "\n",
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
