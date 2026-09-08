"""Export checks exercise actual coupon files and CQ-editor display objects."""

import unittest
from dataclasses import replace

import cadquery as cq

from scripts.preview_bayonet import export_coupon, preview_objects
from windwall.parameters import DEFAULT_PARAMETERS
from windwall.reference_mesh import analyze_binary_stl
from tests.support import temporary_build_directory


class CouponExportTests(unittest.TestCase):
    def test_exports_two_printable_manifold_parts_and_a_step_assembly(self):
        with temporary_build_directory() as destination:
            self.check_export(destination)

    def check_export(self, destination):
        report = export_coupon(DEFAULT_PARAMETERS, destination)
        for name in ("male", "female"):
            mesh = analyze_binary_stl(destination / f"bayonet_{name}.stl")
            self.assertEqual(mesh.component_count, 1)
            self.assertEqual(mesh.boundary_edge_count, 0)
            self.assertEqual(mesh.nonmanifold_edge_count, 0)
            self.assertEqual(mesh.degenerate_face_count, 0)
            self.assertAlmostEqual(mesh.minimum_xyz[2], 0, places=5)
            self.assertGreater(mesh.signed_volume, 0)
        assembly = cq.importers.importStep(str(destination / "bayonet_locked.step"))
        self.assertEqual(len(assembly.val().Solids()), 2)
        self.assertTrue((destination / "bayonet_top.svg").is_file())
        self.assertTrue((destination / "bayonet_fit.json").is_file())
        self.assertLess(report["maximum_motion_intersection_mm3"], 0.01)
        self.assertGreater(report["ccw_stop_intersection_mm3"], 0.05)
        self.assertFalse(report["physically_calibrated"])

    def test_preview_contains_pair_insertion_ghost_and_ccw_marker(self):
        objects = preview_objects(DEFAULT_PARAMETERS)
        self.assertEqual(len(objects), 4)
        for shape, name, options in objects:
            self.assertTrue(shape.val().isValid())
            self.assertTrue(name)
            self.assertIn("color", options)

    def test_fractional_travel_export_includes_the_exact_locked_endpoint(self):
        p = DEFAULT_PARAMETERS
        changed = replace(p, bayonet=replace(p.bayonet, insertion_offset_deg=18.25))
        with temporary_build_directory() as destination:
            report = export_coupon(changed, destination)
        self.assertAlmostEqual(report['motion_samples'][-1]['travel_deg'], 18.25)
        self.assertLess(report['maximum_motion_intersection_mm3'], 0.01)


if __name__ == "__main__":
    unittest.main()
