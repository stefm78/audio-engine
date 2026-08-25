from __future__ import annotations

import json
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from audio_engine.voice_lab_qwen3_contrast_casting import (
    BASELINE,
    CANDIDATES,
    IDENTITY_LINES,
    assemble_bundle,
    render_identity_check,
    select_pair,
)


def _write_voice(path, *, f0, seconds=1.4, harmonics=(1.0, 0.4, 0.2), sr=24000):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    norm = sum(abs(value) for value in harmonics)
    values = []
    for index in range(int(sr * seconds)):
        t = index / sr
        signal = sum(
            weight * math.sin(2 * math.pi * f0 * harmonic * t)
            for harmonic, weight in enumerate(harmonics, 1)
        )
        signal *= 0.5 / norm
        values.append(int(max(-0.99, min(0.99, signal)) * 32767))
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sr)
        stream.writeframes(struct.pack(f"<{len(values)}h", *values))


def _sha256(path):
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class FakeProvider:
    identity_mode = "x_vector_only"

    def __init__(self):
        self.prompts = 0

    def build_identity_prompt(self, anchor):
        self.prompts += 1
        return Path(anchor)

    def synthesize(self, segment, path, *, voice_clone_prompt):
        # The exact audio is irrelevant for contract tests; preserve role-dependent pitch.
        pitch = 145 if "claire" in str(voice_clone_prompt) else 270
        _write_voice(path, f0=pitch, seconds=0.8)


class ContrastCastingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _prepare(self):
        baseline = self.root / "baseline"
        candidates = self.root / "candidates"
        _write_voice(baseline / BASELINE["claire"]["file"], f0=180)
        _write_voice(baseline / BASELINE["lucie"]["file"], f0=190)
        # Test fixtures need matching hashes, so patch the in-memory spec only for this test.
        old_hashes = {role: BASELINE[role]["sha256"] for role in BASELINE}
        for role in BASELINE:
            BASELINE[role]["sha256"] = _sha256(baseline / BASELINE[role]["file"])
        _write_voice(candidates / "claire-a.wav", f0=145, seconds=1.6, harmonics=(1.0, 0.55, 0.08))
        _write_voice(candidates / "claire-b.wav", f0=170, seconds=1.45, harmonics=(1.0, 0.35, 0.18))
        _write_voice(candidates / "lucie-a.wav", f0=270, seconds=1.05, harmonics=(1.0, 0.05, 0.7, 0.25))
        _write_voice(candidates / "lucie-b.wav", f0=230, seconds=1.2, harmonics=(1.0, 0.15, 0.5, 0.2))
        return baseline, candidates, old_hashes

    def test_selects_most_contrasted_cross_role_pair(self):
        baseline, candidates, old_hashes = self._prepare()
        try:
            selected = self.root / "selected"
            result = select_pair(candidates, baseline, selected)
            self.assertEqual(result["status"], "selected")
            self.assertTrue(result["selected"]["eligible"])
            self.assertEqual(result["selected"]["claire_id"], "claire-a")
            self.assertIn(result["selected"]["lucie_id"], {"lucie-a", "lucie-b"})
            self.assertTrue((selected / "reference-claire.wav").is_file())
            self.assertTrue((selected / "reference-lucie.wav").is_file())
        finally:
            for role, digest in old_hashes.items():
                BASELINE[role]["sha256"] = digest

    def test_identity_render_builds_one_prompt_for_two_lines(self):
        baseline, candidates, old_hashes = self._prepare()
        try:
            selected = self.root / "selected"
            result = select_pair(candidates, baseline, selected)
            self.assertEqual(result["status"], "selected")
            provider = FakeProvider()
            out = self.root / "claire-result"
            rendered = render_identity_check("claire", selected, out, provider=provider)
            self.assertEqual(rendered["rendered_count"], len(IDENTITY_LINES))
            self.assertEqual(provider.prompts, 1)
        finally:
            for role, digest in old_hashes.items():
                BASELINE[role]["sha256"] = digest

    def test_bundle_has_two_blind_identity_trials(self):
        baseline, candidates, old_hashes = self._prepare()
        try:
            selected = self.root / "selected"
            self.assertEqual(select_pair(candidates, baseline, selected)["status"], "selected")
            for role in ("claire", "lucie"):
                render_identity_check(role, selected, self.root / f"result-{role}", provider=FakeProvider())
            bundle = self.root / "bundle"
            manifest = assemble_bundle(self.root, bundle)
            self.assertEqual(manifest["trial_count"], 2)
            self.assertTrue((bundle / "index.html").is_file())
            self.assertIn("correct_reference_for_A", manifest["trials"][0])
        finally:
            for role, digest in old_hashes.items():
                BASELINE[role]["sha256"] = digest

    def test_candidate_catalog_has_two_variants_per_role(self):
        counts = {"claire": 0, "lucie": 0}
        for item in CANDIDATES.values():
            counts[item["role"]] += 1
        self.assertEqual(counts, {"claire": 2, "lucie": 2})


if __name__ == "__main__":
    unittest.main()
