import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.audio import run_ffmpeg
from audio_engine.contract import ContractError, validate_program
from audio_engine.effects import public_capabilities
from audio_engine.render import render_program


class FakeProvider:
    name = "fake"
    processing = "local-test"

    def __init__(self, duration=2.0):
        self.calls = 0
        self.duration = duration

    def synthesize(self, segment, path):
        self.calls += 1
        run_ffmpeg([
            "-f", "lavfi",
            "-i", f"sine=frequency=440:sample_rate=24000:duration={self.duration}",
            "-ac", "1",
            "-c:a", "libmp3lame",
            "-b:a", "64k",
            str(path),
        ])


def make_event(path, duration=8.0):
    run_ffmpeg([
        "-f", "lavfi",
        "-i", f"sine=frequency=660:sample_rate=24000:duration={duration}",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(path),
    ])


def bridge_program():
    return {
        "schema_version": 5,
        "id": "bridge",
        "title": "Bridge",
        "profile": "speech",
        "lead_in_ms": 100,
        "soundscape": {
            "events": [
                {
                    "file": "hooves.wav",
                    "role": "bridge",
                    "after_segment": 1,
                    "foreground_ms": 1800,
                    "carry_under_speech_ms": 1400,
                    "gain_db": -20,
                    "placement": "left"
                }
            ],
            "ducking": "speech"
        },
        "segments": [
            {"voice": "voice-a", "text": "First.", "pause_after_ms": 100},
            {"voice": "voice-a", "text": "Second.", "pause_after_ms": 100},
        ]
    }


class V5IntentTests(unittest.TestCase):
    def test_catalog_exposes_bridge_and_short_segment_acoustic_accent(self):
        catalog = public_capabilities(engine_version="test")
        self.assertEqual(catalog["feature_level"], "narrative-sound-direction-v2")
        roles = {item["id"] for item in catalog["effects"]["sound_roles"]}
        self.assertIn("bridge", roles)
        usage = {item["id"]: item for item in catalog["effects"]["acoustic_usage"]}
        self.assertEqual(usage["accent"]["implementation"], "short-segment")
        self.assertLessEqual(usage["accent"]["recommended_max_rendered_ms"], 2500)

    def test_v4_rejects_bridge_semantics(self):
        data = bridge_program()
        data["schema_version"] = 4
        with self.assertRaises(ContractError):
            validate_program(data)

    def test_bridge_requires_following_segment_and_bounded_durations(self):
        data = bridge_program()
        self.assertEqual(validate_program(data)["schema_version"], 5)

        data["soundscape"]["events"][0]["after_segment"] = 2
        with self.assertRaises(ContractError):
            validate_program(data)

        data = bridge_program()
        data["soundscape"]["events"][0]["foreground_ms"] = 100
        with self.assertRaises(ContractError):
            validate_program(data)

        data = bridge_program()
        data["soundscape"]["events"][0]["carry_under_speech_ms"] = 100
        with self.assertRaises(ContractError):
            validate_program(data)

    def test_bridge_foreground_is_actual_solo_time_then_carries_under_next_voice(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            make_event(root / "hooves.wav")
            program = root / "bridge.json"
            data = bridge_program()
            program.write_text(json.dumps(data), encoding="utf-8")
            provider = FakeProvider()
            out = root / "out"

            first = render_program(program, out, provider=provider)
            self.assertEqual(provider.calls, 2)
            timeline = first["mix"]["timeline"]
            bridge = first["mix"]["soundscape"]["components"][0]

            self.assertEqual(first["program_schema_version"], 5)
            self.assertEqual(bridge["intent_role"], "bridge")
            self.assertEqual(bridge["foreground_ms"], 1800.0)
            self.assertEqual(bridge["carry_under_speech_ms"], 1400.0)
            self.assertEqual(bridge["requested_play_duration_ms"], 3200.0)
            self.assertFalse(bridge["duration_clipped"])
            self.assertGreater(bridge["fade_in_ms"], 0)
            self.assertGreater(bridge["fade_out_ms"], 0)

            solo_ms = timeline[2]["start_ms"] - bridge["at_ms"]
            self.assertAlmostEqual(solo_ms, 1800.0, delta=2.0)
            self.assertGreater(
                bridge["at_ms"] + bridge["play_duration_ms"],
                timeline[2]["start_ms"],
            )

            fingerprints = first["mix"]["voice_fingerprints"]
            data["soundscape"]["events"][0]["carry_under_speech_ms"] = 2200
            program.write_text(json.dumps(data), encoding="utf-8")
            remixed = render_program(program, out, provider=provider)
            self.assertEqual(provider.calls, 2)
            self.assertEqual(remixed["mix"]["voice_cache_hits"], 2)
            self.assertEqual(remixed["mix"]["voice_fingerprints"], fingerprints)
            bridge2 = remixed["mix"]["soundscape"]["components"][0]
            self.assertEqual(bridge2["requested_play_duration_ms"], 4000.0)

    def test_bridge_reports_clipping_when_master_ends_before_requested_carry(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            make_event(root / "hooves.wav")
            program = root / "bridge.json"
            program.write_text(json.dumps(bridge_program()), encoding="utf-8")
            result = render_program(program, root / "out", provider=FakeProvider(duration=0.25))
            bridge = result["mix"]["soundscape"]["components"][0]
            self.assertTrue(bridge["duration_clipped"])
            self.assertTrue(bridge["clipped_by_master"])
            self.assertFalse(bridge["clipped_by_source"])


if __name__ == "__main__":
    unittest.main()
