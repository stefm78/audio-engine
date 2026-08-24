import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_engine.voice_lab_qwen3_character_composition import (
    CASES,
    CHARACTERS,
    assemble_bundle,
    experiment_spec,
    render_character,
)


def _wav(payload):
    payload = bytes(payload)
    return b"RIFF" + (len(payload) + 4).to_bytes(4, "little") + b"WAVE" + payload


class _FakeProvider:
    identity_mode = "x_vector_only"

    def __init__(self):
        self.prompt_calls = 0
        self.calls = []

    def build_identity_prompt(self, anchor):
        self.prompt_calls += 1
        return {"anchor": Path(anchor).name}

    def synthesize(self, segment, path, *, voice_clone_prompt):
        self.calls.append((segment.copy(), voice_clone_prompt.copy()))
        Path(path).write_bytes(_wav(segment["text"].encode("utf-8")))


class CharacterCompositionTests(unittest.TestCase):
    def test_spec_is_broader_but_still_lab_only(self):
        spec = experiment_spec()
        self.assertEqual(spec["identity_mode"], "x_vector_only")
        self.assertEqual(len(spec["cases"]), 4)
        self.assertFalse(spec["decision"]["automatic_production_promotion"])
        self.assertFalse(spec["decision"]["age_lineage"])
        self.assertIn("7/8", spec["decision"]["acting_pass"])
        self.assertIn("4/4", spec["decision"]["identity_pass"])

    def test_render_uses_exact_anchor_then_real_character_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            anchors = root / "anchors"
            anchors.mkdir()
            anchor = anchors / CHARACTERS["claire"]["anchor_file"]
            anchor.write_bytes(_wav(b"claire"))
            digest = hashlib.sha256(anchor.read_bytes()).hexdigest()
            provider = _FakeProvider()
            with patch.dict(CHARACTERS["claire"], {"sha256": digest}):
                result = render_character("claire", anchors, root / "out", provider=provider)
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["rendered_count"], len(CASES))
            self.assertEqual(provider.prompt_calls, 1)
            self.assertEqual(len(provider.calls), len(CASES))
            pack = json.loads((root / "out" / "character-pack" / "character.json").read_text(encoding="utf-8"))
            self.assertEqual(pack["anchor"]["sha256"], digest)
            self.assertFalse(pack["claims"]["production_promoted"])
            manifest = json.loads((root / "out" / "render" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["character_id"], "claire")
            self.assertEqual(manifest["rendered_count"], len(CASES))

    def test_wrong_qualified_anchor_fails_before_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            anchors = root / "anchors"
            anchors.mkdir()
            anchor = anchors / CHARACTERS["claire"]["anchor_file"]
            anchor.write_bytes(_wav(b"wrong"))
            provider = _FakeProvider()
            with self.assertRaisesRegex(ValueError, "qualified anchor mismatch"):
                render_character("claire", anchors, root / "out", provider=provider)
            self.assertEqual(provider.prompt_calls, 0)

    def test_assemble_produces_four_screen_blind_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            anchors = root / "anchors"
            anchors.mkdir()
            digests = {}
            for character_id, character in CHARACTERS.items():
                anchor = anchors / character["anchor_file"]
                anchor.write_bytes(_wav(character_id.encode()))
                digests[character_id] = hashlib.sha256(anchor.read_bytes()).hexdigest()

            with patch.dict(CHARACTERS["claire"], {"sha256": digests["claire"]}), patch.dict(
                CHARACTERS["lucie"], {"sha256": digests["lucie"]}
            ):
                render_character("claire", anchors, root / "inputs" / "claire", provider=_FakeProvider())
                render_character("lucie", anchors, root / "inputs" / "lucie", provider=_FakeProvider())
                bundle = assemble_bundle(root / "inputs", root / "bundle", seed=123)

            self.assertEqual(bundle["status"], "success")
            self.assertEqual(bundle["trial_count"], len(CASES))
            self.assertEqual({trial["id"] for trial in bundle["trials"]}, {case["id"] for case in CASES})
            for trial in bundle["trials"]:
                self.assertEqual({option["letter"] for option in trial["options"]}, {"A", "B"})
                self.assertIn(trial["correct_reference_for_A"], {"Référence 1", "Référence 2"})
            html = (root / "bundle" / "index.html").read_text(encoding="utf-8")
            self.assertIn("4 écrans seulement", html)
            self.assertIn("Précédent", html)
            self.assertIn("try{localStorage.setItem", html)
            self.assertIn("qwen3-character-composition-v1", html)
            self.assertIn("Exporter le JSON", html)


if __name__ == "__main__":
    unittest.main()
