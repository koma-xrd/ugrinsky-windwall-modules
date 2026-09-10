"""Export round trips retain every component and manifold unique print candidate."""

import unittest
from unittest.mock import patch

import cadquery as cq

from scripts.preview_assembly import export_assembly
from tests.support import temporary_build_directory
from windwall.parameters import DEFAULT_PARAMETERS


class AssemblyExportTests(unittest.TestCase):
    def test_default_preview_destination_is_isolated_from_release_assembly(self):
        with temporary_build_directory() as root:
            release = root / 'build' / 'assembly' / 'rotor_locked.step'
            manifest = root / 'build' / 'manifest.json'
            release.parent.mkdir(parents=True)
            release.write_bytes(b'validated release')
            manifest.write_bytes(b'validated hashes')

            def write_preview(_parameters, destination):
                destination.mkdir(parents=True)
                (destination / 'rotor_locked.step').write_bytes(b'preview')
                return {'ok': True}

            with patch('scripts.preview_assembly.PROJECT_ROOT', root), \
                    patch('scripts.preview_assembly.export_assembly', side_effect=write_preview) as export, \
                    patch('sys.argv', ['preview_assembly.py']):
                from scripts.preview_assembly import main
                self.assertEqual(main(), 0)

            self.assertEqual(export.call_args.args[1], root / 'build' / 'previews' / 'assembly')
            self.assertEqual(release.read_bytes(), b'validated release')
            self.assertEqual(manifest.read_bytes(), b'validated hashes')

    def test_exports_are_complete_and_round_trip(self):
        with temporary_build_directory() as destination:
            report = export_assembly(DEFAULT_PARAMETERS,destination)
            self.assertEqual(report['export_order'][0],'magnet_pocket_coupon')
            self.assertFalse(report['print_ready'])
            for name in ('base_module','standard_module','top_module','lower_magnet_rotor',
                         'generator_housing','coil_cassette','generator_cover'):
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
                self.assertEqual(len(solid.Solids()), 64)
            self.assertTrue(report['aerodynamic_seam_continuous'])
            for name in ('assembly_fit.json','assembly_inspection.png','top_clamp_section.svg'):
                self.assertTrue((destination/name).is_file())


if __name__ == '__main__':
    unittest.main()
