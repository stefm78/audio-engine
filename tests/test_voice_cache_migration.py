import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.audio import run_ffmpeg
from audio_engine.render import render_program


class FakeProvider:
    name = "fake-migrate"
    processing = "local-test"

    def __init__(self):
        self.calls = 0

    def synthesize(self, segment, path):
        self.calls += 1
        run_ffmpeg([
            "-f", "lavfi",
            "-i", "sine=frequency=440:sample_rate=24000:duration=0.7",
            "-ac", "1",
            "-c:a", "libmp3lame",
            "-b:a", "64k",
            str(path),
        ])


class VoiceCacheMigrationTests(unittest.TestCase):
    def test_previous_manifest_rekeys_unchanged_voice_without_provider_call(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            out = root / "out"
            cache = out / ".cache" / "voices"
            cache.mkdir(parents=True)
            legacy_fp = "legacy-voice-fingerprint"
            legacy_clip = cache / f"{legacy_fp}.mp3"
            run_ffmpeg([
                "-f", "lavfi",
                "-i", "sine=frequency=440:sample_rate=24000:duration=0.7",
                "-ac", "1",
                "-c:a", "libmp3lame",
                "-b:a", "64k",
                str(legacy_clip),
            ])

            program = {
                "schema_version": 1,
                "id": "migration-demo",
                "title": "Migration demo",
                "segments": [{"voice": "voice-a", "text": "Unchanged sentence."}],
            }
            program_path = root / "program.json"
            program_path.write_text(json.dumps(program), encoding="utf-8")

            previous_dir = out / "migration-demo"
            previous_dir.mkdir(parents=True)
            (previous_dir / "manifest.json").write_text(json.dumps({
                "schema_version": 1,
                "status": "success",
                "render_fingerprint": "old-engine-fingerprint",
                "provider": {"name": "fake-migrate"},
                "audio": {"file": "audio.mp3"},
                "transcript": "transcript.json",
                "mix": {"voice_fingerprints": [legacy_fp]},
            }), encoding="utf-8")
            (previous_dir / "transcript.json").write_text(json.dumps({
                "segments": [{
                    "voice": "voice-a",
                    "text": "Unchanged sentence.",
                    "rate": "+0%",
                    "pitch": "+0Hz",
                    "volume": "+0%",
                }]
            }), encoding="utf-8")
            (previous_dir / "audio.mp3").write_bytes(b"old")

            provider = FakeProvider()
            result = render_program(program_path, out, provider=provider)
            self.assertEqual(provider.calls, 0)
            self.assertEqual(result["mix"]["voice_cache_hits"], 1)
            new_fp = result["mix"]["voice_fingerprints"][0]
            self.assertNotEqual(new_fp, legacy_fp)
            self.assertTrue((cache / f"{new_fp}.mp3").exists())
            timing_sidecar = cache / f"{new_fp}.json"
            self.assertTrue(timing_sidecar.exists())
            self.assertGreater(
                json.loads(timing_sidecar.read_text(encoding="utf-8"))["measured_duration_ms"],
                0,
            )


if __name__ == "__main__":
    unittest.main()
