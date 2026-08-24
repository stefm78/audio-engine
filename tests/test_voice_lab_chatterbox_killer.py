import tempfile
import unittest
from pathlib import Path

from audio_engine.voice_lab_chatterbox_killer import experiment_spec, write_blind_player


class VoiceLabChatterboxKillerTests(unittest.TestCase):
    def test_spec_is_minimal_and_never_promotes_production(self):
        spec = experiment_spec()
        self.assertFalse(spec["production_promotion"])
        self.assertEqual(len(spec["cases"]), 2)
        self.assertEqual({c["id"] for c in spec["cases"]}, {"panic", "mystery"})
        self.assertTrue(all(len(c["treatments"]) == 4 for c in spec["cases"]))

    def test_panic_probe_uses_corrected_french_text(self):
        spec = experiment_spec()
        panic = next(c for c in spec["cases"] if c["id"] == "panic")
        self.assertEqual(panic["text"], "Vite ! Ils arrivent ! Fermez la porte !")
        self.assertNotIn("Courez", panic["text"])

    def test_treatments_compare_edge_to_three_chatterbox_levels(self):
        spec = experiment_spec()
        treatments = spec["cases"][0]["treatments"]
        self.assertEqual([t["provider"] for t in treatments].count("edge"), 1)
        self.assertEqual([t["provider"] for t in treatments].count("chatterbox"), 3)
        levels = [t.get("exaggeration") for t in treatments if t["provider"] == "chatterbox"]
        self.assertEqual(levels, [0.5, 0.8, 1.2])

    def test_player_contains_only_complete_cases(self):
        spec = experiment_spec()
        rendered = []
        for case in spec["cases"]:
            for treatment in case["treatments"]:
                rendered.append({
                    "case_id": case["id"],
                    "treatment_id": treatment["id"],
                    "file": f"clips/{case['id']}--{treatment['id']}.wav",
                })
        manifest = {**spec, "rendered": rendered}
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            result = write_blind_player(manifest, root)
            self.assertEqual(result["trial_count"], 2)
            player = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn("Prononciation invalide", player)
            self.assertIn("Aucune acceptable", player)

    def test_core_dependencies_do_not_include_chatterbox(self):
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
        self.assertNotIn('"chatterbox-tts', pyproject)


if __name__ == "__main__":
    unittest.main()
