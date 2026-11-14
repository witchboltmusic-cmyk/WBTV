"""Offline safety tests for BRD natural AI voices. No billed API calls."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import openai_voice

class VoiceAuditionTests(unittest.TestCase):
    def test_distinct_named_character_voices(self):
        names = ["sam", "harold", "ellen", "host", "anchor", "weather", "swap_host"]
        ids = [openai_voice.PROFILE[x]["voice"] for x in names]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(openai_voice.PROFILE[x]["style"] for x in names))

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
