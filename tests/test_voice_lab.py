import tempfile
import unittest
from pathlib import Path

from audio_engine.voice_lab import AGE_STAGES, build_campaign, probe_catalog, render_campaign
from audio_engine.voices import resolve_segments


VOICE_CONFIG = {
    "version": 1,
    "presets": [
        {
            "id": "actor-calm",
            "voice": "fr-FR-ActorNeural",
            "rate": "+0%",
            "pitch": "+0Hz",
            "volume": "+0%",
            "traits": {"gender": "male", "age": "adult", "energy": 2},
            "tags": ["calm"],
        },
        {
            "id": "actor-intense",
            "voice": "fr-FR-ActorNeural",
            "rate": "+12%",
            "pitch": "+5Hz",
            "volume": "+4%",
            "traits": {"gender": "male", "age": "adult", "energy": 5},
            "tags": ["urgent"],
        },
        {
            "id": "other-actor",
            "voice": "fr-FR-OtherNeural",
            "rate": "+0%",
            "pitch": "+0Hz",
            "volume": "+0%",
            "traits": {"gender": "male", "age": "adult", "energy": 3},
            "tags": [],
        },
    ],
}


class FakeProvider:
    name = "fake"
    processing = "local-test"
    expressive_controls = ("rate", "pitch", "volume")

    def list_voices(self, locale_prefix=None):
        voices = [
            {"voice": "fr-FR-OneNeural", "locale": "fr-FR", "gender": "female", "friendly_name": "One"},
            {"voice": "en-US-TwoNeural", "locale": "en-US", "gender": "male", "friendly_name": "Two"},
        ]
        if locale_prefix:
            voices = [item for item in voices if item["locale"].startswith(locale_prefix)]
        return voices

    def synthesize(self, segment, path):
        Path(path).write_bytes(b"fake-mp3")


class VoiceLabTests(unittest.TestCase):
    def test_probe_catalog_separates_identity_emotion_and_age(self):
        catalog = probe_catalog()
        self.assertTrue(catalog["principles"]["identity_first"])
        self.assertTrue(catalog["principles"]["emotion_never_implies_recast"])
        self.assertEqual(tuple(catalog["age_stages"]), AGE_STAGES)
        self.assertTrue(any(item["kind"] == "age-lineage" for item in catalog["probes"]))
        self.assertTrue(any(item["kind"] == "performance" for item in catalog["probes"]))

    def test_campaign_plan_can_scan_provider_french_voices_without_invented_traits(self):
        plan = build_campaign(
            voice_config=VOICE_CONFIG,
            provider=FakeProvider(),
            scope="provider",
            stage="fingerprint",
        )
        self.assertEqual(plan["candidate_count"], 1)
        self.assertEqual(plan["probe_count"], 3)
        self.assertEqual(plan["job_count"], 3)
        self.assertEqual(plan["jobs"][0]["candidate"]["voice"], "fr-FR-OneNeural")
        self.assertNotIn("traits", plan["jobs"][0]["candidate"])

    def test_render_campaign_is_best_effort_and_persists_manifest(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            result = render_campaign(
                root,
                voice_config=VOICE_CONFIG,
                provider=FakeProvider(),
                scope="presets",
                stage="age",
            )
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["rendered_count"], len(VOICE_CONFIG["presets"]))
            self.assertTrue((root / "campaign.json").exists())
            self.assertEqual(
                len(list((root / "clips").glob("*.mp3"))),
                len(VOICE_CONFIG["presets"]),
            )

    def test_character_target_changes_do_not_recast_identity(self):
        program = {
            "segments": [
                {
                    "character_id": "captain",
                    "target": {"gender": "male", "age": "adult", "energy": 2},
                    "text": "Calme.",
                },
                {
                    "character_id": "captain",
                    "target": {"gender": "male", "age": "adult", "energy": 5, "tags": ["urgent"]},
                    "text": "Urgence.",
                    "rate": "+15%",
                },
            ]
        }
        resolved = resolve_segments(program, VOICE_CONFIG)
        self.assertEqual(resolved[0]["voice"], resolved[1]["voice"])
        self.assertEqual(resolved[1]["rate"], "+15%")
        self.assertEqual(resolved[0]["casting_identity"], "fr-FR-ActorNeural")

    def test_same_provider_voice_may_change_preset_for_performance(self):
        program = {
            "segments": [
                {"character_id": "captain", "preset": "actor-calm", "text": "Calme."},
                {"character_id": "captain", "preset": "actor-intense", "text": "Courez !"},
            ]
        }
        resolved = resolve_segments(program, VOICE_CONFIG)
        self.assertEqual(resolved[0]["voice"], "fr-FR-ActorNeural")
        self.assertEqual(resolved[1]["voice"], "fr-FR-ActorNeural")
        self.assertEqual(resolved[0]["resolved_preset"], "actor-calm")
        self.assertEqual(resolved[1]["resolved_preset"], "actor-intense")

    def test_different_provider_voice_for_same_character_is_rejected(self):
        program = {
            "segments": [
                {"character_id": "captain", "preset": "actor-calm", "text": "Calme."},
                {"character_id": "captain", "preset": "other-actor", "text": "Autre voix."},
            ]
        }
        with self.assertRaisesRegex(ValueError, "cannot silently change provider voice"):
            resolve_segments(program, VOICE_CONFIG)


if __name__ == "__main__":
    unittest.main()
