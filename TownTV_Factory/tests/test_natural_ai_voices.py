"""Offline safety tests for BRD natural AI voices. No billed API calls."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import openai_voice

class VoiceAuditionTests(unittest.TestCase):
    def test_consistent_female_anchor_and_unique_callers(self):
        anchor = openai_voice.PROFILE["anchor"]
        self.assertEqual(anchor["voice"], "shimmer")
        self.assertIn("woman", anchor["style"].lower())
        self.assertIn("Medium-slow", anchor["style"])
        # The news and weather shows can share an announcer; callers cannot.
        names = ["sam", "harold", "ellen", "host"]
        ids = [openai_voice.PROFILE[x]["voice"] for x in names]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(p["style"] for p in openai_voice.PROFILE.values()))

    def test_anchor_cadence_preserves_all_words(self):
        original = ("Tonight's leading story: Sam Evers says he saw a figure. "
                    "The town has not agreed, and a meeting is expected.")
        spoken = openai_voice.format_spoken_copy(original, "anchor")
        self.assertIn("\n\n", spoken)
        self.assertIn(":\n", spoken)
        self.assertEqual(" ".join(spoken.split()), original)
        self.assertEqual(openai_voice.format_spoken_copy(original, "sam"), original)

    def test_rejects_unknown_speaker(self):
        with self.assertRaises(ValueError):
            openai_voice.profile_for("unknown")

    def test_require_api_key_before_network(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                openai_voice._generate_pcm("Hello.", openai_voice.PROFILE["sam"])

    def test_reject_empty_audio(self):
        with self.assertRaisesRegex(ValueError, "zero speech"):
            openai_voice.synthesize([], "/tmp/do-not-create.wav")

if __name__ == "__main__":
    unittest.main()
