import inspect
import unittest

from audio_engine.providers.chatterbox_mtl_v3 import ChatterboxMultilingualV3Provider


class ChatterboxRuntimeDependencyTests(unittest.TestCase):
    def test_synthesis_does_not_depend_on_pydub_or_ffprobe(self):
        source = inspect.getsource(ChatterboxMultilingualV3Provider.synthesize)
        self.assertNotIn("pydub", source)
        self.assertNotIn("ffprobe", source)

    def test_h1b_gain_is_bounded_in_adapter(self):
        source = inspect.getsource(ChatterboxMultilingualV3Provider.synthesize)
        self.assertIn("max(-8.0, min(8.0", source)
        self.assertIn("target_dbfs - current_dbfs", source)


if __name__ == "__main__":
    unittest.main()
