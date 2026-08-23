import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_engine.sound.library import _query_variants, hydrate_sound_library


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def requirement(sound_id="church-bell-distant"):
    return {
        "version": 1,
        "sounds": [
            {
                "id": sound_id,
                "type": "event",
                "query": "distant cathedral bell",
                "required_tags": ["bell"],
                "preferred_tags": ["cathedral", "distant"],
                "providers": ["wikimedia-commons"],
                "min_score": 70,
            }
        ],
    }


def selected_result(output_dir, sound_id="church-bell-distant", audio=b"newly-acquired-audio"):
    digest = sha256_bytes(audio)
    acquisition = Path(output_dir)
    assets = acquisition / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    source = assets / f"{sound_id}.ogg"
    source.write_bytes(audio)
    entry = {
        "id": sound_id,
        "type": "event",
        "status": "validated",
        "tags": ["bell", "cathedral", "distant"],
        "content_sha256": digest,
        "source": {"provider": "wikimedia-commons"},
        "license": {"id": "CC0-1.0", "verified": True},
        "asset": {"file": f"assets/{sound_id}.ogg", "status": "locked"},
    }
    return {
        "status": "selected",
        "selected_id": sound_id,
        "selected": entry,
        "selected_score": 92,
        "materialized": {"asset": str(source)},
        "network_requests_required": True,
    }


class SoundLibraryTests(unittest.TestCase):
    def test_natural_contextual_queries_precede_generic_fallback(self):
        item = {
            "query": "cathedral bell",
            "required_tags": ["bell"],
            "preferred_tags": ["cathedral", "church", "distant"],
        }
        variants = _query_variants(item)
        self.assertEqual(variants[0], "cathedral bell")
        self.assertIn("cathedral bells", variants)
        self.assertIn("church bell", variants)
        self.assertIn("church bells", variants)
        self.assertIn("distant bell", variants)
        self.assertLess(variants.index("church bells"), variants.index("bell"))

    def test_restores_exact_validated_seed_without_network(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            seed = root / "seed"
            seed.mkdir()
            audio = b"already-validated-audio"
            (seed / "church-bell-distant.ogg").write_bytes(audio)
            catalog = {
                "version": 1,
                "entries": [
                    {
                        "id": "church-bell-distant",
                        "type": "event",
                        "status": "validated",
                        "tags": ["bell", "cathedral"],
                        "content_sha256": sha256_bytes(audio),
                        "source": {"provider": "wikimedia-commons"},
                        "license": {"id": "CC0-1.0", "verified": True},
                        "asset": {"file": "assets/church-bell-distant.ogg", "status": "locked"},
                    }
                ],
            }
            (seed / "church-bell-distant.catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
            requirements = root / "requirements.json"
            requirements.write_text(json.dumps(requirement()), encoding="utf-8")

            with patch("audio_engine.sound.library.ensure_sound", side_effect=AssertionError("network path called")):
                result = hydrate_sound_library(requirements, output_dir=root / "library", seed_dir=seed)

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["resolved_count"], 1)
            self.assertEqual(result["restored_count"], 1)
            self.assertEqual(result["network_acquisition_count"], 0)
            hydrated = json.loads((root / "library" / "sounds.json").read_text(encoding="utf-8"))
            self.assertEqual(hydrated["entries"][0]["id"], "church-bell-distant")
            self.assertEqual(hydrated["entries"][0]["asset"]["file"], "assets/church-bell-distant.ogg")
            self.assertEqual((root / "library" / "assets" / "church-bell-distant.ogg").read_bytes(), audio)

    def test_acquires_missing_sound_and_merges_runtime_catalog(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            requirements = root / "requirements.json"
            requirements.write_text(json.dumps(requirement()), encoding="utf-8")

            def fake_ensure(query, **kwargs):
                return selected_result(kwargs["output_dir"])

            with patch("audio_engine.sound.library.ensure_sound", side_effect=fake_ensure):
                result = hydrate_sound_library(requirements, output_dir=root / "library", seed_dir=root / "missing-seed")

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["network_acquisition_count"], 1)
            self.assertEqual(result["restored_count"], 0)
            hydrated = json.loads((root / "library" / "sounds.json").read_text(encoding="utf-8"))
            self.assertEqual(len(hydrated["entries"]), 1)
            self.assertEqual(hydrated["entries"][0]["content_sha256"], sha256_bytes(b"newly-acquired-audio"))
            self.assertTrue((root / "library" / "catalogs" / "church-bell-distant.catalog.json").exists())
            self.assertTrue((root / "library" / "selections" / "church-bell-distant.selection.json").exists())

    def test_broadens_query_without_weakening_hard_requirements(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            data = requirement()
            data["sounds"][0]["required_tags"] = ["bell", "cathedral"]
            data["sounds"][0]["preferred_tags"] = ["church", "distant"]
            requirements = root / "requirements.json"
            requirements.write_text(json.dumps(data), encoding="utf-8")
            calls = []

            def fake_ensure(query, **kwargs):
                calls.append((query, list(kwargs["required_tags"]), kwargs["limit"]))
                if len(calls) < 3:
                    return {"status": "no-selection", "action": "continue-discovery", "qualified_count": 0}
                return selected_result(kwargs["output_dir"])

            with patch("audio_engine.sound.library.ensure_sound", side_effect=fake_ensure):
                result = hydrate_sound_library(requirements, output_dir=root / "library")

            self.assertEqual(result["status"], "success")
            self.assertEqual(len(calls), 3)
            self.assertEqual(calls[0][0], "distant cathedral bell")
            self.assertNotEqual(calls[1][0], calls[0][0])
            self.assertTrue(all(tags == ["bell", "cathedral"] for _, tags, _ in calls))
            self.assertGreater(calls[2][2], calls[0][2])
            evidence = json.loads(
                (root / "library" / "selections" / "church-bell-distant.selection.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(evidence["query_attempts"]), 3)
            self.assertEqual(evidence["query_attempts"][-1]["status"], "selected")

    def test_unresolved_requirement_is_reported_without_human_fallback(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            requirements = root / "requirements.json"
            requirements.write_text(json.dumps(requirement()), encoding="utf-8")
            with patch(
                "audio_engine.sound.library.ensure_sound",
                return_value={"status": "no-selection", "action": "continue-discovery"},
            ) as mocked:
                result = hydrate_sound_library(requirements, output_dir=root / "library")
            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["unresolved_count"], 1)
            self.assertEqual(result["unresolved"][0]["action"], "continue-discovery")
            self.assertGreater(mocked.call_count, 1)
            self.assertGreater(len(result["unresolved"][0]["query_attempts"]), 1)

    def test_duplicate_requirement_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            data = requirement()
            data["sounds"].append(dict(data["sounds"][0]))
            requirements = root / "requirements.json"
            requirements.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                hydrate_sound_library(requirements, output_dir=root / "library")


if __name__ == "__main__":
    unittest.main()
