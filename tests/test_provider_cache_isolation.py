import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_engine.provider_cache import prewarm_promoted_provider_cache
from audio_engine.providers.factory import CacheOnlyProvider
from audio_engine.render import render_program

from test_multi_provider import ToneProvider


class ProviderCacheIsolationTests(unittest.TestCase):
    def write_program_and_voices(self, root):
        root = Path(root)
        program = root / "program.json"
        voices = root / "voices.json"
        program.write_text(
            json.dumps({
                "schema_version": 1,
                "id": "prewarm",
                "title": "Provider prewarm",
                "segments": [
                    {"provider": "alpha", "voice": "voice-a", "text": "Alpha."},
                    {"provider": "beta", "voice": "voice-b", "text": "Beta."},
                    {"provider": "alpha", "voice": "voice-a", "text": "Again."},
                ],
            }),
            encoding="utf-8",
        )
        voices.write_text(json.dumps({"presets": []}), encoding="utf-8")
        return program, voices

    def test_prewarm_selects_only_matching_provider_segments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            program, voices = self.write_program_and_voices(root)
            provider = ToneProvider("alpha", 440)
            calls = []

            def fake_render(segment, actual_provider, cache_root):
                calls.append((segment["text"], actual_provider.name, Path(cache_root)))
                index = len(calls)
                return root / f"{index}.mp3", index == 1, f"fp-{index}"

            with (
                patch(
                    "audio_engine.provider_cache.build_promoted_providers",
                    return_value={"alpha": provider},
                ),
                patch(
                    "audio_engine.provider_cache.render_voice_clip",
                    side_effect=fake_render,
                ),
            ):
                report = prewarm_promoted_provider_cache(
                    program,
                    voices,
                    root / "alpha-package.json",
                    root / "cache",
                )

            self.assertEqual([item[0] for item in calls], ["Alpha.", "Again."])
            self.assertTrue(all(item[1] == "alpha" for item in calls))
            self.assertEqual(report["provider"], "alpha")
            self.assertEqual(report["segment_count"], 2)
            self.assertEqual(report["cache_hits"], 1)
            self.assertEqual(report["cache_misses"], 1)
            self.assertEqual(report["fingerprints"], ["fp-1", "fp-2"])

    def test_cache_only_provider_reuses_prewarmed_clip_without_runtime_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            program = root / "program.json"
            program.write_text(
                json.dumps({
                    "schema_version": 1,
                    "id": "cache-only-hit",
                    "title": "Cache only hit",
                    "segments": [
                        {"provider": "alpha", "voice": "voice-a", "text": "Alpha."},
                    ],
                }),
                encoding="utf-8",
            )
            provider = ToneProvider("alpha", 440)
            first = render_program(program, root / "out", providers={"alpha": provider})
            self.assertEqual(provider.calls, 1)
            shutil.rmtree(root / "out" / "cache-only-hit")

            second = render_program(
                program,
                root / "out",
                providers={"alpha": CacheOnlyProvider(provider)},
            )
            self.assertEqual(provider.calls, 1)
            self.assertEqual(second["mix"]["voice_fingerprints"], first["mix"]["voice_fingerprints"])

    def test_cache_only_provider_fails_closed_on_missing_clip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            program = root / "program.json"
            program.write_text(
                json.dumps({
                    "schema_version": 1,
                    "id": "cache-only-miss",
                    "title": "Cache only miss",
                    "segments": [
                        {"provider": "alpha", "voice": "voice-a", "text": "Alpha."},
                    ],
                }),
                encoding="utf-8",
            )
            provider = ToneProvider("alpha", 440)
            with self.assertRaisesRegex(RuntimeError, "cache-only in final render"):
                render_program(
                    program,
                    root / "out",
                    providers={"alpha": CacheOnlyProvider(provider)},
                )
            self.assertEqual(provider.calls, 0)


if __name__ == "__main__":
    unittest.main()
