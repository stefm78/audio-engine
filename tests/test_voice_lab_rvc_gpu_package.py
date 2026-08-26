from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.voice_lab_rvc_gpu_package import (
    BATCH_SIZE,
    MODEL_ASSETS,
    RVC_CONFIG_BLOB,
    RVC_REVISION,
    TOTAL_EPOCHS,
    build_filelist,
    expected_training_argv,
    package_spec,
    validate_dataset_manifest,
    write_filelist,
)


class RvcGpuPackageTests(unittest.TestCase):
    def test_contract_is_frozen_v2_32k_batch4_200_epochs(self):
        spec = package_spec()
        self.assertEqual(spec["rvc"]["revision"], RVC_REVISION)
        self.assertEqual(spec["rvc"]["config_git_blob"], RVC_CONFIG_BLOB)
        self.assertEqual(BATCH_SIZE, 4)
        self.assertEqual(TOTAL_EPOCHS, 200)
        self.assertEqual(spec["training"]["seed"], 1234)
        self.assertFalse(spec["training"]["parameter_tuning"])
        self.assertFalse(spec["production_qualified"])
        self.assertEqual(len(MODEL_ASSETS), 5)

    def test_training_argv_has_no_dynamic_hyperparameters(self):
        argv = expected_training_argv()
        self.assertIn("-bs", argv)
        self.assertEqual(argv[argv.index("-bs") + 1], "4")
        self.assertEqual(argv[argv.index("-te") + 1], "200")
        self.assertEqual(argv[argv.index("-f0") + 1], "1")
        self.assertEqual(argv[argv.index("-v") + 1], "v2")
        self.assertEqual(argv[argv.index("-c") + 1], "0")

    def test_dataset_manifest_requires_all_machine_gates(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "manifest.json"
            data = {
                "status": "dataset-pass",
                "accepted_duration_seconds": 312.0,
                "aggregate_wer": 0.012,
                "expansion_acceptance_rate": 0.90,
                "retries": 0,
                "substitutions": 0,
            }
            p.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate_dataset_manifest(p)["status"], "dataset-pass")
            data["aggregate_wer"] = 0.051
            p.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_dataset_manifest(p)

    def test_filelist_matches_rvc_single_speaker_f0_layout(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            exp = root / "logs" / "lucie_rvc_v2_32k"
            for sub in ("0_gt_wavs", "3_feature768", "2a_f0", "2b-f0nsf"):
                (exp / sub).mkdir(parents=True, exist_ok=True)
            for name in ("000.wav", "001.wav"):
                (exp / "0_gt_wavs" / name).write_bytes(b"wav")
                (exp / "3_feature768" / f"{Path(name).stem}.npy").write_bytes(b"f")
                (exp / "2a_f0" / f"{name}.npy").write_bytes(b"f0")
                (exp / "2b-f0nsf" / f"{name}.npy").write_bytes(b"f0n")
            rows = build_filelist(exp)
            self.assertEqual(len(rows), 2)
            self.assertTrue(rows[0].endswith("|0"))
            out = write_filelist(exp, root)
            lines = out.read_text().splitlines()
            self.assertEqual(len(lines), 4)
            self.assertEqual(lines[-1], lines[-2])
            self.assertIn("mute32k.wav", lines[-1])


if __name__ == "__main__":
    unittest.main()
