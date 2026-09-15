"""Geometric capture, mounting and rotor-interface regressions for the upper 608."""

from dataclasses import replace
import json
import unittest

import cadquery as cq

from windwall.assembly import build_locked_rotor_assembly
from windwall.parameters import DEFAULT_PARAMETERS
from windwall.top_support import build_top_support, build_top_support_assembly, audit_top_support


class TopSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.support = build_top_support(DEFAULT_PARAMETERS)
        cls.rotor = build_locked_rotor_assembly(DEFAULT_PARAMETERS)

    def assert_clear(self, left, right):
        self.assertLess(left.intersect(right).val().Volume(), 1e-6)

    def test_plate_has_top_open_seat_and_closed_bottom_shoulder(self):
        s = self.support
        self.assertEqual(s.plate_size_mm, (80.0, 50.0, 12.0))
        box = s.shape.val().BoundingBox()
        self.assertAlmostEqual(box.xlen, 80)
        self.assertAlmostEqual(box.ylen, 50)
        self.assertAlmostEqual(box.zlen, 12)
        self.assertTrue(s.shape.val().isValid())
        self.assertEqual(len(s.shape.val().Solids()), 1)
        self.assertEqual(s.bearing_seat_diameter_mm, 22.2)
        self.assertEqual(s.bearing_seat_depth_mm, 7.2)
        self.assertAlmostEqual(s.bottom_shoulder_mm, 4.8)
        seat = cq.Workplane('XY').circle(11.1).extrude(20).translate((0, 0, 505.6))
        self.assert_clear(s.shape, seat)
        shoulder = (cq.Workplane('XY').circle(11).circle(4.4).extrude(4.8)
                    .translate((0, 0, 500.8)))
        self.assertAlmostEqual(s.shape.intersect(shoulder).val().Volume(),
                               shoulder.val().Volume(), places=5)

    def test_bearing_inserts_from_above_and_is_captured_by_plate_and_frame(self):
        s = self.support
        for lift in (0, 0.1, 1, 7.2, 20):
            self.assert_clear(s.shape, s.bearing.translate((0, 0, lift)))
        self.assertGreater(s.shape.intersect(s.bearing.translate((0, 0, -0.1))).val().Volume(), 1)
        self.assert_clear(s.wood_frame_reference, s.bearing.translate((0, 0, 0.19)))
        self.assertGreater(s.wood_frame_reference.intersect(
            s.bearing.translate((0, 0, 0.3))).val().Volume(), 1)
        for dx, dy in ((0.09, 0), (-0.09, 0), (0, 0.09), (0, -0.09)):
            self.assert_clear(s.shape, s.bearing.translate((dx, dy, 0)))
        for dx, dy in ((0.2, 0), (-0.2, 0), (0, 0.2), (0, -0.2)):
            self.assertGreater(s.shape.intersect(s.bearing.translate((dx, dy, 0))).val().Volume(), 0.01)

    def test_four_symmetric_bottom_countersinks_clear_nominal_4x40_screws(self):
        s = self.support
        self.assertEqual(set(s.wood_screw_axes), {(-30, -15), (-30, 15), (30, -15), (30, 15)})
        for axis, screw in zip(s.wood_screw_axes, s.wood_screws, strict=True):
            self.assert_clear(s.shape, screw)
            self.assertAlmostEqual(screw.val().BoundingBox().zlen, 40)
            bottom_access = (cq.Workplane('XY').center(*axis).circle(4.2).extrude(15.01)
                             .translate((0, 0, s.plate_bottom_z_mm - 15)))
            self.assert_clear(s.shape, bottom_access)
            above_sink = (cq.Workplane('XY').center(*axis).circle(4).extrude(0.1)
                          .translate((0, 0, s.plate_bottom_z_mm + 2.1)))
            self.assertGreater(s.shape.intersect(above_sink).val().Volume(), 1)

    def test_stationary_parts_clear_actual_rotor_top_and_clamping_hardware(self):
        s = self.support
        self.assertAlmostEqual(s.plate_bottom_z_mm - self.rotor.parts['top_nut'].val().BoundingBox().zmax, 2)
        self.assertAlmostEqual(s.plate_bottom_z_mm - self.rotor.parts['top'].val().BoundingBox().zmax,
                               10.8, places=5)
        for name in ('top', 'top_washer', 'top_nut'):
            for stationary in (s.shape, s.bearing, s.wood_frame_reference):
                for axial_shift in (-1, 0, 1):
                    self.assert_clear(stationary, self.rotor.parts[name].translate((0, 0, axial_shift)))

    def test_extended_shaft_engages_608_through_axial_float_without_printed_sleeve(self):
        s = self.support
        self.assertAlmostEqual(s.required_shaft_tip_z_mm, 513.8)
        self.assertAlmostEqual(s.required_shaft_extension_mm, 12.0)
        self.assertLess(self.rotor.parts['shaft'].val().BoundingBox().zmax,
                        s.bearing.val().BoundingBox().zmin)
        self.assertAlmostEqual(s.required_shaft_reference.val().BoundingBox().zmin,
                               self.rotor.parts['shaft'].val().BoundingBox().zmin, places=5)
        for shift in (-1, 0, 1):
            shaft = s.required_shaft_reference.translate((0, 0, shift))
            for stationary in (s.shape, s.bearing, s.wood_frame_reference):
                self.assert_clear(stationary, shaft)
            self.assertGreaterEqual(shaft.val().BoundingBox().zmax + 1e-6,
                                    s.bearing.val().BoundingBox().zmax)
        clearance = cq.Workplane('XY').circle(4.4).extrude(12).translate((0, 0, 500.8))
        self.assert_clear(s.shape, clearance)

    def test_assembly_keeps_reference_components_separate_and_named(self):
        assembly = build_top_support_assembly(DEFAULT_PARAMETERS)
        self.assertEqual(set(assembly.objects) - {assembly.name}, {
            'top_support_plate', 'bearing_608', 'upper_wood_frame_reference',
            'required_extended_m8_reference', 'wood_screw_1_reference',
            'wood_screw_2_reference', 'wood_screw_3_reference', 'wood_screw_4_reference'})

    def test_full_bearing_engagement_combines_seat_play_and_downward_shaft_float(self):
        s = self.support
        highest_bearing = s.bearing.translate((0, 0, 0.2))
        lowest_shaft = s.required_shaft_reference.translate((0, 0, -1))
        self.assertGreaterEqual(lowest_shaft.val().BoundingBox().zmax + 1e-6,
                                highest_bearing.val().BoundingBox().zmax)

    def test_audit_reports_real_capture_clearance_and_unintegrated_rod_extension(self):
        report = audit_top_support(DEFAULT_PARAMETERS)
        json.dumps(report, allow_nan=False)
        self.assertGreater(report['downward_capture_contact_mm3'], 1)
        self.assertGreater(report['upward_capture_contact_mm3'], 1)
        self.assertAlmostEqual(report['bearing_axial_play_mm'], 0.2)
        self.assertAlmostEqual(report['minimum_hardware_gap_mm'], 2)
        self.assertAlmostEqual(report['minimum_gap_at_axial_float_mm'], 1)
        self.assertLess(report['stationary_rotating_interference_mm3'], 1e-6)
        self.assertFalse(report['existing_rotor_shaft_reaches_bearing'])
        self.assertTrue(report['shaft_extension_integration_required'])
        self.assertFalse(report['primary_axial_support'])
        self.assertFalse(report['physically_calibrated'])

    def test_support_tracks_changed_stage_height_and_reports_rod_already_long_enough(self):
        p = replace(DEFAULT_PARAMETERS, rotor=replace(DEFAULT_PARAMETERS.rotor, stage_height_mm=75),
                    closure=replace(DEFAULT_PARAMETERS.closure, rod_projection_mm=20))
        s = build_top_support(p)
        self.assertAlmostEqual(s.plate_bottom_z_mm, 535.8)
        self.assertAlmostEqual(s.required_shaft_tip_z_mm, 548.8)
        self.assertEqual(s.required_shaft_extension_mm, 0)
        self.assertAlmostEqual(s.required_shaft_reference.val().BoundingBox().zmax, 553.8)

    def test_support_clears_top_when_recessed_clamp_is_below_module_face(self):
        p = replace(DEFAULT_PARAMETERS,
                    modules=replace(DEFAULT_PARAMETERS.modules, washer_seat_depth_mm=3),
                    manufacturing=replace(DEFAULT_PARAMETERS.manufacturing, nut_pocket_depth_mm=0.2),
                    generator=replace(DEFAULT_PARAMETERS.generator, clamp_washer_thickness_mm=0.2))
        s = build_top_support(p)
        rotor = build_locked_rotor_assembly(p)
        rotating_top = [rotor.parts[name] for name in ('top', 'top_washer', 'top_nut')]
        highest_face = max(shape.val().BoundingBox().zmax for shape in rotating_top)
        self.assertAlmostEqual(s.shape.val().BoundingBox().zmin - highest_face, 2, places=5)
        for shape in rotating_top:
            for shift in (0, 1):
                self.assert_clear(s.shape, shape.translate((0, 0, shift)))

    def test_rejects_impossible_capture_or_mismatched_shaft(self):
        variants = [
            replace(DEFAULT_PARAMETERS, bearings=replace(DEFAULT_PARAMETERS.bearings,
                                                        radial_housing_seat_depth_mm=10)),
            replace(DEFAULT_PARAMETERS, bearings=replace(DEFAULT_PARAMETERS.bearings,
                                                        radial_housing_seat_depth_mm=6.9)),
            replace(DEFAULT_PARAMETERS, shaft=replace(DEFAULT_PARAMETERS.shaft, nominal_diameter_mm=8.1)),
            replace(DEFAULT_PARAMETERS, rotor=replace(DEFAULT_PARAMETERS.rotor, stage_height_mm=float('nan'))),
        ]
        for p in variants:
            with self.subTest(parameters=p), self.assertRaises(ValueError):
                build_top_support(p)


if __name__ == '__main__':
    unittest.main()
