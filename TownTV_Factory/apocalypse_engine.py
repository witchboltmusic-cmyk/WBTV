#!/usr/bin/env python3
"""Persistent fictional disaster engine for Bramhollow's TV broadcasts.

The engine (not the writing model) owns physical changes, casualties, missing
persons, damaged places, threats, chronology and public knowledge. A survivor
cannot call the station after being recorded dead. Existing history stays intact.
All events and locations are fictional. This module NEVER calls an AI API.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import random

# The station never receives these labels; they are internal simulation rules.
ZONES = (
    "reservoir", "depot", "school", "library", "hardware",
    "laundry", "residential", "town_hall", "eastern_road", "station",
)
THREAT_TYPES = {
    "a": {"zones": ("reservoir", "school", "residential", "library"),
          "pace": 1, "intensity": 2},
    "b": {"zones": ("depot", "laundry", "hardware", "eastern_road"),
          "pace": 2, "intensity": 3},
    "c": {"zones": ("eastern_road", "town_hall", "station", "residential"),
          "pace": 1, "intensity": 4},
}
# Each stage is a factual event. The broadcaster gets the public_description,
# NOT the hidden threat types, agenda, rules or internal coordinates.
INCIDENTS = (
    {
        "place": "reservoir", "time": "05:41", "casualties": 0,
        "headline": "County crews abandon reservoir inspection after equipment failure",
        "public_description": (
            "A county inspection crew found an upright white structure standing behind "
            "the reservoir pump building. It measured approximately nineteen feet from "
            "the ground to its highest visible point. Six folded projections extended "
            "from its back. A tractor stalled forty feet away. The crew left the site "
            "when every work light failed in sequence. No injuries were reported."
        ),
        "changes": [],
    },
    {
        "place": "laundry", "time": "19:06", "casualties": 2,
        "headline": "Two confirmed dead following West End Laundromat emergency",
        "public_description": (
            "Emergency workers recovered two bodies at West End Laundromat. Both were "
            "found standing against a locked service door. The medical examiner reported "
            "that their clothing was fused to the painted metal. The victims had been "
            "heard knocking from inside the wall after the building was evacuated. "
            "The structure is closed, and June Mercer was hospitalized following exposure."
        ),
        "changes": [("injured", "june"), ("closed", "laundry")],
    },
    {
        "place": "library", "time": "21:38", "casualties": 1,
        "headline": "Resident killed after library corridor sealed itself",
        "public_description": (
            "Ernest Pike was confirmed dead in an incident at Bramhollow Library. "
            "A corridor wall was found extending through a doorway that had been open "
            "minutes earlier. His body was located on the opposite side without any "
            "break in the plaster. A maintenance worker said the wall was still warm. "
            "The library has closed until further notice."
        ),
        "changes": [("dead", "ernest"), ("closed", "library")],
    },
    {
        "place": "hardware", "time": "18:22", "casualties": 4,
        "headline": "Vale Hardware destroyed; owner among confirmed dead",
        "public_description": (
            "Four people were killed inside Vale Hardware after the storefront folded "
            "inward without an explosion. Owner Harold Vale is among the dead. "
            "Fire crews located the front door on the basement ceiling, still attached "
            "to the frame. The business has been permanently closed. Authorities "
            "have ordered residents to leave the adjoining block."
        ),
        "changes": [("dead", "harold"), ("destroyed", "hardware")],
    },
    {
        "place": "residential", "time": "13:17", "casualties": 37,
        "headline": "Thirty-seven deaths confirmed in Willow Street incident",
        "public_description": (
            "County dispatch confirmed thirty-seven deaths after a series of white "
            "figures entered occupied homes on Willow Street. Doors and windows "
            "remained locked. Responders reported that the figures passed through "
            "interior walls without damaging them. Several rooms were found empty "
            "except for neatly folded clothing and human teeth embedded in the floor. "
            "Violet Dunn is among those confirmed dead."
        ),
        "changes": [("dead", "violet"), ("evacuated", "residential")],
    },
    {
        "place": "eastern_road", "time": "07:12", "casualties": 63,
        "headline": "Evacuation convoy returns with missing and deceased passengers",
        "public_description": (
            "Sixty-three deaths were confirmed after the county evacuation convoy "
            "returned to Bramhollow from the opposite direction of travel. Several "
            "vehicles were filled with soil to the windows. Their occupants had not "
            "been aboard at departure. The eastern highway has been replaced for "
            "two miles by a smooth, warm surface. Transit driver Sam Evers remains "
            "missing; no death has been confirmed."
        ),
        "changes": [("missing", "sam"), ("closed", "depot")],
    },
    {
        "place": "station", "time": "23:43", "casualties": 11,
        "headline": "BRD TV 8 transmitter building sealed during live broadcast",
        "public_description": (
            "Eleven deaths were confirmed in and around the BRD TV 8 transmitter "
            "building. Emergency teams found the stairwell filled with interlocking "
            "white material that moved when touched. The building's doors no longer "
            "connect to the lobby. The studio remains on auxiliary power and "
            "continues transmitting recorded material."
        ),
        "changes": [("closed", "station")],
    },
)
LATER_INCIDENTS = (
    {
        "place": "town_hall", "time": "04:12", "casualties": 9,
        "headline": "Courthouse basement recovered without building above it",
        "public_description": (
            "Nine deaths are confirmed after the upper floors of Town Hall vanished. "
            "The basement and its utility connections remain undamaged. The missing "
            "floors were last seen from the county road at 4:12 this morning."
        ),
        "changes": [("destroyed", "town_hall")],
    },
    {
        "place": "school", "time": "12:26", "casualties": 14,
        "headline": "County school declared unsafe following noon incident",
        "public_description": (
            "Fourteen adults were killed after a white structure appeared above "
            "the school parking lot. Emergency responders found rows of identical "
            "handprints on the inside of the gymnasium ceiling. The building has "
            "been evacuated and school operations suspended."
        ),
        "changes": [("closed", "school")],
    },
    {
        "place": "residential", "time": "02:03", "casualties": 6,
        "headline": "Emergency crews withdraw from western residential block",
        "public_description": (
            "Six additional deaths were confirmed in homes west of the town square. "
            "Rescue crews reported hearing the deceased call from behind exterior "
            "walls while standing beside the recovered bodies. The affected block "
            "has been declared inaccessible."
        ),
        "changes": [("evacuated", "west_residential")],
    },
)
CLOSED_STATES = {"closed": "temporary_closed", "destroyed": "destroyed"}
UNAVAILABLE = {"dead", "missing", "moved", "away", "evacuated", "injured"}


def get_state(state, day):
    """Create the horror chronology only once. Never reset an existing history."""
    return state.setdefault("apocalypse", {
        "first_day": day,
        "last_day": day - 1,
        "stage": 0,
        "total_confirmed_dead": 0,
        "confirmed_missing": [],
        "confirmed_dead": [],
        "closed_places": [],
        "entities": {
            key: {"zone": spec["zones"][0], "arrived": False,
                  "encounters": 0}
            for key, spec in THREAT_TYPES.items()
        },
        "incidents": [],
    })


def _pick_record(first_day, index, seed):
    if index < len(INCIDENTS):
        return deepcopy(INCIDENTS[index])
    # Later events differ deterministically but never rewrite past incidents.
    rng = random.Random((seed ^ first_day * 1013) + index * 9917)
    return deepcopy(LATER_INCIDENTS[rng.randrange(len(LATER_INCIDENTS))])


def _move_entities(record, stage):
    for key, spec in THREAT_TYPES.items():
        entity = record["entities"][key]
        if stage < (1 if key == "a" else 3 if key == "b" else 5):
            continue
        zones = spec["zones"]
        previous = entity["zone"]
        position = zones.index(previous) if previous in zones else 0
        entity["zone"] = zones[(position + spec["pace"]) % len(zones)]
        entity["arrived"] = True
        entity["encounters"] += 1


def _apply_person_change(state, record, change, person_id, day):
    person = state.get("residents", {}).get(person_id)
    if person is None:
        return None
    old = person.get("status", "home")
    if change == "dead":
        if old == "dead":
            return None
        person["status"] = "dead"
        person["away_until"] = 0
        person["fate_day"] = day
        if person_id not in record["confirmed_dead"]:
            record["confirmed_dead"].append(person_id)
    elif change == "missing":
        if old in ("dead", "missing"):
            return None
        person["status"] = "missing"
        person["away_until"] = 0
        person["fate_day"] = day
        if person_id not in record["confirmed_missing"]:
            record["confirmed_missing"].append(person_id)
    elif change == "injured":
        if old in ("dead", "missing", "moved"):
            return None
        person["status"] = "injured"
        person["fate_day"] = day
    else:
        return None
    return {"resident_id": person_id, "name": person["name"],
            "previous_status": old, "status": person["status"]}


def _apply_site_change(state, record, change, place, day):
    if change in CLOSED_STATES and place in state.get("businesses", {}):
        site = state["businesses"][place]
        site["status"] = CLOSED_STATES[change]
        site["reopen_day"] = 10**9
        item = {"place": place, "name": site["name"],
                "status": site["status"], "day": day}
    else:
        # Library, station, school, and roads are tracked even though they
        # aren't ordinary commercial businesses in town_engine.py.
        item = {"place": place, "status": change, "day": day}
    existing = next((x for x in record["closed_places"] if x["place"] == place), None)
    if existing:
        existing.update(item)
    else:
        record["closed_places"].append(item)
    return item


def advance_incident(state, daily):
    """Advance by at most one day and share only public incident facts.

    Idempotent on repeat. Deaths are actual state changes. No invented
    causal explanation or theological identity reaches the broadcaster.
    """
    day = int(daily["day"])
    record = get_state(state, day)
    if day < record["last_day"]:
        raise ValueError("Cannot rewind a persistent disaster")
    if day == record["last_day"]:
        past = next((x for x in record["incidents"] if x["day"] == day), None)
        if past:
            daily["horror"] = deepcopy(past)
            return past
        raise ValueError("Recorded horror day is missing from chronology")
    if day != record["last_day"] + 1:
        raise ValueError("Disaster simulation requires contiguous days")
    index = day - record["first_day"]
    incident = _pick_record(record["first_day"], index, int(state["seed"]))
    stage = min(7, index + 1)
    _move_entities(record, stage)
    changes = []
    for kind, subject in incident.pop("changes"):
        if kind in {"dead", "missing", "injured"}:
            result = _apply_person_change(state, record, kind, subject, day)
        else:
            result = _apply_site_change(state, record, kind, subject, day)
        if result:
            changes.append(result)
    record["total_confirmed_dead"] += incident["casualties"]
    incident.update({
        "day": day,
        "stage": stage,
        "confirmed_deaths_today": incident.pop("casualties"),
        "confirmed_deaths_total": record["total_confirmed_dead"],
        "verified_changes": changes,
        "confirmed_missing": list(record["confirmed_missing"]),
        "confirmed_dead": list(record["confirmed_dead"]),
        "classification": "confirmed county incident bulletin",
    })
    record["last_day"] = day
    record["stage"] = stage
    record["incidents"].append(deepcopy(incident))
    record["incidents"] = record["incidents"][-90:]
    public_event = {
        "day": day, "headline": incident["headline"], "text": incident["public_description"],
        "category": "emergency", "surreal": True, "thread": "county_emergency",
        "location": incident["place"], "time": incident["time"],
        "confirmed_deaths": incident["confirmed_deaths_today"],
    }
    daily["events"].insert(0, public_event)
    state.setdefault("history", []).append(public_event)
    state["history"] = state["history"][-800:]
    daily["horror"] = deepcopy(incident)
    daily["businesses_closed"] = [
        b["name"] for b in state.get("businesses", {}).values()
        if b.get("status") != "open"
    ]
    return incident


def public_context(state, daily):
    """Only ground truth that has reached residents or officials."""
    incident = daily.get("horror")
    if not incident:
        return {"enabled": False}
    record = state["apocalypse"]
    return {
        "enabled": True,
        "day": incident["day"],
        "stage": incident["stage"],
        "official_bulletin": {
            k: incident[k] for k in (
                "headline", "public_description", "place", "time",
                "confirmed_deaths_today", "confirmed_deaths_total",
                "verified_changes", "classification"
            )
        },
        "recent_confirmed_incidents": [
            {"day": i["day"], "headline": i["headline"],
             "text": i["public_description"],
             "fatalities": i["confirmed_deaths_today"]}
            for i in record["incidents"][-4:]
        ],
        "resident_status": {
            k: {"name": v["name"], "status": v.get("status", "home")}
            for k, v in state.get("residents", {}).items()
        },
        "closed_sites": deepcopy(record["closed_places"]),
        "total_confirmed_deaths": record["total_confirmed_dead"],
        "known_missing": deepcopy(record["confirmed_missing"]),
        # SECRET entity types, locations, abilities and objectives are excluded.
    }
