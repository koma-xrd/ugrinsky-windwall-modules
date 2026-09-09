"""Electrical manual figures must encode the experimental safety workflow."""

import unittest
import os
from pathlib import Path
import re
from unittest.mock import patch

from PIL import Image

from scripts.manual import electrical_figures
from scripts.manual.electrical_figures import (
    build_test_matrix,
    estimate_final_turns,
    magnet_polarities,
    render_electrical_figures,
)
from scripts.manual.manual_data import load_manual_data
from tests.support import temporary_build_directory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MPL_CACHE = PROJECT_ROOT / 'build' / 'matplotlib'
MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR', str(MPL_CACHE))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


class ManualElectricalFigureTests(unittest.TestCase):
    def _draw_without_saving(self, drawing_id):
        data = load_manual_data(PROJECT_ROOT)
        drawing = data['drawings'][drawing_id]
        with patch.object(electrical_figures, '_finish_sheet'):
            electrical_figures._RENDERERS[drawing_id](
                Path('unused.png'), drawing_id, drawing, data
            )
        return plt.gcf(), data, drawing

    @staticmethod
    def _wire_edges(figure):
        edges = set()
        for line in figure.axes[0].lines:
            points = [
                (round(float(x), 2), round(float(y), 2))
                for x, y in zip(line.get_xdata(), line.get_ydata())
            ]
            edges.update(zip(points, points[1:]))
        return edges

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

    def test_e07_visible_identifiers_match_authoritative_drawing_items(self):
        figure, _data, drawing = self._draw_without_saving('E07')
        try:
            visible_ids = {
                item_id
                for text in figure.findobj(match=plt.Text)
                for item_id in re.findall(r'\b[PH]\d{2}\b', text.get_text())
            }
        finally:
            plt.close(figure)

        self.assertEqual(visible_ids, set(drawing['items']))

    def test_e10_explicitly_labels_series_current_and_parallel_voltage_measurement(self):
        figure, _data, _drawing = self._draw_without_saving('E10')
        try:
            rendered_text = '\n'.join(
                text.get_text() for text in figure.findobj(match=plt.Text)
            )
            wire_vertices = {
                (round(float(x), 2), round(float(y), 2))
                for line in figure.axes[0].lines
                for x, y in zip(line.get_xdata(), line.get_ydata())
            }
        finally:
            plt.close(figure)

        for label in (
            'A~ IN REIHE',
            'V~ PARALLEL ZU RTEST',
            'A DC IN REIHE',
            'V DC PARALLEL ZU RTEST',
        ):
            with self.subTest(label=label):
                self.assertIn(label, rendered_text)
        self.assertGreaterEqual(rendered_text.count('RTEST = ____ Ω'), 2)
        self.assertIn((3.12, 4.55), wire_vertices)
        self.assertIn((3.12, 1.60), wire_vertices)

    def test_e10_bridge_rectifier_has_four_terminal_topology(self):
        figure, _data, _drawing = self._draw_without_saving('E10')
        try:
            rendered_text = '\n'.join(
                text.get_text() for text in figure.findobj(match=plt.Text)
            )
            wire_edges = self._wire_edges(figure)
        finally:
            plt.close(figure)

        for terminal in ('AC~1', 'AC~2', 'DC +', 'DC -'):
            with self.subTest(terminal=terminal):
                self.assertIn(terminal, rendered_text)
        for edge in (
            ((3.98, 2.45), (4.18, 2.45)),
            ((3.12, 1.60), (4.18, 1.60)),
            ((5.43, 2.45), (5.58, 2.45)),
            ((5.43, 0.82), (5.43, 1.60)),
        ):
            with self.subTest(edge=edge):
                self.assertIn(edge, wire_edges)

    def test_e10_comparison_panel_has_blank_dc_voltage_and_current_fields(self):
        figure, _data, _drawing = self._draw_without_saving('E10')
        try:
            rendered_text = '\n'.join(
                text.get_text() for text in figure.findobj(match=plt.Text)
            )
        finally:
            plt.close(figure)

        self.assertIn('V DC ____ V', rendered_text)
        self.assertIn('I DC ____ A', rendered_text)

    def test_e08_direction_arrow_uses_one_adjacent_path_segment(self):
        data = load_manual_data(PROJECT_ROOT)
        drawing = data['drawings']['E08']
        captured_arrows = []

        def capture_arrow(_ax, start, end, **style):
            captured_arrows.append((start, end, style))

        with (
            patch.object(electrical_figures, '_finish_sheet'),
            patch.object(electrical_figures, '_arrow', side_effect=capture_arrow),
        ):
            electrical_figures._render_e08(
                Path('unused.png'), 'E08', drawing, data
            )
        figure = plt.gcf()
        plt.close(figure)

        points, _legs = electrical_figures._serpentine_geometry(18, 1.35, 2.65)
        shifted = [(6.0 + x, 4.05 + y) for x, y in points]
        adjacent_segments = set(zip(shifted, shifted[1:]))
        copper_arrows = [
            (start, end) for start, end, style in captured_arrows
            if style.get('color') == electrical_figures._COPPER
        ]

        self.assertEqual(len(copper_arrows), 1)
        self.assertIn(copper_arrows[0], adjacent_segments)

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
