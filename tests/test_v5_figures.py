"""The drawing handoff must describe actual, legible V5 CAD scenes."""

import importlib.util
import hashlib
import json
from pathlib import Path
import unittest

from PIL import Image

from tests.support import temporary_build_directory


class V5FigureTests(unittest.TestCase):
    def test_feature_anchors_and_complete_frame_installation(self):
        from scripts.manual.v5_figures import build_v5_scenes

        scenes, _ = build_v5_scenes()
        scenes = {scene.drawing_id: scene for scene in scenes}
        for drawing_id in ('E08', 'E09'):
            panel = scenes[drawing_id].panels[0]
            callout = next(c for c in panel.callouts if c.name == 'housing')
            with self.subTest(drawing=drawing_id):
                self.assertIsNotNone(callout.target, 'Feature labels need explicit CAD anchors')
                if callout.target is None:
                    continue
                x, y, z = callout.target
                floor = next(p.record.source_bounds_mm[0][2] for p in panel.parts
                             if p.record.name == 'housing')
                if drawing_id == 'E08':
                    self.assertAlmostEqual(z-floor, 27, places=5)
                    self.assertLess(x, -58)
                    self.assertAlmostEqual(y, 0)
                else:
                    self.assertAlmostEqual((x*x+y*y)**.5, 69, places=5)
                    self.assertAlmostEqual(z-floor, 3.4, places=5)
        outlet = next(c for c in scenes['E10'].panels[0].callouts
                      if c.name == 'coil_cassette')
        with self.subTest(drawing='E10'):
            self.assertGreaterEqual(sum(v*v for v in outlet.marker_offset_mm)**.5, 12,
                                    'A short leader must leave the six-mm opening visible')

        for drawing_id in ('E14', 'E15'):
            panel = scenes[drawing_id].panels[0]
            parts = {part.record.name: part.record for part in panel.parts}
            with self.subTest(drawing=drawing_id):
                self.assertIn('lower_wood_frame_reference', parts)
                for name in ('lower_wood_frame_reference', 'upper_wood_frame_reference'):
                    reference = parts[name]
                    self.assertIs(reference.printable, False)
                    self.assertTrue(reference.reference_note)
                    self.assertEqual(reference.motion, 'stationary')
                    self.assertGreaterEqual(reference.display_bounds_mm[1][0]
                                            - reference.display_bounds_mm[0][0], 240)
                self.assertAlmostEqual(parts['lower_wood_frame_reference'].display_bounds_mm[1][2],
                                       parts['housing'].source_bounds_mm[0][2], places=5)
                self.assertAlmostEqual(parts['upper_wood_frame_reference'].display_bounds_mm[0][2],
                                       parts['top_support'].source_bounds_mm[1][2], places=5)
                for i in range(1, 5):
                    lower = parts[f'lower_wood_screw_{i}_reference']
                    upper = parts[f'wood_screw_{i}_reference']
                    self.assertIs(lower.printable, False)
                    self.assertTrue(lower.reference_note)
                    self.assertEqual(lower.installation_direction, (0, 0, -1))
                    self.assertEqual(upper.installation_direction, (0, 0, 1))
                    minimum, maximum = lower.source_bounds_mm
                    axis = tuple(round((minimum[j]+maximum[j])/2, 5) for j in (0, 1))
                    self.assertEqual(axis, ((83, 0), (0, 83), (-83, 0), (0, -83))[i-1])
                    floor = parts['housing'].source_bounds_mm[0][2]
                    self.assertAlmostEqual(maximum[2]-floor, 8, places=5)
                    self.assertAlmostEqual(floor-minimum[2], 22, places=5)
                self.assertTrue(any('von oben' in c.label for p in scenes[drawing_id].panels
                                    for c in p.callouts))
                self.assertTrue(any('von unten' in c.label for p in scenes[drawing_id].panels
                                    for c in p.callouts))

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
            for drawing_id in ('E08', 'E09', 'E10', 'E14', 'E15'):
                serialized = next(r for r in exported['figures'] if r['drawing_id'] == drawing_id)
                self.assertTrue(serialized['callouts'])
                if drawing_id in ('E08', 'E09'):
                    anchor = next(c for c in serialized['callouts'] if c['name'] == 'housing')
                    self.assertIsNotNone(anchor['target'])
                if drawing_id == 'E10':
                    anchor = next(c for c in serialized['callouts'] if c['name'] == 'coil_cassette')
                    self.assertNotEqual(anchor['marker_offset_mm'], [0, 0])
                if drawing_id in ('E14', 'E15'):
                    references = {part['name']: part for part in serialized['parts']}
                    for name in ('lower_wood_frame_reference', 'upper_wood_frame_reference'):
                        self.assertFalse(references[name]['printable'])
                        self.assertTrue(references[name]['reference_note'])


if __name__ == '__main__':
    unittest.main()
