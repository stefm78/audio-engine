import subprocess
import sys
import unittest


class CliLabIsolationTests(unittest.TestCase):
    def test_importing_production_cli_does_not_import_voice_lab(self):
        probe = (
            "import sys; "
            "import audio_engine.cli; "
            "assert 'audio_engine.voice_lab' not in sys.modules, "
            "'Production CLI imported audio_engine.voice_lab eagerly'"
        )
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
