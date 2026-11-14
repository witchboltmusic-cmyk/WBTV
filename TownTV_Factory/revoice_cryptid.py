#!/usr/bin/env python3
"""Render already-generated cryptid broadcasts with new voices, at zero LLM cost.

Downloads the existing pilot scripts/reports artifact before running. This
reuses the original narration and original LLM-authored Night Line conversation,
preserving story details and persistent character nominations.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil

import cryptid_trial as pilot
import generate as tv

ROOT = Path(__file__).resolve().parent


def parse_scripts(file):
    source = file.read_text(encoding="utf-8")
    matcher = re.compile(r"(?m)^\[(News|Weather|Swap Shop|Night Line)\]\n")
    parts = list(matcher.finditer(source))
    if len(parts) != 4:
        raise ValueError(f"Expected four program scripts in {file}, found {len(parts)}")
    return {m.group(1): source[m.end(): (parts[i+1].start() if i+1 < len(parts) else len(source))].strip()
            for i, m in enumerate(parts)}


def revoice_one(daily, programs, dialogue, state):
    headline = daily["cryptid"]["headline"]
    regular_news = next((e["headline"] for e in daily.get("events", [])
                         if e.get("category") == "community" and e.get("thread") != "cryptid_naming"),
                        "Local community bulletins")
    def single(name, speaker, display, second):
        return {"name": name, "segments": [(speaker, programs[name])],
                "narration": programs[name], "display": display,
                "second": second, "events": [headline]}
    result = [
        single("News", "anchor", headline, regular_news),
        single("Weather", "weather", daily["weather"]["label"], daily["weather"]["forecast"]),
        single("Swap Shop", "swap_host", daily["swap"], "County classifieds"),
        {"name": "Night Line",
         "segments": [(x["speaker_id"], x["text"]) for x in dialogue],
         "narration": " ".join(x["text"] for x in dialogue),
         "display": daily["call"]["caller_text"], "second": "Open telephone lines",
         "events": [headline]},
    ]
    clips = []
    for program in result:
        output = tv.render_program(program, daily, state, "piper")
        if output.get("voice_engine") != "piper":
            raise RuntimeError("Output used old speech engine: " + str(output))
        clips.append(output)
    return clips


def main():
    ap = argparse.ArgumentParser(description="Re-render pilot's ORIGINAL scripts with separate Piper voices")
    ap.add_argument("--state", type=Path, default=pilot.TRIAL_STATE)
    ap.add_argument("--out", type=Path, default=tv.OUT)
    args = ap.parse_args()
    if not args.state.exists():
        ap.error("Persistent pilot state missing; cannot recover character dialogue")
    state = json.loads(args.state.read_text("utf-8"))
    record = state.get("cryptid_trial", {})
    dialogue_by_day = {x["day"]: x["turns"] for x in record.get("recent_dialogue", [])}
    tv.OUT = args.out
    tv.OUT.mkdir(exist_ok=True, parents=True)
    tv.TEMP = args.out / "_render"
    pilot.active_voice_engine("piper")
    tv.synthesize = pilot.speak
    reports = sorted(args.out.glob("day_*_cryptid_report.json"))
    if not reports:
        ap.error("No prior LLM pilot reports were downloaded into " + str(args.out))
    render_log = []
    for report_path in reports:
        day = json.loads(report_path.read_text("utf-8"))["day"]
        day_number = day["day"]
        original_scripts = args.out / f"day_{day_number:03d}_cryptid_scripts.txt"
        if not original_scripts.exists():
            raise FileNotFoundError(f"Original scripts not found: {original_scripts}")
        turns = dialogue_by_day.get(day_number)
        if not turns:
            raise RuntimeError(f"Original multi-speaker Night Line dialogue for Day {day_number} "
                               "is missing from saved state; refusing to invent replacement dialogue")
        scripts = parse_scripts(original_scripts)
        try:
            clips = revoice_one(day, scripts, turns, state)
        finally:
            shutil.rmtree(tv.TEMP, ignore_errors=True)
        render_log.append({"day": day_number, "date": day["air_date"], "clips": clips})
        print(f"Revoiced Day {day_number} with Piper neural voices; preserved original story.")
    (args.out / "cryptid_piper_revoice_manifest.json").write_text(
        json.dumps({"engine": "piper", "new_llm_calls": 0,
                    "source": "original BRD cryptid pilot", "reports": render_log}, indent=2) + "\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
