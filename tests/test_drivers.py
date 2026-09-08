"""Actual joint solids catch missing stops, undersized pilots and blocked motion."""

from dataclasses import replace
from math import cos, radians, sin
import unittest

import cadquery as cq

from windwall.drivers import (build_drivers, build_driver_pockets,
                              build_screw_pilots, build_joint_coupon)
from windwall.parameters import DEFAULT_PARAMETERS


class DriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coupon = build_joint_coupon(DEFAULT_PARAMETERS)

    def test_joint_uses_two_real_transition_drivers_and_two_screws(self):
        self.assertEqual(len(self.coupon.driver_centers), 2)
        self.assertEqual(len(self.coupon.screw_axes), 2)
        for builder in (build_drivers, build_driver_pockets, build_screw_pilots):
            shape = builder(DEFAULT_PARAMETERS).val()
            self.assertTrue(shape.isValid())
            self.assertEqual(len(shape.Solids()), 2)

    def test_both_print_parts_are_connected_valid_solids(self):
        for part in (self.coupon.male, self.coupon.female):
            self.assertTrue(part.val().isValid())
            self.assertEqual(len(part.val().Solids()), 1)

    def test_locked_joint_has_no_unplanned_interference(self):
        self.assertLess(self.coupon.unplanned_intersection_volume_mm3(), 0.01)

    def test_insertion_and_lock_sweep_are_clear(self):
        for travel in (0, 0.5, 3, 6, 9, 12, 15, 17.5, 18):
            with self.subTest(travel=travel):
                self.assertLess(self.coupon.male_at_travel(travel).intersect(
                    self.coupon.female).val().Volume(), 0.01)
        for lift in (1, 4, 8, 16, 24):
            self.assertLess(self.coupon.male_at_travel(0).translate((0,0,lift)).intersect(
                self.coupon.female).val().Volume(), 0.01)

    def test_driver_stops_block_ccw_and_release_cw(self):
        drivers = build_drivers(DEFAULT_PARAMETERS)
        self.assertGreater(drivers.rotate((0,0,0), (0,0,1), 0.5).intersect(
            self.coupon.female).val().Volume(), 0.05)
        self.assertLess(drivers.rotate((0,0,0), (0,0,1), -0.5).intersect(
            self.coupon.female).val().Volume(), 0.01)

    def test_shaft_and_radial_holes_are_actually_open(self):
        p = DEFAULT_PARAMETERS
        shaft = cq.Workplane('XY').circle(p.shaft.clearance_hole_diameter_mm/2-1e-5).extrude(40)
        for part in (self.coupon.male, self.coupon.female):
            self.assertLess(part.intersect(shaft).val().Volume(), 0.01)
        for axis in self.coupon.screw_axes:
            self.assertLess(self.coupon.male.intersect(axis.pilot).val().Volume(), 0.01)
            self.assertLess(self.coupon.female.intersect(axis.clearance).val().Volume(), 0.01)
            self.assertGreaterEqual(axis.minimum_pilot_edge_margin_mm, 3)
            # The complete screwdriver corridor outside the head must be clear.
            self.assertLess(self.coupon.male.union(self.coupon.female).intersect(
                axis.access).val().Volume(), 0.01)

    def test_parameter_changes_modify_pilot_volume_and_reject_thin_walls(self):
        p = DEFAULT_PARAMETERS
        changed = replace(p, manufacturing=replace(p.manufacturing, screw_pilot_diameter_mm=2.5))
        self.assertGreater(build_screw_pilots(changed).val().Volume(), build_screw_pilots(p).val().Volume())
        with self.assertRaises(ValueError):
            build_drivers(replace(p, drivers=replace(p.drivers, root_thickness_mm=2)))

    def test_loaded_material_surrounds_holes_away_from_radial_openings(self):
        p = DEFAULT_PARAMETERS
        for axis in self.coupon.screw_axes:
            angle = radians(axis.angle_deg)
            direction = cq.Vector(cos(angle), sin(angle), 0)
            # A 3 mm annulus around each bore must be material, including near
            # neighboring bayonet channels; the radial entry faces are exempt.
            for part, hole_radius, inner, outer in (
                    (self.coupon.female, p.drivers.screw_clearance_diameter_mm/2,
                     p.bayonet.hub_outer_diameter_mm/2+p.manufacturing.radial_clearance_mm+0.01,
                     axis.head_radius_mm-0.01),
                    (self.coupon.male, p.manufacturing.screw_pilot_diameter_mm/2,
                     axis.head_radius_mm-p.manufacturing.screw_length_mm+0.01,
                     p.bayonet.hub_outer_diameter_mm/2-0.01)):
                point = cq.Vector(inner*cos(angle), inner*sin(angle), axis.center_z_mm)
                shell = cq.Workplane(obj=cq.Solid.makeCylinder(hole_radius+3-1e-5,
                    outer-inner, point, direction)).cut(cq.Workplane(obj=cq.Solid.makeCylinder(
                        hole_radius+1e-5, outer-inner, point, direction)))
                bounds = cq.Workplane('XY').circle(outer).circle(inner).extrude(40)
                missing = shell.intersect(bounds).cut(part)
                self.assertLess(missing.val().Volume(), 0.01, f'wall missing at {axis.angle_deg}')

    def test_registration_records_twist_without_claiming_blade_continuity(self):
        self.assertEqual(self.coupon.registration['blade_top_phase_deg'], 60)
        self.assertEqual(self.coupon.registration['nominal_module_rotation_deg'], 0)
        self.assertFalse(self.coupon.registration['module_end_registration_verified'])

    def test_radial_screws_are_distinct_modulo_full_turns(self):
        p = DEFAULT_PARAMETERS
        with self.assertRaises(ValueError):
            build_screw_pilots(replace(p, drivers=replace(p.drivers, screw_angles_deg=(70,430))))
        changed = replace(p, drivers=replace(p.drivers, screw_angles_deg=(-290,540)))
        pilots = build_screw_pilots(changed)
        self.assertLess(pilots.cut(build_screw_pilots(p)).val().Volume(), 0.01)

    def test_reusable_joint_has_no_coupon_nut_pocket(self):
        from windwall.drivers import build_joint_interface
        interface = build_joint_interface(DEFAULT_PARAMETERS)
        top = interface.male.val().BoundingBox().zmax
        self.assertTrue(interface.male.val().isInside((6,0,top-0.1)))
        self.assertFalse(self.coupon.male.val().isInside((6,0,top-0.1)))

    def test_top_accessible_nut_pocket_has_configured_size_depth_and_floor(self):
        m = DEFAULT_PARAMETERS.manufacturing
        top = self.coupon.male.val().BoundingBox().zmax
        probe = (cq.Workplane('XY').polygon(6, (m.nut_pocket_across_flats_mm-1e-4)/cos(radians(30)))
                 .extrude(m.nut_pocket_depth_mm-1e-4)
                 .translate((0,0,top-m.nut_pocket_depth_mm+1e-4)))
        self.assertLess(self.coupon.male.intersect(probe).val().Volume(), 0.01)
        self.assertTrue(self.coupon.male.val().isInside((6,0,top-m.nut_pocket_depth_mm-0.01)))


if __name__ == '__main__':
    unittest.main()
