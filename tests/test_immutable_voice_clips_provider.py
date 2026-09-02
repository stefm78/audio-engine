import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_engine.contract import ContractError
from audio_engine.providers.factory import build_promoted_providers
from audio_engine.providers.immutable_voice_clips import ImmutableVoiceClipsProvider


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ImmutableVoiceClipsProviderTests(unittest.TestCase):
    def make_fixture(self, root):
        root = Path(root)
        clip = root / "clip.wav"
        clip.write_bytes(b"RIFF-immutable-converted-clip")
        voices = root / "voices.json"
        voices.write_text('{"presets":[]}', encoding="utf-8")
        package = {
            "schema_version": 1,
            "id": "immutable-clips-test",
            "provider": {
                "id": "immutable-voice-clips-v1",
                "implementation_version": "1.0.0",
            },
            "runtime": {
                "kind": "python",
                "python": "3.12",
                "device": "cpu",
                "dependencies": [
                    {"name": "recit-audio-engine", "version": "0.9.2"},
                ],
            },
            "model": {
                "id": "immutable-local-clips",
                "source": "local",
                "revision": "bundle-v1",
                "integrity": [
                    {
                        "name": "clip.wav",
                        "path": "clip.wav",
                        "sha256": sha(clip),
                    }
                ],
            },
            "voice_pack_sha256": sha(voices),
            "synthesis": {"seed": 0, "parameters": {}},
            "references": [
                {"id": "slot-1", "path": "clip.wav", "sha256": sha(clip)}
            ],
            "fallback": "fail",
        }
        package_path = root / "provider.json"
        package_path.write_text(json.dumps(package), encoding="utf-8")
        return package_path, clip

    def test_factory_promotes_provider_and_hash_locks_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, _ = self.make_fixture(tmp)
            providers = build_promoted_providers(
                [package_path],
                workspace_root=tmp,
            )
            provider = providers["immutable-voice-clips-v1"]
            self.assertIsInstance(provider, ImmutableVoiceClipsProvider)
            self.assertEqual(len(provider.cache_identity()), 64)
            self.assertFalse(provider.edge_silence_normalization)

    def test_segment_must_explicitly_name_one_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, _ = self.make_fixture(tmp)
            provider = ImmutableVoiceClipsProvider(package_path, workspace_root=tmp)
            with self.assertRaisesRegex(ContractError, "provider_parameters.reference"):
                provider._resolved_reference({
                    "sequence": 1,
                    "text": "Exact authored line.",
                    "voice": "identity",
                })

    def test_unknown_reference_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, _ = self.make_fixture(tmp)
            provider = ImmutableVoiceClipsProvider(package_path, workspace_root=tmp)
            with self.assertRaisesRegex(ContractError, "Unknown immutable voice clip"):
                provider._resolved_reference({
                    "sequence": 1,
                    "text": "Exact authored line.",
                    "voice": "identity",
                    "provider_parameters": {"reference": "wrong"},
                })

    def test_synthesize_only_transcodes_exact_selected_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, clip = self.make_fixture(tmp)
            provider = ImmutableVoiceClipsProvider(package_path, workspace_root=tmp)
            output = Path(tmp) / "out.mp3"
            observed = {}

            def fake_ffmpeg(args):
                observed["args"] = list(args)
                output.write_bytes(b"mp3")

            with patch(
                "audio_engine.providers.immutable_voice_clips.run_ffmpeg",
                side_effect=fake_ffmpeg,
            ):
                provider.synthesize({
                    "sequence": 1,
                    "text": "Exact authored line.",
                    "voice": "identity",
                    "provider_parameters": {"reference": "slot-1"},
                }, output)

            self.assertTrue(output.is_file())
            self.assertIn(str(clip), observed["args"])
            joined = " ".join(observed["args"])
            self.assertNotIn("-af", observed["args"])
            self.assertNotIn("volume=", joined)
            self.assertNotIn("atempo=", joined)
            self.assertNotIn("asetrate=", joined)


if __name__ == "__main__":
    unittest.main()
