"""Release artifacts must be complete, reproducible and fail closed on defects."""

from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

import cadquery as cq

from tests.support import temporary_build_directory
from windwall.assembly import RotorAssembly
from windwall.export import _export_assembly, export_all, export_part, validate_mesh
from windwall.parameters import DEFAULT_PARAMETERS


class ExportTests(unittest.TestCase):
    def test_all_unique_parts_export_as_valid_step_and_stl(self):
        with temporary_build_directory() as destination:
            manifest = export_all(destination)
            self.assertEqual(manifest.part_names(), {
                'base_rotor_module', 'standard_rotor_module', 'top_rotor_module',
                'top_closure', 'lower_magnet_rotor',
            })
            self.assertEqual({part.name for part in manifest.coupons}, {
                'bayonet_male', 'bayonet_female', 'joint_male', 'joint_female',
                'magnet_pocket_coupon',
            })
            for part in (*manifest.production_parts, *manifest.coupons):
                with self.subTest(part=part.name):
                    self.assertTrue(part.step_path.is_file())
                    self.assertTrue(part.stl_path.is_file())
                    self.assertEqual(part.boundary_edge_count, 0)
                    self.assertEqual(part.nonmanifold_edge_count, 0)
                    self.assertEqual(part.degenerate_face_count, 0)
                    self.assertEqual(part.mesh.component_count, 1)
                    self.assertGreater(part.mesh.triangle_count, 0)
                    self.assertGreater(part.cad_volume_mm3, 0)
                    self.assertAlmostEqual(part.mesh.minimum_xyz[2], 0, places=5)
                    imported = cq.importers.importStep(str(part.step_path)).val()
                    self.assertTrue(imported.isValid())
                    self.assertEqual(len(imported.Solids()), 1)
                    self.assertAlmostEqual(imported.Volume(1e-6), part.cad_volume_mm3, delta=0.01)
            data = json.loads((destination / 'manifest.json').read_text())
            self.assertEqual(data['parameters'], json.loads(json.dumps(asdict(DEFAULT_PARAMETERS))))
            self.assertEqual(data['production_quantity'], 9)
            self.assertFalse(data['physical_fit_verified'])
            self.assertFalse(data['print_ready'])
            self.assertEqual(data['assembly_audit']['seam_phase_jump_deg'], -60)
            self.assertEqual(data['assembly_audit']['internal_blade_twist_deg'], 60)
            for record in data['production_parts'] + data['coupons']:
                for suffix in ('step', 'stl'):
                    path = destination / record[f'{suffix}_path']
                    self.assertFalse(Path(record[f'{suffix}_path']).is_absolute())
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record[f'{suffix}_sha256'])
            for assembly in data['assemblies']:
                self.assertEqual(assembly['component_count'], 34)
                self.assertEqual(len(assembly['components']), 34)
                self.assertTrue(all(component['cad_valid'] for component in assembly['components']))
                path = destination / assembly['step_path']
                imported = cq.importers.importStep(str(path)).val()
                self.assertTrue(imported.isValid())
                self.assertEqual(len(imported.Solids()), 34)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), assembly['step_sha256'])

    def test_part_bytes_ignore_output_directory_and_other_export_counters(self):
        with temporary_build_directory() as destination:
            shape = cq.Workplane('XY').box(10, 12, 4).faces('>Z').workplane().hole(3)
            first = export_part('sample', shape, destination / 'first')
            export_part('unrelated', cq.Workplane('XY').box(1, 2, 3), destination / 'middle')
            second = export_part('sample', shape, destination / 'second')
            self.assertEqual(first.step_path.read_bytes(), second.step_path.read_bytes())
            self.assertEqual(first.stl_path.read_bytes(), second.stl_path.read_bytes())

    def test_multiple_solid_candidate_is_rejected(self):
        with temporary_build_directory() as destination:
            shape = cq.Workplane('XY').box(2, 2, 2).union(cq.Workplane('XY').box(2, 2, 2).translate((5, 0, 0)))
            with self.assertRaisesRegex(ValueError, 'one valid solid'):
                export_part('disconnected', shape, destination)

    def test_fresh_named_assembly_bytes_are_reproducible(self):
        def fixture():
            parts = {f'component_{i}': cq.Workplane('XY').box(2, 3, 4).translate((i * 5, 0, 0))
                     for i in range(34)}
            # Release export consumes the named shapes and placements only.
            # Full generator construction is exercised in the end-to-end test.
            return RotorAssembly(DEFAULT_PARAMETERS, parts, (), None, {}, ())

        with temporary_build_directory() as destination:
            first = _export_assembly(fixture(), destination / 'first', DEFAULT_PARAMETERS)
            second = _export_assembly(fixture(), destination / 'second', DEFAULT_PARAMETERS)
            self.assertEqual(first['step_sha256'], second['step_sha256'])

    def test_invalid_tessellation_tolerances_are_rejected(self):
        for field in ('export_linear_tolerance_mm', 'export_angular_tolerance_rad'):
            for value in (0, -1, float('nan'), float('inf')):
                with self.subTest(field=field, value=value), temporary_build_directory() as destination:
                    parameters = replace(DEFAULT_PARAMETERS, manufacturing=replace(
                        DEFAULT_PARAMETERS.manufacturing, **{field: value}))
                    with self.assertRaisesRegex(ValueError, 'tolerance'):
                        export_part('sample', cq.Workplane('XY').box(2, 2, 2), destination, parameters)

    def test_bad_mesh_topology_and_component_counts_are_rejected(self):
        fixture = Path(__file__).parent / 'fixtures/tetrahedron_binary.stl'
        with temporary_build_directory() as destination:
            valid = validate_mesh(fixture)
            self.assertEqual(valid.component_count, 1)
            with self.assertRaisesRegex(ValueError, 'component'):
                validate_mesh(fixture, expected_components=2)
            data = fixture.read_bytes()
            # Removing a face opens three boundary edges; duplicating one makes
            # three edges non-manifold. A collapsed face has zero area.
            count = struct.unpack_from('<I', data, 80)[0]
            variants = {
                'boundary': data[:80] + struct.pack('<I', count - 1) + data[84:-50],
                'nonmanifold': data[:80] + struct.pack('<I', count + 1) + data[84:] + data[84:134],
                'degenerate': data[:80] + struct.pack('<I', count + 1) + data[84:] + bytes(50),
            }
            for name, payload in variants.items():
                path = destination / f'{name}.stl'
                path.write_bytes(payload)
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'topology'):
                    validate_mesh(path)

    def test_failed_rebuild_removes_stale_success_manifest(self):
        with temporary_build_directory() as destination:
            (destination / 'manifest.json').write_text('{"old_success": true}')
            invalid = cq.Workplane('XY').box(2, 2, 2).union(cq.Workplane('XY').box(2, 2, 2).translate((5, 0, 0)))
            # Real builder work is slow; substitute only its invalid CAD result.
            # File writes, validation and fail-closed cleanup remain real.
            with patch('windwall.export.build_magnet_pocket_coupon', return_value=invalid):
                with self.assertRaises(ValueError):
                    export_all(destination)
            self.assertFalse((destination / 'manifest.json').exists())


if __name__ == '__main__':
    unittest.main()
