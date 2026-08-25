import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_engine.voice_lab_qwen3_style_transplant import CASES, CHARACTERS, assemble_bundle, experiment_spec, render_character


def _wav(payload=b"x"):
    return b"RIFF" + (len(payload) + 4).to_bytes(4, "little") + b"WAVE" + payload


class _FakeProvider:
    identity_mode = "frozen-xvector-plus-foreign-icl-style"

    def __init__(self):
        self.identity_calls = 0
        self.style_calls = []
        self.synth_calls = []

    def build_identity_embedding(self, anchor):
        self.identity_calls += 1
        return {"anchor": Path(anchor).name}

    def build_style_prompt(self, identity, style_wav, style_text):
        self.style_calls.append((identity, Path(style_wav).name, style_text))
        return {"identity": identity, "style": Path(style_wav).name}

    def synthesize(self, segment, path, *, voice_clone_prompt):
        self.synth_calls.append((segment.copy(), voice_clone_prompt.copy()))
        Path(path).write_bytes(_wav(segment["text"].encode("utf-8")))


class StyleTransplantTests(unittest.TestCase):
    def test_spec_targets_only_failed_breadth_cases(self):
        spec = experiment_spec()
        self.assertEqual([c["id"] for c in CASES], ["mystery", "wonder", "sadness-contained"])
        self.assertIn("3/3", spec["decision"]["identity_pass"])
        self.assertIn("5/6", spec["decision"]["acting_pass"])
        self.assertTrue(spec["decision"]["no_tuning"])
        self.assertFalse(spec["decision"]["production_promotion"])

    def test_render_reuses_one_identity_embedding_and_three_style_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            anchors, styles = root / "anchors", root / "styles"
            anchors.mkdir(); styles.mkdir()
            anchor = anchors / CHARACTERS["claire"]["anchor_file"]
            anchor.write_bytes(_wav(b"claire"))
            digest = hashlib.sha256(anchor.read_bytes()).hexdigest()
            for case in CASES:
                (styles / f"{case['id']}.wav").write_bytes(_wav(case["id"].encode()))
            provider = _FakeProvider()
            with patch.dict(CHARACTERS["claire"], {"sha256": digest}):
                result = render_character("claire", anchors, styles, root / "out", provider=provider)
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["rendered_count"], 3)
            self.assertEqual(provider.identity_calls, 1)
            self.assertEqual(len(provider.style_calls), 3)
            self.assertEqual(len(provider.synth_calls), 3)
            self.assertTrue(all(call[0]["language"] == "French" for call in provider.synth_calls))

    def test_wrong_anchor_fails_before_identity_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); anchors, styles = root / "anchors", root / "styles"
            anchors.mkdir(); styles.mkdir()
            (anchors / CHARACTERS["claire"]["anchor_file"]).write_bytes(_wav(b"wrong"))
            for case in CASES:
                (styles / f"{case['id']}.wav").write_bytes(_wav())
            provider = _FakeProvider()
            with self.assertRaisesRegex(ValueError, "qualified anchor mismatch"):
                render_character("claire", anchors, styles, root / "out", provider=provider)
            self.assertEqual(provider.identity_calls, 0)

    def test_bundle_is_three_blind_screens(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); anchors, styles = root / "anchors", root / "styles"
            anchors.mkdir(); styles.mkdir()
            digests = {}
            for cid, char in CHARACTERS.items():
                p = anchors / char["anchor_file"]; p.write_bytes(_wav(cid.encode())); digests[cid] = hashlib.sha256(p.read_bytes()).hexdigest()
            for case in CASES:
                (styles / f"{case['id']}.wav").write_bytes(_wav(case["id"].encode()))
            with patch.dict(CHARACTERS["claire"], {"sha256": digests["claire"]}), patch.dict(CHARACTERS["lucie"], {"sha256": digests["lucie"]}):
                render_character("claire", anchors, styles, root / "inputs" / "claire", provider=_FakeProvider())
                render_character("lucie", anchors, styles, root / "inputs" / "lucie", provider=_FakeProvider())
                bundle = assemble_bundle(root / "inputs", root / "bundle", seed=17)
            self.assertEqual(bundle["trial_count"], 3)
            self.assertEqual({t["id"] for t in bundle["trials"]}, {c["id"] for c in CASES})
            html = (root / "bundle" / "index.html").read_text(encoding="utf-8")
            self.assertIn("qwen3-style-transplant-killer-v1", html)
            self.assertIn("Exporter le JSON", html)
            self.assertIn("Précédent", html)
            self.assertIn("try{localStorage.setItem", html)


if __name__ == "__main__":
    unittest.main()
