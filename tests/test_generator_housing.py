import unittest
from dataclasses import replace
from math import cos, pi, sin

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
        self.assertEqual(len(parts.cover_fasteners), 4)

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

    def test_four_m4_paths_align_with_separate_external_mount_axes(self):
        parts = self.parts
        self.assertEqual(len(parts.cover_fasteners), 4)
        self.assertEqual(len(parts.bottom_mount_tabs), 4)
        for fastener in parts.cover_fasteners:
            for reference in (fastener.screw, fastener.nut, fastener.driver_access):
                self.assertLess(parts.housing.intersect(reference).val().Volume(), 1e-6)
                self.assertLess(parts.cover.intersect(reference).val().Volume(), 1e-6)
            self.assertGreater((fastener.axis_xy_mm[0] ** 2 +
                                fastener.axis_xy_mm[1] ** 2) ** 0.5 - 4.3, 60)
        for fastener, tab in zip(parts.cover_fasteners, parts.bottom_mount_tabs, strict=True):
            fastener_radius = (fastener.axis_xy_mm[0] ** 2 + fastener.axis_xy_mm[1] ** 2) ** 0.5
            tab_radius = (tab.axis_xy_mm[0] ** 2 + tab.axis_xy_mm[1] ** 2) ** 0.5
            self.assertAlmostEqual(fastener.axis_xy_mm[0] / fastener_radius,
                                   tab.axis_xy_mm[0] / tab_radius, places=6)
            self.assertAlmostEqual(fastener.axis_xy_mm[1] / fastener_radius,
                                   tab.axis_xy_mm[1] / tab_radius, places=6)
            self.assertGreater(tab_radius - fastener_radius, 10)
            self.assertLess(parts.housing.intersect(tab.screw_access).val().Volume(), 1e-6)

    def test_each_cardinal_fastener_boss_is_fused_to_its_bottom_tab(self):
        parts = self.parts
        for fastener, tab in zip(parts.cover_fasteners, parts.bottom_mount_tabs, strict=True):
            x, y = fastener.axis_xy_mm
            boss_envelope = (cq.Workplane('XY').circle(6).extrude(5)
                             .translate((x, y, 0)))
            self.assertGreater(tab.shape.intersect(boss_envelope).val().Volume(), 400)

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

    def test_cover_underside_is_flat_for_support_free_printing(self):
        parts = self.parts
        nominal_bottom = parts.metadata['cover_bottom_z_mm']
        bounds = parts.cover.val().BoundingBox()
        self.assertAlmostEqual(bounds.zmin, nominal_bottom, places=6)

        # The central bearing shoulder and the surrounding diaphragm must both
        # begin on the same print-bed plane; only the required shaft bore is open.
        for radius in (15.0, 30.0, 58.0):
            below_bed = (cq.Workplane('XY').circle(0.5).extrude(0.1)
                         .translate((radius, 0, nominal_bottom - 0.1)))
            first_layer = (cq.Workplane('XY').circle(0.5).extrude(0.1)
                           .translate((radius, 0, nominal_bottom)))
            self.assertLess(parts.cover.intersect(below_bed).val().Volume(), 1e-6)
            self.assertGreater(parts.cover.intersect(first_layer).val().Volume(), 0.05)

    def test_cable_passage_is_open_and_explicitly_not_waterproof(self):
        parts = self.parts
        for shape in (parts.housing, parts.coil_cassette):
            self.assertLess(shape.intersect(parts.cable_passage).val().Volume(), 1e-6)
        self.assertFalse(parts.metadata['waterproof'])
        self.assertEqual(parts.metadata['role'], 'stationary')
        self.assertGreaterEqual(parts.metadata['rotating_keepout_diameter_mm'], 120)

    def test_cassette_has_eighteen_open_serpentine_guide_islands(self):
        parts = self.parts
        self.assertEqual(parts.metadata.get('serpentine_guide_count'), 18)
        self.assertEqual(parts.metadata.get('serpentine_guide_pitch_radius_mm'), 44.5)
        for index in range(18):
            angle = 2 * pi * index / 18
            guide_probe = (cq.Workplane('XY').circle(1).extrude(1)
                           .translate((44.5 * cos(angle), 44.5 * sin(angle), 32)))
            wire_angle = angle + pi / 18
            wire_space = (cq.Workplane('XY').circle(1).extrude(1)
                          .translate((44.5 * cos(wire_angle),
                                      44.5 * sin(wire_angle), 32)))
            self.assertGreater(parts.coil_cassette.intersect(guide_probe).val().Volume(), 2)
            self.assertLess(parts.coil_cassette.intersect(wire_space).val().Volume(), 1e-6)
        self.assertLess(parts.coil_cassette.intersect(parts.winding_volume).val().Volume(), 1e-6)

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

    def test_cassette_height_keeps_cable_boss_below_cover(self):
        # Boss centre is 6 mm above cassette bottom, radius 6 mm; the cover
        # starts 0.15 mm above cassette top, giving a minimum height of 11.85.
        for height in (10.0, 11.849):
            p = replace(DEFAULT_PARAMETERS, generator=replace(
                DEFAULT_PARAMETERS.generator, coil_former_height_mm=height))
            with self.subTest(height=height), self.assertRaisesRegex(ValueError, 'cable boss'):
                build_generator_housing(p)
        p = replace(DEFAULT_PARAMETERS, generator=replace(
            DEFAULT_PARAMETERS.generator, coil_former_height_mm=11.85))
        parts = build_generator_housing(p)
        self.assertAlmostEqual(parts.metadata['cover_bottom_z_mm'], 39.0)
        self.assertLess(parts.housing.intersect(parts.cover).val().Volume(), 1e-6)

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
