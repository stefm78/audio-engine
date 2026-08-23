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

    def __init__(self):
        self.calls = 0

    def synthesize(self, segment, path):
        self.calls += 1
        run_ffmpeg([
            "-f", "lavfi",
            "-i", "sine=frequency=440:sample_rate=24000:duration=0.20",
            "-ac", "1",
            "-c:a", "libmp3lame",
            "-b:a", "64k",
            str(path),
        ])


def make_event(path, duration=1.0):
    run_ffmpeg([
        "-f", "lavfi",
        "-i", f"sine=frequency=660:sample_rate=24000:duration={duration}",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(path),
    ])


class V4EffectsTests(unittest.TestCase):
    def test_capability_catalog_contains_only_bounded_public_features(self):
        catalog = public_capabilities(engine_version="test")
        self.assertEqual(catalog["version"], 2)
        self.assertIn(4, catalog["program_schema_versions"])
        self.assertIn(5, catalog["program_schema_versions"])
        spaces = {item["id"] for item in catalog["effects"]["acoustic_spaces"]}
        self.assertEqual(
            spaces,
            {"dry", "outdoor-open", "small-stone-room", "large-stone-interior", "confined-stone"},
        )
        self.assertFalse(catalog["policy"]["binaural_hrtf"])
        self.assertFalse(catalog["policy"]["arbitrary_plugin_chain"])

    def test_v3_rejects_v4_scene_fields(self):
        data = {
            "schema_version": 3,
            "id": "old",
            "title": "Old",
            "soundscape": {
                "events": [
                    {
                        "file": "bell.wav",
                        "at_ms": 100,
                        "role": "punctuation",
                    }
                ]
            },
            "segments": [{"voice": "voice-a", "text": "Test."}],
        }
        with self.assertRaises(ContractError):
            validate_program(data)

    def test_v4_scene_requires_segment_anchor_and_bounded_space(self):
        data = {
            "schema_version": 4,
            "id": "scene",
            "title": "Scene",
            "soundscape": {
                "events": [
                    {
                        "file": "bell.wav",
                        "role": "scene",
                        "after_segment": 1,
                        "space_ms": 1200,
                    }
                ]
            },
            "segments": [{"voice": "voice-a", "text": "Test."}],
        }
        self.assertEqual(validate_program(data)["schema_version"], 4)
        data["soundscape"]["events"][0]["space_ms"] = 100
        with self.assertRaises(ContractError):
            validate_program(data)

    def test_scene_reserves_voice_free_space_fades_and_reuses_dry_voice_cache(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            make_event(root / "bell.wav", duration=1.5)
            program = root / "scene.json"
            data = {
                "schema_version": 4,
                "id": "v4-scene",
                "title": "V4 scene",
                "profile": "speech",
                "acoustic_space": "large-stone-interior",
                "lead_in_ms": 100,
                "soundscape": {
                    "events": [
                        {
                            "file": "bell.wav",
                            "role": "scene",
                            "after_segment": 1,
                            "space_ms": 1400,
                            "gain_db": -20,
                            "placement": "right"
                        },
                        {
                            "file": "bell.wav",
                            "role": "punctuation",
                            "at_ms": 100,
                            "gain_db": -28
                        }
                    ],
                    "ducking": "speech"
                },
                "segments": [
                    {"voice": "voice-a", "text": "First.", "pause_after_ms": 100},
                    {"voice": "voice-a", "text": "Second.", "pause_after_ms": 100}
                ]
            }
            program.write_text(json.dumps(data), encoding="utf-8")
            provider = FakeProvider()
            out = root / "out"
            first = render_program(program, out, provider=provider)
            self.assertEqual(provider.calls, 2)
            self.assertEqual(first["program_schema_version"], 4)
            self.assertEqual(first["mix"]["timeline"][1]["pause_after_ms"], 1400.0)
            self.assertEqual(first["mix"]["timeline"][1]["acoustic_space"], "large-stone-interior")
            components = first["mix"]["soundscape"]["components"]
            scene = components[0]
            punctuation = components[1]
            self.assertEqual(scene["intent_role"], "scene")
            self.assertEqual(scene["after_segment"], 1)
            self.assertGreater(scene["fade_out_ms"], 0)
            self.assertGreater(scene["at_ms"], first["mix"]["timeline"][1]["end_ms"])
            self.assertEqual(punctuation["intent_role"], "punctuation")
            self.assertGreater(punctuation["fade_out_ms"], 0)

            first_voice_fingerprints = first["mix"]["voice_fingerprints"]
            data["acoustic_space"] = "small-stone-room"
            program.write_text(json.dumps(data), encoding="utf-8")
            remixed = render_program(program, out, provider=provider)
            self.assertEqual(provider.calls, 2)
            self.assertEqual(remixed["mix"]["voice_cache_hits"], 2)
            self.assertEqual(remixed["mix"]["voice_fingerprints"], first_voice_fingerprints)
            self.assertEqual(remixed["mix"]["timeline"][1]["acoustic_space"], "small-stone-room")


if __name__ == "__main__":
    unittest.main()
