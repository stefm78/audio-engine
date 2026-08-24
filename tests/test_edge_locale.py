import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from audio_engine.providers.edge import EdgeProvider, _speech_locale


class EdgeLocaleTests(unittest.TestCase):
    def test_native_voice_uses_its_provider_locale(self):
        communicate = SimpleNamespace(voice="fr-FR-DeniseNeural")
        self.assertEqual(_speech_locale(communicate), "fr-FR")

    def test_explicit_language_locale_overrides_multilingual_voice_locale(self):
        communicate = SimpleNamespace(
            voice="en-US-AvaMultilingualNeural",
            _audio_engine_language_locale="fr-FR",
        )
        self.assertEqual(_speech_locale(communicate), "fr-FR")

    def test_provider_attaches_explicit_language_locale_before_save(self):
        captured = {}

        class FakeCommunicate:
            def __init__(self, text, voice, rate, pitch, volume):
                self.text = text
                self.voice = voice
                captured["instance"] = self

            async def save(self, path):
                Path(path).write_bytes(b"fake")

        with tempfile.TemporaryDirectory() as temp_value:
            output = Path(temp_value) / "voice.mp3"
            with patch("audio_engine.providers.edge.edge_tts.Communicate", FakeCommunicate):
                provider = EdgeProvider()
                asyncio.run(provider.synthesize_async({
                    "text": "Bonjour.",
                    "voice": "en-US-AvaMultilingualNeural",
                    "rate": "+0%",
                    "pitch": "+0Hz",
                    "volume": "+0%",
                    "language_locale": "fr-FR",
                }, output))
            self.assertTrue(output.exists())
            self.assertEqual(
                captured["instance"]._audio_engine_language_locale,
                "fr-FR",
            )


if __name__ == "__main__":
    unittest.main()
