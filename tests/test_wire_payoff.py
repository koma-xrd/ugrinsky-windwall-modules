import unittest

import cadquery as cq

from windwall.parameters import DEFAULT_PARAMETERS
from windwall.winding_tool_parameters import DEFAULT_WINDING_TOOL_PARAMETERS as P
from windwall.wire_payoff import build_wire_payoff


class WirePayoffTests(unittest.TestCase):
    def test_platter_pilot_and_bearing_match_design(self):
        payoff = build_wire_payoff(P, DEFAULT_PARAMETERS)
        self.assertEqual(payoff.metadata['platter_diameter_mm'], 150.0)
        self.assertEqual(payoff.metadata['spool_pilot_mm'], [15.0, 20.0])
        self.assertEqual(
            payoff.metadata['bearing_nominal_dimensions_mm'],
            [25.0, 42.0, 11.0],
        )

    def test_51105_motion_ownership_is_explicit(self):
        payoff = build_wire_payoff(P, DEFAULT_PARAMETERS)
        self.assertEqual(set(payoff.rotating_parts), {'platter', 'shaft_washer'})
        self.assertIn('housing_washer', payoff.stationary_parts)
        self.assertIn('rolling_envelope', payoff.bearing_internal_parts)

    def test_brake_has_free_running_and_drag_states_but_no_lock_state(self):
        free = build_wire_payoff(P, DEFAULT_PARAMETERS, brake_setting=0.0)
        drag = build_wire_payoff(P, DEFAULT_PARAMETERS, brake_setting=1.0)
        self.assertEqual(free.metadata['felt_compression_mm'], 0.0)
        self.assertGreater(drag.metadata['felt_compression_mm'], 0.0)
        self.assertFalse(drag.metadata['normal_adjustment_can_lock_platter'])
        with self.assertRaisesRegex(ValueError, 'brake setting'):
            build_wire_payoff(P, DEFAULT_PARAMETERS, brake_setting=1.01)

    def test_platter_is_a_removable_printable_solid_with_chamfered_pilot(self):
        payoff = build_wire_payoff(P, DEFAULT_PARAMETERS)
        box = payoff.platter.val().BoundingBox()

        self.assertEqual(
            tuple(payoff.printable_parts),
            ('base', 'platter', 'adjuster'),
        )
        self.assertLessEqual(box.xlen, 150.0 + 1e-6)
        self.assertLessEqual(box.ylen, 150.0 + 1e-6)
        self.assertTrue(any(face.geomType() == 'CONE'
                            for face in payoff.platter.val().Faces()))
        self.assertLess(payoff.platter.intersect(payoff.base).val().Volume(), 1e-6)
        self.assertLess(
            payoff.platter.translate((0, 0, 30.0))
            .intersect(payoff.base).val().Volume(),
            1e-6,
        )
        self.assertTrue(
            payoff.metadata['platter_removable_without_disturbing_seat'])

    def test_existing_51105_fit_candidates_are_physical_interfaces(self):
        payoff = build_wire_payoff(P, DEFAULT_PARAMETERS)
        housing_washer = payoff.stationary_parts['housing_washer']
        shaft_washer = payoff.rotating_parts['shaft_washer']

        self.assertEqual(payoff.metadata['bearing_housing_seat_diameter_mm'], 42.2)
        self.assertEqual(payoff.metadata['bearing_rotating_pilot_diameter_mm'], 24.8)
        self.assertLess(payoff.base.intersect(housing_washer).val().Volume(), 1e-6)
        self.assertAlmostEqual(payoff.base.val().distance(housing_washer.val()), 0.0)
        self.assertGreater(
            payoff.base.intersect(
                housing_washer.translate((0, 0, -0.05))).val().Volume(),
            0.05,
        )
        self.assertLess(payoff.platter.intersect(shaft_washer).val().Volume(), 1e-6)
        self.assertAlmostEqual(
            payoff.platter.val().distance(shaft_washer.val()), 0.0)
        self.assertGreater(
            payoff.platter.translate((0, 0, -0.05))
            .intersect(shaft_washer).val().Volume(),
            0.05,
        )

        pilot_probe = (cq.Workplane('XY').circle(12.39).extrude(8.0)
                       .translate((0, 0, 12.0)))
        self.assertAlmostEqual(
            payoff.platter.intersect(pilot_probe).val().Volume(),
            pilot_probe.val().Volume(),
            places=5,
        )

    def test_base_has_real_bench_holes_and_clamp_lands(self):
        payoff = build_wire_payoff(P, DEFAULT_PARAMETERS)

        self.assertEqual(payoff.metadata['bench_hole_count'], 4)
        self.assertEqual(payoff.metadata['clamp_land_count'], 2)
        self.assertGreater(payoff.base.val().BoundingBox().xlen, 150.0)
        for index, fastener in enumerate(payoff.bench_fastener_references):
            with self.subTest(fastener=index + 1):
                self.assertLess(
                    payoff.base.intersect(fastener).val().Volume(), 1e-6)
                self.assertGreater(
                    payoff.base.intersect(
                        fastener.translate((0.35, 0, 0))).val().Volume(),
                    0,
                )

    def test_brake_members_are_separate_and_felt_is_replaceable(self):
        payoff = build_wire_payoff(P, DEFAULT_PARAMETERS, brake_setting=0.5)

        self.assertEqual(
            set(payoff.brake_parts),
            {'adjuster', 'spring', 'washer', 'screw', 'felt'},
        )
        self.assertTrue(payoff.metadata['felt_replaceable'])
        self.assertNotIn('felt', payoff.printable_parts)
        for name, shape in payoff.brake_parts.items():
            with self.subTest(part=name):
                self.assertTrue(shape.val().isValid())
                self.assertEqual(len(shape.val().Solids()), 1)
                self.assertGreater(shape.val().Volume(), 0)

    def test_positive_adjuster_stop_preserves_rigid_clearance_at_full_drag(self):
        payoff = build_wire_payoff(P, DEFAULT_PARAMETERS, brake_setting=1.0)
        clearance = payoff.metadata['hard_stop_clearance_mm']

        self.assertGreater(clearance, 0.0)
        self.assertAlmostEqual(
            payoff.adjuster.val().distance(payoff.platter.val()),
            clearance,
            places=5,
        )
        for name in ('adjuster', 'washer', 'screw'):
            with self.subTest(rigid_member=name):
                self.assertGreaterEqual(
                    payoff.brake_parts[name].val().distance(
                        payoff.platter.val()),
                    clearance - 1e-6,
                )
        self.assertLess(payoff.adjuster.intersect(payoff.base).val().Volume(), 1e-6)
        self.assertGreater(
            payoff.adjuster.translate((0, 0, 0.1))
            .intersect(payoff.base).val().Volume(),
            0,
        )
        self.assertAlmostEqual(payoff.felt.val().distance(payoff.platter.val()), 0.0)
        self.assertAlmostEqual(payoff.felt.val().distance(payoff.adjuster.val()), 0.0)

    def test_payoff_is_passive_and_rejects_nonfinite_or_boolean_settings(self):
        payoff = build_wire_payoff(P, DEFAULT_PARAMETERS)
        self.assertFalse(payoff.metadata['mechanically_synchronized_with_winder'])
        self.assertFalse(payoff.metadata['powered_operation_validated'])
        for setting in (-0.01, float('nan'), float('inf'), True, '0.5'):
            with self.subTest(setting=setting), self.assertRaisesRegex(
                    ValueError, 'brake setting'):
                build_wire_payoff(P, DEFAULT_PARAMETERS, brake_setting=setting)


if __name__ == '__main__':
    unittest.main()
