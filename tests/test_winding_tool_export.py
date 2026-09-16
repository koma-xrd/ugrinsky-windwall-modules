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
from windwall.winding_tool_export import export_winding_tool, _print_inventory
from windwall.winding_tool_parameters import diameter_settings_mm


def copied_ownership(model):
    return {tool: {name: dict(owner) for name, owner in records.items()}
            for tool, records in model.ownership.items()}


def file_hashes(root):
    if not root.exists():
        return {}
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob('*')) if path.is_file()}


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
            self.assertFalse((destination / 'manifest.json').exists())

    def test_failed_assembly_or_service_audit_removes_stale_manifest(self):
        for failed_gate in ('valid_solids', 'complete_coil_removal'):
            with self.subTest(gate=failed_gate), temporary_build_directory() as destination:
                (destination / 'manifest.json').write_text('{"old_success": true}')
                audit = {'valid_solids': True, 'complete_coil_removal': True}
                audit[failed_gate] = False
                with self.reference_dependencies(audit):
                    with self.assertRaisesRegex(ValueError, 'audit'):
                        export_winding_tool(destination)
                self.assertFalse((destination / 'manifest.json').exists())

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
                with self.reference_dependencies(), patch(
                        f'windwall.winding_tool_export.{target}', side_effect=ValueError(message)):
                    with self.assertRaisesRegex(ValueError, message):
                        export_winding_tool(destination)
                self.assertFalse((destination / 'manifest.json').exists())

    def test_tampered_artifact_hash_prevents_manifest_publication(self):
        def tamper_print(_model, destination, _bom):
            part = next((destination / 'stl').glob('*.stl'))
            part.write_bytes(part.read_bytes() + b'tampered')
            return ()

        with temporary_build_directory() as destination, self.reference_dependencies():
            with self.assertRaisesRegex(ValueError, 'hash'):
                export_winding_tool(destination, supporting_artifact_exporter=tamper_print)
            self.assertFalse((destination / 'manifest.json').exists())

    def test_fresh_builds_in_different_directories_have_identical_artifact_bytes(self):
        with temporary_build_directory() as destination:
            self.export_reference(destination / 'first')
            export_part('unrelated', cq.Workplane('XY').box(1, 2, 3), destination / 'other')
            self.export_reference(destination / 'second')
            first = file_hashes(destination / 'first')
            second = file_hashes(destination / 'second')
            self.assertEqual(first, second)
            self.assertTrue(first)

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
