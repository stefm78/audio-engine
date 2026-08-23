import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.audio import run_ffmpeg
from audio_engine.assemble import assemble_plan
from audio_engine.contract import ContractError, validate_program
from audio_engine.render import render_program
from audio_engine.voices import load_voice_config, public_catalog, recommend_presets


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


class SmokeTests(unittest.TestCase):
    def test_contract_rejects_empty_segments(self):
        with self.assertRaises(ContractError):
            validate_program({
                "schema_version": 1,
                "id": "bad",
                "title": "Bad",
                "segments": [],
            })

    def test_schema_v1_rejects_spatial_fields(self):
        with self.assertRaises(ContractError):
            validate_program({
                "schema_version": 1,
                "id": "bad-spatial",
                "title": "Bad spatial",
                "segments": [{
                    "voice": "test",
                    "text": "Test",
                    "placement": "left",
                }],
            })

    def test_voice_catalog_publishes_quality_gate(self):
        config, _ = load_voice_config()
        catalog = public_catalog(config)
        self.assertTrue(catalog["presets"])
        criteria = catalog["quality_validation"]["criteria"]
        self.assertEqual(criteria[0]["id"], "french_pronunciation")
        self.assertTrue(criteria[0]["eliminatory"])
        self.assertEqual(catalog["selection_rules"]["score_direction"], "lower-is-better")

    def test_voice_recommendation_uses_validated_palette(self):
        config, _ = load_voice_config()
        result = recommend_presets({
            "gender": "male",
            "age": "adult",
            "energy": 5,
            "authority": 3,
            "warmth": 4,
            "tags": ["narrateur", "vif"],
        }, config, limit=3)
        self.assertEqual(len(result["recommendations"]), 3)
        self.assertEqual(result["recommendations"][0]["preset"]["id"], "narrateur-vif")
        self.assertLessEqual(
            result["recommendations"][0]["score"],
            result["recommendations"][1]["score"],
        )

    def test_render_offline_provider_and_cache(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            program = root / "program.json"
            program.write_text(json.dumps({
                "schema_version": 1,
                "id": "smoke",
                "title": "Smoke",
                "profile": "speech",
                "segments": [
                    {
                        "voice": "unused-test-voice",
                        "text": "Test",
                        "pause_after_ms": 100,
                    }
                ],
            }), encoding="utf-8")
            out = root / "out"
            provider = FakeProvider()
            manifest = render_program(program, out, provider=provider)
            self.assertEqual(manifest["status"], "success")
            self.assertFalse(manifest["cache_hit"])
            self.assertEqual(provider.calls, 1)
            self.assertEqual(manifest["audio"]["bitrate_kbps"], 80)
            self.assertEqual(manifest["audio"]["sample_rate_hz"], 24000)
            self.assertEqual(manifest["audio"]["channels"], 1)
            self.assertTrue(manifest["render_fingerprint"])
            self.assertTrue((out / "smoke" / "audio.mp3").stat().st_size > 0)
            self.assertTrue((out / "smoke" / "manifest.json").exists())
            self.assertTrue((out / "smoke" / "transcript.json").exists())

            cached = render_program(program, out, provider=provider)
            self.assertTrue(cached["cache_hit"])
            self.assertEqual(provider.calls, 1)
            self.assertEqual(cached["render_fingerprint"], manifest["render_fingerprint"])

            program.write_text(json.dumps({
                "schema_version": 1,
                "id": "smoke",
                "title": "Smoke",
                "profile": "speech",
                "segments": [
                    {
                        "voice": "unused-test-voice",
                        "text": "Changed",
                        "pause_after_ms": 100,
                    }
                ],
            }), encoding="utf-8")
            changed = render_program(program, out, provider=provider)
            self.assertFalse(changed["cache_hit"])
            self.assertEqual(provider.calls, 2)
            self.assertNotEqual(changed["render_fingerprint"], manifest["render_fingerprint"])

    def test_stereo_placement_reuses_voice_clips_when_mix_changes(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            program = root / "dialogue.json"
            base = {
                "schema_version": 2,
                "id": "dialogue",
                "title": "Dialogue",
                "profile": "speech",
                "actors": {
                    "a": {"placement": "left"},
                    "b": {"placement": "right"},
                },
                "segments": [
                    {"character_id": "a", "voice": "voice-a", "text": "Bonjour.", "pause_after_ms": 50},
                    {"character_id": "b", "voice": "voice-b", "text": "Bonjour aussi.", "pause_after_ms": 50},
                ],
            }
            program.write_text(json.dumps(base), encoding="utf-8")
            out = root / "out"
            provider = FakeProvider()
            first = render_program(program, out, provider=provider)
            self.assertEqual(first["audio"]["channels"], 2)
            self.assertEqual(first["audio"]["bitrate_kbps"], 96)
            self.assertEqual(provider.calls, 2)
            self.assertEqual(first["mix"]["voice_cache_hits"], 0)

            base["actors"] = {
                "a": {"placement": "right"},
                "b": {"placement": "left"},
            }
            program.write_text(json.dumps(base), encoding="utf-8")
            remixed = render_program(program, out, provider=provider)
            self.assertFalse(remixed["cache_hit"])
            self.assertEqual(provider.calls, 2)
            self.assertEqual(remixed["mix"]["voice_cache_hits"], 2)
            pans = [segment["resolved_pan"] for segment in json.loads(
                (out / "dialogue" / "transcript.json").read_text(encoding="utf-8")
            )["segments"]]
            self.assertEqual(pans, [0.45, -0.45])

    def test_ambience_mix_and_ambience_cache(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            ambience = root / "room.wav"
            run_ffmpeg([
                "-f", "lavfi",
                "-i", "anoisesrc=color=pink:sample_rate=24000:duration=1.5",
                "-ac", "2",
                "-c:a", "pcm_s16le",
                str(ambience),
            ])
            program = root / "scene.json"
            data = {
                "schema_version": 2,
                "id": "scene",
                "title": "Scene",
                "profile": "speech",
                "ambience": {
                    "file": "room.wav",
                    "gain_db": -24,
                    "loop": True,
                    "fade_in_ms": 50,
                    "fade_out_ms": 50,
                    "ducking": "speech",
                },
                "segments": [{
                    "voice": "voice-a",
                    "text": "Test with ambience.",
                    "pause_after_ms": 100,
                }],
            }
            program.write_text(json.dumps(data), encoding="utf-8")
            out = root / "out"
            provider = FakeProvider()
            first = render_program(program, out, provider=provider)
            self.assertEqual(first["audio"]["channels"], 2)
            self.assertEqual(first["mix"]["ducking"], "speech")
            self.assertIsNotNone(first["mix"]["ambience"])
            self.assertFalse(first["mix"]["ambience_cache_hit"])
            self.assertEqual(provider.calls, 1)

            data["ambience"]["gain_db"] = -20
            program.write_text(json.dumps(data), encoding="utf-8")
            remixed = render_program(program, out, provider=provider)
            self.assertEqual(provider.calls, 1)
            self.assertEqual(remixed["mix"]["voice_cache_hits"], 1)
            self.assertFalse(remixed["mix"]["ambience_cache_hit"])

    def test_assemble(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            for name in ("a.mp3", "b.mp3"):
                run_ffmpeg([
                    "-f", "lavfi",
                    "-i", "anullsrc=r=24000:cl=mono",
                    "-t", "0.15",
                    "-c:a", "libmp3lame",
                    "-b:a", "64k",
                    str(root / name),
                ])
            plan = root / "assembly.json"
            plan.write_text(json.dumps({
                "schema_version": 1,
                "id": "assembled",
                "profile": "speech",
                "inputs": [
                    {"file": "a.mp3", "pause_after_ms": 100},
                    {"file": "b.mp3"},
                ],
            }), encoding="utf-8")
            out = root / "out"
            manifest = assemble_plan(plan, out)
            self.assertEqual(manifest["status"], "success")
            self.assertTrue((out / "assembled" / "audio.mp3").stat().st_size > 0)


if __name__ == "__main__":
    unittest.main()
