"""Real solid checks catch reversed pockets, false gaps, blocked rods and lost fusion."""

from dataclasses import replace
from math import cos, radians, sin
import unittest

import cadquery as cq

from windwall.generator import build_generator_assembly, build_magnet_pocket_coupon
from windwall.parameters import DEFAULT_PARAMETERS


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assembly = build_generator_assembly(DEFAULT_PARAMETERS)

    def test_two_magnet_rotors_share_the_m8_axis_and_base_is_fused(self):
        a = self.assembly
        self.assertEqual(a.magnet_rotor_count, 2)
        self.assertEqual(a.rotating_axis_diameter_mm, 8.0)
        self.assertTrue(a.upper_rotor_integrated_with_base)
        for shape in (a.base_module.shape, a.lower_rotor, a.upper_carrier):
            self.assertTrue(shape.val().isValid())
            self.assertEqual(len(shape.val().Solids()), 1)
            self.assertLess(shape.intersect(a.shaft).val().Volume(), 0.01)
        self.assertLess(a.upper_carrier.cut(a.base_module.shape).val().Volume(), 0.01)
        self.assertAlmostEqual(a.base_module.shape.val().BoundingBox().zmin, -13, places=5)

    def test_stator_between_rotors_has_real_positive_adjustable_gaps(self):
        a = self.assembly
        self.assertAlmostEqual(a.upper_air_gap_mm(), 1.5, places=5)
        self.assertAlmostEqual(a.lower_air_gap_mm(), 1.5, places=5)
        self.assertLess(a.rotor_stator_intersection_volume_mm3(), 0.01)
        p = DEFAULT_PARAMETERS
        # A larger lower gap moves the rear clamp down; extend the cup as well.
        changed = replace(p, generator=replace(p.generator, upper_air_gap_mm=2.25,
                          lower_air_gap_mm=3.0, base_height_mm=30))
        other = build_generator_assembly(changed)
        self.assertAlmostEqual(other.upper_air_gap_mm(), 2.25, places=5)
        self.assertAlmostEqual(other.lower_air_gap_mm(), 3.0, places=5)
        self.assertLess(other.rotor_stator_intersection_volume_mm3(), 0.01)
        self.assertAlmostEqual(other.spacer.val().BoundingBox().zlen, 19.25, places=5)

    def test_actual_stationary_and_rotating_hardware_envelopes_do_not_overlap(self):
        a = self.assembly
        for name, stationary in a.stationary.parts.items():
            self.assertTrue(stationary.val().isValid(), name)
            self.assertEqual(len(stationary.val().Solids()), 1, name)
            for moving in (a.base_module.shape, a.lower_rotor, a.shaft, a.spacer, *a.clamp_hardware.values()):
                self.assertLess(stationary.intersect(moving).val().Volume(), 0.01, name)
        self.assertAlmostEqual(a.stationary.coil_former.val().BoundingBox().zlen, 12)
        self.assertAlmostEqual(a.stationary.stator_cover.val().BoundingBox().zlen, 2)
        self.assertAlmostEqual(a.stationary.base.val().BoundingBox().zlen, 27)

    def test_magnet_pockets_face_stator_with_loaded_blind_floors(self):
        a = self.assembly
        # Independent first and opposite reference-hole centers, radius 44.5.
        for shape, opening, direction in ((a.upper_carrier,-13,1), (a.lower_rotor,-30,-1)):
            for index in range(18):
                x,y = 44.5*cos(radians(index*20)),44.5*sin(radians(index*20))
                self.assertFalse(shape.val().isInside((x,y,opening+direction)))
                self.assertTrue(shape.val().isInside((x,y,opening+direction*2.5)))
            for x in (-44.5,44.5):
                cavity = cq.Workplane('XY').center(x,0).circle(5.4999).extrude(1.9998).translate(
                    (0,0,opening+0.0001 if direction == 1 else opening-1.9999))
                self.assertLess(shape.intersect(cavity).val().Volume(), 0.01)
                self.assertTrue(shape.val().isInside((x,0,opening+direction*4.5)))
                self.assertTrue(shape.val().isInside((x+(7 if x>0 else -7),0,opening+direction*1.5)))
            self.assertAlmostEqual(shape.val().BoundingBox().xlen, 106, places=5)
            self.assertAlmostEqual(shape.val().BoundingBox().zlen, 10, places=5)

    def test_upper_captive_torque_nut_is_open_below_and_has_a_load_floor(self):
        a = self.assembly
        nut = a.clamp_hardware['upper_nut']
        self.assertLess(nut.intersect(a.base_module.shape).val().Volume(), 0.01)
        self.assertTrue(a.base_module.shape.val().isInside((6,0,-5)))
        self.assertEqual(a.base_module.nut_pocket_across_flats_mm, 13.3)
        self.assertGreater(a.spacer.val().Volume(), 0)

    def test_coupon_has_three_distinct_open_pockets_with_three_mm_floor(self):
        coupon = build_magnet_pocket_coupon(DEFAULT_PARAMETERS)
        self.assertTrue(coupon.val().isValid())
        self.assertEqual(len(coupon.val().Solids()), 1)
        self.assertAlmostEqual(coupon.val().BoundingBox().zlen,5)
        for x, radius in ((-18,5.4),(0,5.5),(18,5.6)):
            hole = cq.Workplane('XY').center(x,0).circle(radius-0.0001).extrude(1.9998).translate((0,0,3.0001))
            self.assertLess(coupon.intersect(hole).val().Volume(), 0.01)
            self.assertTrue(coupon.val().isInside((x,0,1.5)))

    def test_invalid_gaps_rims_floors_and_central_hardware_are_rejected(self):
        p = DEFAULT_PARAMETERS
        for updates in ({'upper_air_gap_mm':0}, {'lower_air_gap_mm':-1},
                        {'upper_air_gap_mm':float('nan')}, {'carrier_diameter_mm':104},
                        {'magnet_pocket_depth_mm':5}, {'magnet_pocket_count':2},
                        {'spacer_outer_diameter_mm':13}, {'bearing_outer_diameter_mm':14},
                        {'bearing_length_mm':12}, {'carrier_height_mm':8},
                        {'rib_width_mm':80}):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                build_generator_assembly(replace(p,generator=replace(p.generator,**updates)))


if __name__ == '__main__':
    unittest.main()
