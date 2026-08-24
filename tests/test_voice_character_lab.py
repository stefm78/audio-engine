import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.voice_character_lab import (
    CharacterLabError,
    freeze_character_identity,
    load_character_identity,
    render_character_lines,
)


class _FakeProvider:
    identity_mode = "x_vector_only"

    def __init__(self, fail_id=None):
        self.fail_id = fail_id
        self.prompt_calls = 0
        self.calls = []

    def build_identity_prompt(self, anchor):
        self.prompt_calls += 1
        return {"anchor": Path(anchor).name}

    def synthesize(self, segment, path, *, voice_clone_prompt):
        self.calls.append((segment.copy(), voice_clone_prompt.copy()))
        if self.fail_id and self.fail_id in str(segment["text"]):
            raise RuntimeError("synthetic line failure")
        Path(path).write_bytes((segment["text"] + str(segment["seed"])).encode())


class CharacterLabTests(unittest.TestCase):
    def _pack(self, root):
        source = root / "source.wav"
        source.write_bytes(b"approved-french-anchor")
        pack = root / "pack"
        result = freeze_character_identity(
            "claire",
            source,
            pack,
            base_seed=42,
            source={"qualification_issue": 65},
        )
        return source, pack, result

    def test_freeze_creates_hash_bound_non_production_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, pack, result = self._pack(root)
            data = json.loads((pack / "character.json").read_text(encoding="utf-8"))
            expected = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(result["anchor_sha256"], expected)
            self.assertEqual(data["anchor"]["sha256"], expected)
            self.assertFalse(data["anchor"]["regeneration"])
            self.assertTrue(data["claims"]["stable_character"])
            self.assertFalse(data["claims"]["age_lineage"])
            self.assertFalse(data["claims"]["production_promoted"])

    def test_freeze_refuses_silent_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, pack, _ = self._pack(root)
            other = root / "other.wav"
            other.write_bytes(b"different")
            with self.assertRaisesRegex(CharacterLabError, "silent replacement"):
                freeze_character_identity("claire", other, pack)

    def test_load_fails_closed_on_tampered_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, pack, _ = self._pack(root)
            (pack / "anchor.wav").write_bytes(b"tampered")
            with self.assertRaisesRegex(CharacterLabError, "hash mismatch"):
                load_character_identity(pack / "character.json")

    def test_contract_rejects_unqualified_age_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, pack, _ = self._pack(root)
            spec = pack / "character.json"
            data = json.loads(spec.read_text(encoding="utf-8"))
            data["claims"]["age_lineage"] = True
            spec.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(CharacterLabError, "age-lineage"):
                load_character_identity(spec)

    def test_render_builds_identity_once_and_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, pack, _ = self._pack(root)
            provider = _FakeProvider()
            lines = [
                {"id": "panic", "text": "Sortez maintenant !"},
                {"id": "calm", "text": "Je vais vous expliquer."},
            ]
            first = render_character_lines(pack / "character.json", lines, root / "out1", provider=provider)
            seeds1 = [item["seed"] for item in first["rendered"]]
            provider2 = _FakeProvider()
            second = render_character_lines(pack / "character.json", lines, root / "out2", provider=provider2)
            seeds2 = [item["seed"] for item in second["rendered"]]
            self.assertEqual(first["status"], "success")
            self.assertEqual(first["rendered_count"], 2)
            self.assertEqual(provider.prompt_calls, 1)
            self.assertEqual(provider2.prompt_calls, 1)
            self.assertEqual(seeds1, seeds2)
            self.assertTrue(first["anchor_verified_before_and_after"])
            self.assertFalse(first["production_promoted"])

    def test_line_failure_is_best_effort_without_recast(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, pack, _ = self._pack(root)
            provider = _FakeProvider(fail_id="FAIL")
            result = render_character_lines(
                pack / "character.json",
                [
                    {"id": "one", "text": "Première ligne."},
                    {"id": "two", "text": "FAIL"},
                    {"id": "three", "text": "Troisième ligne."},
                ],
                root / "out",
                provider=provider,
            )
            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["rendered_count"], 2)
            self.assertEqual(result["failure_count"], 1)
            self.assertEqual(provider.prompt_calls, 1)
            self.assertEqual(len(provider.calls), 3)
            self.assertEqual(result["provider"], "qwen3-xvector-lab")

    def test_invalid_line_is_contract_error_not_silent_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, pack, _ = self._pack(root)
            with self.assertRaisesRegex(CharacterLabError, "empty text"):
                render_character_lines(
                    pack / "character.json",
                    [{"id": "bad", "text": ""}],
                    root / "out",
                    provider=_FakeProvider(),
                )


if __name__ == "__main__":
    unittest.main()
