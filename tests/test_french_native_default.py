import unittest

from audio_engine.voices import load_voice_config, public_catalog, resolve_segments


class FrenchNativeDefaultTests(unittest.TestCase):
    def setUp(self):
        self.config, _ = load_voice_config()

    def test_fr_fr_default_is_native_henri_narrator(self):
        default = self.config["language_defaults"]["fr-FR"]
        self.assertEqual(default["preset"], "narrateur-vif")
        self.assertEqual(default["voice"], "fr-FR-HenriNeural")
        self.assertEqual(default["voice_class"], "native")
        self.assertNotIn("Multilingual", default["voice"])

    def test_narrateur_vif_resolves_to_henri_with_existing_prosody(self):
        program = {
            "language": "fr-FR",
            "segments": [{
                "preset": "narrateur-vif",
                "text": "Entrez par la Puerta del León puis poursuivez en français.",
            }]
        }
        segment = resolve_segments(program, self.config)[0]
        self.assertEqual(segment["voice"], "fr-FR-HenriNeural")
        self.assertEqual(segment["rate"], "+8%")
        self.assertEqual(segment["pitch"], "+14Hz")
        self.assertEqual(segment["volume"], "+5%")

    def test_uncast_fr_fr_segment_uses_native_language_default(self):
        program = {
            "language": "fr-FR",
            "segments": [{
                "target": {},
                "text": "Narration française sans casting explicite.",
            }],
        }
        segment = resolve_segments(program, self.config)[0]
        self.assertEqual(segment["resolved_preset"], "narrateur-vif")
        self.assertEqual(segment["voice"], "fr-FR-HenriNeural")
        self.assertEqual(segment["casting_alternatives"], [])

    def test_nonempty_casting_target_still_uses_role_ranking(self):
        program = {
            "language": "fr-FR",
            "segments": [{
                "target": {"gender": "female", "tags": ["marchande"]},
                "text": "Ceci reste une demande de casting explicite.",
            }],
        }
        segment = resolve_segments(program, self.config)[0]
        self.assertEqual(segment["resolved_preset"], "marchande-truculente")
        self.assertEqual(segment["voice"], "fr-FR-DeniseNeural")
        self.assertTrue(segment["casting_alternatives"])

    def test_explicit_multilingual_voice_remains_explicit_opt_in(self):
        program = {
            "language": "fr-FR",
            "segments": [{
                "voice": "fr-FR-RemyMultilingualNeural",
                "text": "Voix explicitement demandée.",
            }]
        }
        segment = resolve_segments(program, self.config)[0]
        self.assertEqual(segment["voice"], "fr-FR-RemyMultilingualNeural")
        self.assertIsNone(segment["resolved_preset"])

    def test_role_specific_preset_is_not_silently_recast(self):
        program = {
            "language": "fr-FR",
            "segments": [{
                "preset": "officier-autorite",
                "text": "Ordre explicite du rôle.",
            }]
        }
        segment = resolve_segments(program, self.config)[0]
        self.assertEqual(segment["voice"], "fr-FR-RemyMultilingualNeural")
        self.assertEqual(segment["resolved_preset"], "officier-autorite")

    def test_public_catalog_exposes_language_default(self):
        catalog = public_catalog(self.config)
        self.assertEqual(
            catalog["language_defaults"]["fr-FR"]["voice"],
            "fr-FR-HenriNeural",
        )


if __name__ == "__main__":
    unittest.main()
