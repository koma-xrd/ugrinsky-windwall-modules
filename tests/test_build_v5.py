"""The clean V5 release must contain usable geometry and truthful ownership."""

import hashlib
import json
from pathlib import Path
import struct
import unittest

import cadquery as cq

from scripts.build_v5 import build_v5
from tests.support import temporary_build_directory
from windwall.reference_mesh import analyze_binary_stl


PRINT_PARTS = {
    'base_rotor_module', 'standard_rotor_module', 'top_rotor_module',
    'lower_magnet_rotor', 'generator_housing', 'coil_cassette',
    'generator_cover', 'top_support',
}
COUPONS = {
    '51105_outer_seat_coupon', '25mm_pilot_coupon', '608_seat_coupon',
    'coil_cassette_segment_coupon', 'magnet_pocket_coupon',
    'bayonet_male', 'bayonet_female', 'joint_male', 'joint_female',
}


class BuildV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = temporary_build_directory()
        cls.root = cls.workspace.__enter__()
        cls.addClassCleanup(cls.workspace.__exit__, None, None, None)
        cls.destination = cls.root / 'first'
        cls.manifest = build_v5(cls.destination)

    def artifact(self, record, suffix):
        return self.destination / Path(record[f'{suffix}_path']).relative_to('release/v5')

    def test_clean_output_contains_exact_print_and_assembly_inventory(self):
        expected = {'manifest.json'}
        expected.update(f'step/{name}.step' for name in PRINT_PARTS | COUPONS)
        expected.update(f'stl/{name}.stl' for name in PRINT_PARTS)
        expected.update(f'coupons/{name}.stl' for name in COUPONS)
        expected.update(f'assembly/{name}.step' for name in ('rotor_locked', 'generator', 'fence_assembly'))
        self.assertEqual({p.relative_to(self.destination).as_posix()
                          for p in self.destination.rglob('*') if p.is_file()}, expected)
        self.assertEqual({p['name'] for p in self.manifest['production_parts']}, PRINT_PARTS)
        self.assertEqual({p['name'] for p in self.manifest['coupons']}, COUPONS)
        self.assertNotIn('top_closure', json.dumps(self.manifest).lower())
        self.assertNotIn('top-closure', json.dumps(self.manifest).lower())

    def test_every_print_body_is_binary_manifold_and_step_imports(self):
        for record in self.manifest['production_parts'] + self.manifest['coupons']:
            with self.subTest(part=record['name']):
                path = self.artifact(record, 'stl')
                payload = path.read_bytes()
                triangles = struct.unpack_from('<I', payload, 80)[0]
                self.assertEqual(len(payload), 84 + 50 * triangles)
                mesh = analyze_binary_stl(path)
                self.assertEqual((mesh.component_count, mesh.boundary_edge_count,
                                  mesh.nonmanifold_edge_count, mesh.degenerate_face_count), (1, 0, 0, 0))
                self.assertAlmostEqual(mesh.minimum_xyz[2], 0, places=5)
                imported = cq.importers.importStep(str(self.artifact(record, 'step'))).val()
                self.assertTrue(imported.isValid())
                self.assertEqual(len(imported.Solids()), 1)
                for suffix in ('step', 'stl'):
                    self.assertEqual(hashlib.sha256(self.artifact(record, suffix).read_bytes()).hexdigest(),
                                     record[f'{suffix}_sha256'])

    def test_manifest_records_roles_quantities_dimensions_and_unverified_limits(self):
        self.assertNotIn('closure', self.manifest['parameters'])
        self.assertNotIn('closure_pilot_depth_mm', self.manifest['parameters']['modules'])
        self.assertNotIn('closure_screw_radius_mm', self.manifest['parameters']['modules'])
        self.assertEqual(self.manifest['parameters']['shaft_end'],
                         {'rod_projection_mm': 3.0, 'shaft_bottom_projection_mm': 5.0})
        records = self.manifest['production_parts'] + self.manifest['coupons'] + self.manifest['assemblies']
        records += [component for assembly in self.manifest['assemblies'] for component in assembly['components']]
        for record in records:
            with self.subTest(name=record['name']):
                self.assertIn(record['role'], {'rotating', 'stationary', 'hardware-reference', 'coupon'})
                self.assertGreater(record['quantity'], 0)
                self.assertEqual(len(record['dimensions_mm']['size_xyz']), 3)
                self.assertTrue(record['source_builder'].startswith('windwall.'))
                self.assertTrue(record['topology_result']['cad_valid'])
                self.assertFalse(record['physical_validation_verified'])
                self.assertTrue(record['known_limitations'])
        parts = {r['name']: r for r in self.manifest['production_parts']}
        self.assertEqual(self.manifest['production_quantity'], 12)
        self.assertEqual(parts['standard_rotor_module']['quantity'], 5)
        self.assertEqual(parts['generator_housing']['role'], 'stationary')
        self.assertEqual(parts['top_support']['role'], 'stationary')
        self.assertEqual(parts['base_rotor_module']['role'], 'rotating')
        coupons = {r['name']: r for r in self.manifest['coupons']}
        self.assertEqual(coupons['51105_outer_seat_coupon']['fit_dimensions_mm']['seat_diameters'], [42.0, 42.2, 42.4])
        self.assertEqual(coupons['25mm_pilot_coupon']['fit_dimensions_mm']['pilot_diameters'], [24.6, 24.8, 25.0])
        self.assertNotEqual(coupons['51105_outer_seat_coupon']['stl_sha256'],
                            coupons['25mm_pilot_coupon']['stl_sha256'])

    def test_seat_and_pilot_files_preserve_each_physical_fit_surface(self):
        coupons = {r['name']: r for r in self.manifest['coupons']}
        seats = cq.importers.importStep(str(self.artifact(coupons['51105_outer_seat_coupon'], 'step'))).val().Solids()[0]
        pilots = cq.importers.importStep(str(self.artifact(coupons['25mm_pilot_coupon'], 'step'))).val().Solids()[0]
        for x, radius in ((-55, 21.0), (0, 21.1), (55, 21.2)):
            self.assertFalse(seats.isInside(cq.Vector(x+radius-0.05, -28, 8), 1e-6))
            self.assertTrue(seats.isInside(cq.Vector(x+radius+0.05, -28, 8), 1e-6))
            self.assertTrue(seats.isInside(cq.Vector(x, -28, 1), 1e-6))
        for x, radius in ((-55, 12.3), (0, 12.4), (55, 12.5)):
            self.assertTrue(pilots.isInside(cq.Vector(x+radius-0.05, 28, 18), 1e-6))
            self.assertFalse(pilots.isInside(cq.Vector(x+radius+0.05, 28, 18), 1e-6))

    def test_total_step_has_one_extended_shaft_and_stationary_upper_support(self):
        assemblies = {r['name']: r for r in self.manifest['assemblies']}
        total = assemblies['fence_assembly']
        components = {r['name']: r for r in total['components']}
        self.assertEqual(total['component_count'], 37)
        self.assertEqual(total['cad_solid_count'], 71)
        self.assertNotIn('spacer', components)
        self.assertEqual(components['shaft']['quantity'], 1)
        self.assertEqual(components['shaft']['role'], 'hardware-reference')
        self.assertEqual(components['shaft']['motion'], 'rotating')
        self.assertAlmostEqual(components['shaft']['dimensions_mm']['minimum_xyz'][2], -42)
        self.assertAlmostEqual(components['shaft']['dimensions_mm']['maximum_xyz'][2], 513.3)
        self.assertNotIn('required_extended_m8_reference', components)
        for name in ('top_support', 'bearing_608', 'upper_wood_frame_reference'):
            self.assertIn(name, components)
        self.assertEqual(components['top_support']['role'], 'stationary')
        self.assertEqual(components['bearing_608']['role'], 'hardware-reference')
        self.assertEqual(components['upper_magnets']['quantity'], 18)
        self.assertEqual(components['upper_magnets']['cad_solid_count'], 18)
        self.assertEqual(assemblies['rotor_locked']['stage_count'], 7)
        self.assertEqual(assemblies['generator']['component_count'], 22)
        for assembly in assemblies.values():
            imported = cq.importers.importStep(str(self.artifact(assembly, 'step'))).val()
            self.assertTrue(imported.isValid())
            self.assertEqual(len(imported.Solids()), assembly['cad_solid_count'])
            if assembly['name'] == 'fence_assembly':
                rods = [s.BoundingBox() for s in imported.Solids()
                        if s.BoundingBox().zlen > 500 and s.BoundingBox().xlen < 9]
                self.assertEqual(len(rods), 1)
                self.assertAlmostEqual(rods[0].zmin, -42, places=5)
                self.assertAlmostEqual(rods[0].zmax, 513.3, places=5)
        audit = self.manifest['fence_assembly_audit']
        self.assertTrue(audit['extended_shaft_integrated'])
        self.assertAlmostEqual(audit['shaft_extension_mm'], 12)
        self.assertLess(audit['upper_support_rotating_intersection_mm3'], 0.01)

    def test_fresh_rebuild_is_byte_identical_and_paths_are_portable(self):
        second = self.root / 'second'
        second_manifest = build_v5(second)
        self.assertEqual(second_manifest, self.manifest)
        for first in self.destination.rglob('*'):
            if first.is_file():
                self.assertEqual(hashlib.sha256(first.read_bytes()).digest(),
                                 hashlib.sha256((second / first.relative_to(self.destination)).read_bytes()).digest(),
                                 first.name)
        text = (self.destination / 'manifest.json').read_text(encoding='utf-8')
        self.assertNotIn(str(self.root), text)
        self.assertNotIn('C:', text)
        self.assertNotIn('\\\\', text)


if __name__ == '__main__':
    unittest.main()
