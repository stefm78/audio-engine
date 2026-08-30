import json
import unittest
from pathlib import Path

from audio_engine.contract import validate_program
from audio_engine.preflight import preflight_program


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "directors"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def leaves(value, path=""):
    result = {}
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}/{key}"
            result.update(leaves(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            child = f"{path}/{index}"
            result.update(leaves(item, child))
    else:
        result[path or "/"] = value
    return result


def pointer_get(value, pointer):
    current = value
    for part in pointer.strip("/").split("/"):
        if not part:
            continue
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


class ProductionDirectorProfileTests(unittest.TestCase):
    def _check(self, stem, product, expected_schema):
        plan = load(f"{stem}.plan.json")
        program = load(f"{stem}.program.json")
        disposition = load(f"{stem}.disposition.json")

        self.assertEqual(plan["production_plan_version"], 1)
        self.assertEqual(plan["product"], product)
        self.assertTrue(plan["id"])
        self.assertTrue(plan["title"])
        self.assertEqual(plan["language"], "fr-FR")
        self.assertTrue(plan["objective"])
        self.assertTrue(plan["casting"])
        self.assertTrue(plan["beats"])
        self.assertTrue(plan["risk_hints"])
        self.assertTrue(plan["product_context"])

        allowed_importance = {"essential", "important", "supportive", "optional"}
        allowed_fallback = {"fail", "omit-and-warn", "continue-without"}
        for beat in plan["beats"]:
            self.assertIn(beat["importance"], allowed_importance)
            self.assertIn(beat["speaker"], plan["casting"])
            self.assertTrue(beat["performance_intent"])
            self.assertTrue(beat["sound_recipe"])
        for value in plan["fallback_policy"].values():
            self.assertIn(value, allowed_fallback)

        plan_leaves = leaves(plan)
        entries = disposition["entries"]
        entry_paths = [entry["path"] for entry in entries]
        self.assertEqual(len(entry_paths), len(set(entry_paths)), "duplicate disposition path")
        self.assertEqual(set(plan_leaves), set(entry_paths), "silent or extra field disposition")

        for entry in entries:
            self.assertIn(entry["disposition"], {"program", "consumer_metadata", "unsupported"})
            if entry["disposition"] == "program":
                target = entry.get("target")
                self.assertTrue(target, entry)
                if target.startswith("/"):
                    pointer_get(program, target)
                else:
                    self.assertTrue(target.startswith("@"), entry)
            else:
                self.assertTrue(entry.get("reason"), entry)

        self.assertEqual(program["schema_version"], expected_schema)
        self.assertEqual(program["id"], plan["id"])
        self.assertEqual(program["title"], plan["title"])
        self.assertEqual(program["language"], plan["language"])
        self.assertEqual(len(program["segments"]), len(plan["beats"]))

        for index, beat in enumerate(plan["beats"]):
            segment = program["segments"][index]
            self.assertEqual(segment["text"], beat["text"])
            self.assertEqual(segment["preset"], plan["casting"][beat["speaker"]]["preset"])
            if beat["sound_recipe"] == "clean-narration":
                self.assertNotIn("acoustic_space", segment)
            elif beat["sound_recipe"] == "acoustic-accent":
                self.assertEqual(
                    segment["acoustic_space"],
                    beat["recipe_params"]["acoustic_space"],
                )
            else:
                self.fail(f"fixture uses untested recipe: {beat['sound_recipe']}")

        validate_program(program)
        report = preflight_program(FIXTURES / f"{stem}.program.json")
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["tts_calls"], 0)
        self.assertFalse(report["network_access"])

    def test_audioguide_station(self):
        plan = load("audioguide-station.plan.json")
        required = {
            "station_id",
            "location_label",
            "visual_cue",
            "target_duration_s",
            "max_duration_s",
            "resume_after_beats",
            "listening_environment",
            "next_step",
            "optional_content_policy",
        }
        self.assertEqual(set(plan["product_context"]), required)
        self.assertLessEqual(
            plan["product_context"]["target_duration_s"],
            plan["product_context"]["max_duration_s"],
        )
        self._check("audioguide-station", "audioguide", 1)

    def test_audiobook_scene(self):
        plan = load("audiobook-scene.plan.json")
        required = {
            "book_id",
            "part_id",
            "chapter_id",
            "scene_id",
            "arc_position",
            "continuity_scope",
            "sound_density",
            "narrator_pace_policy",
            "chapter_assembly_id",
        }
        self.assertEqual(set(plan["product_context"]), required)
        self._check("audiobook-scene", "audiobook", 4)


if __name__ == "__main__":
    unittest.main()
