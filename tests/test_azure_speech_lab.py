import tempfile
import unittest
from pathlib import Path
from unittest import mock

from audio_engine.providers.azure_speech_lab import AzureSpeechLabProvider


class _Response:
    def __init__(self, payload=b"mp3"):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.payload


class AzureSpeechLabProviderTests(unittest.TestCase):
    def test_requires_explicit_credentials(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "AZURE_SPEECH_KEY"):
                AzureSpeechLabProvider()

    def test_ssml_supports_native_style_without_touching_identity(self):
        provider = AzureSpeechLabProvider(key="key", region="westeurope")
        ssml = provider._ssml({
            "text": "Vite ! Ils arrivent !",
            "voice": "fr-FR-Marc:MAI-Voice-2",
            "language_locale": "fr-FR",
            "style": "fearful",
            "styledegree": 1.5,
        })
        self.assertIn("name='fr-FR-Marc:MAI-Voice-2'", ssml)
        self.assertIn("style='fearful'", ssml)
        self.assertIn("styledegree='1.5'", ssml)
        self.assertIn("xml:lang='fr-FR'", ssml)

    def test_style_degree_is_bounded(self):
        provider = AzureSpeechLabProvider(key="key", region="westeurope")
        with self.assertRaisesRegex(ValueError, "between 0.01 and 2.0"):
            provider._ssml({
                "text": "Texte.",
                "voice": "fr-FR-Soleil:MAI-Voice-2",
                "style": "fearful",
                "styledegree": 2.5,
            })

    def test_synthesize_uses_rest_endpoint_and_writes_payload(self):
        provider = AzureSpeechLabProvider(key="secret", region="francecentral")
        with tempfile.TemporaryDirectory() as temp_value:
            target = Path(temp_value) / "voice.mp3"
            with mock.patch(
                "audio_engine.providers.azure_speech_lab.urllib.request.urlopen",
                return_value=_Response(b"azure-mp3"),
            ) as call:
                provider.synthesize({
                    "text": "Depuis trois nuits...",
                    "voice": "fr-FR-Soleil:MAI-Voice-2",
                    "style": "whispering",
                }, target)
            self.assertEqual(target.read_bytes(), b"azure-mp3")
            request = call.call_args.args[0]
            self.assertEqual(
                request.full_url,
                "https://francecentral.tts.speech.microsoft.com/cognitiveservices/v1",
            )
            self.assertIn(b"whispering", request.data)
            self.assertEqual(request.get_header("Ocp-apim-subscription-key"), "secret")


if __name__ == "__main__":
    unittest.main()
