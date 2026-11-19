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

    def test_split_retries_mismatched_long_transcript(self):
        large = "The building is closed and county crews remain outside. " * 14
        calls = []
        def fake(fragment, profile):
            calls.append(fragment)
            if len(fragment) > 300:
                raise openai_voice.SpeechMismatchError("mismatch 0.44")
            return b"\x10\x00" * 48  # valid-sized fake signed-16 PCM
        with patch.object(openai_voice, "_generate_pcm", side_effect=fake):
            audio = openai_voice._reliable_pcm(large, openai_voice.PROFILE["anchor"])
        self.assertGreater(len(calls), 2)
        self.assertEqual(calls[0], large)
        self.assertTrue(all(len(x) <= 300 for x in calls[1:]))
        self.assertGreater(len(audio), 96)
        self.assertEqual(
            openai_voice._normalize(" ".join(calls[1:])),
            openai_voice._normalize(large),
        )

    def test_repeated_short_mismatch_still_fails_closed(self):
        text = "This is a verified report."
        with patch.object(
            openai_voice, "_generate_pcm",
            side_effect=openai_voice.SpeechMismatchError("mismatch"),
        ) as generator:
            with self.assertRaisesRegex(
                openai_voice.SpeechMismatchError, "no mismatched audio",
            ):
                openai_voice._reliable_pcm(text, openai_voice.PROFILE["anchor"])
        self.assertEqual(generator.call_count, 3)

    def test_no_retry_on_unrelated_api_error(self):
        with patch.object(
            openai_voice, "_generate_pcm",
            side_effect=RuntimeError("Invalid API key"),
        ) as generator:
            with self.assertRaisesRegex(RuntimeError, "Invalid API key"):
                openai_voice._reliable_pcm("Hello.", openai_voice.PROFILE["host"])
        self.assertEqual(generator.call_count, 1)

    def test_all_resident_callers_have_persistent_audio_identity(self):
        from cryptid_trial import CALLER_CAST
        for speaker in CALLER_CAST:
            profile = openai_voice.profile_for(speaker)
            self.assertTrue(profile["telephone"])
            self.assertTrue(profile["voice"])
            self.assertTrue(profile["style"])

    def test_phone_turn_passes_prior_spoken_line_for_conversational_delivery(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        with TemporaryDirectory() as temp:
            dest = Path(temp) / "voice.wav"
            captured = []
            def fake_audio(text, profile):
                captured.append((text, profile.get("previous_turn")))
                return b"\\x00\\x00" * 24000
            with patch.object(openai_voice, "_reliable_pcm", side_effect=fake_audio):
                openai_voice._make_wave("Did you see the door?", "host", dest,
                                        previous_turn="oscar: The door was gone.")
            self.assertEqual(captured[0][0], "Did you see the door?")
            self.assertEqual(captured[0][1], "oscar: The door was gone.")
            self.assertTrue(dest.exists())

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
