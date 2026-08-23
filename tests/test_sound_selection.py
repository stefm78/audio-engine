import unittest

from audio_engine.sound.selection import select_candidates


def candidate(sound_id, *, duration, channels=2, tags=None, verified=True, sample_rate=44100, license_id="CC0-1.0"):
    return {
        "schema_version": 2,
        "status": "candidate",
        "id": sound_id,
        "type": "ambience",
        "audio": {
            "duration_seconds": duration,
            "channels": channels,
            "sample_rate_hz": sample_rate,
        },
        "tags": list(tags or []),
        "source": {
            "provenance_complete": True,
            "identifier": sound_id,
        },
        "license": {
            "id": license_id,
            "verified": verified,
            "raw_redistribution": "allowed",
        },
        "review": {
            "technical_probe": "passed",
            "automated_quality": "passed",
        },
    }


class SoundSelectionTests(unittest.TestCase):
    def test_selects_best_candidate_deterministically(self):
        short = candidate("short", duration=40, tags=["cathedral", "calm"])
        long = candidate("long", duration=180, tags=["cathedral", "calm", "reverberant"])
        result = select_candidates(
            [short, long],
            sound_type="ambience",
            required_tags=["cathedral", "calm"],
            preferred_tags=["reverberant"],
            min_score=70,
        )
        self.assertEqual(result["status"], "selected")
        self.assertEqual(result["selected_id"], "long")
        self.assertEqual(result["decision"], "automatic")

    def test_unverified_license_is_rejected_without_human_fallback(self):
        bad = candidate("bad", duration=180, tags=["forest"], verified=False)
        result = select_candidates([bad], sound_type="ambience", required_tags=["forest"])
        self.assertEqual(result["status"], "no-selection")
        self.assertEqual(result["action"], "continue-discovery")
        self.assertIn("license-not-machine-verified", result["evaluations"][0]["gates"])

    def test_missing_semantic_tag_continues_discovery(self):
        wrong = candidate("wrong", duration=180, tags=["city"])
        result = select_candidates([wrong], sound_type="ambience", required_tags=["forest"])
        self.assertEqual(result["status"], "no-selection")
        self.assertTrue(any(g.startswith("missing-required-tags") for g in result["evaluations"][0]["gates"]))


if __name__ == "__main__":
    unittest.main()
