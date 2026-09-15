"""Tool releases certify actual geometry, inventory and reproducible bytes."""

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
from windwall.winding_tool_assembly import build_winding_tool_assemblies
from windwall.winding_tool_export import export_winding_tool
from windwall.winding_head import build_winding_head
from windwall.winding_tool_parameters import DEFAULT_WINDING_TOOL_PARAMETERS


class WindingToolPrintabilityTests(unittest.TestCase):
    def test_fresh_rib_builds_export_identical_bytes(self):
        with temporary_build_directory() as destination:
            digests = []
            for index in range(4):
                rib = build_winding_head(DEFAULT_WINDING_TOOL_PARAMETERS, 127.0).ribs[0]
                result = export_part('rib', rib, destination / str(index))
                digests.append((result.step_sha256, result.stl_sha256))
            self.assertEqual(len(set(digests)), 1, digests)

    def test_rib_master_exports_without_collapsed_corner_triangles(self):
        rib = build_winding_head(DEFAULT_WINDING_TOOL_PARAMETERS, 127.0).ribs[0]
        with temporary_build_directory() as destination:
            result = export_part('rib', rib, destination)
            self.assertEqual(result.mesh.degenerate_face_count, 0)
            self.assertEqual(result.mesh.boundary_edge_count, 0)
            self.assertEqual(result.mesh.nonmanifold_edge_count, 0)


class WindingToolExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = build_winding_tool_assemblies()

    def test_tooling_export_has_valid_unique_parts_assemblies_bom_and_manifest(self):
        with temporary_build_directory() as destination:
            manifest = export_winding_tool(destination)
            data = json.loads(manifest.path.read_text(encoding='utf-8'))
            quantities = {part.name: part.quantity for part in manifest.printable_parts}
            self.assertEqual(quantities, {
                'winding_head_backplate': 1, 'winding_head_cam': 1,
                'winding_head_clamp': 1, 'winding_head_slider': 6, 'winding_head_rib': 6,
                'winding_frame_base': 1, 'winding_frame_upright': 2,
                'winding_frame_head_hub': 1, 'winding_frame_head_retaining_collar': 1,
                'winding_frame_crank': 1, 'wire_payoff_base': 1,
                'wire_payoff_platter': 1, 'wire_payoff_adjuster': 1,
            })
            self.assertEqual(data['printable_quantity'], 24)
            self.assertEqual(list(quantities), sorted(quantities))
            self.assertEqual(len(list((destination / 'stl').glob('*.stl'))), 13)
            self.assertEqual(len(list((destination / 'step').glob('*.step'))), 13)
            self.assertEqual(data['reference_diameter_mm'], 127.0)
            self.assertEqual(data['diameter_range_mm'], [110.0, 145.0])
            self.assertEqual(data['tape_layout']['station_angles_deg'], list(range(0, 360, 20)))
            self.assertFalse(data['physical_fit_verified'])
            self.assertFalse(data['powered_operation_validated'])
            self.assertTrue(data['assembly_audit']['valid'])
            self.assertEqual(data['ownership']['wire_payoff']['bearing_internal'], ['rolling_envelope'])
            self.assertIn('housing_washer', data['ownership']['wire_payoff']['stationary'])
            self.assertIn('shaft_washer', data['ownership']['wire_payoff']['rotating'])
            self.assertTrue(any('Powered' in limit for limit in data['known_limitations']))
            for record, part in zip(data['printable_parts'], manifest.printable_parts):
                self.assertTrue(record['source_builder'].startswith('windwall.'))
                self.assertEqual(record['known_limitations'], data['known_limitations'])
                self.assertTrue(record['topology_result']['stl_closed_manifold'])
                self.assertEqual(part.mesh.component_count, 1)
                self.assertAlmostEqual(part.mesh.minimum_xyz[2], 0, places=5)
                for extension in ('step', 'stl'):
                    path = destination / record[f'{extension}_path']
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                                     record[f'{extension}_sha256'])
                imported = cq.importers.importStep(str(part.step_path)).val()
                self.assertTrue(imported.isValid())
                self.assertEqual(len(imported.Solids()), 1)
            self.assertEqual({item['name'] for item in manifest.assemblies},
                             {'winding_jig', 'wire_payoff', 'winding_jig_exploded'})
            assemblies = {item['name']: item for item in data['assemblies']}
            for assembly in assemblies.values():
                path = destination / assembly['step_path']
                imported = cq.importers.importStep(str(path)).val()
                self.assertTrue(imported.isValid())
                self.assertEqual(len(imported.Solids()), assembly['cad_solid_count'])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), assembly['step_sha256'])
                text = path.read_text(encoding='utf-8')
                for component in assembly['components']:
                    self.assertIn(component['name'], text)
                    self.assertEqual(component['printable'], 'print_part' in component)
                    if component['printable']:
                        self.assertIn(component['print_part'], quantities)
            self.assertNotEqual(assemblies['winding_jig']['cad_bounds_mm'],
                                assemblies['winding_jig_exploded']['cad_bounds_mm'])
            bom = json.loads((destination / 'bom.json').read_text(encoding='utf-8'))
            self.assertEqual({row['item']: row['quantity'] for row in bom['printable_parts']}, quantities)
            hardware = {row['item']: row['quantity'] for row in bom['hardware']}
            self.assertEqual(hardware['608 bearing'], 2)
            self.assertEqual(hardware['51105 thrust bearing'], 1)
            self.assertEqual(hashlib.sha256((destination / 'bom.json').read_bytes()).hexdigest(),
                             data['bom_sha256'])
            for filename in ('bom.json', 'manifest.json'):
                raw = (destination / filename).read_bytes()
                self.assertNotIn(b'\r', raw)
                self.assertEqual(raw.decode(), json.dumps(json.loads(raw), indent=2, sort_keys=True) + '\n')

    def test_fresh_builds_have_identical_artifact_bytes(self):
        with temporary_build_directory() as destination:
            export_winding_tool(destination / 'first')
            export_part('unrelated', cq.Workplane('XY').box(1, 2, 3), destination / 'other')
            export_winding_tool(destination / 'second')
            files = sorted(path.relative_to(destination / 'first')
                           for path in (destination / 'first').rglob('*') if path.is_file())
            for name in files:
                self.assertEqual((destination / 'first' / name).read_bytes(),
                                 (destination / 'second' / name).read_bytes(), name)

    def test_failed_audit_removes_stale_manifest(self):
        members = dict(self.model.winding_jig)
        del members['slider_6']
        invalid = replace(self.model, winding_jig=members)
        with temporary_build_directory() as destination:
            (destination / 'manifest.json').write_text('{"old_success": true}')
            with patch('windwall.winding_tool_export.build_winding_tool_assemblies', return_value=invalid):
                with self.assertRaisesRegex(ValueError, 'audit'):
                    export_winding_tool(destination)
            self.assertFalse((destination / 'manifest.json').exists())

    def test_failed_artifact_or_bom_never_publishes_manifest(self):
        for target in ('export_part', '_export_step', 'winding_tool_bom'):
            with self.subTest(target=target), temporary_build_directory() as destination:
                (destination / 'manifest.json').write_text('{"old_success": true}')
                # Fault injection at slow CAD/I/O boundaries leaves publication real.
                with patch('windwall.winding_tool_export.build_winding_tool_assemblies', return_value=self.model):
                    with patch(f'windwall.winding_tool_export.{target}', side_effect=ValueError('injected failure')):
                        with self.assertRaisesRegex(ValueError, 'injected failure'):
                            export_winding_tool(destination)
                self.assertFalse((destination / 'manifest.json').exists())

    def test_cli_builds_to_explicit_directory_and_propagates_failure(self):
        root = Path(__file__).resolve().parents[1]
        with temporary_build_directory() as destination:
            # Check the application's exit separately from the known Windows
            # OCP interpreter-teardown failure; never suppress the host status.
            with patch.object(sys, 'argv', ['build_winding_tool.py', '--output-dir', str(destination)]):
                with self.assertRaises(SystemExit) as result:
                    runpy.run_path(str(root / 'scripts/build_winding_tool.py'), run_name='__main__')
            self.assertEqual(result.exception.code, 0)
            self.assertTrue((destination / 'manifest.json').is_file())
            # A file cannot serve as an output directory; the CLI must exit nonzero.
            failed = subprocess.run([sys.executable, str(root / 'scripts/run_geometry.py'),
                                     str(root / 'scripts/build_winding_tool.py'),
                                     '--output-dir', str(destination / 'bom.json')], capture_output=True)
            self.assertNotEqual(failed.returncode, 0)


if __name__ == '__main__':
    unittest.main()
