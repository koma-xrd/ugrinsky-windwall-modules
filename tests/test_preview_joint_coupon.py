import unittest
from dataclasses import replace

import cadquery as cq

from scripts.preview_joint_coupon import export_coupon
from windwall.parameters import DEFAULT_PARAMETERS
from windwall.reference_mesh import analyze_binary_stl
from tests.support import temporary_build_directory


class JointExportTests(unittest.TestCase):
    def test_export_contains_manifold_pair_step_and_fit_evidence(self):
        with temporary_build_directory() as destination:
            p = DEFAULT_PARAMETERS
            changed = replace(p, bayonet=replace(p.bayonet, insertion_offset_deg=18.25))
            report = export_coupon(changed, destination)
            self.assertEqual(report.get('locking_lift_mm'), 1.0)
            self.assertLess(report['maximum_rigid_motion_intersection_mm3'], .01)
            self.assertNotIn('blade_seam', report)
            self.assertEqual(report['torque_interface'], 'central_bayonet_only')
            self.assertEqual(report['blade_ends'], 'plain_flush_samples')
            self.assertAlmostEqual(report['motion_samples'][-1]['travel_deg'], 18.25)
            for name in ('male', 'female'):
                mesh = analyze_binary_stl(destination / f'joint_{name}.stl')
                self.assertEqual(mesh.component_count, 1)
                self.assertEqual(mesh.boundary_edge_count, 0)
                self.assertEqual(mesh.nonmanifold_edge_count, 0)
                self.assertEqual(mesh.degenerate_face_count, 0)
                self.assertAlmostEqual(mesh.minimum_xyz[2], 0, places=5)
            step = cq.importers.importStep(str(destination / 'joint_locked.step'))
            self.assertEqual(len(step.val().Solids()), 2)
            self.assertLess(report['locked_intersection_mm3'], 0.01)
            self.assertGreater(report['ccw_stop_intersection_mm3'], 0.05)
            self.assertGreater(report['cw_snap_lock_intersection_mm3'], 0.01)
            self.assertFalse(report['elastic_snap_fit_verified'])
            self.assertFalse(report['physically_calibrated'])
            self.assertTrue((destination / 'joint_top.svg').is_file())
            self.assertTrue((destination / 'joint_fit.json').is_file())


if __name__ == '__main__':
    unittest.main()
