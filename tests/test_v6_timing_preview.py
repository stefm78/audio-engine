import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.audio import probe_duration_seconds, run_ffmpeg
from audio_engine.contract import ContractError, validate_program
from audio_engine.preview import preview_program
from audio_engine.render import render_program
from audio_engine.timing import timing_report


class FakeProvider:
    name = "fake-v6"
    processing = "local-test"

    def __init__(self):
        self.calls = 0

    def synthesize(self, segment, path):
        self.calls += 1
        duration = 1.2 if segment["sequence"] == 1 else 1.0
        run_ffmpeg([
            "-f", "lavfi",
            "-i", f"sine=frequency=440:sample_rate=24000:duration={duration}",
            "-ac", "1",
            "-c:a", "libmp3lame",
            "-b:a", "64k",
            str(path),
        ])


def make_event(path, duration=8.0):
    run_ffmpeg([
        "-f", "lavfi",
        "-i", f"sine=frequency=660:sample_rate=24000:duration={duration}",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(path),
    ])


def relative_program():
    return {
        "schema_version": 6,
        "id": "relative-bridge",
        "title": "Relative bridge",
        "profile": "speech",
        "lead_in_ms": 100,
        "soundscape": {
            "events": [{
                "file": "event.wav",
                "role": "bridge",
                "after_segment": 1,
                "foreground_ms": 1000,
                "carry_through_segments": 1,
                "tail_ms": 600,
                "gain_db": -20,
            }],
            "ducking": "speech",
        },
        "segments": [
            {"voice": "voice-a", "text": "First segment.", "pause_after_ms": 100},
            {"voice": "voice-a", "text": "Second measured segment.", "pause_after_ms": 800},
        ],
    }


class V6TimingPreviewTests(unittest.TestCase):
    def test_v5_rejects_relative_bridge_fields_and_v6_requires_one_carry_mode(self):
        data = relative_program()
        data["schema_version"] = 5
        with self.assertRaises(ContractError):
            validate_program(data)

        data = relative_program()
        data["soundscape"]["events"][0]["carry_under_speech_ms"] = 900
        with self.assertRaises(ContractError):
            validate_program(data)

    def test_relative_bridge_uses_measured_next_segment_duration(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            make_event(root / "event.wav")
            program_path = root / "program.json"
            program_path.write_text(json.dumps(relative_program()), encoding="utf-8")
            provider = FakeProvider()
            out = root / "out"

            manifest = render_program(program_path, out, provider=provider)
            self.assertEqual(provider.calls, 2)
            resolution = manifest["mix"]["resolved_sound_intent"][0]
            timeline = manifest["mix"]["timeline"]
            expected = timeline[2]["end_ms"] + 600 - timeline[2]["start_ms"]
            self.assertAlmostEqual(resolution["resolved_carry_under_speech_ms"], expected, delta=3)
            self.assertEqual(resolution["carry_mode"], "through-segments")

            component = manifest["mix"]["soundscape"]["components"][0]
            self.assertAlmostEqual(
                component["requested_play_duration_ms"],
                1000 + expected,
                delta=3,
            )
            self.assertFalse(component["duration_clipped"])

    def test_voice_timing_sidecar_and_preview_are_reusable(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            make_event(root / "event.wav")
            program_path = root / "program.json"
            program_path.write_text(json.dumps(relative_program()), encoding="utf-8")
            out = root / "out"
            provider = FakeProvider()

            render_program(program_path, out, provider=provider)
            sidecars = list((out / ".cache" / "voices").glob("*.json"))
            self.assertEqual(len(sidecars), 2)
            for sidecar in sidecars:
                data = json.loads(sidecar.read_text(encoding="utf-8"))
                self.assertGreater(data["measured_duration_ms"], 0)

            timing = timing_report(program_path, out, provider=provider)
            self.assertEqual(timing["exact_segments"], 2)
            self.assertEqual(timing["estimated_segments"], 0)

            result = preview_program(
                program_path,
                out,
                event=1,
                before_ms=300,
                after_ms=300,
                provider=provider,
            )
            self.assertEqual(provider.calls, 2)
            preview_path = Path(result["previews"][0]["file"])
            self.assertTrue(preview_path.exists())
            self.assertGreater(probe_duration_seconds(preview_path), 1.0)


if __name__ == "__main__":
    unittest.main()
