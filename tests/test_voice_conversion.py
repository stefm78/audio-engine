import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_engine.cli import build_parser
from audio_engine.contract import ContractError
from audio_engine.voice_conversion import (
    convert_beltout_once,
    load_beltout_checkpoint_manifest,
    verify_beltout_conversion_inputs,
)


ROLES = ("decoder", "pitch", "encoder", "flow", "mel2wav", "speaker", "tokenizer")


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


class BeltOutVoiceConversionTests(unittest.TestCase):
    def checkpoint_manifest(self, root):
        data = {
            role: {"file": f"{role}.bin", "sha256": sha_bytes(role.encode())}
            for role in ROLES
        }
        path = Path(root) / "checkpoints.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_checkpoint_manifest_requires_exact_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.checkpoint_manifest(tmp)
            parsed = load_beltout_checkpoint_manifest(path)
            self.assertEqual(set(parsed), set(ROLES))
            data = json.loads(path.read_text(encoding="utf-8"))
            data.pop("pitch")
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "must contain exactly"):
                load_beltout_checkpoint_manifest(path)

    def test_existing_output_blocks_one_shot_before_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.wav"
            target = root / "target.wav"
            source.write_bytes(b"source")
            target.write_bytes(b"target")
            output = root / "out.wav"
            output.write_bytes(b"already-generated")
            with self.assertRaisesRegex(ContractError, "retry or best-of-N is forbidden"):
                verify_beltout_conversion_inputs(
                    source=source,
                    source_sha256=sha_bytes(b"source"),
                    target_reference=target,
                    target_reference_sha256=sha_bytes(b"target"),
                    beltout_source=root / "beltout",
                    expected_revision="a" * 40,
                    checkpoint_dir=root / "checkpoints",
                    checkpoint_manifest=self.checkpoint_manifest(root),
                    output=output,
                    report=root / "report.json",
                    seed=1,
                    n_timesteps=10,
                )

    def test_wrong_source_hash_fails_before_model_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.wav"
            target = root / "target.wav"
            source.write_bytes(b"source")
            target.write_bytes(b"target")
            checkpoints = root / "checkpoints"
            checkpoints.mkdir()
            with self.assertRaisesRegex(ContractError, "source SHA-256 mismatch"):
                verify_beltout_conversion_inputs(
                    source=source,
                    source_sha256="0" * 64,
                    target_reference=target,
                    target_reference_sha256=sha_bytes(b"target"),
                    beltout_source=root / "beltout",
                    expected_revision="a" * 40,
                    checkpoint_dir=checkpoints,
                    checkpoint_manifest=self.checkpoint_manifest(root),
                    output=root / "out.wav",
                    report=root / "report.json",
                    seed=1,
                    n_timesteps=10,
                )

    def test_success_report_binds_inputs_conversion_and_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "out.wav"
            report = root / "report.json"
            validated = {
                "source": root / "source.wav",
                "source_sha256": "1" * 64,
                "target_reference": root / "target.wav",
                "target_reference_sha256": "2" * 64,
                "beltout_source": root / "beltout",
                "expected_revision": "3" * 40,
                "checkpoint_dir": root / "checkpoints",
                "checkpoints": {
                    role: {
                        "file": f"{role}.bin",
                        "path": str(root / f"{role}.bin"),
                        "sha256": sha_bytes(role.encode()),
                    }
                    for role in ROLES
                },
                "output": output,
                "report": report,
                "seed": 42,
                "n_timesteps": 10,
            }

            def fake_convert(actual):
                actual["output"].write_bytes(b"converted")
                return {
                    "technical": {"status": "PASS"},
                    "source_duration_seconds": 1.0,
                    "output_duration_seconds": 1.0,
                    "duration_ratio": 1.0,
                    "duration_pass": True,
                    "speaker_embedding": {"direction_pass": True},
                    "pass": True,
                }

            with (
                patch(
                    "audio_engine.voice_conversion.verify_beltout_conversion_inputs",
                    return_value=validated,
                ),
                patch(
                    "audio_engine.voice_conversion._convert_with_beltout",
                    side_effect=fake_convert,
                ),
            ):
                result = convert_beltout_once(
                    source="unused",
                    source_sha256="1" * 64,
                    target_reference="unused",
                    target_reference_sha256="2" * 64,
                    beltout_source="unused",
                    expected_revision="3" * 40,
                    checkpoint_dir="unused",
                    checkpoint_manifest="unused",
                    output=output,
                    report=report,
                    seed=42,
                    n_timesteps=10,
                )

            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["retry_allowed_after_output"])
            self.assertFalse(result["conversion"]["best_of_n"])
            self.assertFalse(result["conversion"]["second_pass"])
            self.assertEqual(result["output"]["sha256"], sha_bytes(b"converted"))
            self.assertEqual(json.loads(report.read_text(encoding="utf-8")), result)

    def test_cli_exposes_explicit_one_shot_arguments(self):
        args = build_parser().parse_args([
            "voice-conversion",
            "beltout-once",
            "--source", "source.wav",
            "--source-sha256", "1" * 64,
            "--target-reference", "target.wav",
            "--target-reference-sha256", "2" * 64,
            "--beltout-source", "beltout",
            "--expected-revision", "3" * 40,
            "--checkpoint-dir", "checkpoints",
            "--checkpoint-manifest", "checkpoints.json",
            "--seed", "42",
            "--n-timesteps", "10",
            "--out", "out.wav",
            "--report", "report.json",
        ])
        self.assertEqual(args.command, "voice-conversion")
        self.assertEqual(args.voice_conversion_command, "beltout-once")
        self.assertEqual(args.seed, 42)
        self.assertEqual(args.n_timesteps, 10)


if __name__ == "__main__":
    unittest.main()
