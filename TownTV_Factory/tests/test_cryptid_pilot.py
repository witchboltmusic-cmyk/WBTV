"""Offline cryptid tests: no paid API calls or video rendering."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# This test imports the pilot in CI after the OpenAI package is installed.
from town_engine import initial_state, advance
from apocalypse_engine import advance_incident
from cryptid_trial import context_for, apply_response, VOICES, SCHEMA

def fake_response(phase, caller="sam"):
    options = {
        1: [{"resident_id":"sam","name":"Reservoir Rambler"}],
        2: [{"resident_id":"harold","name":"Mud Walker"},
            {"resident_id":"ellen","name":"Northbank Visitor"}],
        3: [],
    }
    return {
        "lead_headline": (
            "Sam Evers Names Reservoir Animal Amid Confusion"
            if phase == 1 else
            "Harold Vale Challenges Ellen Price Over Creature Name"
        ),
        "nominations": options.get(phase, []),
        "opinions": [{"resident_id":who, "belief":"Unconfirmed sighting",
                      "stance":"Name matters"} for who in ("sam","harold","ellen")],
        "shows": {
            "news": {"narration":"Bramhollow residents discussed a proposed name for an unidentified animal near the reservoir."},
            "weather":{"narration":"Clouds and light rain are expected in portions of Morrow County this afternoon.",
                       "footnote":"Reduced visibility possible near the reservoir."},
            "swap_shop":{"narration":"A resident has asked for a spare suggestion box for a local naming poll.",
                         "listing":"Wanted: spare suggestion box"},
            "night_line":{"turns":[
                {"speaker_id": "host" if i % 2 == 0 else caller,
                 "text": ("Where did that happen? Please tell me the street."
                          if i % 2 == 0 else
                          "I was standing on the corner beside the library.")}
                for i in range(14)]},
        },
    }

class CryptidPilotTests(unittest.TestCase):
    def test_three_day_continuity(self):
        state = initial_state()
        for phase in range(1, 4):
            daily = advance(state)
            context = context_for(state,daily)
            self.assertEqual(context["phase"], phase)
            programs = apply_response(state,daily,context,
                                      fake_response(phase, context["call_in_guest"]["resident_id"]))
            self.assertEqual([p["name"] for p in programs],
                             ["News","Weather","Swap Shop","Night Line"])
            self.assertFalse(state["cryptid_trial"]["minds"]["harold"]["witnessed"])
            self.assertFalse(state["cryptid_trial"]["minds"]["ellen"]["witnessed"])
            self.assertTrue(state["cryptid_trial"]["minds"]["sam"]["witnessed"])
            self.assertEqual(len(state["cryptid_trial"]["public_record"]),phase)
            self.assertEqual(daily["cryptid"]["headline"],fake_response(phase)["lead_headline"])
            self.assertEqual(len(programs[-1]["segments"]),14)
        self.assertEqual(len(state["cryptid_trial"]["names"]),3)

    def test_horror_continuity_prevents_dead_or_missing_callers(self):
        state = initial_state()
        for phase in range(1, 7):
            daily = advance(state)
            advance_incident(state, daily)
            context = context_for(state, daily)
            available = context["available_speakers"]
            guest = context["call_in_guest"]
            self.assertTrue(guest is None or
                            state["residents"][guest["resident_id"]]["status"] == "home")
            result = fake_response(phase, guest["resident_id"] if guest else "sam")
            result["lead_headline"] = daily["horror"]["headline"]
            result["opinions"] = [p for p in result["opinions"]
                                  if p["resident_id"] in available]
            if phase == 4:
                self.assertNotIn("harold", available)
                invalid = fake_response(phase)
                invalid["lead_headline"] = result["lead_headline"]
                with self.assertRaises(ValueError):
                    apply_response(state,daily,context,invalid)
            programs = apply_response(state,daily,context,result)
            self.assertEqual(len(programs),4)
            self.assertEqual(programs[0]["display"], daily["horror"]["headline"])
            self.assertEqual(
                set(who for who, _ in programs[-1]["segments"]),
                {"host", guest["resident_id"]}
            )
            self.assertEqual(
                [who for who, _ in programs[-1]["segments"]],
                ["host" if i % 2 == 0 else guest["resident_id"]
                 for i in range(14)]
            )
        self.assertNotIn("sam", context["available_speakers"])
        self.assertEqual(state["residents"]["sam"]["status"], "missing")
        self.assertEqual(state["residents"]["harold"]["status"], "dead")

    def test_nightline_rejects_panel_discussion_and_same_speaker_twice(self):
        state = initial_state()
        daily = advance(state)
        context = context_for(state, daily)
        guest = context["call_in_guest"]["resident_id"]
        bad = fake_response(1, guest)
        bad["shows"]["night_line"]["turns"][3]["speaker_id"] = "ellen"
        with self.assertRaisesRegex(ValueError, "ONE live caller"):
            apply_response(state, daily, context, bad)
        repeated = fake_response(1, guest)
        repeated["shows"]["night_line"]["turns"][3]["speaker_id"] = "host"
        with self.assertRaisesRegex(ValueError, "ONE live caller"):
            apply_response(state, daily, context, repeated)
        self.assertEqual(state["cryptid_trial"]["public_record"], [])

    def test_guest_selection_avoids_deceased_and_repeated_callers(self):
        from cryptid_trial import select_nightline_guest
        state = initial_state()
        day1 = advance(state)
        a = select_nightline_guest(state, day1)
        state["cryptid_trial"] = {"last_nightline_guest": a["resident_id"]}
        day2 = advance(state)
        b = select_nightline_guest(state, day2)
        self.assertNotEqual(a["resident_id"], b["resident_id"])
        state["residents"][b["resident_id"]]["status"] = "dead"
        c = select_nightline_guest(state, day2)
        self.assertNotEqual(c["resident_id"], b["resident_id"])
        for item in state["residents"].values():
            item["status"] = "dead"
        self.assertIsNone(select_nightline_guest(state, day2))

    def test_reject_unexpected_witness_nomination(self):
        state = initial_state()
        daily = advance(state)
        context = context_for(state,daily)
        invalid = fake_response(1)
        invalid["nominations"].append({"resident_id":"ellen","name":"Another Name"})
        with self.assertRaises(ValueError):
            apply_response(state,daily,context,invalid)
        self.assertEqual(state["cryptid_trial"]["names"],{})

    def test_new_horror_episodes_use_the_existing_openai_voice_cast(self):
        import cryptid_trial as pilot
        import openai_voice
        previous = pilot.tv.synthesize
        try:
            self.assertEqual(pilot.configure_voice_renderer("realtime"), "realtime")
            self.assertIs(pilot.tv.synthesize, openai_voice.synthesize)
            self.assertEqual(openai_voice.PROFILE["anchor"]["voice"], "shimmer")
            self.assertTrue(openai_voice.PROFILE["anchor"]["style"].startswith("ONE adult woman"))
            for speaker in ("host", "weather", "swap_host", "sam", "harold", "ellen"):
                self.assertIn(speaker, openai_voice.PROFILE)
        finally:
            pilot.tv.synthesize = previous

    def test_stable_voice_profiles_and_strict_schema(self):
        self.assertNotEqual(VOICES["sam"],VOICES["harold"])
        self.assertNotEqual(VOICES["harold"],VOICES["ellen"])
        self.assertFalse(SCHEMA["additionalProperties"])

if __name__ == "__main__":
    unittest.main()
