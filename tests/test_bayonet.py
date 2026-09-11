"""Real solid checks catch reversed tracks, missing stops and tight fit envelopes."""

from dataclasses import replace
from math import cos, radians, sin
import unittest

import cadquery as cq

from windwall.bayonet import (
    build_bayonet_coupon, build_female_bayonet, build_male_bayonet, locked_angle_deg,
)
from windwall.parameters import DEFAULT_PARAMETERS


class BayonetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coupon = build_bayonet_coupon(DEFAULT_PARAMETERS)

    def test_locking_motion_is_counterclockwise_and_ends_at_zero(self):
        self.assertEqual(locked_angle_deg(DEFAULT_PARAMETERS), 18.0)
        male = self.coupon.male_at_travel(0).val()
        angle = radians(-18)
        self.assertTrue(male.isInside((20*cos(angle), 20*sin(angle), 5.5)))
        self.assertFalse(male.isInside((20, 0, 5.5)))
        self.assertTrue(self.coupon.male_at_travel(18).val().isInside((20, 0, 5.5)))

    def test_coupon_is_valid_and_contains_exactly_three_physical_lugs(self):
        for part in (self.coupon.male, self.coupon.female):
            self.assertTrue(part.val().isValid())
            self.assertEqual(len(part.val().Solids()), 1)
        self.assertEqual(self.coupon.lug_centers_deg, (0.0, 120.0, 240.0))
        shell = cq.Workplane("XY").circle(23).circle(19).extrude(10)
        self.assertEqual(len(self.coupon.male.intersect(shell).val().Solids()), 3)

    def assert_only_snap_region_intersects(self, male):
        collision = male.intersect(self.coupon.female)
        if collision.val().Volume() >= 0.01:
            snap_region = (cq.Workplane('XY').circle(22).circle(20.4)
                           .extrude(1.9).translate((0,0,3.9)))
            self.assertLess(collision.cut(snap_region).val().Volume(), 0.01)

    def test_axial_insertion_is_clear_and_zero_rise_locking_only_meets_snap_features(self):
        for lift in range(13):
            with self.subTest(insertion_lift_mm=lift):
                inserted = self.coupon.male_at_travel(0).translate((0, 0, lift))
                self.assertLess(inserted.intersect(self.coupon.female).val().Volume(), 0.01)
        for travel in range(19):
            with self.subTest(travel_deg=travel):
                male = self.coupon.male_at_travel(travel)
                self.assert_only_snap_region_intersects(male)
                self.assertAlmostEqual(male.val().BoundingBox().zmin
                    - self.coupon.male_at_travel(0).val().BoundingBox().zmin, 0)

    def test_locked_coupon_clearance_is_geometric_and_excludes_intentional_stop(self):
        self.assertLess(self.coupon.locked_intersection_volume_mm3(), 0.01)
        self.assertAlmostEqual(self.coupon.male.val().distance(self.coupon.female.val()), 0, places=5)
        self.assertGreaterEqual(self.coupon.minimum_locked_clearance_mm(), 0.20)

    def test_counterclockwise_stop_and_clockwise_snap_block_locked_torque(self):
        clockwise = self.coupon.male.rotate((0, 0, 0), (0, 0, 1), -0.5)
        ccw = self.coupon.male.rotate((0, 0, 0), (0, 0, 1), 0.5)
        self.assertGreater(clockwise.intersect(self.coupon.female).val().Volume(), 0.01)
        collision = ccw.intersect(self.coupon.female)
        self.assertGreater(collision.val().Volume(), 0.05)
        # Independently bounded stop neighborhoods: no bore/roof/floor collision.
        stops = cq.Workplane("XY")
        for angle in (0, 120, 240):
            box = (cq.Workplane("XY").box(7, 4, 5, centered=False)
                   .translate((18.7, 4, 3)).rotate((0,0,0), (0,0,1), angle))
            stops = stops.union(box)
        self.assertLess(collision.cut(stops).val().Volume(), 0.01)

    def test_locked_lugs_cannot_be_pulled_out_axially(self):
        self.assertGreater(self.coupon.male.translate((0, 0, 2)).intersect(
            self.coupon.female).val().Volume(), 1)

    def test_track_floor_retains_the_configured_loaded_wall(self):
        point = (20*cos(radians(-36)), 20*sin(radians(-36)), 2.99)
        self.assertTrue(self.coupon.female.val().isInside(point))

    def test_added_seating_headroom_preserves_three_mm_roof_above_locked_lug(self):
        roof = (cq.Workplane('XY').box(.2,.5,2.9998,centered=(True,True,False))
                .translate((20,0,7.7001)))
        self.assertLess(roof.cut(self.coupon.female).val().Volume(), 1e-6)

    def test_lower_circular_rail_is_continuous_beneath_every_entry_window(self):
        for angle_deg in range(0,360,10):
            point = (20*cos(radians(angle_deg)),20*sin(radians(angle_deg)),2.9)
            self.assertTrue(self.coupon.female.val().isInside(point),angle_deg)

    def test_fractional_motion_only_meets_the_permanent_snap_features(self):
        for travel in (0.5, 4.5, 8.5, 12.5, 17.5):
            with self.subTest(travel=travel):
                self.assert_only_snap_region_intersects(self.coupon.male_at_travel(travel))

    def test_m8_shaft_passes_through_both_parts(self):
        shaft = cq.Workplane("XY").circle(4.4-1e-5).extrude(30)
        for part in (self.coupon.male, self.coupon.female):
            self.assertLess(part.intersect(shaft).val().Volume(), 0.01)

    def test_male_center_is_open_except_for_small_shaft_guide_and_spokes(self):
        male = self.coupon.male.val()
        self.assertTrue(male.isInside((5.2, 0, 6)))
        self.assertFalse(male.isInside((10, 5, 6)))

    def test_locked_snap_prevents_clockwise_release(self):
        clockwise_release = self.coupon.male.rotate((0,0,0),(0,0,1),-0.5)
        self.assertGreater(clockwise_release.intersect(self.coupon.female).val().Volume(), 0.01)

    def test_running_gap_excludes_snap_pawl_faces_without_removing_the_lock(self):
        self.assertGreaterEqual(self.coupon.minimum_locked_clearance_mm(), 0.20)
        reverse = self.coupon.male.rotate((0,0,0),(0,0,1),-0.5)
        self.assertGreater(reverse.intersect(self.coupon.female).val().Volume(), 0.01)
        self.assertLess(self.coupon.locked_intersection_volume_mm3(), 0.01)

    def test_motion_rejects_travel_outside_the_track(self):
        for travel in (-1, 19, float("nan")):
            with self.subTest(travel=travel), self.assertRaises(ValueError):
                self.coupon.male_at_travel(travel)

    def test_custom_clearances_change_actual_receiver_geometry(self):
        parameters = replace(DEFAULT_PARAMETERS, manufacturing=replace(
            DEFAULT_PARAMETERS.manufacturing, radial_clearance_mm=0.45, axial_clearance_mm=0.40))
        loose = build_bayonet_coupon(parameters)
        bore_probe = (17.35*cos(radians(60)), 17.35*sin(radians(60)), 1)
        self.assertTrue(self.coupon.female.val().isInside(bore_probe))
        self.assertFalse(loose.female.val().isInside(bore_probe))
        self.assertGreaterEqual(loose.minimum_locked_clearance_mm(), 0.35)

    def test_builders_accept_a_common_z_plane(self):
        for builder, original in ((build_male_bayonet, self.coupon.male),
                                  (build_female_bayonet, self.coupon.female)):
            moved = builder(DEFAULT_PARAMETERS, z_plane_mm=70)
            self.assertAlmostEqual(moved.val().BoundingBox().zmin,
                                   original.val().BoundingBox().zmin + 70)

    def test_invalid_dimensions_are_rejected_before_cad_construction(self):
        for change in ({"lug_count": 4}, {"insertion_offset_deg": -18},
                       {"root_fillet_mm": 0}, {"ramp_rise_mm": float("nan")}):
            parameters = replace(DEFAULT_PARAMETERS, bayonet=replace(DEFAULT_PARAMETERS.bayonet, **change))
            with self.subTest(change=change), self.assertRaises(ValueError):
                build_bayonet_coupon(parameters)
        for clearance in (0, -0.1, float("nan")):
            parameters = replace(DEFAULT_PARAMETERS, manufacturing=replace(
                DEFAULT_PARAMETERS.manufacturing, radial_clearance_mm=clearance))
            with self.subTest(clearance=clearance), self.assertRaises(ValueError):
                build_bayonet_coupon(parameters)


if __name__ == "__main__":
    unittest.main()
