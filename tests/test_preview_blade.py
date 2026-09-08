"""Deterministic checks for external-reference measurement, never STL booleans."""

import unittest
import numpy as np

from scripts.preview_blade import fit_circle, join_segments, slice_triangles


class MeasurementTests(unittest.TestCase):
    def test_slice_interpolates_triangle_edges(self):
        triangles = np.array([[[0, 0, 0], [2, 0, 2], [0, 2, 2]]])
        np.testing.assert_allclose(slice_triangles(triangles, 1), [[[1, 0], [0, 1]]])

    def test_join_accepts_small_gaps_and_closes_loop(self):
        segments = np.array([[[1, 0], [1, 1]], [[0, 0], [1.01, 0]],
                             [[1, 1.01], [0, 0.01]]])
        loops = join_segments(segments)
        self.assertEqual(len(loops), 1)
        np.testing.assert_allclose(loops[0][0], loops[0][-1])

    def test_join_rejects_open_section(self):
        with self.assertRaises(ValueError):
            join_segments(np.array([[[0, 0], [1, 0]]]))

    def test_circle_fit_recovers_known_arc(self):
        angle = np.linspace(0, 1.8, 40)
        points = np.column_stack((3 + 5 * np.cos(angle), -2 + 5 * np.sin(angle)))
        fit = fit_circle(points)
        np.testing.assert_allclose(fit["center_mm"], [3, -2], atol=1e-9)
        self.assertAlmostEqual(fit["radius_mm"], 5)
        self.assertLess(fit["rms_mm"], 1e-9)

    def test_circle_fit_rejects_non_circular_samples(self):
        angle = np.linspace(0, 2 * np.pi, 50)
        points = np.column_stack((5 * np.cos(angle), 9 * np.sin(angle)))
        with self.assertRaises(ValueError):
            fit_circle(points)


if __name__ == "__main__":
    unittest.main()
