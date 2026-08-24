import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.audio import run_ffmpeg
from audio_engine.render import render_program


def write_tone(path, duration=0.7):
    run_ffmpeg([
        "-f", "lavfi",
        "-i", f"sine=frequency=440:sample_rate=24000:duration={duration}",
        "-ac", "1",
        "-c:a", "libmp3lame",
        "-b:a", "64k",
        str(path),
    ])


def write_padded_tone(path):
    # 200 ms provider lead + 300 ms speech + 250 ms intentional internal pause
    # + 300 ms speech + 1000 ms provider tail = 2050 ms raw.
    run_ffmpeg([
        "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono:d=0.2",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=24000:duration=0.3",
        "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono:d=0.25",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=24000:duration=0.3",
        "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono:d=1.0",
        "-filter_complex", "[0:a][1:a][2:a][3:a][4:a]concat=n=5:v=0:a=1[out]",
        "-map", "[out]",
        "-ac", "1",
        "-c:a", "libmp3lame",
        "-b:a", "64k",
        str(path),
    ])


class FakeProvider:
    name = "fake-migrate"
    processing = "local-test"

    def __init__(self):
        self.calls = 0

    def synthesize(self, segment, path):
        self.calls += 1
        write_tone(path)


class PaddedFakeProvider(FakeProvider):
    name = "fake-padded"

    def synthesize(self, segment, path):
        self.calls += 1
        write_padded_tone(path)


class VoiceCacheMigrationTests(unittest.TestCase):
    def test_previous_manifest_rekeys_and_normalizes_without_provider_call(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            out = root / "out"
            cache = out / ".cache" / "voices"
            cache.mkdir(parents=True)
            legacy_fp = "legacy-voice-fingerprint"
            legacy_clip = cache / f"{legacy_fp}.mp3"
            write_padded_tone(legacy_clip)

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
            timing = json.loads((cache / f"{new_fp}.json").read_text(encoding="utf-8"))
            self.assertTrue(timing["edge_silence_normalized"])
            # Provider padding is gone; the deliberate 250 ms internal pause survives.
            self.assertGreater(timing["measured_duration_ms"], 850)
            self.assertLess(timing["measured_duration_ms"], 1300)

    def test_new_synthesis_normalizes_only_clip_edges(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            out = root / "out"
            program = {
                "schema_version": 1,
                "id": "edge-normalization-demo",
                "title": "Edge normalization demo",
                "segments": [{"voice": "voice-a", "text": "New sentence."}],
            }
            program_path = root / "program.json"
            program_path.write_text(json.dumps(program), encoding="utf-8")

            provider = PaddedFakeProvider()
            result = render_program(program_path, out, provider=provider)
            self.assertEqual(provider.calls, 1)
            self.assertEqual(result["mix"]["voice_cache_hits"], 0)
            fingerprint = result["mix"]["voice_fingerprints"][0]
            timing = json.loads(
                (out / ".cache" / "voices" / f"{fingerprint}.json").read_text(encoding="utf-8")
            )
            self.assertTrue(timing["edge_silence_normalized"])
            self.assertGreater(timing["measured_duration_ms"], 850)
            self.assertLess(timing["measured_duration_ms"], 1300)


if __name__ == "__main__":
    unittest.main()