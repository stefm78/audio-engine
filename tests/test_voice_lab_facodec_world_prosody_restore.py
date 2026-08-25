from __future__ import annotations

import unittest

import numpy as np

from audio_engine.voice_lab_facodec_world_prosody_restore import transfer_world_parameters


class WorldProsodyRestoreTests(unittest.TestCase):
    def test_keeps_target_f0_center_and_source_relative_motion(self):
        source_f0 = np.array([0.0, 100.0, 200.0, 0.0])
        target_f0 = np.array([0.0, 200.0, 200.0, 0.0])
        source_sp = np.ones((4, 3))
        target_sp = np.ones((4, 3)) * 4.0
        ap = np.ones((4, 3)) * 0.2
        out_f0, _, _ = transfer_world_parameters(
            source_f0, source_sp, ap, target_f0, target_sp, ap
        )
        self.assertEqual(out_f0[0], 0.0)
        self.assertEqual(out_f0[-1], 0.0)
        self.assertAlmostEqual(float(np.median(out_f0[out_f0 > 0.0])), 200.0)
        self.assertAlmostEqual(out_f0[2] / out_f0[1], 2.0)

    def test_preserves_target_spectral_shape_up_to_frame_gain(self):
        source_f0 = np.array([100.0, 110.0, 120.0])
        target_f0 = np.array([200.0, 210.0, 220.0])
        source_sp = np.array([[1.0, 2.0, 4.0], [4.0, 8.0, 16.0], [1.0, 2.0, 4.0]])
        target_sp = np.array([[2.0, 6.0, 10.0], [3.0, 9.0, 15.0], [4.0, 12.0, 20.0]])
        source_ap = np.full((3, 3), 0.3)
        target_ap = np.full((3, 3), 0.8)
        _, out_sp, _ = transfer_world_parameters(
            source_f0, source_sp, source_ap, target_f0, target_sp, target_ap
        )
        for frame in range(3):
            np.testing.assert_allclose(
                out_sp[frame] / out_sp[frame, 0],
                target_sp[frame] / target_sp[frame, 0],
            )

    def test_transfers_source_aperiodicity_without_blend_parameter(self):
        f0 = np.array([100.0, 100.0])
        sp = np.ones((2, 2))
        source_ap = np.array([[0.1, 0.2], [0.3, 0.4]])
        target_ap = np.full((2, 2), 0.9)
        _, _, out_ap = transfer_world_parameters(
            f0, sp, source_ap, f0 * 2.0, sp * 2.0, target_ap
        )
        np.testing.assert_allclose(out_ap, source_ap)


if __name__ == "__main__":
    unittest.main()
