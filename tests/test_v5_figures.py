"""The drawing handoff must describe actual, legible V5 CAD scenes."""

import importlib.util
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image

from tests.support import temporary_build_directory


class V5FigureTests(unittest.TestCase):
    def test_scene_copy_and_manifest_use_canonical_english(self):
        from scripts.manual.v5_figures import build_v5_scenes

        scenes, _ = build_v5_scenes()
        rendered_copy = []
        for scene in scenes:
            rendered_copy.extend((scene.title, scene.caption, scene.note))
            for panel in scene.panels:
                rendered_copy.append(panel.title)
                rendered_copy.extend(callout.label for callout in panel.callouts)
                rendered_copy.extend(part.record.reference_note for part in panel.parts)
        forbidden = ('rotierend', 'stationär', 'gehäuse', 'wicklung', 'mutter', 'schraube',
                     'oben', 'unten', 'prüf', 'nicht drucken', 'montage', 'stufe', 'blatt')
        joined = ' '.join(rendered_copy).casefold()
        self.assertFalse([word for word in forbidden if word in joined])
        self.assertEqual(len(scenes), 15)

        root = Path(__file__).resolve().parents[1]
        inventory = json.loads((root / 'release/v5/drawings/figures.json').read_text(encoding='utf-8'))
        self.assertEqual(inventory['raster_language'], 'en-GB')
        self.assertEqual(len(inventory['figures']), 15)
    def test_feature_anchors_and_complete_frame_installation(self):
        from scripts.manual.v5_figures import build_v5_scenes

        scenes, _ = build_v5_scenes()
        scenes = {scene.drawing_id: scene for scene in scenes}
        for drawing_id in ('E06', 'E07'):
            poles = getattr(scenes[drawing_id], 'magnet_poles', ())
            self.assertEqual(len(poles), 36, 'Both 18-magnet winding faces need pole labels')
            rings = {name: sorted((pole for pole in poles if pole.name == name),
                                  key=lambda pole: pole.index)
                     for name in ('upper_magnets', 'lower_magnets')}
            self.assertEqual([pole.pole for pole in rings['upper_magnets']], list('NS' * 9))
            self.assertEqual([pole.pole for pole in rings['lower_magnets']], list('SN' * 9))
            self.assertEqual([pole.angle_degrees for pole in rings['upper_magnets']],
                             list(range(0, 360, 20)))
            for upper, lower in zip(*rings.values(), strict=True):
                self.assertEqual(upper.center_mm[:2], lower.center_mm[:2])
                self.assertEqual(upper.angle_degrees, lower.angle_degrees)
                self.assertGreater(upper.center_mm[2], lower.center_mm[2])
                self.assertEqual(upper.facing_direction, (0, 0, -1))
                self.assertEqual(lower.facing_direction, (0, 0, 1))
                self.assertNotEqual(upper.pole, lower.pole)
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
                self.assertTrue(any('from above' in c.label for p in scenes[drawing_id].panels
                                    for c in p.callouts))
                self.assertTrue(any('from below' in c.label for p in scenes[drawing_id].panels
                                    for c in p.callouts))

    def test_tracked_51105_drawing_uses_the_two_release_coupon_parts(self):
        root = Path(__file__).resolve().parents[1]
        inventory = json.loads((root / 'release/v5/drawings/figures.json').read_text(encoding='utf-8'))
        record = next(item for item in inventory['figures'] if item['drawing_id'] == 'E11')
        self.assertEqual({part['name'] for part in record['parts']},
                         {'51105_outer_seat_coupon', '25mm_pilot_coupon'})

    def test_renderer_exists(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.manual.v5_figures'))

    def test_rejects_parameters_that_do_not_match_geometry_provenance(self):
        from scripts.manual.v5_figures import render_v5_figures
        from windwall.parameters import DEFAULT_PARAMETERS

        p = replace(DEFAULT_PARAMETERS, generator=replace(
            DEFAULT_PARAMETERS.generator, coil_former_height_mm=13.0))
        with temporary_build_directory() as output:
            with self.assertRaisesRegex(ValueError, 'parameters.*manifest'):
                render_v5_figures(output, p)
            self.assertEqual(list(output.iterdir()), [])

    def test_rendered_inventory_and_installed_generator_order(self):
        from scripts.manual.v5_figures import render_v5_figures
        import matplotlib.pyplot as plt
        from matplotlib.figure import Figure

        observed_poles = {}
        observed_text = {}
        close_figure = plt.close

        def inspect_then_close(figure=None):
            if isinstance(figure, Figure):
                drawing_id = figure.texts[0].get_text().split()[0]
                observed_poles[drawing_id] = [text.get_text() for axes in figure.axes
                                              for text in axes.texts
                                              if text.get_text() in ('N', 'S')]
                observed_text[drawing_id] = [text.get_text() for text in figure.texts]
                observed_text[drawing_id].extend(text.get_text() for axes in figure.axes
                                                 for text in axes.texts)
            close_figure(figure)

        with temporary_build_directory() as output:
            with patch('scripts.manual.v5_figures.plt.close', side_effect=inspect_then_close):
                records = render_v5_figures(output)
            self.assertEqual([r.drawing_id for r in records], [f'E{i:02d}' for i in range(1, 16)])
            self.assertEqual(len(list(output.glob('*.png'))), 15)
            exported = json.loads((output / 'figures.json').read_text(encoding='utf-8'))
            tracked_index = Path(__file__).resolve().parents[1] / 'release/v5/drawings/figures.json'
            self.assertEqual((output / 'figures.json').read_bytes(), tracked_index.read_bytes())
            self.assertEqual(len(exported['figures']), 15)
            self.assertEqual(exported['raster_language'], 'en-GB')
            forbidden_raster_copy = ('rotierend', 'stationär', 'gehäuse', 'wicklung',
                                     'mutter', 'schraube', 'prüf', 'quelle:', 'oben', 'unten')
            for drawing_id, labels in observed_text.items():
                raster_copy = ' '.join(labels).casefold()
                self.assertFalse([word for word in forbidden_raster_copy if word in raster_copy],
                                 f'{drawing_id} contains non-English raster copy')
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
                self.assertEqual(record.language, 'en-GB')
                self.assertTrue(any('ROTATING' in label for label in record.rotation_state_legend))
                self.assertTrue(any('STATIONARY' in label for label in record.rotation_state_legend))
                self.assertTrue(record.parts)
                self.assertTrue(all(part.source_builder for part in record.parts))
                self.assertNotIn('top_closure', {part.name for part in record.parts})
                self.assertNotIn('Top-Closure', record.caption + record.alt_text + ' '.join(record.callout_labels))
            for drawing_id in ('E06', 'E07'):
                record = next(r for r in records if r.drawing_id == drawing_id)
                self.assertEqual(observed_poles[drawing_id], list('NS' * 9 + 'SN' * 9),
                                 'The actual rendered figure must contain both full polarity rings')
                self.assertEqual(len(record.magnet_poles), 36)
                parts = {part.name: part for part in record.parts}
                self.assertLess(parts['lower_magnets'].display_bounds_mm[1][2],
                                parts['winding_volume'].display_bounds_mm[0][2])
                self.assertLess(parts['housing'].display_bounds_mm[0][2],
                                parts['lower_magnet_rotor'].display_bounds_mm[0][2])
                self.assertGreater(parts['housing'].display_bounds_mm[1][2],
                                   parts['lower_magnets'].display_bounds_mm[1][2])
                for name in ('housing', 'coil_cassette', 'cover', 'winding_volume'):
                    self.assertEqual(parts[name].motion, 'stationary')
                self.assertEqual(parts['lower_magnet_rotor'].motion, 'rotating')
                self.assertNotIn('spacer', parts)
            cover_fasteners = next(r for r in records if r.drawing_id == 'E09')
            self.assertTrue(any('4 × M4' in label for label in cover_fasteners.callout_labels))
            upper = next(r for r in records if r.drawing_id == 'E13')
            self.assertTrue(any('from below' in label for label in upper.callout_labels))
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
