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
        ids = {source["id"] for source in result["sources"]}
        self.assertIn("openverse", ids)
        self.assertIn("pixabay", ids)
        self.assertIn("soundly", ids)
        openverse = next(source for source in result["sources"] if source["id"] == "openverse")
        self.assertIn("quiet+cathedral+room+tone", openverse["search_url"])

    def test_discovery_plan_can_filter_sources(self):
        result = discovery_plan("forest", ["freesound", "pixabay"])
        self.assertEqual(result["count"], 2)
        self.assertEqual({source["id"] for source in result["sources"]}, {"freesound", "pixabay"})
        with self.assertRaises(ValueError):
            discovery_plan("forest", ["not-a-source"])

    def test_qualification_fingerprints_local_audio_without_approving_it(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            audio = root / "cathedral-room.wav"
            run_ffmpeg([
                "-f", "lavfi",
                "-i", "anoisesrc=color=pink:sample_rate=48000:duration=0.4",
                "-ac", "2",
                "-c:a", "pcm_s16le",
                str(audio),
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
            self.assertEqual(result["status"], "candidate")
            self.assertEqual(result["id"], "cathedral-calm-candidate")
            self.assertEqual(result["audio"]["channels"], 2)
            self.assertEqual(result["audio"]["sample_rate_hz"], 48000)
            self.assertGreater(result["audio"]["duration_seconds"], 0)
            self.assertEqual(len(result["file"]["content_sha256"]), 64)
            self.assertTrue(result["source"]["provenance_complete"])
            self.assertEqual(result["license"]["declared"], "CC0-1.0")
            self.assertFalse(result["license"]["verified"])
            self.assertFalse(result["promotion"]["eligible"])
            self.assertEqual(result["review"]["listening_quality"], "pending")

    def test_qualification_rejects_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            qualify_candidate("does-not-exist.wav")


if __name__ == "__main__":
    unittest.main()
