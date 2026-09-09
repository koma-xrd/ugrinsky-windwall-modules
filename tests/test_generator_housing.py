import unittest
from dataclasses import replace

import cadquery as cq

from windwall.generator_housing import (audit_coil_retention, build_coil_cassette,
                                       build_coil_fit_coupon, build_generator_cover,
                                       build_generator_housing)
from windwall.parameters import DEFAULT_PARAMETERS
from windwall.reference_mesh import analyze_binary_stl
from tests.support import temporary_build_directory


class GeneratorHousingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = build_generator_housing(DEFAULT_PARAMETERS)

    def test_coil_is_supported_centered_keyed_and_cover_retained(self):
        parts = self.parts
        audit = audit_coil_retention(parts)
        self.assertGreater(audit['downward_support_contact_mm3'], 1)
        self.assertGreaterEqual(audit['radial_clearance_mm'], 0.30)
        self.assertLessEqual(audit['radial_clearance_mm'], 0.40)
        self.assertGreater(audit['anti_rotation_contact_mm3'], 1)
        self.assertLessEqual(audit['upward_cover_clearance_mm'], 0.20)
        self.assertEqual(len(parts.bottom_mount_tabs), 4)
        self.assertEqual(len(parts.cover_fasteners), 6)

    def test_printable_parts_are_single_solids_and_assemble_without_interference(self):
        parts = self.parts
        for shape in (parts.housing, parts.coil_cassette, parts.cover):
            self.assertTrue(shape.val().isValid())
            self.assertEqual(len(shape.val().Solids()), 1)
        for left, right in ((parts.housing, parts.coil_cassette),
                            (parts.housing, parts.cover),
                            (parts.coil_cassette, parts.cover)):
            self.assertLess(left.intersect(right).val().Volume(), 1e-6)
        for solid in (parts.housing, parts.coil_cassette, parts.cover):
            self.assertLess(solid.intersect(parts.winding_volume).val().Volume(), 1e-6)

    def test_closed_floor_clear_rotor_envelope_and_top_removal(self):
        parts = self.parts
        rotor_space = cq.Workplane('XY').circle(60).extrude(20).translate((0, 0, 4))
        floor_probe = cq.Workplane('XY').circle(59).extrude(2).translate((0, 0, 0.5))
        self.assertLess(parts.housing.intersect(rotor_space).val().Volume(), 1e-6)
        self.assertAlmostEqual(parts.housing.intersect(floor_probe).val().Volume(),
                               floor_probe.val().Volume(), places=5)
        for lift in (0.1, 6, 12, 20):
            self.assertLess(parts.housing.intersect(
                parts.coil_cassette.translate((0, 0, lift))).val().Volume(), 1e-6)

    def test_radial_pilot_and_both_key_flanks_stop_motion(self):
        parts = self.parts
        for x, y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            self.assertLess(parts.housing.intersect(parts.coil_cassette.translate(
                (0.30 * x, 0.30 * y, 0))).val().Volume(), 1e-6)
            self.assertGreater(parts.housing.intersect(parts.coil_cassette.translate(
                (0.45 * x, 0.45 * y, 0))).val().Volume(), 1)
        for angle in (-1, 1):
            self.assertGreater(parts.housing.intersect(parts.coil_cassette.rotate(
                (0, 0, 0), (0, 0, 1), angle)).val().Volume(), 1)
        self.assertLess(parts.cover.intersect(parts.coil_cassette.translate(
            (0, 0, 0.14))).val().Volume(), 1e-6)
        self.assertGreater(parts.cover.intersect(parts.coil_cassette.translate(
            (0, 0, 0.25))).val().Volume(), 1)

    def test_six_m4_paths_nut_pockets_and_external_mount_access_are_clear(self):
        parts = self.parts
        for fastener in parts.cover_fasteners:
            for reference in (fastener.screw, fastener.nut, fastener.driver_access):
                self.assertLess(parts.housing.intersect(reference).val().Volume(), 1e-6)
                self.assertLess(parts.cover.intersect(reference).val().Volume(), 1e-6)
            self.assertGreater((fastener.axis_xy_mm[0] ** 2 +
                                fastener.axis_xy_mm[1] ** 2) ** 0.5 - 4.3, 60)
        for tab in parts.bottom_mount_tabs:
            self.assertLess(parts.housing.intersect(tab.screw_access).val().Volume(), 1e-6)

    def test_bearing_seat_is_top_open_with_a_load_shoulder(self):
        parts = self.parts
        seat_z = parts.metadata['bearing_seat_floor_z_mm']
        seat = (cq.Workplane('XY').circle(21.1).extrude(11.2)
                .translate((0, 0, seat_z)))
        self.assertLess(parts.cover.intersect(seat).val().Volume(), 1e-6)
        washer = parts.housing_washer
        self.assertLess(parts.cover.intersect(washer).val().Volume(), 1e-6)
        self.assertGreater(parts.cover.intersect(
            washer.translate((0, 0, -0.1))).val().Volume(), 1)
        shaft = cq.Workplane('XY').circle(4.4).extrude(30).translate((0, 0, 27))
        self.assertLess(parts.cover.intersect(shaft).val().Volume(), 1e-6)

    def test_cable_passage_is_open_and_explicitly_not_waterproof(self):
        parts = self.parts
        for shape in (parts.housing, parts.coil_cassette):
            self.assertLess(shape.intersect(parts.cable_passage).val().Volume(), 1e-6)
        self.assertFalse(parts.metadata['waterproof'])
        self.assertEqual(parts.metadata['role'], 'stationary')
        self.assertGreaterEqual(parts.metadata['rotating_keepout_diameter_mm'], 120)

    def test_public_builders_and_segment_coupon(self):
        for shape in (build_coil_cassette(DEFAULT_PARAMETERS),
                      build_generator_cover(DEFAULT_PARAMETERS)):
            self.assertTrue(shape.val().isValid())
            self.assertEqual(len(shape.val().Solids()), 1)
        coupon = build_coil_fit_coupon(DEFAULT_PARAMETERS)
        self.assertEqual(coupon.radial_clearances_mm, (0.30, 0.35, 0.40))
        self.assertTrue(coupon.shape.val().isValid())
        self.assertEqual(len(coupon.shape.val().Solids()), 1)

    def test_rejects_cassette_that_cannot_fit_shell(self):
        p = replace(DEFAULT_PARAMETERS, generator=replace(
            DEFAULT_PARAMETERS.generator, coil_former_diameter_mm=130))
        with self.assertRaisesRegex(ValueError, 'cassette'):
            build_generator_housing(p)

    def test_exported_print_bodies_are_closed_manifold_meshes(self):
        p = DEFAULT_PARAMETERS
        shapes = (self.parts.housing, self.parts.coil_cassette, self.parts.cover,
                  build_coil_fit_coupon(p).shape)
        with temporary_build_directory() as destination:
            for index, shape in enumerate(shapes):
                path = destination / f'housing-part-{index}.stl'
                cq.exporters.export(shape, str(path),
                                    tolerance=p.manufacturing.export_linear_tolerance_mm,
                                    angularTolerance=p.manufacturing.export_angular_tolerance_rad)
                mesh = analyze_binary_stl(path)
                self.assertEqual(mesh.component_count, 1)
                self.assertEqual(mesh.boundary_edge_count, 0)
                self.assertEqual(mesh.nonmanifold_edge_count, 0)
                self.assertEqual(mesh.degenerate_face_count, 0)
                self.assertGreater(mesh.signed_volume, 0)


if __name__ == '__main__':
    unittest.main()
