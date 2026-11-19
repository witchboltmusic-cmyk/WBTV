"""Offline tests: persistent horror simulation, no paid API and no rendered gore."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from town_engine import initial_state, upgrade_state, advance, make_swap, make_call, resident_activity
from apocalypse_engine import advance_incident, public_context


class ApocalypseContinuityTests(unittest.TestCase):
    def test_incidents_persist_over_existing_world_history(self):
        state = initial_state()
        old_day = advance(state)
        state["cryptid_trial"] = {
            "first_day": 1, "names": {"sam": "Longshape"},
            "minds": {}, "public_record": [], "recent_dialogue": [],
        }
        old_history = deepcopy(state["history"])
        for index in range(7):
            day = advance(state)
            incident = advance_incident(state, day)
            self.assertEqual(incident["day"], day["day"])
            self.assertEqual(state["apocalypse"]["last_day"], day["day"])
            self.assertEqual(day["events"][0]["headline"], incident["headline"])
            self.assertEqual(day["horror"]["confirmed_deaths_total"],
                             state["apocalypse"]["total_confirmed_dead"])
            self.assertTrue(any(x == old_history[0] for x in state["history"]))
            self.assertNotIn("entities", public_context(state, day))
            self.assertEqual(len(state["apocalypse"]["incidents"]), index + 1)
        self.assertEqual(state["residents"]["ernest"]["status"], "dead")
        self.assertEqual(state["residents"]["harold"]["status"], "dead")
        self.assertEqual(state["residents"]["sam"]["status"], "missing")
        self.assertEqual(state["businesses"]["hardware"]["status"], "destroyed")
        self.assertEqual(state["businesses"]["laundry"]["status"], "temporary_closed")
        self.assertGreater(state["apocalypse"]["total_confirmed_dead"], 60)
        self.assertIn("library", {x["place"] for x in state["apocalypse"]["closed_places"]})
        self.assertIn("station", {x["place"] for x in state["apocalypse"]["closed_places"]})
        restored = upgrade_state(json.loads(json.dumps(state)))
        self.assertEqual(restored["apocalypse"], state["apocalypse"])
        self.assertEqual(restored["cryptid_trial"], state["cryptid_trial"])
        self.assertEqual(restored["residents"]["harold"]["status"], "dead")

    def test_repeating_a_day_does_not_repeat_casualties(self):
        state = initial_state()
        day = advance(state)
        first = advance_incident(state, day)
        total = state["apocalypse"]["total_confirmed_dead"]
        repeated = advance_incident(state, day)
        self.assertEqual(first, repeated)
        self.assertEqual(state["apocalypse"]["total_confirmed_dead"], total)
        self.assertEqual(len(state["apocalypse"]["incidents"]), 1)

    def test_public_information_does_not_expose_private_entity_identity(self):
        state = initial_state()
        day = advance(state)
        advance_incident(state, day)
        record = public_context(state, day)
        self.assertTrue(record["enabled"])
        self.assertIn("official_bulletin", record)
        for secret in ("entities", "THREAT_TYPES", "agenda", "secret", "objective"):
            self.assertNotIn(secret, json.dumps(record))
        self.assertNotIn("public_disaster", state)

    def test_no_dead_people_reappear_in_generic_town_generator(self):
        state = initial_state()
        for person in state["residents"].values():
            person["status"] = "dead"
        # Underlying town engine must never pull deceased people into its routine
        # callers, swap listings, or volunteer announcements.
        rng = __import__("random").Random(19)
        swap = make_swap(state, 100, rng, None)
        caller = make_call(state, 100, rng, None, None)
        citizen = resident_activity(state, 100, rng)
        for value in (swap, json.dumps(caller), citizen["text"]):
            for person in state["residents"].values():
                self.assertNotIn(person["name"], value)


if __name__ == "__main__":
    unittest.main()
