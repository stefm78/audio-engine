import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.audio import run_ffmpeg
from audio_engine.voice.render import render_voice_clip


class PreservingProvider:
    name = "preserving-test"
    processing = "local-test"
    edge_silence_normalization = False

    def synthesize(self, segment, path):
        run_ffmpeg([
            "-f", "lavfi",
            "-i", "sine=frequency=440:sample_rate=24000:duration=0.20",
            "-ac", "1",
            "-c:a", "libmp3lame",
            "-b:a", "64k",
            str(path),
        ])


class ProviderNormalizationTests(unittest.TestCase):
    def test_provider_can_preserve_clip_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            segment = {
                "text": "Test",
                "voice": "test-voice",
                "rate": "+0%",
                "pitch": "+0Hz",
                "volume": "+0%",
            }
            provider = PreservingProvider()
            _, _, fingerprint = render_voice_clip(segment, provider, root)
            metadata = json.loads(
                (root / f"{fingerprint}.json").read_text(encoding="utf-8")
            )
            self.assertFalse(metadata["edge_silence_normalized"])


if __name__ == "__main__":
    unittest.main()
