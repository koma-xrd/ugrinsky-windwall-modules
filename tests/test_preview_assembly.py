"""Export round trips retain every component and manifold unique print candidate."""

import unittest

import cadquery as cq

from scripts.preview_assembly import export_assembly
from tests.support import temporary_build_directory
from windwall.parameters import DEFAULT_PARAMETERS


class AssemblyExportTests(unittest.TestCase):
    def test_exports_are_complete_and_round_trip(self):
        with temporary_build_directory() as destination:
            report = export_assembly(DEFAULT_PARAMETERS,destination)
            self.assertEqual(report['export_order'][0],'magnet_pocket_coupon')
            self.assertFalse(report['print_ready'])
            for name in ('base_module','standard_module','top_module','top_closure','lower_magnet_rotor'):
                mesh = report['exports'][name]['mesh']
                self.assertEqual(mesh['component_count'],1)
                self.assertEqual(mesh['boundary_edge_count'],0)
                self.assertEqual(mesh['nonmanifold_edge_count'],0)
                self.assertEqual(mesh['degenerate_face_count'],0)
                self.assertAlmostEqual(mesh['minimum_xyz'][2],0,places=5)
                solid = cq.importers.importStep(str(destination / f'{name}.step')).val()
                self.assertTrue(solid.isValid())
                self.assertEqual(len(solid.Solids()),1)
            for name in ('rotor_locked','rotor_exploded'):
                solid = cq.importers.importStep(str(destination / f'{name}.step')).val()
                self.assertTrue(solid.isValid())
                self.assertEqual(len(solid.Solids()),34)
            for name in ('assembly_fit.json','assembly_inspection.png','top_closure_section.svg'):
                self.assertTrue((destination/name).is_file())


if __name__ == '__main__':
    unittest.main()
