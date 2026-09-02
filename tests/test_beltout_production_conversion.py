import math
import tempfile
import unittest
from pathlib import Path

from audio_engine.beltout_conversion import (
    BeltOutConversionError,
    constant_gain_db,
    convert_once,
)


class BeltOutProductionConversionTests(unittest.TestCase):
    def test_constant_gain_matches_rms_ratio(self):
        gain = constant_gain_db(0.2, 0.1, 8.0)
        self.assertAlmostEqual(gain, 20.0 * math.log10(2.0), places=6)

    def test_constant_gain_is_clamped(self):
        self.assertEqual(constant_gain_db(1.0, 0.01, 8.0), 8.0)
        self.assertEqual(constant_gain_db(0.01, 1.0, 8.0), -8.0)

    def test_constant_gain_rejects_invalid_rms(self):
        with self.assertRaises(BeltOutConversionError):
            constant_gain_db(0.0, 0.1, 8.0)
        with self.assertRaises(BeltOutConversionError):
            constant_gain_db(0.1, 0.0, 8.0)

    def test_existing_output_refuses_second_pass_before_runtime_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "converted.wav"
            output.write_bytes(b"already-produced")
            with self.assertRaisesRegex(
                BeltOutConversionError,
                "overwrite/retry forbidden",
            ):
                convert_once(
                    root / "source.wav",
                    root / "anchor.wav",
                    root / "beltout-src",
                    root / "checkpoints",
                    output,
                    seed=123,
                )

    def test_cli_and_runtime_installer_are_pinned(self):
        root = Path(__file__).resolve().parents[1]
        cli = (root / "src/audio_engine/cli.py").read_text(encoding="utf-8")
        installer = (
            root / "scripts/install_beltout_production_runtime.sh"
        ).read_text(encoding="utf-8")
        self.assertIn('sub.add_parser("beltout"', cli)
        self.assertIn("--n-timesteps", cli)
        self.assertIn("--gain-clamp-db", cli)
        for marker in (
            "torch==2.6.0",
            "torchaudio==2.6.0",
            "numpy==1.26.4",
            "librosa==0.11.0",
            "s3tokenizer==0.3.0",
            "torchcrepe==0.0.24",
            "transformers==4.46.3",
            "diffusers==0.29.0",
            "conformer==0.3.2",
            "safetensors==0.5.3",
            "huggingface_hub==0.33.1",
            "scipy==1.15.3",
            "tqdm==4.67.1",
            "soundfile==0.13.1",
            "BELTOUT_PRODUCTION_RUNTIME_READY",
        ):
            self.assertIn(marker, installer)


if __name__ == "__main__":
    unittest.main()
