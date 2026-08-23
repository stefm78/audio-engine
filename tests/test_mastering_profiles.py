import unittest

from audio_engine.profiles import LOSSY_TRUE_PEAK_DB, get_profile


class MasteringProfileTests(unittest.TestCase):
    def test_mp3_profiles_reserve_encoder_true_peak_headroom(self):
        self.assertEqual(LOSSY_TRUE_PEAK_DB, -2.5)
        for name in ("speech", "speech-high"):
            profile = get_profile(name, stereo=True)
            self.assertEqual(profile["codec"], "libmp3lame")
            self.assertEqual(profile["container"], "mp3")
            self.assertLessEqual(profile["true_peak_db"], -2.5)


if __name__ == "__main__":
    unittest.main()
