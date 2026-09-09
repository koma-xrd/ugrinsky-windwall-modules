"""Electrical manual figures must encode the experimental safety workflow."""

import unittest
from pathlib import Path

from PIL import Image

from scripts.manual.electrical_figures import (
    build_test_matrix,
    estimate_final_turns,
    magnet_polarities,
    render_electrical_figures,
)
from scripts.manual.manual_data import load_manual_data
from tests.support import temporary_build_directory


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ManualElectricalFigureTests(unittest.TestCase):
    def test_polarity_alternates_and_opposed_faces_attract(self):
        top, bottom = magnet_polarities(18)

        self.assertTrue(all(top[i] != top[(i + 1) % 18] for i in range(18)))
        self.assertTrue(all(top[i] != bottom[i] for i in range(18)))

    def test_polarity_rejects_counts_that_cannot_close_the_alternating_ring(self):
        for invalid_count in (0, -2, 17):
            with self.subTest(count=invalid_count), self.assertRaises(ValueError):
                magnet_polarities(invalid_count)

    def test_turn_estimate_rounds_up_and_rejects_missing_measurement(self):
        self.assertEqual(estimate_final_turns(20, 8.0, 60.0), 150)
        with self.assertRaises(ValueError):
            estimate_final_turns(20, 0.0, 60.0)

    def test_turn_estimate_rejects_nonpositive_inputs(self):
        for arguments in ((0, 8.0, 60.0), (20, -1.0, 60.0), (20, 8.0, 0.0)):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                estimate_final_turns(*arguments)

    def test_matrix_uses_measured_wire_diameters_and_three_turn_counts(self):
        self.assertEqual(build_test_matrix([0.18, 0.31]), [
            (0.18, 20), (0.18, 40), (0.18, 80),
            (0.31, 20), (0.31, 40), (0.31, 80),
        ])

    def test_matrix_rejects_empty_or_nonpositive_measured_diameters(self):
        for diameters in ([], [0.0], [-0.18], [0.18, 0.0]):
            with self.subTest(diameters=diameters), self.assertRaises(ValueError):
                build_test_matrix(diameters)

    def test_electrical_figures_match_manual_data_and_print_resolution(self):
        data = load_manual_data(PROJECT_ROOT)
        with temporary_build_directory() as destination:
            records = render_electrical_figures(PROJECT_ROOT, destination)

            self.assertEqual(
                [record.drawing_id for record in records],
                ['E07', 'E08', 'E09', 'E10', 'E11'],
            )
            for record in records:
                with self.subTest(drawing_id=record.drawing_id):
                    drawing = data['drawings'][record.drawing_id]
                    self.assertEqual(record.callouts, tuple(drawing['items']))
                    self.assertEqual(record.path.name, Path(drawing['figure_file']).name)
                    self.assertGreater(record.path.stat().st_size, 50_000)
                    with Image.open(record.path) as image:
                        self.assertGreaterEqual(max(image.size), 2200)


if __name__ == '__main__':
    unittest.main()
