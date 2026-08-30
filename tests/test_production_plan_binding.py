import hashlib
import json
import unittest
from pathlib import Path

from audio_engine.contract import validate_program
from audio_engine.preflight import preflight_program


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "directors"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def leaves(value, path=""):
    result = {}
    if isinstance(value, dict):
        for key, item in value.items():
            result.update(leaves(item, f"{path}/{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            result.update(leaves(item, f"{path}/{index}"))
    else:
        result[path or "/"] = value
    return result


def git_blob_sha1(path):
    content = path.read_bytes()
    payload = b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    return hashlib.sha1(payload).hexdigest()


class ProductionPlanBindingTests(unittest.TestCase):
    def test_program_ref_preserves_exact_program_without_text_duplication(self):
        plan_path = FIXTURES / "audiobook-scene-ref.plan.json"
        disp_path = FIXTURES / "audiobook-scene-ref.disposition.json"
        plan = load(plan_path)
        disposition = load(disp_path)

        binding = plan["content_binding"]
        self.assertEqual(binding["mode"], "program-ref")
        self.assertEqual(binding["content_authority"], "program")
        self.assertNotIn("/text", "\n".join(leaves(plan)))

        program_path = ROOT / binding["program"]
        self.assertTrue(program_path.is_file())
        self.assertEqual(git_blob_sha1(program_path), binding["git_blob_sha1"])
        program = load(program_path)

        self.assertEqual(plan["id"], program["id"])
        self.assertEqual(plan["title"], program["title"])
        self.assertEqual(plan["language"], program["language"])

        segment_count = len(program["segments"])
        for overlay in plan["overlays"]:
            start, end = overlay["segment_range"]
            self.assertGreaterEqual(start, 1)
            self.assertGreaterEqual(end, start)
            self.assertLessEqual(end, segment_count)

        presets = {segment.get("preset") for segment in program["segments"]}
        for casting in plan["casting"].values():
            selector = casting["program_selector"]
            self.assertIn(selector["preset"], presets)

        plan_leaves = set(leaves(plan))
        paths = [item["path"] for item in disposition["entries"]]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(plan_leaves, set(paths))

        validate_program(program)
        report = preflight_program(program_path)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["tts_calls"], 0)
        self.assertFalse(report["network_access"])

    def test_existing_inline_fixtures_remain_implicit_inline(self):
        for name in ("audioguide-station.plan.json", "audiobook-scene.plan.json"):
            plan = load(FIXTURES / name)
            self.assertNotIn("content_binding", plan)
            self.assertTrue(plan["beats"])
            self.assertTrue(all("text" in beat for beat in plan["beats"]))


if __name__ == "__main__":
    unittest.main()
