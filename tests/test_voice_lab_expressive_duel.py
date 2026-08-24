import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.voice_lab_expressive_duel import experiment_spec, render_experiment


class FakeProvider:
    def __init__(self, name):
        self.name = name
        self.segments = []

    def synthesize(self, segment, path):
        self.segments.append(dict(segment))
        Path(path).write_bytes(b"fake-mp3")


class VoiceLabExpressiveDuelTests(unittest.TestCase):
    def test_spec_has_controlled_and_mai_cases(self):
        spec = experiment_spec()
        self.assertFalse(spec["production_promotion"])
        self.assertEqual(len(spec["cases"]), 12)
        controlled = [c for c in spec["cases"] if c["kind"] == "controlled-same-base-voice"]
        mai = [c for c in spec["cases"] if c["kind"] == "mai-ceiling"]
        self.assertEqual(len(controlled), 4)
        self.assertEqual(len(mai), 8)
        self.assertTrue(all(len(c["options"]) == 4 for c in spec["cases"]))

    def test_controlled_cases_keep_same_voice_identity(self):
        spec = experiment_spec()
        for case in spec["cases"]:
            if case["kind"] != "controlled-same-base-voice":
                continue
            self.assertIn(case["voice"], {"fr-FR-DeniseNeural", "fr-FR-HenriNeural"})
            providers = {o["provider"] for o in case["options"]}
            self.assertEqual(providers, {"edge", "azure"})

    def test_mai_hard_cases_use_native_styles(self):
        spec = experiment_spec()
        mai = [c for c in spec["cases"] if c["kind"] == "mai-ceiling"]
        styles = {
            o.get("style")
            for case in mai
            for o in case["options"]
            if o.get("style")
        }
        self.assertTrue({"fearful", "whispering", "determined", "surprised"}.issubset(styles))

    def test_render_writes_48_clips_manifest_and_blind_player(self):
        edge = FakeProvider("edge")
        azure = FakeProvider("azure")
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            result = render_experiment(root, edge=edge, azure=azure)
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["rendered_count"], 48)
            self.assertEqual(result["failure_count"], 0)
            self.assertEqual(len(list((root / "clips").glob("*.mp3"))), 48)
            self.assertTrue((root / "manifest.json").exists())
            self.assertTrue((root / "index.html").exists())
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(manifest["production_promotion"])
            self.assertEqual(len(edge.segments), 4)
            self.assertEqual(len(azure.segments), 44)
            self.assertTrue(any(s.get("style") == "fearful" for s in azure.segments))
            self.assertTrue(all(s.get("language_locale") == "fr-FR" for s in edge.segments + azure.segments))


if __name__ == "__main__":
    unittest.main()
