"""Compact permanent-joint coupons preserve the approved open-spoke geometry."""

from dataclasses import replace
from math import cos, radians
import unittest

import cadquery as cq

from windwall.drivers import build_joint_coupon, build_joint_interface
from windwall.parameters import DEFAULT_PARAMETERS


class JointCouponTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coupon = build_joint_coupon(DEFAULT_PARAMETERS)
        cls.interface = build_joint_interface(DEFAULT_PARAMETERS)

    def test_print_pair_is_connected_and_locked_without_overlap(self):
        for part in (self.coupon.male, self.coupon.female):
            self.assertTrue(part.val().isValid())
            self.assertEqual(len(part.val().Solids()), 1)
        self.assertLess(self.coupon.unplanned_intersection_volume_mm3(), 0.01)
        self.assertEqual(self.coupon.driver_centers, ())
        self.assertEqual(self.coupon.screw_axes, ())

    def test_both_permanent_stops_resist_rotation_and_axial_pull(self):
        for angle in (-0.5, 0.5):
            rotated = self.coupon.male.rotate((0,0,0),(0,0,1),angle)
            self.assertGreater(rotated.intersect(self.coupon.female).val().Volume(), 0.01)
        self.assertGreater(self.coupon.male.translate((0,0,2)).intersect(self.coupon.female).val().Volume(), 1)

    def test_shaft_and_axial_insertion_remain_open(self):
        shaft = cq.Workplane('XY').circle(4.3999).extrude(40)
        for part in (self.coupon.male, self.coupon.female):
            self.assertLess(part.intersect(shaft).val().Volume(), 0.01)
        for lift in (1, 4, 8, 16, 24):
            inserted = self.coupon.male_at_travel(0).translate((0,0,lift))
            self.assertLess(inserted.intersect(self.coupon.female).val().Volume(), 0.01)

    def test_registration_reports_the_successive_sixty_degree_blade_phase(self):
        self.assertEqual(self.coupon.registration['blade_top_phase_deg'], 60)
        self.assertEqual(self.coupon.registration['joint_locked_phase_deg'], 60)
        self.assertTrue(self.coupon.registration['module_end_registration_verified'])

    def test_coupon_exposes_two_plain_blade_samples_and_raised_locking_clearance(self):
        self.assertEqual(self.coupon.blade_sample_count, 2)
        self.assertFalse(hasattr(self.coupon, 'tongue_count'))
        self.assertFalse(hasattr(self.coupon, 'groove_count'))
        outer = cq.Workplane('XY').circle(62).circle(26).extrude(30)
        for part in (self.coupon.male, self.coupon.female):
            self.assertGreater(part.intersect(outer).val().Volume(), 10)
        for travel in (0, .5, 6, 12, 17.5, 18):
            moving = self.coupon.male_at_travel(travel).translate((0,0,1))
            snap = cq.Workplane('XY').circle(22).circle(20.4).extrude(3).translate((0,0,3.9))
            collision = moving.intersect(self.coupon.female).val()
            if collision.Volume() >= .01:
                self.assertLess(collision.cut(snap.val()).Volume(), .01)

    def test_calibration_recess_is_4_point_2_mm_deep_and_has_no_solid_hex_floor(self):
        self.assertEqual(getattr(self.coupon, 'nut_calibration_recess_depth_mm', None), 4.2)
        self.assertIsNone(self.interface.nut_calibration_recess_depth_mm)
        male = self.coupon.male
        self.assertAlmostEqual(male.val().BoundingBox().zmax, 17.7)
        probe = (cq.Workplane('XY').polygon(6, 13.2999/cos(radians(30)))
                 .extrude(4.1999).translate((0,0,9.5001)))
        self.assertLess(male.intersect(probe).val().Volume(), 0.01)
        self.assertTrue(male.val().isInside((5.2,0,9.49)))
        self.assertFalse(male.val().isInside((5.2,0,9.51)))
        self.assertFalse(male.val().isInside((0,6.5,9.49)))
        self.assertTrue(self.interface.male.val().isInside((5.2,0,13.6)))

    def test_coupon_rejects_invalid_calibration_dimensions(self):
        p = DEFAULT_PARAMETERS
        for changes in ({'nut_pocket_depth_mm': 0}, {'nut_pocket_across_flats_mm': float('nan')}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                build_joint_coupon(replace(p, manufacturing=replace(p.manufacturing, **changes)))


if __name__ == '__main__':
    unittest.main()
