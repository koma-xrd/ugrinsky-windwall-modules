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
            {'adjuster', 'spring', 'washer', 'screw', 'nut', 'felt'},
        )
        self.assertTrue(payoff.metadata['felt_replaceable'])
        self.assertNotIn('felt', payoff.printable_parts)
        for name, shape in payoff.brake_parts.items():
            with self.subTest(part=name):
                self.assertTrue(shape.val().isValid())
                self.assertEqual(len(shape.val().Solids()), 1)
                self.assertGreater(shape.val().Volume(), 0)

    def test_brake_has_supported_load_path_and_captive_screw_engagement(self):
        for setting in (0.0, 1.0):
            payoff = build_wire_payoff(
                P, DEFAULT_PARAMETERS, brake_setting=setting)
            nut = getattr(payoff, 'nut', None)
            with self.subTest(setting=setting, member='nut'):
                self.assertIsNotNone(nut)
            if nut is None:
                continue

            contacts = (
                ('base/spring', payoff.base, payoff.spring),
                ('spring/washer', payoff.spring, payoff.washer),
                ('washer/adjuster', payoff.washer, payoff.adjuster),
                ('adjuster/felt', payoff.adjuster, payoff.felt),
                ('felt/platter', payoff.felt, payoff.platter),
                ('base/screw-head', payoff.base, payoff.screw),
            )
            for name, first, second in contacts:
                with self.subTest(setting=setting, contact=name):
                    self.assertAlmostEqual(
                        first.val().distance(second.val()), 0.0, places=5)

            with self.subTest(setting=setting, reaction='spring seat'):
                self.assertGreater(
                    payoff.spring.translate((0, 0, -0.05))
                    .intersect(payoff.base).val().Volume(),
                    0,
                )
            with self.subTest(setting=setting, reaction='screw head seat'):
                self.assertGreater(
                    payoff.screw.translate((0, 0, 0.05))
                    .intersect(payoff.base).val().Volume(),
                    0,
                )

            self.assertLess(nut.intersect(payoff.adjuster).val().Volume(), 1e-6)
            self.assertLess(nut.intersect(payoff.screw).val().Volume(), 1e-6)
            for z_offset in (-0.2, 0.2):
                with self.subTest(setting=setting,
                                  captive_nut_axial_offset=z_offset):
                    self.assertGreater(
                        nut.translate((0, 0, z_offset))
                        .intersect(payoff.adjuster).val().Volume(),
                        0,
                    )
            nut_box = nut.val().BoundingBox()
            nut_axis = (
                (nut_box.xmin + nut_box.xmax) / 2,
                (nut_box.ymin + nut_box.ymax) / 2,
            )
            with self.subTest(setting=setting, reaction='nut anti-rotation'):
                self.assertGreater(
                    nut.rotate(
                        (nut_axis[0], nut_axis[1], 0),
                        (nut_axis[0], nut_axis[1], 1),
                        10.0,
                    ).intersect(payoff.adjuster).val().Volume(),
                    0,
                )
            with self.subTest(setting=setting, retention='engaged screw'):
                self.assertGreater(
                    nut.translate((0.25, 0, 0))
                    .intersect(payoff.screw).val().Volume(),
                    0,
                )

            self.assertGreater(
                payoff.metadata['spring_preload_remaining_mm'], 0.0)
            self.assertGreaterEqual(
                payoff.metadata['screw_nut_engagement_mm'], 2.0)

    def test_lowered_adjuster_and_nut_have_collision_free_service_path(self):
        payoff = build_wire_payoff(P, DEFAULT_PARAMETERS, brake_setting=0.0)
        nut = getattr(payoff, 'nut', None)
        members = {'adjuster': payoff.adjuster}
        if nut is not None:
            members['nut'] = nut

        for name, member in members.items():
            for travel_mm in range(0, 25):
                with self.subTest(member=name, travel_mm=travel_mm):
                    self.assertLess(
                        member.translate((travel_mm, 0, 0))
                        .intersect(payoff.base).val().Volume(),
                        1e-6,
                    )
        self.assertIsNotNone(nut)
        if nut is not None:
            for travel_mm in range(0, 10):
                with self.subTest(member='nut/adjuster',
                                  travel_mm=travel_mm):
                    self.assertLess(
                        nut.translate((travel_mm, 0, 0))
                        .intersect(payoff.adjuster).val().Volume(),
                        1e-6,
                    )
        self.assertEqual(payoff.metadata.get('adjuster_service_setting'), 0.0)
        self.assertEqual(
            payoff.metadata.get('adjuster_service_direction'),
            '+X after screw removal',
        )

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
