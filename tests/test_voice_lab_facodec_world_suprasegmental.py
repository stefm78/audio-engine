from __future__ import annotations

import inspect
import unittest

import numpy as np

from audio_engine.voice_lab_facodec_world_suprasegmental import (
    transfer_suprasegmental_world_parameters,
)


class SuprasegmentalWorldTests(unittest.TestCase):
    def test_preserves_target_voicing_mask_and_target_f0_center(self):
        source_f0 = np.array([100.0, 0.0, 200.0, 0.0, 120.0])
        target_f0 = np.array([0.0, 180.0, 200.0, 0.0, 220.0])
        source_sp = np.ones((5, 4))
        target_sp = np.ones((5, 4)) * 2.0
        source_ap = np.full((5, 4), 0.15)
        target_ap = np.full((5, 4), 0.85)

        out_f0, _, _ = transfer_suprasegmental_world_parameters(
            source_f0, source_sp, source_ap, target_f0, target_sp, target_ap
        )

        np.testing.assert_array_equal(out_f0 > 0.0, target_f0 > 0.0)
        self.assertAlmostEqual(
            float(np.median(out_f0[out_f0 > 0.0])),
            float(np.median(target_f0[target_f0 > 0.0])),
            places=10,
        )

    def test_preserves_target_aperiodicity_exactly(self):
        source_f0 = np.array([100.0, 120.0, 140.0])
        target_f0 = np.array([200.0, 0.0, 240.0])
        source_sp = np.ones((3, 3))
        target_sp = np.ones((3, 3)) * 3.0
        source_ap = np.array(
            [[0.01, 0.02, 0.03], [0.04, 0.05, 0.06], [0.07, 0.08, 0.09]]
        )
        target_ap = np.array(
            [[0.91, 0.82, 0.73], [0.64, 0.55, 0.46], [0.37, 0.28, 0.19]]
        )

        _, _, out_ap = transfer_suprasegmental_world_parameters(
            source_f0, source_sp, source_ap, target_f0, target_sp, target_ap
        )
        np.testing.assert_array_equal(out_ap, target_ap)

    def test_preserves_target_spectral_shape_per_frame(self):
        source_f0 = np.array([100.0, 110.0, 120.0])
        target_f0 = np.array([200.0, 210.0, 220.0])
        source_sp = np.array(
            [[1.0, 1.0, 1.0], [4.0, 4.0, 4.0], [0.25, 0.25, 0.25]]
        )
        target_sp = np.array(
            [[2.0, 6.0, 10.0], [3.0, 9.0, 15.0], [4.0, 12.0, 20.0]]
        )
        source_ap = np.full((3, 3), 0.2)
        target_ap = np.full((3, 3), 0.8)

        _, out_sp, _ = transfer_suprasegmental_world_parameters(
            source_f0, source_sp, source_ap, target_f0, target_sp, target_ap
        )

        for frame in range(3):
            np.testing.assert_allclose(
                out_sp[frame] / out_sp[frame, 0],
                target_sp[frame] / target_sp[frame, 0],
                rtol=1e-12,
                atol=1e-12,
            )

    def test_target_median_spectral_amplitude_is_retained(self):
        source_f0 = np.array([100.0, 120.0, 140.0, 160.0])
        target_f0 = np.array([180.0, 200.0, 220.0, 240.0])
        source_sp = np.array(
            [[1.0, 1.0], [4.0, 4.0], [0.25, 0.25], [2.0, 2.0]]
        )
        target_sp = np.array(
            [[2.0, 8.0], [3.0, 12.0], [5.0, 20.0], [7.0, 28.0]]
        )
        ap = np.full((4, 2), 0.5)

        _, out_sp, _ = transfer_suprasegmental_world_parameters(
            source_f0, source_sp, ap, target_f0, target_sp, ap
        )

        target_log_amp = 0.5 * np.log(np.mean(target_sp, axis=1))
        output_log_amp = 0.5 * np.log(np.mean(out_sp, axis=1))
        self.assertAlmostEqual(
            float(np.median(output_log_amp)),
            float(np.median(target_log_amp)),
            places=10,
        )

    def test_public_transfer_has_no_blend_or_strength_parameter(self):
        names = tuple(inspect.signature(transfer_suprasegmental_world_parameters).parameters)
        self.assertEqual(
            names,
            (
                "source_f0",
                "source_sp",
                "source_ap",
                "target_f0",
                "target_sp",
                "target_ap",
            ),
        )
        self.assertFalse(any("blend" in name or "strength" in name for name in names))


if __name__ == "__main__":
    unittest.main()
