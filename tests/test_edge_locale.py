import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from audio_engine.providers.edge import (
    EdgeProvider,
    _explicit_language_scoped_text,
    _speech_locale,
)
from audio_engine.voice.render import (
    provider_cache_identity,
    voice_content_key,
    voice_fingerprint,
)


class EdgeLocaleTests(unittest.TestCase):
    def test_cache_identity_is_explicit_and_keeps_qualified_legacy_aliases(self):
        provider = EdgeProvider()
        self.assertEqual(
            provider_cache_identity(provider),
            "edge-tts-7.2.8|ssml-locale-v1|voice-synthesis-v2-edge-silence-normalized",
        )
        self.assertEqual(
            set(provider.cache_compatible_identities),
            {
                "dfc727bb784bcb630165714b90a01266d524a1c4aa3485b6c6d106e7a1f8e6a6",
                "7c58d0ba7ff7c0bd2b8a14f28a342274407e893f92d1eccdbb0daca90be2b380",
            },
        )

    def test_native_voice_uses_its_provider_locale(self):
        communicate = SimpleNamespace(voice="fr-FR-DeniseNeural")
        self.assertEqual(_speech_locale(communicate), "fr-FR")

    def test_explicit_language_locale_overrides_multilingual_voice_locale(self):
        communicate = SimpleNamespace(
            voice="en-US-AvaMultilingualNeural",
            _audio_engine_language_locale="fr-FR",
        )
        self.assertEqual(_speech_locale(communicate), "fr-FR")

    def test_explicit_locale_wraps_only_multilingual_voice_with_lang_element(self):
        multi = SimpleNamespace(
            voice="fr-FR-RemyMultilingualNeural",
            _audio_engine_language_locale="fr-FR",
        )
        native = SimpleNamespace(
            voice="fr-FR-HenriNeural",
            _audio_engine_language_locale="fr-FR",
        )
        self.assertEqual(
            _explicit_language_scoped_text(multi, "Bonjour."),
            "<lang xml:lang='fr-FR'>Bonjour.</lang>",
        )
        self.assertEqual(
            _explicit_language_scoped_text(native, "Bonjour."),
            "Bonjour.",
        )

    def test_explicit_locale_participates_in_voice_cache_identity(self):
        provider = EdgeProvider()
        baseline = {
            "text": "Qui es-tu ?",
            "voice": "fr-FR-RemyMultilingualNeural",
            "rate": "+5%",
            "pitch": "+8Hz",
            "volume": "+2%",
        }
        localized = {**baseline, "language_locale": "fr-FR"}
        self.assertNotEqual(
            voice_content_key(baseline, "edge"),
            voice_content_key(localized, "edge"),
        )
        self.assertNotEqual(
            voice_fingerprint(baseline, provider),
            voice_fingerprint(localized, provider),
        )

    def test_unavailable_voice_is_reported_explicitly_after_provider_retries(self):
        class FakeNoAudioReceived(Exception):
            pass

        class FakeCommunicate:
            def __init__(self, text, voice, rate, pitch, volume):
                self.voice = voice

            async def save(self, path):
                raise FakeNoAudioReceived("no audio")

        async def fake_list_voices():
            return [
                {"ShortName": "fr-FR-HenriNeural", "Locale": "fr-FR"},
                {"ShortName": "fr-FR-DeniseNeural", "Locale": "fr-FR"},
            ]

        with tempfile.TemporaryDirectory() as temp_value:
            output = Path(temp_value) / "voice.mp3"
            with (
                patch("audio_engine.providers.edge.edge_tts.Communicate", FakeCommunicate),
                patch(
                    "audio_engine.providers.edge.edge_tts.exceptions.NoAudioReceived",
                    FakeNoAudioReceived,
                ),
                patch("audio_engine.providers.edge.edge_tts.list_voices", fake_list_voices),
                patch("audio_engine.providers.edge.asyncio.sleep", return_value=None),
            ):
                provider = EdgeProvider()
                with self.assertRaisesRegex(
                    RuntimeError,
                    "Edge voice is unavailable.*fr-FR-AlainNeural.*No fallback",
                ):
                    asyncio.run(provider.synthesize_async({
                        "text": "Bonjour.",
                        "voice": "fr-FR-AlainNeural",
                        "rate": "+0%",
                        "pitch": "+0Hz",
                        "volume": "+0%",
                    }, output))

    def test_provider_attaches_explicit_language_locale_before_save(self):
        captured = {}

        class FakeCommunicate:
            def __init__(self, text, voice, rate, pitch, volume):
                self.text = text
                self.voice = voice
                self.tts_config = SimpleNamespace(voice=voice)
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
            self.assertEqual(
                captured["instance"].tts_config._audio_engine_language_locale,
                "fr-FR",
            )


if __name__ == "__main__":
    unittest.main()
