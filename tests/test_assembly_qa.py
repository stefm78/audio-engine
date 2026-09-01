import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_engine.assemble import assemble_plan
from audio_engine.qa import qa_render


class AssemblyProvenanceQATests(unittest.TestCase):
    def test_assembly_manifest_hashes_inputs_and_qa_accepts_complete_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "scene.mp3"
            source.write_bytes(b"scene-audio")
            plan = root / "block.json"
            plan.write_text(json.dumps({
                "schema_version": 1,
                "id": "block-a",
                "inputs": [{"file": "scene.mp3", "pause_after_ms": 0}],
            }), encoding="utf-8")

            def fake_concat(parts, output_path, profile):
                Path(output_path).write_bytes(b"assembled-audio")

            with (
                patch("audio_engine.assemble.probe_duration_seconds", return_value=1.25),
                patch("audio_engine.assemble.encode_concat", side_effect=fake_concat),
            ):
                manifest = assemble_plan(plan, root / "out")

            render_dir = root / "out" / "block-a"
            self.assertEqual(manifest["assembly"]["input_count"], 1)
            self.assertEqual(len(manifest["assembly"]["inputs"][0]["sha256"]), 64)
            self.assertEqual(len(manifest["engine_code_sha256"]), 64)
            self.assertEqual(len(manifest["render_fingerprint"]), 64)

            with (
                patch("audio_engine.qa.probe_duration_seconds", return_value=1.25),
                patch(
                    "audio_engine.qa._loudness_metrics",
                    return_value={
                        "integrated_lufs": -16.0,
                        "true_peak_dbtp": -2.5,
                        "lra_lu": 4.0,
                        "threshold_lufs": -26.0,
                    },
                ),
                patch(
                    "audio_engine.qa._silence_metrics",
                    return_value={
                        "threshold_db": -45,
                        "minimum_event_seconds": 0.8,
                        "interval_count": 0,
                        "total_seconds": 0.0,
                        "longest_seconds": 0.0,
                        "ratio": 0.0,
                        "intervals": [],
                    },
                ),
            ):
                report = qa_render(render_dir)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["kind"], "assembly")
            self.assertIn("assembly_inputs", [check["id"] for check in report["checks"]])


if __name__ == "__main__":
    unittest.main()
