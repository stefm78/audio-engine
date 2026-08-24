import unittest

from audio_engine.voice_lab import probe_catalog


class VoiceLabPanicProbeTests(unittest.TestCase):
    def test_canonical_panic_probe_uses_linguistically_validated_replacement(self):
        probes = {item["id"]: item for item in probe_catalog()["probes"]}
        panic = probes["emotion-panic"]
        self.assertEqual(panic["text"], "Vite ! Ils arrivent ! Fermez la porte !")
        self.assertNotIn("Courez", panic["text"])


if __name__ == "__main__":
    unittest.main()
