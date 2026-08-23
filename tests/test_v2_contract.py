import os
import tempfile
import unittest
from pathlib import Path

from audio_engine.ambience.prepare import resolve_ambience_source
from audio_engine.contract import ContractError, validate_program


class V2ContractTests(unittest.TestCase):
    def test_rejects_remote_and_absolute_ambience(self):
        for file_value in ("https://example.test/room.wav", "/tmp/room.wav"):
            with self.subTest(file=file_value):
                with self.assertRaises(ContractError):
                    validate_program({
                        "schema_version": 2,
                        "id": "bad-ambience",
                        "title": "Bad ambience",
                        "ambience": {"file": file_value},
                        "segments": [{"voice": "test", "text": "Hello"}],
                    })

    def test_numeric_pan_is_not_public_contract(self):
        with self.assertRaises(ContractError):
            validate_program({
                "schema_version": 2,
                "id": "bad-pan",
                "title": "Bad pan",
                "segments": [{
                    "voice": "test",
                    "text": "Hello",
                    "pan": -0.4,
                }],
            })

    def test_ambience_cannot_escape_workspace(self):
        with tempfile.TemporaryDirectory() as temp_value:
            temp = Path(temp_value)
            workspace = temp / "workspace"
            program_dir = workspace / "series" / "demo" / "audio"
            program_dir.mkdir(parents=True)
            program = program_dir / "episode.json"
            program.write_text("{}", encoding="utf-8")
            outside = temp / "outside.wav"
            outside.write_bytes(b"not-a-real-wave")

            previous = Path.cwd()
            os.chdir(workspace)
            try:
                with self.assertRaises(ValueError):
                    resolve_ambience_source(program, "../../../../outside.wav")
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
