"""Exports must provide the coupon first and keep unverified fits visible."""

import unittest

import cadquery as cq

from scripts.preview_generator import export_generator
from tests.support import temporary_build_directory
from windwall.parameters import DEFAULT_PARAMETERS


class GeneratorExportTests(unittest.TestCase):
    def test_exported_carriers_coupon_and_reference_step_are_valid(self):
        with temporary_build_directory() as destination:
            report = export_generator(DEFAULT_PARAMETERS,destination)
            self.assertEqual(report['export_order'][0],'magnet_pocket_coupon')
            self.assertFalse(report['print_ready'])
            self.assertFalse(report['physical_magnet_fit_verified'])
            self.assertFalse(report['physical_bearing_fit_verified'])
            self.assertFalse(report['electrical_design_finalized'])
            self.assertEqual(report['coupon_pocket_diameters_left_to_right_mm'],[10.8,11.0,11.2])
            for name in ('magnet_pocket_coupon','base_with_upper_carrier','lower_magnet_rotor'):
                mesh = report['parts'][name]['mesh']
                self.assertEqual(mesh['component_count'],1)
                self.assertEqual(mesh['boundary_edge_count'],0)
                self.assertEqual(mesh['nonmanifold_edge_count'],0)
                self.assertEqual(mesh['degenerate_face_count'],0)
                self.assertAlmostEqual(mesh['minimum_xyz'][2],0,places=5)
                imported = cq.importers.importStep(str(destination / f'{name}.step')).val()
                self.assertTrue(imported.isValid())
                self.assertEqual(len(imported.Solids()),1)
            assembly = cq.importers.importStep(str(destination / 'generator_assembly.step')).val()
            self.assertTrue(assembly.isValid())
            self.assertEqual(len(assembly.Solids()), 56)
            self.assertEqual(report['rotation_states']['housing'], 'stationary')
            self.assertEqual(report['rotation_states']['lower_magnet_rotor'], 'rotating')
            self.assertEqual(report['rotation_states']['51105_rolling_envelope'], 'bearing')
            self.assertAlmostEqual(report['upper_air_gap_mm'],1.5,places=5)
            self.assertAlmostEqual(report['lower_air_gap_mm'],1.5,places=5)
            self.assertLess(report['maximum_rotating_stationary_intersection_mm3'],0.01)
            self.assertTrue((destination / 'generator_section.svg').is_file())
            self.assertTrue((destination / 'generator_fit.json').is_file())


if __name__ == '__main__':
    unittest.main()
