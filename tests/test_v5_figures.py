"""The drawing handoff must describe actual, legible V5 CAD scenes."""

import importlib.util
import hashlib
import json
from pathlib import Path
import unittest

from PIL import Image

from tests.support import temporary_build_directory


class V5FigureTests(unittest.TestCase):
    def test_tracked_51105_drawing_uses_the_two_release_coupon_parts(self):
        root = Path(__file__).resolve().parents[1]
        inventory = json.loads((root / 'release/v5/drawings/figures.json').read_text(encoding='utf-8'))
        record = next(item for item in inventory['figures'] if item['drawing_id'] == 'E11')
        self.assertEqual({part['name'] for part in record['parts']},
                         {'51105_outer_seat_coupon', '25mm_pilot_coupon'})

    def test_renderer_exists(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.manual.v5_figures'))

    def test_rendered_inventory_and_installed_generator_order(self):
        from scripts.manual.v5_figures import render_v5_figures

        with temporary_build_directory() as output:
            records = render_v5_figures(output)
            self.assertEqual([r.drawing_id for r in records], [f'E{i:02d}' for i in range(1, 16)])
            self.assertEqual(len(list(output.glob('*.png'))), 15)
            exported = json.loads((output / 'figures.json').read_text(encoding='utf-8'))
            self.assertEqual(len(exported['figures']), 15)
            for record in records:
                tracked = Path(__file__).resolve().parents[1] / 'release/v5/drawings' / record.filename
                self.assertEqual(hashlib.sha256(record.path.read_bytes()).hexdigest(),
                                 hashlib.sha256(tracked.read_bytes()).hexdigest(),
                                 f'{record.drawing_id} must reproduce the tracked release image')
                with Image.open(record.path) as picture:
                    self.assertEqual(picture.size, (record.pixel_width, record.pixel_height))
                    self.assertGreaterEqual(picture.width, 2400)
                    self.assertGreaterEqual(picture.height, 1680)
                    self.assertEqual(picture.info['Description'], record.alt_text)
                self.assertEqual(record.filename, record.path.name)
                self.assertTrue(record.caption and record.alt_text and record.callout_labels)
                self.assertEqual(record.language, 'de')
                self.assertTrue(any('ROTIEREND' in label for label in record.rotation_state_legend))
                self.assertTrue(any('STATIONÄR' in label for label in record.rotation_state_legend))
                self.assertTrue(record.parts)
                self.assertTrue(all(part.source_builder for part in record.parts))
                self.assertNotIn('top_closure', {part.name for part in record.parts})
                self.assertNotIn('Top-Closure', record.caption + record.alt_text + ' '.join(record.callout_labels))
            for drawing_id in ('E06', 'E07'):
                record = next(r for r in records if r.drawing_id == drawing_id)
                parts = {part.name: part for part in record.parts}
                self.assertLess(parts['lower_magnet_rotor'].display_bounds_mm[1][2],
                                parts['winding_volume'].display_bounds_mm[0][2])
                self.assertLess(parts['housing'].display_bounds_mm[0][2],
                                parts['lower_magnet_rotor'].display_bounds_mm[0][2])
                self.assertGreater(parts['housing'].display_bounds_mm[1][2],
                                   parts['lower_magnet_rotor'].display_bounds_mm[1][2])
                for name in ('housing', 'coil_cassette', 'cover', 'winding_volume'):
                    self.assertEqual(parts[name].motion, 'stationary')
                self.assertEqual(parts['lower_magnet_rotor'].motion, 'rotating')
            upper = next(r for r in records if r.drawing_id == 'E13')
            self.assertTrue(any('von unten' in label for label in upper.callout_labels))
            self.assertTrue(any(part.name == 'upper_wood_frame_reference' for part in upper.parts))


if __name__ == '__main__':
    unittest.main()
