import unittest

from audio_engine.contract import ContractError, validate_program


def base_program():
    return {
        "schema_version": 3,
        "id": "soundscape",
        "title": "Soundscape",
        "soundscape": {
            "bed": {"file": "bed.wav"},
            "layers": [
                {"file": "wind.wav", "gain_db": -30},
                {"sound": "crowd-distant", "gain_db": -32},
            ],
            "events": [
                {"sound": "church-bell", "at_ms": 1200, "placement": "right"}
            ],
        },
        "segments": [{"voice": "test", "text": "Hello"}],
    }


class V3SoundscapeContractTests(unittest.TestCase):
    def test_accepts_bounded_soundscape(self):
        self.assertEqual(validate_program(base_program())["schema_version"], 3)

    def test_v2_rejects_soundscape(self):
        data = base_program()
        data["schema_version"] = 2
        with self.assertRaises(ContractError):
            validate_program(data)

    def test_rejects_more_than_two_layers(self):
        data = base_program()
        data["soundscape"]["layers"].append({"file": "rain.wav"})
        with self.assertRaises(ContractError):
            validate_program(data)

    def test_rejects_more_than_sixteen_events(self):
        data = base_program()
        data["soundscape"]["events"] = [
            {"file": "bell.wav", "at_ms": index * 100}
            for index in range(17)
        ]
        with self.assertRaises(ContractError):
            validate_program(data)

    def test_requires_exactly_one_sound_or_file(self):
        for item in (
            {"sound": "bell", "file": "bell.wav", "at_ms": 10},
            {"at_ms": 10},
        ):
            data = base_program()
            data["soundscape"]["events"] = [item]
            with self.subTest(item=item):
                with self.assertRaises(ContractError):
                    validate_program(data)

    def test_event_requires_non_negative_timestamp(self):
        for value in (None, -1):
            data = base_program()
            data["soundscape"]["events"] = [{"file": "bell.wav", "at_ms": value}]
            with self.subTest(value=value):
                with self.assertRaises(ContractError):
                    validate_program(data)

    def test_rejects_remote_or_absolute_files(self):
        for value in ("https://example.test/bed.wav", "/tmp/bed.wav"):
            data = base_program()
            data["soundscape"] = {"bed": {"file": value}}
            with self.subTest(value=value):
                with self.assertRaises(ContractError):
                    validate_program(data)

    def test_rejects_legacy_ambience_and_soundscape_together(self):
        data = base_program()
        data["ambience"] = {"file": "legacy.wav"}
        with self.assertRaises(ContractError):
            validate_program(data)


if __name__ == "__main__":
    unittest.main()
