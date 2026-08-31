import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_engine.voice_lab_azure import (
    AzureSpeechLabClient,
    AzureSpeechLabError,
    build_ssml,
)


class FakeResponse:
    def __init__(self, payload=b"fake-mp3"):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return self.payload


class AzureSpeechLabTests(unittest.TestCase):
    def test_ssml_escapes_text_and_serializes_style(self):
        ssml = build_ssml(
            'Ulysse & Pénélope < ensemble',
            'fr-FR-HenriNeural',
            style='sad',
            styledegree=0.75,
            rate='-4%',
            pitch='-10Hz',
            volume='+2%',
        )
        self.assertIn('Ulysse &amp; Pénélope &lt; ensemble', ssml)
        self.assertIn('mstts:express-as style="sad" styledegree="0.75"', ssml)
        self.assertIn('prosody rate="-4%" pitch="-10Hz" volume="+2%"', ssml)
        self.assertIn('voice name="fr-FR-HenriNeural"', ssml)

    def test_invalid_styledegree_rejected(self):
        with self.assertRaises(ValueError):
            build_ssml("Bonjour", "fr-FR-HenriNeural", style="sad", styledegree=2.1)
        with self.assertRaises(ValueError):
            build_ssml("Bonjour", "fr-FR-HenriNeural", styledegree=1.0)

    def test_missing_credentials_fail_explicitly(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AzureSpeechLabError):
                AzureSpeechLabClient.from_env()

    def test_request_uses_region_headers_and_writes_audio(self):
        captured = {}
        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = request.data.decode("utf-8")
            captured["timeout"] = timeout
            return FakeResponse(b"abc123")

        client = AzureSpeechLabClient("secret", "francecentral", opener=opener)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "clip.mp3"
            manifest = client.synthesize(
                "Pénélope…",
                "fr-FR-HenriNeural",
                out,
                style="sad",
                styledegree=0.8,
            )
            self.assertEqual(out.read_bytes(), b"abc123")
        self.assertEqual(
            captured["url"],
            "https://francecentral.tts.speech.microsoft.com/cognitiveservices/v1",
        )
        headers = {k.lower(): v for k, v in captured["headers"].items()}
        self.assertEqual(headers["ocp-apim-subscription-key"], "secret")
        self.assertEqual(headers["x-microsoft-outputformat"], "audio-24khz-96kbitrate-mono-mp3")
        self.assertIn('style="sad"', captured["body"])
        self.assertEqual(manifest["provider"], "azure-speech-lab")
        self.assertNotIn("key", manifest)


if __name__ == "__main__":
    unittest.main()
