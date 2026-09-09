"""Solid regression checks for the enclosed generator and its axial load path."""

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

    def test_lower_rotor_is_wholly_inside_housing_below_stationary_coil(self):
        a = self.assembly
        self.assertTrue(hasattr(a, 'housing'), 'V5 must contain a real stationary housing')
        housing, lower, coil = (shape.val().BoundingBox() for shape in
                                (a.housing, a.lower_rotor, a.coil_cassette))
        self.assertLess(lower.zmax, coil.zmin)
        self.assertLess(housing.zmin, lower.zmin)
        self.assertGreater(housing.zmax, lower.zmax)
        self.assertLess(lower.xlen, 121)
        self.assertLess(a.housing.intersect(a.lower_rotor).val().Volume(), 0.01)
        self.assertGreater(lower.zmin - housing.zmin, 3)
        self.assertAlmostEqual(a.shaft.val().BoundingBox().zmin, -42, places=5)
        self.assertGreater(a.shaft.val().BoundingBox().zmin - housing.zmin, 3)

    def test_complete_ownership_and_all_stationary_clearances(self):
        a = self.assembly
        self.assertTrue(hasattr(a, 'rotating_parts'), 'V5 must declare motion ownership')
        self.assertTrue(set(a.rotating_parts).isdisjoint(a.stationary_parts))
        self.assertTrue({'base', 'lower_magnet_rotor', 'shaft', 'spacer',
                         'upper_nut', 'lower_nut', '51105_shaft_washer'} <= set(a.rotating_parts))
        self.assertTrue({'housing', 'coil_cassette', 'cover', 'winding_volume',
                         '51105_housing_washer'} <= set(a.stationary_parts))
        for name, stationary in a.stationary_parts.items():
            for moving_name, moving in a.rotating_parts.items():
                self.assertLess(stationary.intersect(moving).val().Volume(), 0.01,
                                f'{moving_name}/{name}')
        report = a.collision_report()
        self.assertEqual(len(report['rotating_stationary_pairs_mm3']),
                         len(a.rotating_parts) * len(a.stationary_parts))
        self.assertLess(report['unintended_intersection_mm3'], 0.01)

    def test_magnetic_gaps_are_measured_from_magnets_to_active_winding_faces(self):
        a = self.assembly
        self.assertTrue(hasattr(a, 'air_gap_report'), 'V5 must measure the active winding faces')
        report = a.air_gap_report()
        self.assertAlmostEqual(report['upper_air_gap_mm'], 1.5, places=5)
        self.assertAlmostEqual(report['lower_air_gap_mm'], 1.5, places=5)
        self.assertAlmostEqual(a.magnets['upper'].val().BoundingBox().zmin, -13, places=5)
        self.assertAlmostEqual(a.magnets['lower'].val().BoundingBox().zmax, -27, places=5)
        self.assertAlmostEqual(a.winding_volume.val().BoundingBox().zmin, -25.5, places=5)
        self.assertAlmostEqual(a.winding_volume.val().BoundingBox().zmax, -14.5, places=5)
        self.assertAlmostEqual(a.coil_cassette.val().BoundingBox().zmin -
                               a.lower_rotor.val().BoundingBox().zmax, 0.5, places=5)
        p = DEFAULT_PARAMETERS
        changed = replace(p, generator=replace(p.generator, upper_air_gap_mm=2.25,
                                                lower_air_gap_mm=3.0))
        other = build_generator_assembly(changed)
        self.assertAlmostEqual(other.air_gap_report()['upper_air_gap_mm'], 2.25, places=5)
        self.assertAlmostEqual(other.air_gap_report()['lower_air_gap_mm'], 3.0, places=5)
        self.assertLess(other.collision_report()['unintended_intersection_mm3'], 0.01)

    def test_rotation_samples_keep_the_stationary_enclosure_clear(self):
        a = self.assembly
        for angle in (45, 135, 225, 315):
            moving = {name: shape.rotate((0, 0, 0), (0, 0, 1), angle)
                      for name, shape in a.rotating_parts.items()}
            self.assertLess(a.collision_report(moving)['unintended_intersection_mm3'], 0.01)

    def test_bearing_support_penetration_is_not_exempt_from_collision_report(self):
        a = self.assembly
        moving = dict(a.rotating_parts, base=a.base_module.shape.translate((0, 0, -0.2)))
        report = a.collision_report(moving)
        self.assertGreater(report['intended_bearing_contacts']['base/51105_shaft_washer']['intersection_mm3'], 0.05)
        self.assertGreater(report['unintended_intersection_mm3'], 0.05)

    def test_supplied_shaft_washer_controls_support_penetration_and_rolling_contact(self):
        a = self.assembly
        moving = dict(a.rotating_parts)
        moving['51105_shaft_washer'] = moving['51105_shaft_washer'].translate((0, 0, 0.2))
        report = a.collision_report(moving)
        contacts = report['intended_bearing_contacts']
        actual_penetration = a.base_module.shape.intersect(moving['51105_shaft_washer']).val().Volume()
        self.assertAlmostEqual(actual_penetration, 178.9137016, places=4)
        with self.subTest(contact='Base support penetration'):
            self.assertAlmostEqual(contacts['base/51105_shaft_washer']['intersection_mm3'],
                                   actual_penetration, places=5)
        with self.subTest(contact='Rolling envelope gap'):
            self.assertAlmostEqual(contacts['51105_rolling_envelope/51105_shaft_washer']['distance_mm'],
                                   0.2, places=5)
        with self.subTest(contact='Aggregate collision'):
            self.assertAlmostEqual(report['unintended_intersection_mm3'], actual_penetration, places=5)

    def test_51105_pilot_and_both_axial_support_surfaces_carry_load(self):
        a = self.assembly
        self.assertTrue(hasattr(a, 'bearings'), 'V5 requires a placed 51105 reference')
        bearing = a.bearings['51105']
        self.assertEqual(bearing.nominal_dimensions_mm, (25, 42, 11))
        self.assertAlmostEqual(a.base_module.bearing_seat_diameter_mm, 42.2)
        self.assertAlmostEqual(a.base_module.bearing_pilot_diameter_mm, 24.8)
        pilot = cq.Workplane('XY').circle(12.3999).circle(8).extrude(8).translate((0, 0, -12.5))
        self.assertLess(pilot.cut(a.base_module.shape).val().Volume(), 0.01)
        for supported, support in ((bearing.parts['housing_washer'], a.cover),
                                   (a.base_module.shape, bearing.parts['shaft_washer'])):
            self.assertLess(supported.intersect(support).val().Volume(), 0.01)
            self.assertAlmostEqual(supported.val().distance(support.val()), 0, places=5)
            self.assertGreater(supported.translate((0, 0, -0.05)).intersect(support).val().Volume(), 0.05)
        contacts = a.collision_report()['intended_bearing_contacts']
        self.assertEqual(set(contacts), {'cover/51105_housing_washer',
                                        'base/51105_shaft_washer',
                                        '51105_housing_washer/51105_rolling_envelope',
                                        '51105_rolling_envelope/51105_shaft_washer'})
        self.assertTrue(all(item['distance_mm'] < 0.0001 for item in contacts.values()))

    def test_rotors_are_connected_and_m8_shaft_and_raised_hex_remain_open(self):
        a = self.assembly
        self.assertEqual(a.magnet_rotor_count, 2)
        self.assertTrue(a.upper_rotor_integrated_with_base)
        self.assertEqual(a.rotating_axis_diameter_mm, 8)
        for shape in (a.base_module.shape, a.lower_rotor, a.upper_carrier):
            self.assertTrue(shape.val().isValid())
            self.assertEqual(len(shape.val().Solids()), 1)
            self.assertLess(shape.intersect(a.shaft).val().Volume(), 0.01)
        for nut_name, body in (('upper_nut', a.base_module.shape), ('lower_nut', a.lower_rotor)):
            nut = a.clamp_hardware[nut_name]
            self.assertLess(nut.intersect(body).val().Volume(), 0.01)
            self.assertGreater(nut.translate((0, 0, 0.05)).intersect(body).val().Volume(), 0.05)
            for drop in (0, 1, 4, 10):
                self.assertLess(nut.translate((0, 0, -drop)).intersect(body).val().Volume(), 0.01)
        self.assertGreater(a.base_module.nut_pocket_bottom_z_mm,
                           a.base_module.bearing_seat_bottom_z_mm)
        self.assertEqual(a.lower_rotor_nut_pocket_across_flats_mm, 13.3)

    def test_magnet_pockets_face_stator_with_loaded_blind_floors(self):
        for shape, opening, direction in ((self.assembly.upper_carrier, -13, 1),
                                           (self.assembly.lower_rotor, -27, -1)):
            for index in range(18):
                x, y = 44.5*cos(radians(index*20)), 44.5*sin(radians(index*20))
                self.assertFalse(shape.val().isInside((x, y, opening+direction)))
                self.assertTrue(shape.val().isInside((x, y, opening+direction*2.5)))
            self.assertAlmostEqual(shape.val().BoundingBox().xlen, 106, places=5)
        for magnets in self.assembly.magnets.values():
            self.assertEqual(len(magnets.val().Solids()), 18)

    def test_coupon_has_three_distinct_open_pockets_with_three_mm_floor(self):
        coupon = build_magnet_pocket_coupon(DEFAULT_PARAMETERS)
        self.assertTrue(coupon.val().isValid())
        self.assertEqual(len(coupon.val().Solids()), 1)
        for x, radius in ((-18, 5.4), (0, 5.5), (18, 5.6)):
            hole = cq.Workplane('XY').center(x, 0).circle(radius-0.0001).extrude(1.9998).translate((0, 0, 3.0001))
            self.assertLess(coupon.intersect(hole).val().Volume(), 0.01)
            self.assertTrue(coupon.val().isInside((x, 0, 1.5)))

    def test_invalid_gaps_rims_floors_and_central_hardware_are_rejected(self):
        p = DEFAULT_PARAMETERS
        for updates in ({'upper_air_gap_mm': 0}, {'lower_air_gap_mm': -1},
                        {'upper_air_gap_mm': float('nan')}, {'carrier_diameter_mm': 104},
                        {'magnet_pocket_depth_mm': 5}, {'magnet_pocket_count': 2},
                        {'spacer_outer_diameter_mm': 25}, {'lower_air_gap_mm': 20},
                        {'upper_air_gap_mm': 0.5}, {'carrier_height_mm': 8},
                        {'rib_width_mm': 80}):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                build_generator_assembly(replace(p, generator=replace(p.generator, **updates)))


if __name__ == '__main__':
    unittest.main()
