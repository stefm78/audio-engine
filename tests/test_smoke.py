import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.audio import run_ffmpeg
from audio_engine.assemble import assemble_plan
from audio_engine.contract import ContractError, validate_program
from audio_engine.render import render_program

class FakeProvider:
    name = "fake"
    processing = "local-test"

    def synthesize(self, segment, path):
        run_ffmpeg([
            "-f", "lavfi",
            "-i", "anullsrc=r=24000:cl=mono",
            "-t", "0.20",
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

    def test_render_offline_provider(self):
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
            manifest = render_program(program, out, provider=FakeProvider())
            self.assertEqual(manifest["status"], "success")
            self.assertEqual(manifest["audio"]["bitrate_kbps"], 80)
            self.assertEqual(manifest["audio"]["sample_rate_hz"], 24000)
            self.assertEqual(manifest["audio"]["channels"], 1)
            self.assertTrue((out / "smoke" / "audio.mp3").stat().st_size > 0)
            self.assertTrue((out / "smoke" / "manifest.json").exists())
            self.assertTrue((out / "smoke" / "transcript.json").exists())

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
