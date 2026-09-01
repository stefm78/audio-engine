import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_engine.qa import _timeline_checks, qa_render


class QATests(unittest.TestCase):
    def test_timeline_gap_coherence(self):
        manifest = {
            "program_schema_version": 6,
            "mix": {
                "timeline": {
                    "1": {"start_ms": 250, "end_ms": 750, "pause_after_ms": 350},
                    "2": {"start_ms": 1100, "end_ms": 1600, "pause_after_ms": 400},
                }
            },
        }
        transcript = {"segments": [{}, {}]}
        result = _timeline_checks(manifest, transcript, 2.0)
        self.assertTrue(result["valid"])
        self.assertEqual(result["gaps"][0]["delta_ms"], 0.0)

    def test_structural_qa_passes_with_mocked_audio_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "audio.mp3").write_bytes(b"not-real-audio")
            transcript = {
                "segments": [
                    {
                        "sequence": 1,
                        "speaker": "Narrator",
                        "character_id": "narrator",
                    }
                ]
            }
            (root / "transcript.json").write_text(json.dumps(transcript), encoding="utf-8")
            manifest = {
                "status": "success",
                "id": "sample",
                "program_schema_version": 6,
                "profile": "speech",
                "audio": {"file": "audio.mp3", "duration_seconds": 1.1, "channels": 1},
                "transcript": "transcript.json",
                "source_sha256": "a" * 64,
                "voice_config_sha256": "b" * 64,
                "engine_code_sha256": "c" * 64,
                "render_fingerprint": "d" * 64,
                "engine_version": "1.0.0",
                "provider": {"name": "edge"},
                "mix": {
                    "voice_clip_count": 1,
                    "voice_fingerprints": ["e" * 64],
                    "timeline": {
                        "1": {"start_ms": 250, "end_ms": 750, "pause_after_ms": 350}
                    },
                },
            }
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with (
                patch("audio_engine.qa.probe_duration_seconds", return_value=1.1),
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
                report = qa_render(root)
            self.assertEqual(report["status"], "PASS")
            self.assertTrue((root / "qa-report.json").is_file())

    def test_missing_audio_fails_and_still_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest.json").write_text(
                json.dumps({
                    "status": "success",
                    "id": "sample",
                    "audio": {"file": "audio.mp3"},
                    "transcript": "transcript.json",
                }),
                encoding="utf-8",
            )
            report = qa_render(root)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("files", report["failed_checks"] if "failed_checks" in report else [c["id"] for c in report["checks"] if c["status"] == "FAIL"])


if __name__ == "__main__":
    unittest.main()
