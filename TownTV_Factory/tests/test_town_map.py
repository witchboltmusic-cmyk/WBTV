"""Deterministic, read-only Channel 02 map tests. No external API or TTS."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from town_engine import initial_state, advance
from town_map import (PLACES, MINS, build_schedules, location_at, walking_path,
                      read_day_report, static_map, render_frame)


class TownMapTests(unittest.TestCase):
    def setUp(self):
        self.state = initial_state()
        self.daily = advance(self.state)

    def test_schedule_is_deterministic_and_does_not_change_shared_state(self):
        snapshot = json.dumps(self.state, sort_keys=True)
        one = build_schedules(self.state, self.daily)
        two = build_schedules(self.state, self.daily)
        self.assertEqual(one, two)
        self.assertEqual(json.dumps(self.state, sort_keys=True), snapshot)
        self.assertIn("sam", one)
        self.assertEqual(one["sam"][1][1], "depot")
        self.assertEqual(one["harold"][1][1], "hardware")
        self.assertEqual(one["ellen"][1][1], "library")
        self.assertEqual(one["sam"][-1][1], one["sam"][0][1])

    def test_people_out_of_town_are_not_on_map(self):
        self.state["residents"]["harold"]["status"] = "away"
        schedule = build_schedules(self.state, self.daily)
        self.assertNotIn("harold", schedule)

    def test_routes_use_actual_streets_not_diagonal_teleporting(self):
        points = walking_path("hardware", "cinema")
        self.assertEqual(points[0], PLACES["hardware"]["at"])
        self.assertEqual(points[-1], PLACES["cinema"]["at"])
        self.assertTrue(any(p[1] == 97 for p in points))
        self.assertTrue(any(p[1] == 173 for p in points))
        self.assertTrue(any(p[0] in (156, 318) for p in points))
        for a, b in zip(points, points[1:]):
            self.assertTrue(a[0] == b[0] or a[1] == b[1],
                            f"Not a sidewalk route: {a} to {b}")

    def test_position_transitions_follow_timeline(self):
        schedule = [(360, "west_homes", "At home"), (480, "hardware", "Work")]
        home = location_at(schedule, 365)
        commute = location_at(schedule, 470)
        work = location_at(schedule, 500)
        self.assertFalse(home[-1])
        self.assertTrue(commute[-1])
        self.assertFalse(work[-1])
        self.assertEqual(work[2], "hardware")

    def test_video_frame_renders_without_editing_history(self):
        schedules = build_schedules(self.state, self.daily)
        before = deepcopy(self.state)
        base = static_map(self.state)
        frame = render_frame(base, self.state, self.daily, schedules, 6, 12)
        self.assertEqual(frame.size, (960, 540))
        self.assertEqual(before, self.state)

    def test_day_report_is_used_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"day_001_cryptid_report.json"
            p.write_text(json.dumps({"day": self.daily}), encoding="utf-8")
            loaded=read_day_report(p,self.state)
            self.assertEqual(loaded,self.daily)
            self.assertEqual(loaded["weather"],self.daily["weather"])


if __name__ == "__main__":
    unittest.main()
