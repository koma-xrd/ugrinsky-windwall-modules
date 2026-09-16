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
from PIL import Image

from tests.support import temporary_build_directory
from windwall.export import export_part
from windwall.parameters import DEFAULT_PARAMETERS
from windwall.winding_tool_assembly import (
    build_winding_tool_assemblies, winding_tool_bom,
)
from windwall.winding_tool_export import (
    _export_supporting_artifacts, _print_inventory, _supporting_artifact_records,
    export_winding_tool,
)
from windwall.winding_tool_parameters import diameter_settings_mm
from windwall.winding_tool_service import coil_removal_stages, installed_shape


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


SUPPORT_PATHS = {
    'drawings/winding-jig-reference.png',
    'drawings/winding-jig-range.png',
    'drawings/winding-tool-exploded.png',
    'docs/serpentine-coil-winding-tool-de.md',
}


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

    def test_windows_checkout_keeps_source_and_release_guide_byte_identical(self):
        root = Path(__file__).resolve().parents[1]
        source = 'docs/serpentine-coil-winding-tool-de.md'
        release = f'release/winding-tool/{source}'
        guide_bytes = (root / source).read_bytes()
        with temporary_build_directory() as fixture:
            (fixture / '.gitattributes').write_bytes((root / '.gitattributes').read_bytes())
            for relative in (source, release):
                path = fixture / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(guide_bytes)
            try:
                for arguments in (('init', '-q'), ('add', '--', '.gitattributes', source, release),
                                  ('checkout-index', '--all', '--prefix=checkout/')):
                    subprocess.run(['git', '-c', 'core.autocrlf=true', '-c', 'core.safecrlf=false',
                                    *arguments], cwd=fixture, capture_output=True, check=True)
                checked_source = (fixture / 'checkout' / source).read_bytes()
                checked_release = (fixture / 'checkout' / release).read_bytes()
                self.assertEqual(checked_source, checked_release)
                self.assertEqual(checked_source, guide_bytes)
            finally:
                # Git creates read-only objects on Windows; this isolated test
                # repository must remain removable by the fixture's normal cleanup.
                for path in (fixture / '.git').rglob('*'):
                    if path.is_file():
                        path.chmod(0o666)


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
            self.assertEqual({row['path'] for row in data['supporting_artifacts']}, SUPPORT_PATHS)
            for filename in ('bom.json', 'manifest.json'):
                raw = (destination / filename).read_bytes()
                self.assertNotIn(b'\r', raw)
                self.assertEqual(raw.decode(), json.dumps(json.loads(raw), indent=2,
                                                          sort_keys=True) + '\n')

    def test_manifest_assembly_axis_matches_installed_geometry_and_forward_service(self):
        height = self.model.ownership['winding_jig']['wheel']['axis_height_mm']
        probe = cq.Workplane('XY').box(1, 1, 1)
        origin = installed_shape(probe, height).val().Center()
        forward = installed_shape(probe.translate((0, 0, 1)), height).val().Center().sub(origin)
        for actual, expected in zip(forward.toTuple(), (0, -1, 0)):
            self.assertAlmostEqual(actual, expected, places=6)
        removal = cq.Vector(*coil_removal_stages(self.model)[-1]['translation_mm'])
        self.assertAlmostEqual(removal.cross(forward).Length, 0, places=6)
        self.assertGreater(removal.dot(forward), 0)
        with temporary_build_directory() as destination:
            data = self.export_reference(destination,
                supporting_artifact_exporter=lambda _model, _output, _bom: ()).data
            self.assertEqual(data['coordinate_frames']['assembly_step'],
                             'Two independent origins; winding-jig axis Y (forward -Y) and payoff axis Z.')

    def test_manifest_omits_design_settings_not_used_by_the_tooling(self):
        """Shared fastener and coupon settings must not imply tooling hardware."""
        with temporary_build_directory() as destination:
            data = self.export_reference(destination,
                supporting_artifact_exporter=lambda _model, _output, _bom: ()).data
        expected_fields = {
            'manufacturing_parameters': (
                DEFAULT_PARAMETERS.manufacturing,
                ('export_linear_tolerance_mm', 'export_angular_tolerance_rad'),
            ),
            'bearing_parameters': (
                DEFAULT_PARAMETERS.bearings,
                ('radial_bore_diameter_mm', 'radial_outer_diameter_mm',
                 'radial_height_mm', 'radial_housing_seat_diameter_mm',
                 'thrust_bore_diameter_mm', 'thrust_outer_diameter_mm',
                 'thrust_height_mm', 'thrust_housing_seat_diameter_mm',
                 'thrust_rotating_pilot_diameter_mm'),
            ),
        }
        for section, (parameters, names) in expected_fields.items():
            with self.subTest(section=section):
                self.assertEqual(data[section],
                                 {name: getattr(parameters, name) for name in names})

    def test_support_publication_has_exact_current_drawings_and_synchronized_guide(self):
        # Missing support, a stale guide/BOM, omitted CAD occurrences or obsolete
        # release instructions must fail before a success manifest is published.
        root = Path(__file__).resolve().parents[1]
        with temporary_build_directory() as destination:
            records = _supporting_artifact_records(destination, _export_supporting_artifacts(
                self.model, destination, {'items': self.bom_rows}))
            self.assertEqual({row['path'] for row in records}, SUPPORT_PATHS)
            self.assertEqual(set(file_hashes(destination)), SUPPORT_PATHS)
            for record in records:
                path = destination / record['path']
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record['sha256'])
                if path.suffix == '.png':
                    with Image.open(path) as drawing:
                        self.assertEqual(drawing.size, (2000, 1400))
                    self.assertEqual((record['width_px'], record['height_px']), (2000, 1400))

            guide = (destination / 'docs/serpentine-coil-winding-tool-de.md').read_bytes()
            self.assertEqual(guide, (root / 'docs/serpentine-coil-winding-tool-de.md').read_bytes())
            content = guide.decode('utf-8')
            for phrase in ('Schutzbrille', 'Probespule', 'PLA',
                           'Akkuschrauberbetrieb ist nicht freigegeben',
                           'alle sechs Schuhe vollständig', 'nach vorn',
                           'von Hand stoppen', '100–200 mm', '10-mm-Schritten',
                           'drei Bandöffnungen pro Schuh', '18 Bandstellen',
                           'keine gleichmäßige physische 20°-Teilung',
                           'nicht physisch validiert'):
                self.assertIn(phrase, content)
            for stale in ('Kurvenring', 'Kurvenfolger', 'Klemmring', 'Filz', 'Bremseinsteller',
                          'Stahlbundring', 'Ø127', 'winding_frame_', 'winding_head_',
                          'wire_payoff_adjuster', 'M3', 'M4', 'M8', '220 mm nach links'):
                self.assertNotIn(stale, content)
            print_block = content.split('<!-- BEGIN print-bom -->')[1].split('<!-- END print-bom -->')[0]
            printed = {}
            for line in print_block.splitlines():
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if cells and cells[0].isdigit():
                    printed[cells[1].strip('`')] = int(cells[0])
            self.assertEqual(printed, {row['master']: row['quantity'] for row in self.bom_rows
                                       if row['source'] == 'printed'})
            for row in self.bom_rows:
                if row['source'] == 'purchased':
                    self.assertIn(f"| {row['quantity']} | `{row['name']}` | {row['specification']} |", content)

            exploded = next(row for row in records if row['path'].endswith('winding-tool-exploded.png'))
            for tool in ('winding_jig', 'wire_payoff'):
                groups = exploded['exploded_groups'][tool]
                members = [name for group in groups for name in group['members']]
                self.assertEqual(Counter(members), Counter(getattr(self.model, tool).keys()))
                for group in groups:
                    self.assertEqual(group['ownership'], {
                        name: self.model.ownership[tool][name] for name in group['members']})

    def test_two_independent_support_renders_have_identical_bytes(self):
        with temporary_build_directory() as destination:
            first, second = destination / 'first', destination / 'second'
            _export_supporting_artifacts(self.model, first, {'items': self.bom_rows})
            clear_winding_tool_geometry_caches()
            with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies',
                       return_value={'fixture_assembly_audit': True}):
                fresh = build_winding_tool_assemblies()
            _export_supporting_artifacts(fresh, second, {'items': winding_tool_bom(fresh)})
            self.assertEqual(set(file_hashes(first)), SUPPORT_PATHS)
            self.assertEqual(file_hashes(first), file_hashes(second))
            for relative in SUPPORT_PATHS:
                self.assertEqual((first / relative).read_bytes(), (second / relative).read_bytes())

    def test_manifest_lists_every_release_artifact_and_valid_support_hashes(self):
        with temporary_build_directory() as destination:
            data = self.export_reference(destination).data
            expected = {data['bom_path']: data['bom_sha256']}
            for part in data['printable_parts']:
                for kind in ('step', 'stl'):
                    expected[part[f'{kind}_path']] = part[f'{kind}_sha256']
            for assembly in data['assemblies']:
                expected[assembly['step_path']] = assembly['step_sha256']
            self.assertEqual({row['path'] for row in data['supporting_artifacts']}, SUPPORT_PATHS)
            expected.update({row['path']: row['sha256'] for row in data['supporting_artifacts']})
            actual = file_hashes(destination)
            actual.pop('manifest.json')
            self.assertEqual(actual, expected)

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

    def test_two_fresh_real_audited_builds_have_identical_release_artifact_bytes(self):
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
