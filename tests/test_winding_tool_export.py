"""The simple winding-tool release is ownership-derived and fail closed."""

from collections import Counter
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import unittest
from unittest.mock import patch

import cadquery as cq

from tests.support import temporary_build_directory
from windwall.export import export_part
from windwall.winding_tool_assembly import (
    build_winding_tool_assemblies, winding_tool_bom,
)
from windwall.winding_tool_export import (
    _print_inventory, _supporting_artifact_records, export_winding_tool,
)
from windwall.winding_tool_parameters import diameter_settings_mm


def copied_ownership(model):
    return {tool: {name: dict(owner) for name, owner in records.items()}
            for tool, records in model.ownership.items()}


def file_hashes(root):
    if not root.exists():
        return {}
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob('*')) if path.is_file()}


def clear_winding_tool_geometry_caches():
    from windwall import winding_head, winding_tool_assembly, winding_tool_service

    for module in (winding_head, winding_tool_assembly, winding_tool_service):
        for value in vars(module).values():
            clear = getattr(value, 'cache_clear', None)
            if clear is not None:
                clear()


def assert_no_publisher_manifests(test_case, destination):
    test_case.assertFalse((destination / 'manifest.json').exists())
    test_case.assertFalse((destination / 'manifest.pending.json').exists())


class WindingToolReleaseAttributeTests(unittest.TestCase):
    def test_generated_step_diff_attribute_does_not_affect_sources_or_v5(self):
        root = Path(__file__).resolve().parents[1]
        paths = ('release/winding-tool/step/winding_jig_coil_wheel.step',
                 'release/winding-tool/assembly/simplified_winding_jig.step',
                 'release/v5/step/base_rotor_module.step',
                 'release/winding-tool/docs/serpentine-coil-winding-tool-de.md',
                 'src/windwall/winding_tool_export.py')
        result = subprocess.run(['git', 'check-attr', 'diff', '--', *paths],
                                cwd=root, capture_output=True, text=True, check=True)
        values = [line.rsplit(': ', 1)[-1] for line in result.stdout.splitlines()]
        self.assertEqual(values, ['unset', 'unset', 'unspecified', 'unspecified', 'unspecified'])


class WindingToolExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Component geometry stays real. The exhaustive Task 5 audit is tested
        # in its owning module and once in final integrated verification.
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies',
                   return_value={'fixture_assembly_audit': True}):
            cls.model = build_winding_tool_assemblies()
        cls.bom_rows = winding_tool_bom(cls.model)

    @contextmanager
    def reference_dependencies(self, audit=None):
        audit = {'fixture_assembly_audit': True,
                 'complete_coil_removal': True} if audit is None else audit
        with patch('windwall.winding_tool_export.build_winding_tool_assemblies',
                   return_value=self.model), patch(
                       'windwall.winding_tool_export.audit_winding_tool_assemblies',
                       return_value=audit):
            yield

    def export_reference(self, destination, **kwargs):
        with self.reference_dependencies():
            return export_winding_tool(destination, **kwargs)

    def test_release_excludes_every_superseded_part(self):
        with temporary_build_directory() as destination, self.reference_dependencies():
            manifest = export_winding_tool(destination)
            names = '\n'.join(item['name'] for item in manifest.data['printable_parts']).lower()
            for stale in ('cam', 'slider', 'rib', 'clamp', 'brake', 'adjuster', 'upright'):
                self.assertNotIn(stale, names)
            self.assertIn('coil_wheel', names)
            self.assertIn('contact_shoe', names)

    def test_unique_master_set_and_quantities_are_derived_from_occurrence_ownership(self):
        expected = Counter(
            f'{tool}/{owner["master"]}'
            for tool, records in self.model.ownership.items()
            for owner in records.values()
            if owner['source'] == 'printed'
        )
        inventory = _print_inventory(self.model, self.bom_rows)
        actual = {row['master']: row['quantity'] for row in inventory}
        self.assertEqual(actual, dict(sorted(expected.items())))
        self.assertEqual(sum(actual.values()), sum(expected.values()))
        self.assertEqual({row['name'] for row in inventory},
                         {master.replace('/', '_') for master in expected})

    def test_printed_shaft_uses_a_stable_planar_bed_phase_without_geometry_repair(self):
        inventory = _print_inventory(self.model, self.bom_rows)
        shaft = next(row for row in inventory
                     if row['master'] == 'winding_jig/printed_shaft')
        self.assertEqual(shaft['ownership_print_rotations_deg'], (90, 0, 0))
        self.assertEqual(shaft['print_rotations_deg'], (90, -30, 0))
        source = self.model.winding_jig['shaft']
        self.assertAlmostEqual(shaft['shape'].val().Volume(), source.val().Volume(), places=5)
        with temporary_build_directory() as destination:
            part = export_part(shaft['name'], shaft['shape'], destination)
        self.assertEqual(part.mesh.boundary_edge_count, 0)
        self.assertEqual(part.mesh.nonmanifold_edge_count, 0)
        self.assertEqual(part.mesh.degenerate_face_count, 0)
        self.assertAlmostEqual(part.mesh.minimum_xyz[2], 0, places=5)

    def test_every_print_master_passes_topology_step_orientation_and_hash_gates(self):
        expected_masters = {f'{tool}/{owner["master"]}'
                            for tool, records in self.model.ownership.items()
                            for owner in records.values() if owner['source'] == 'printed'}
        with temporary_build_directory() as destination:
            manifest = self.export_reference(destination)
            self.assertEqual(manifest.data, json.loads(manifest.path.read_text('utf-8')))
            self.assertEqual(len(manifest.printable_parts), len(expected_masters))
            for record, part in zip(manifest.data['printable_parts'], manifest.printable_parts):
                with self.subTest(master=record['master']):
                    self.assertEqual(record['material'], 'PLA')
                    self.assertLessEqual(max(record['print_bed_footprint_mm']), 220)
                    self.assertEqual(len(record['print_orientation']['rotations_deg']), 3)
                    self.assertTrue(record['topology_result']['stl_closed_manifold'])
                    self.assertEqual(part.mesh.component_count, 1)
                    self.assertEqual(part.mesh.boundary_edge_count, 0)
                    self.assertEqual(part.mesh.nonmanifold_edge_count, 0)
                    self.assertEqual(part.mesh.degenerate_face_count, 0)
                    self.assertAlmostEqual(part.mesh.minimum_xyz[2], 0, places=5)
                    for extension in ('step', 'stl'):
                        relative = record[f'{extension}_path']
                        self.assertFalse(Path(relative).is_absolute())
                        artifact = destination / relative
                        self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(),
                                         record[f'{extension}_sha256'])
                    imported = cq.importers.importStep(str(part.step_path)).val()
                    self.assertTrue(imported.isValid())
                    self.assertEqual(len(imported.Solids()), 1)

    def test_two_named_assemblies_preserve_members_ownership_and_hashes(self):
        with temporary_build_directory() as destination:
            manifest = self.export_reference(destination)
            expected_names = {'simplified_winding_jig': 'winding_jig',
                              'free_running_wire_payoff': 'wire_payoff'}
            self.assertEqual({row['name'] for row in manifest.assemblies}, set(expected_names))
            self.assertEqual(len(manifest.assemblies), 2)
            for assembly in manifest.assemblies:
                tool = expected_names[assembly['name']]
                with self.subTest(assembly=assembly['name']):
                    self.assertEqual({row['name'] for row in assembly['components']},
                                     set(getattr(self.model, tool)))
                    self.assertEqual({row['name']: row['ownership']
                                      for row in assembly['components']},
                                     self.model.ownership[tool])
                    path = destination / assembly['step_path']
                    imported = cq.importers.importStep(str(path)).val()
                    self.assertTrue(imported.isValid())
                    self.assertEqual(len(imported.Solids()), len(getattr(self.model, tool)))
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                                     assembly['step_sha256'])

    def test_manifest_serializes_canonical_bom_settings_and_prototype_semantics(self):
        with temporary_build_directory() as destination:
            manifest = self.export_reference(destination)
            data = manifest.data
            bom = json.loads((destination / data['bom_path']).read_text('utf-8'))
            self.assertEqual(bom['items'], list(self.bom_rows))
            purchased = {row['name']: row['quantity'] for row in bom['items']
                         if row['source'] == 'purchased'}
            self.assertEqual(purchased, {'608 bearing': 2, '51105 thrust bearing': 1})
            self.assertEqual(hashlib.sha256((destination / data['bom_path']).read_bytes()).hexdigest(),
                             data['bom_sha256'])
            settings = data['wheel_settings']
            self.assertEqual(tuple(row['nominal_diameter_mm'] for row in settings),
                             diameter_settings_mm(self.model.parameters))
            self.assertTrue(all(len(row['actual_tape_angles_deg']) == 18 for row in settings))
            self.assertEqual(data['tape_angle_semantics']['nominal_pitch_deg'], 20)
            self.assertEqual(data['tape_angle_semantics']['nominal_use'], 'sequence labels only')
            self.assertFalse(data['powered_operation'])
            self.assertFalse(data['physical_validation_verified'])
            self.assertTrue(data['known_limitations'])
            self.assertEqual(data['supporting_artifacts'], [])
            for filename in ('bom.json', 'manifest.json'):
                raw = (destination / filename).read_bytes()
                self.assertNotIn(b'\r', raw)
                self.assertEqual(raw.decode(), json.dumps(json.loads(raw), indent=2,
                                                          sort_keys=True) + '\n')

    def test_malformed_ownership_and_quantity_mismatches_cannot_form_inventory(self):
        cases = []
        owners = copied_ownership(self.model)
        owners['winding_jig']['obsolete_cam'] = {
            'master': 'cam', 'group': 'rotating', 'source': 'printed',
            'print_rotations_deg': (0, 0, 0),
        }
        members = dict(self.model.winding_jig)
        members['obsolete_cam'] = members['wheel']
        cases.append(('stale old part', replace(self.model, winding_jig=members, ownership=owners)))

        owners = copied_ownership(self.model)
        owners['winding_jig']['wheel']['source'] = 'purchased'
        cases.append(('hidden print body', replace(self.model, ownership=owners)))

        members = dict(self.model.winding_jig)
        members.pop('shoe_6')
        cases.append(('missing occurrence', replace(self.model, winding_jig=members)))

        owners = copied_ownership(self.model)
        owners['winding_jig']['wheel_copy'] = dict(owners['winding_jig']['wheel'])
        members = dict(self.model.winding_jig)
        members['wheel_copy'] = members['wheel']
        cases.append(('duplicate occurrence', replace(self.model, winding_jig=members,
                                                       ownership=owners)))
        for name, mutant in cases:
            with self.subTest(case=name), self.assertRaises(ValueError):
                _print_inventory(mutant)

        rows = [dict(row) for row in self.bom_rows]
        next(row for row in rows if row.get('master') == 'winding_jig/contact_shoe')['quantity'] += 1
        with self.subTest(case='quantity mismatch'), self.assertRaisesRegex(ValueError, 'quantity'):
            _print_inventory(self.model, tuple(rows))

    def test_noncanonical_bom_cannot_publish(self):
        rows = [dict(row) for row in self.bom_rows]
        next(row for row in rows if row['name'] == '51105 thrust bearing')['quantity'] = 2
        with temporary_build_directory() as destination, self.reference_dependencies(), patch(
                'windwall.winding_tool_export.winding_tool_bom', return_value=tuple(rows)):
            with self.assertRaisesRegex(ValueError, 'BOM'):
                export_winding_tool(destination)
            assert_no_publisher_manifests(self, destination)

    def test_failed_assembly_or_service_audit_removes_stale_manifest(self):
        for failed_gate in ('valid_solids', 'complete_coil_removal'):
            with self.subTest(gate=failed_gate), temporary_build_directory() as destination:
                (destination / 'manifest.json').write_text('{"old_success": true}')
                (destination / 'manifest.pending.json').write_text('{"old_pending": true}')
                audit = {'valid_solids': True, 'complete_coil_removal': True}
                audit[failed_gate] = False
                with self.reference_dependencies(audit):
                    with self.assertRaisesRegex(ValueError, 'audit'):
                        export_winding_tool(destination)
                assert_no_publisher_manifests(self, destination)

    def test_part_mesh_step_assembly_bom_inventory_and_support_fail_closed(self):
        failures = (
            ('export_part', 'invalid STL mesh'),
            ('_export_step', 'failed STEP reimport'),
            ('winding_tool_bom', 'noncanonical BOM'),
            ('_print_inventory', 'inventory mismatch'),
            ('_export_supporting_artifacts', 'drawing or guide failure'),
            ('_verify_artifact_hashes', 'artifact hash failure'),
        )
        for target, message in failures:
            with self.subTest(target=target), temporary_build_directory() as destination:
                (destination / 'manifest.json').write_text('{"old_success": true}')
                (destination / 'manifest.pending.json').write_text('{"old_pending": true}')
                with self.reference_dependencies(), patch(
                        f'windwall.winding_tool_export.{target}', side_effect=ValueError(message)):
                    with self.assertRaisesRegex(ValueError, message):
                        export_winding_tool(destination)
                assert_no_publisher_manifests(self, destination)

    def test_tampered_artifact_hash_prevents_manifest_publication(self):
        def tamper_print(_model, destination, _bom):
            part = next((destination / 'stl').glob('*.stl'))
            part.write_bytes(part.read_bytes() + b'tampered')
            return ()

        with temporary_build_directory() as destination, self.reference_dependencies():
            with self.assertRaisesRegex(ValueError, 'hash'):
                export_winding_tool(destination, supporting_artifact_exporter=tamper_print)
            assert_no_publisher_manifests(self, destination)

    def test_support_inventory_rejects_reserved_publisher_names_and_aliases(self):
        aliases = (
            'manifest.json', './manifest.json', 'MANIFEST.JSON',
            'manifest.json.', 'manifest.json ',
            'manifest.pending.json', './MANIFEST.PENDING.JSON',
            'manifest.pending.json.', 'manifest.pending.json ',
        )
        with temporary_build_directory() as destination:
            (destination / 'manifest.json').write_bytes(b'provider manifest')
            (destination / 'manifest.pending.json').write_bytes(b'provider pending')
            for alias in aliases:
                with self.subTest(alias=alias), self.assertRaisesRegex(ValueError, 'manifest'):
                    _supporting_artifact_records(destination, ({'path': alias},))

    def test_support_inventory_rejects_external_windows_paths_and_normalizes_relative_paths(self):
        with temporary_build_directory() as fixture:
            destination = fixture / 'release'
            destination.mkdir()
            outside = fixture / 'outside.txt'
            outside.write_bytes(b'external source must never be hashed')
            invalid = (
                '../outside.txt', r'..\outside.txt', str(outside.resolve()),
                outside.resolve().as_posix(), r'\outside.txt', '/outside.txt',
                'C:/outside.txt', r'C:\outside.txt', 'docs/../../outside.txt',
            )
            for path in invalid:
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'path'):
                    _supporting_artifact_records(destination, ({'path': path},))

            artifact = destination / 'docs' / 'guide.txt'
            artifact.parent.mkdir()
            artifact.write_bytes(b'portable')
            records = _supporting_artifact_records(
                destination, ({'path': './docs//guide.txt'},))
            self.assertEqual(records[0]['path'], 'docs/guide.txt')

    def test_reserved_support_manifest_paths_cannot_publish_or_survive(self):
        for reserved_name in ('manifest.json', 'manifest.pending.json'):
            with self.subTest(path=reserved_name), temporary_build_directory() as destination:
                def reserved(_model, output, _bom):
                    (output / 'manifest.json').write_bytes(b'provider manifest')
                    (output / 'manifest.pending.json').write_bytes(b'provider pending')
                    return ({'path': reserved_name},)

                with self.reference_dependencies():
                    with self.assertRaisesRegex(ValueError, 'manifest'):
                        export_winding_tool(destination, supporting_artifact_exporter=reserved)
                assert_no_publisher_manifests(self, destination)

    def test_support_provider_exception_removes_both_publisher_manifests(self):
        def fail_after_writing(_model, destination, _bom):
            (destination / 'manifest.json').write_bytes(b'provider manifest')
            (destination / 'manifest.pending.json').write_bytes(b'provider pending')
            raise RuntimeError('support provider failed after writing manifests')

        with temporary_build_directory() as destination, self.reference_dependencies():
            with self.assertRaisesRegex(RuntimeError, 'after writing manifests'):
                export_winding_tool(destination, supporting_artifact_exporter=fail_after_writing)
            assert_no_publisher_manifests(self, destination)

    def test_two_fresh_real_audited_builds_have_identical_core_artifact_bytes(self):
        with temporary_build_directory() as destination:
            clear_winding_tool_geometry_caches()
            export_winding_tool(destination / 'first')
            export_part('unrelated', cq.Workplane('XY').box(1, 2, 3), destination / 'other')
            clear_winding_tool_geometry_caches()
            export_winding_tool(destination / 'second')
            first_root = destination / 'first'
            second_root = destination / 'second'
            first_paths = sorted(path.relative_to(first_root).as_posix()
                                 for path in first_root.rglob('*') if path.is_file())
            second_paths = sorted(path.relative_to(second_root).as_posix()
                                  for path in second_root.rglob('*') if path.is_file())
            self.assertEqual(first_paths, second_paths)
            self.assertTrue(first_paths)
            for relative in first_paths:
                with self.subTest(artifact=relative):
                    self.assertEqual((first_root / relative).read_bytes(),
                                     (second_root / relative).read_bytes())

    def test_cli_builds_explicit_destination_without_mutating_tracked_release(self):
        root = Path(__file__).resolve().parents[1]
        release_before = file_hashes(root / 'release/winding-tool')
        with temporary_build_directory() as destination, self.reference_dependencies():
            with patch.object(sys, 'argv', ['build_winding_tool.py', '--output-dir', str(destination)]):
                with self.assertRaises(SystemExit) as result:
                    runpy.run_path(str(root / 'scripts/build_winding_tool.py'), run_name='__main__')
            self.assertEqual(result.exception.code, 0)
            self.assertTrue((destination / 'manifest.json').is_file())
            failed = subprocess.run([sys.executable, str(root / 'scripts/run_geometry.py'),
                                     str(root / 'scripts/build_winding_tool.py'),
                                     '--output-dir', str(destination / 'bom.json')], capture_output=True)
            self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(file_hashes(root / 'release/winding-tool'), release_before)


if __name__ == '__main__':
    unittest.main()
