"""Exported mesh and STEP round trips validate the three printable module bodies."""

import unittest

import cadquery as cq

from scripts.preview_modules import export_modules
from tests.support import temporary_build_directory
from windwall.parameters import DEFAULT_PARAMETERS


class ModuleExportTests(unittest.TestCase):
    def test_each_module_exports_as_one_closed_mesh_and_step_solid(self):
        with temporary_build_directory() as destination:
            report = export_modules(DEFAULT_PARAMETERS, destination)
            self.assertTrue((destination / 'magnet_pocket_coupon.stl').is_file())
            for name in ('base','standard','top'):
                mesh = report['modules'][name]['mesh']
                self.assertEqual(mesh['component_count'], 1)
                self.assertEqual(mesh['boundary_edge_count'], 0)
                self.assertEqual(mesh['nonmanifold_edge_count'], 0)
                self.assertEqual(mesh['degenerate_face_count'], 0)
                shape = cq.importers.importStep(str(destination / f'{name}_module.step')).val()
                self.assertTrue(shape.isValid())
                self.assertEqual(len(shape.Solids()), 1)
                self.assertTrue((destination / f'{name}_module.svg').is_file())
            self.assertTrue(report['aerodynamic_seam_continuous'])
            self.assertTrue(report['upper_magnet_carrier_integrated'])
            self.assertEqual(report['nominal_module_rotation_deg'], 60)
            self.assertFalse(report['elastic_snap_fit_verified'])
            self.assertLess(report['maximum_locked_intersection_mm3'], 0.01)
            self.assertTrue((destination / 'module_fit.json').is_file())


if __name__ == '__main__':
    unittest.main()
