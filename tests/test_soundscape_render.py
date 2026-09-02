import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.audio import run_ffmpeg
from audio_engine.contract import sha256_file
from audio_engine.render import render_program
from audio_engine.sound.render import PLACEMENT_PAN as SOUND_PLACEMENT_PAN


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


def make_audio(path, source, duration=1.0, channels=2):
    run_ffmpeg([
        "-f", "lavfi",
        "-i", f"{source}:sample_rate=24000:duration={duration}",
        "-ac", str(channels),
        "-c:a", "pcm_s16le",
        str(path),
    ])


class SoundscapeRenderTests(unittest.TestCase):
    def test_subtle_event_pan_values_are_exactly_bounded(self):
        self.assertEqual(SOUND_PLACEMENT_PAN["slight-left"], -0.16)
        self.assertEqual(SOUND_PLACEMENT_PAN["slight-right"], 0.16)
        self.assertEqual(SOUND_PLACEMENT_PAN["left"], -0.45)
        self.assertEqual(SOUND_PLACEMENT_PAN["right"], 0.45)

    def test_local_bed_layer_event_render_and_voice_reuse(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            make_audio(root / "bed.wav", "anoisesrc=color=pink", 1.0, 2)
            make_audio(root / "layer.wav", "anoisesrc=color=white", 1.0, 2)
            make_audio(root / "bell.wav", "sine=frequency=880", 0.10, 1)
            program = root / "scene.json"
            data = {
                "schema_version": 3,
                "id": "scene",
                "title": "Scene",
                "profile": "speech",
                "soundscape": {
                    "bed": {"file": "bed.wav", "gain_db": -24, "fade_in_ms": 20, "fade_out_ms": 20},
                    "layers": [{"file": "layer.wav", "gain_db": -32}],
                    "events": [{"file": "bell.wav", "at_ms": 100, "gain_db": -20, "placement": "right"}],
                    "ducking": "speech",
                },
                "segments": [{"voice": "voice-a", "text": "Test.", "pause_after_ms": 100}],
            }
            program.write_text(json.dumps(data), encoding="utf-8")
            out = root / "out"
            provider = FakeProvider()
            first = render_program(program, out, provider=provider)
            self.assertEqual(first["audio"]["channels"], 2)
            self.assertEqual(first["audio"]["bitrate_kbps"], 96)
            self.assertEqual(provider.calls, 1)
            self.assertEqual(first["mix"]["soundscape"]["component_count"], 3)
            self.assertEqual(
                [item["role"] for item in first["mix"]["soundscape"]["components"]],
                ["bed", "layer", "event"],
            )
            self.assertFalse(first["mix"]["soundscape_cache_hit"])

            data["soundscape"]["events"][0]["at_ms"] = 150
            program.write_text(json.dumps(data), encoding="utf-8")
            remixed = render_program(program, out, provider=provider)
            self.assertFalse(remixed["cache_hit"])
            self.assertEqual(provider.calls, 1)
            self.assertEqual(remixed["mix"]["voice_cache_hits"], 1)
            self.assertFalse(remixed["mix"]["soundscape_cache_hit"])

    def test_catalog_ids_are_hash_verified_and_manifested(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            assets = root / "assets"
            assets.mkdir()
            make_audio(assets / "room.wav", "anoisesrc=color=pink", 1.0, 2)
            make_audio(assets / "bell.wav", "sine=frequency=660", 0.10, 1)
            catalog = root / "sounds.json"
            catalog.write_text(json.dumps({
                "version": 1,
                "policy": {"publication": "validated-only"},
                "entries": [
                    {
                        "id": "room",
                        "type": "ambience",
                        "status": "validated",
                        "tags": ["interior"],
                        "content_sha256": sha256_file(assets / "room.wav"),
                        "source": {"provider": "test", "page": "https://example.test/room"},
                        "license": {"id": "CC0-1.0", "verified": True, "attribution": None},
                        "asset": {"file": "assets/room.wav"},
                        "defaults": {"gain_db": -25},
                    },
                    {
                        "id": "bell",
                        "type": "event",
                        "status": "validated",
                        "tags": ["bell"],
                        "content_sha256": sha256_file(assets / "bell.wav"),
                        "source": {"provider": "test", "page": "https://example.test/bell"},
                        "license": {"id": "CC0-1.0", "verified": True, "attribution": None},
                        "asset": {"file": "assets/bell.wav"},
                    },
                ],
            }), encoding="utf-8")
            program = root / "scene.json"
            program.write_text(json.dumps({
                "schema_version": 3,
                "id": "catalog-scene",
                "title": "Catalog scene",
                "soundscape": {
                    "bed": {"sound": "room"},
                    "events": [{"sound": "bell", "at_ms": 100}],
                },
                "segments": [{"voice": "voice-a", "text": "Test.", "pause_after_ms": 100}],
            }), encoding="utf-8")
            manifest = render_program(
                program,
                root / "out",
                provider=FakeProvider(),
                sounds_path=catalog,
            )
            components = manifest["mix"]["soundscape"]["components"]
            self.assertEqual([item["sound"] for item in components], ["room", "bell"])
            self.assertTrue(all(item["license"]["verified"] for item in components))
            self.assertTrue(all(item["source_sha256"] == item["catalog_content_sha256"] for item in components))

            bad_catalog = json.loads(catalog.read_text(encoding="utf-8"))
            bad_catalog["entries"][0]["content_sha256"] = "0" * 64
            catalog.write_text(json.dumps(bad_catalog), encoding="utf-8")
            with self.assertRaises(ValueError):
                render_program(
                    program,
                    root / "out-bad",
                    provider=FakeProvider(),
                    sounds_path=catalog,
                )


if __name__ == "__main__":
    unittest.main()
