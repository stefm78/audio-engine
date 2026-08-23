import unittest

from audio_engine.sound.selection import evaluate_candidate, select_candidates


def candidate(
    sound_id,
    *,
    duration,
    channels=2,
    tags=None,
    verified=True,
    sample_rate=44100,
    license_id="CC0-1.0",
    sound_type="ambience",
    rank=None,
):
    value = {
        "schema_version": 2,
        "status": "candidate",
        "id": sound_id,
        "type": sound_type,
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
    if rank is not None:
        value["discovery"] = {"rank": rank}
    return value


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

    def test_zero_preferred_context_misses_default_quality_threshold(self):
        generic = candidate(
            "generic-bell",
            duration=15,
            sound_type="event",
            tags=["bell", "memorial"],
            rank=1,
        )
        result = select_candidates(
            [generic],
            sound_type="event",
            required_tags=["bell"],
            preferred_tags=["cathedral", "church", "distant"],
            min_score=70,
        )
        self.assertEqual(result["status"], "no-selection")
        evaluation = result["evaluations"][0]
        self.assertTrue(evaluation["eligible"])
        self.assertLess(evaluation["score"], 70)
        self.assertIn("preferred-context-miss", evaluation["reasons"])

    def test_preferred_context_is_soft_and_can_be_explicitly_accepted_lower(self):
        generic = candidate(
            "generic-bell",
            duration=15,
            sound_type="event",
            tags=["bell", "memorial"],
            rank=1,
        )
        result = select_candidates(
            [generic],
            sound_type="event",
            required_tags=["bell"],
            preferred_tags=["cathedral", "church", "distant"],
            min_score=60,
        )
        self.assertEqual(result["status"], "selected")
        self.assertEqual(result["selected_id"], "generic-bell")

    def test_contextual_bell_beats_generic_technically_perfect_bell(self):
        generic = candidate(
            "generic-bell",
            duration=15,
            sound_type="event",
            tags=["bell", "memorial"],
            rank=1,
        )
        contextual = candidate(
            "church-bell",
            duration=25,
            channels=1,
            sound_type="event",
            tags=["bell", "church"],
            license_id="CC-BY-4.0",
            rank=3,
        )
        result = select_candidates(
            [generic, contextual],
            sound_type="event",
            required_tags=["bell"],
            preferred_tags=["cathedral", "church", "distant"],
            min_score=70,
        )
        self.assertEqual(result["status"], "selected")
        self.assertEqual(result["selected_id"], "church-bell")
        generic_eval = next(item for item in result["evaluations"] if item["id"] == "generic-bell")
        contextual_eval = next(item for item in result["evaluations"] if item["id"] == "church-bell")
        self.assertGreater(contextual_eval["score"], generic_eval["score"])


if __name__ == "__main__":
    unittest.main()
