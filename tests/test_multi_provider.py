import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.audio import run_ffmpeg
from audio_engine.render import render_program
from audio_engine.voices import resolve_segments


class ToneProvider:
    processing = "local-test"

    def __init__(self, name, frequency):
        self.name = name
        self.frequency = frequency
        self.calls = 0

    def cache_identity(self):
        return f"{self.name}-runtime-v1"

    def synthesize(self, segment, path):
        self.calls += 1
        run_ffmpeg([
            "-f", "lavfi",
            "-i", f"sine=frequency={self.frequency}:sample_rate=24000:duration=0.20",
            "-ac", "1",
            "-c:a", "libmp3lame",
            "-b:a", "64k",
            str(path),
        ])


class MultiProviderRoutingTests(unittest.TestCase):
    def write_program(self, root, data):
        path = Path(root) / "program.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_routes_each_segment_to_declared_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            program = self.write_program(root, {
                "schema_version": 1,
                "id": "multi",
                "title": "Multi provider",
                "segments": [
                    {"provider": "alpha", "voice": "voice-a", "text": "Alpha."},
                    {"provider": "beta", "voice": "voice-b", "text": "Beta."},
                ],
            })
            alpha = ToneProvider("alpha", 440)
            beta = ToneProvider("beta", 550)
            manifest = render_program(
                program,
                root / "out",
                providers={"alpha": alpha, "beta": beta},
            )
            self.assertEqual(alpha.calls, 1)
            self.assertEqual(beta.calls, 1)
            self.assertEqual(manifest["provider"]["name"], "multi")
            self.assertEqual(
                [item["name"] for item in manifest["providers"]],
                ["alpha", "beta"],
            )
            self.assertEqual(manifest["mix"]["voice_providers"], ["alpha", "beta"])
            transcript = json.loads(
                (root / "out" / "multi" / "transcript.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                [item["provider"] for item in transcript["segments"]],
                ["alpha", "beta"],
            )

    def test_missing_declared_provider_fails_before_synthesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            program = self.write_program(root, {
                "schema_version": 1,
                "id": "missing",
                "title": "Missing provider",
                "segments": [
                    {"provider": "alpha", "voice": "voice-a", "text": "Alpha."},
                    {"provider": "missing", "voice": "voice-b", "text": "Missing."},
                ],
            })
            alpha = ToneProvider("alpha", 440)
            with self.assertRaisesRegex(ValueError, "Production provider 'missing' is unavailable"):
                render_program(program, root / "out", providers={"alpha": alpha})
            self.assertEqual(alpha.calls, 0)

    def test_provider_parameters_and_seed_change_voice_cache_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = {
                "schema_version": 1,
                "id": "controls",
                "title": "Provider controls",
                "segments": [{
                    "provider": "alpha",
                    "voice": "voice-a",
                    "text": "Controlled.",
                    "provider_seed": 42,
                    "provider_parameters": {"temperature": 0.7},
                }],
            }
            program = self.write_program(root, data)
            alpha = ToneProvider("alpha", 440)
            first = render_program(program, root / "out", providers={"alpha": alpha})
            first_fp = first["mix"]["voice_fingerprints"][0]
            self.assertEqual(alpha.calls, 1)

            data["segments"][0]["provider_parameters"]["temperature"] = 0.8
            program.write_text(json.dumps(data), encoding="utf-8")
            second = render_program(program, root / "out", providers={"alpha": alpha})
            self.assertEqual(alpha.calls, 2)
            self.assertNotEqual(first_fp, second["mix"]["voice_fingerprints"][0])

    def test_character_provider_identity_cannot_change_silently(self):
        program = {
            "schema_version": 1,
            "id": "continuity",
            "title": "Continuity",
            "segments": [
                {
                    "character_id": "hero",
                    "provider": "alpha",
                    "voice": "voice-a",
                    "text": "Première ligne.",
                },
                {
                    "character_id": "hero",
                    "provider": "beta",
                    "voice": "voice-a",
                    "text": "Deuxième ligne.",
                },
            ],
        }
        with self.assertRaisesRegex(ValueError, "cannot silently change provider"):
            resolve_segments(program, {"presets": []})


if __name__ == "__main__":
    unittest.main()
