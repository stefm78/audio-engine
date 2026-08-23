import tempfile
import unittest
from pathlib import Path

from audio_engine.ambience.discovery import discovery_plan
from audio_engine.ambience.qualification import qualify_candidate
from audio_engine.audio import run_ffmpeg


class AmbienceToolTests(unittest.TestCase):
    def test_discovery_plan_is_broad_and_offline(self):
        result = discovery_plan("quiet cathedral room tone")
        self.assertEqual(result["mode"], "discovery-plan")
        self.assertEqual(result["network_requests_performed"], 0)
        self.assertGreaterEqual(result["count"], 12)

    def test_discovery_plan_can_filter_sources(self):
        result = discovery_plan("forest", ["freesound", "pixabay"])
        self.assertEqual(result["count"], 2)
        with self.assertRaises(ValueError):
            discovery_plan("forest", ["not-a-source"])

    def test_qualification_fingerprints_source_and_creates_audit_preview(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            audio = root / "cathedral-room.wav"
            run_ffmpeg([
                "-f", "lavfi", "-i", "anoisesrc=color=pink:sample_rate=48000:duration=0.4",
                "-ac", "2", "-c:a", "pcm_s16le", str(audio),
            ])
            result = qualify_candidate(
                audio,
                candidate_id="cathedral-calm-candidate",
                source_provider="Example source",
                source_page="https://example.test/sound/1",
                source_identifier="sound-1",
                license_id="CC0-1.0",
                raw_redistribution="allowed",
                tags=["interior", "calm"],
            )
            self.assertEqual(result["schema_version"], 2)
            self.assertEqual(result["type"], "ambience")
            self.assertTrue(result["file"]["canonical"])
            self.assertFalse(result["license"]["verified"])
            self.assertFalse(result["promotion"]["eligible"])
            self.assertEqual(result["review"]["automated_quality"], "failed")
            preview = Path(result["preview"]["path"])
            self.assertTrue(preview.exists())
            self.assertEqual(result["preview"]["purpose"], "audit-only")
            self.assertFalse(result["preview"]["canonical"])
            self.assertNotEqual(result["file"]["content_sha256"], result["preview"]["content_sha256"])

    def test_trusted_open_source_is_machine_verified_without_human_gate(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            audio = root / "bell.wav"
            run_ffmpeg([
                "-f", "lavfi", "-i", "sine=frequency=500:sample_rate=44100:duration=1",
                "-ac", "2", "-c:a", "pcm_s16le", str(audio),
            ])
            result = qualify_candidate(
                audio,
                candidate_type="event",
                source_provider="wikimedia-commons",
                source_page="https://commons.wikimedia.org/wiki/File:Bell.ogg",
                license_id="CC0-1.0",
                tags=["bell", "church"],
            )
            self.assertTrue(result["license"]["verified"])
            self.assertEqual(result["license"]["verification_method"], "trusted-source-metadata")
            self.assertEqual(result["review"]["automated_quality"], "passed")
            self.assertTrue(result["promotion"]["eligible"])

    def test_qualification_can_redirect_preview_without_changing_source_identity(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            audio = root / "source.ogg"
            preview_dir = root / "audit"
            run_ffmpeg([
                "-f", "lavfi", "-i", "anoisesrc=color=white:sample_rate=44100:duration=0.3",
                "-ac", "1", "-c:a", "libvorbis", str(audio),
            ])
            result = qualify_candidate(audio, candidate_type="event", preview_dir=preview_dir)
            self.assertEqual(Path(result["preview"]["path"]).parent, preview_dir)
            self.assertEqual(result["file"]["name"], "source.ogg")
            self.assertTrue(result["file"]["canonical"])

    def test_qualification_rejects_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            qualify_candidate("does-not-exist.wav")


if __name__ == "__main__":
    unittest.main()
