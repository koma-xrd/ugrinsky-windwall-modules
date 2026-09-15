import unittest
from math import pi

import cadquery as cq

from windwall.parameters import DEFAULT_PARAMETERS
from windwall.winding_frame import build_winding_frame
from windwall.winding_head import WindingHeadParts
from windwall.winding_tool_parameters import DEFAULT_WINDING_TOOL_PARAMETERS as P


class WindingFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = build_winding_frame(P, DEFAULT_PARAMETERS)

    def test_frame_uses_two_608_bearings_on_one_eight_mm_axis(self):
        frame = self.frame
        self.assertEqual(len(frame.bearings), 2)
        self.assertEqual(frame.metadata['shaft_diameter_mm'], 8.0)
        self.assertEqual(
            frame.metadata['bearing_nominal_dimensions_mm'],
            [8.0, 22.0, 7.0],
        )
        self.assertTrue(frame.metadata['drive_interfaces_coaxial'])

    def test_manual_drive_and_mounting_features_are_present(self):
        frame = self.frame
        self.assertEqual(frame.metadata['hex_socket_across_flats_mm'], 6.35)
        self.assertTrue(frame.metadata['positive_head_retention'])
        self.assertGreaterEqual(frame.metadata['bench_hole_count'], 4)
        self.assertEqual(frame.metadata['clamp_land_count'], 2)

    def test_each_printable_body_is_one_valid_solid(self):
        for name, shape in self.frame.printable_parts.items():
            with self.subTest(part=name):
                self.assertTrue(shape.val().isValid())
                self.assertEqual(len(shape.val().Solids()), 1)

    def test_bearings_fit_real_inward_seats_with_outer_shoulders(self):
        frame = self.frame
        self.assertEqual(frame.metadata['bearing_seat_diameter_mm'], 22.2)
        self.assertEqual(frame.metadata['bearing_seat_depth_mm'], 7.2)
        for side, upright, bearing, outward_x in zip(
                ('left', 'right'), frame.uprights, frame.bearings, (-1.0, 1.0),
                strict=True):
            with self.subTest(side=side):
                self.assertLess(upright.intersect(bearing).val().Volume(), 1e-6)
                displaced = bearing.translate((0.3 * outward_x, 0, 0))
                self.assertGreater(upright.intersect(displaced).val().Volume(), 0)

    def test_uprights_have_aligned_bolted_interfaces_to_the_base(self):
        frame = self.frame
        self.assertEqual(len(frame.upright_fastener_references), 4)
        for index, fastener in enumerate(frame.upright_fastener_references):
            upright = frame.uprights[index // 2]
            with self.subTest(fastener=index + 1):
                self.assertLess(frame.base.intersect(fastener).val().Volume(), 1e-6)
                self.assertLess(upright.intersect(fastener).val().Volume(), 1e-6)
                offset_fastener = fastener.translate((0, 0.35, 0))
                self.assertGreater(frame.base.intersect(offset_fastener).val().Volume(), 0)
                self.assertGreater(upright.intersect(offset_fastener).val().Volume(), 0)

    def test_removable_cross_pins_positively_retain_the_head_stack(self):
        frame = self.frame
        self.assertIsInstance(frame.head, WindingHeadParts)
        retainers = (frame.head_hub, frame.head_retaining_collar)
        self.assertEqual(len(frame.head_retaining_pin_references), 2)
        for name, retainer, pin in zip(
                ('hub', 'collar'), retainers,
                frame.head_retaining_pin_references, strict=True):
            with self.subTest(retainer=name):
                self.assertLess(retainer.intersect(pin).val().Volume(), 1e-6)
                self.assertLess(
                    frame.shaft_reference.intersect(pin).val().Volume(), 1e-6)
                displaced_pin = pin.translate((0, 0.3, 0))
                self.assertGreater(retainer.intersect(displaced_pin).val().Volume(), 0)
                self.assertGreater(
                    frame.shaft_reference.intersect(displaced_pin).val().Volume(), 0)

        self.assertGreater(
            frame.head.backplate.translate((-0.4, 0, 0))
            .intersect(frame.head_hub).val().Volume(),
            0,
        )

    def test_drive_pins_lock_head_rotation_and_withdraw_for_removal(self):
        frame = self.frame
        axis_start = (0, 0, 95.0)
        axis_end = (1, 0, 95.0)

        self.assertEqual(frame.metadata.get('head_torque_pin_count'), 3)
        self.assertLess(
            frame.head_hub.intersect(frame.head.backplate).val().Volume(),
            1e-6,
        )
        rotated_backplate = frame.head.backplate.rotate(
            axis_start, axis_end, 15.0)
        self.assertGreater(
            frame.head_hub.intersect(rotated_backplate).val().Volume(),
            0,
        )
        self.assertLess(
            frame.head_hub.translate((-6.0, 0, 0))
            .intersect(frame.head.backplate).val().Volume(),
            1e-6,
        )

    def test_adjustment_screws_control_head_preload_through_task2_clamp(self):
        frame = self.frame
        screws = getattr(frame, 'preload_screw_references', ())
        self.assertEqual(len(screws), 3)
        for index, screw in enumerate(screws):
            with self.subTest(screw=index + 1):
                self.assertLess(
                    screw.intersect(frame.head.clamp).val().Volume(), 1e-6)
                self.assertLess(
                    screw.intersect(frame.head_retaining_collar).val().Volume(),
                    1e-6,
                )
                advanced = screw.translate((-0.15, 0, 0))
                self.assertGreater(
                    advanced.intersect(frame.head.clamp).val().Volume(), 0)
                self.assertLess(
                    advanced.intersect(
                        frame.head_retaining_collar).val().Volume(),
                    1e-6,
                )
                self.assertGreater(
                    screw.translate((0, 0.3, 0))
                    .intersect(frame.head_retaining_collar).val().Volume(),
                    0,
                )

        self.assertGreater(
            frame.head.clamp.translate((-0.1, 0, 0))
            .intersect(frame.head.cam).val().Volume(),
            0,
        )
        self.assertGreater(
            frame.head.backplate.translate((-0.05, 0, 0))
            .intersect(frame.head_hub).val().Volume(),
            0,
        )

    def test_captive_preload_nuts_react_axial_load_and_block_rotation(self):
        frame = self.frame
        nuts = getattr(frame, 'preload_nut_references', ())
        self.assertEqual(len(nuts), 3)
        for index, (nut, screw) in enumerate(zip(
                nuts, frame.preload_screw_references, strict=True)):
            box = nut.val().BoundingBox()
            axis_y = (box.ymin + box.ymax) / 2
            axis_z = (box.zmin + box.zmax) / 2
            with self.subTest(nut=index + 1):
                self.assertLess(
                    nut.intersect(frame.head_retaining_collar).val().Volume(),
                    1e-6,
                )
                self.assertLess(nut.intersect(screw).val().Volume(), 1e-6)
                self.assertGreater(
                    nut.translate((-0.3, 0, 0))
                    .intersect(frame.head_retaining_collar).val().Volume(),
                    0,
                )
                self.assertGreater(
                    nut.translate((0.3, 0, 0))
                    .intersect(frame.head_retaining_collar).val().Volume(),
                    0,
                )
                self.assertGreater(
                    nut.rotate((0, axis_y, axis_z),
                               (1, axis_y, axis_z), 10.0)
                    .intersect(frame.head_retaining_collar).val().Volume(),
                    0,
                )

    def test_captive_preload_nuts_have_service_access_and_bom_metadata(self):
        frame = self.frame
        nuts = getattr(frame, 'preload_nut_references', ())
        hardware = frame.metadata.get('preload_hardware', {})

        self.assertEqual(len(nuts), 3)
        self.assertEqual(hardware.get('screw_designation'),
                         'M3 x 10 mm socket-head cap screw')
        self.assertEqual(hardware.get('nut_standard'), 'ISO 4032 M3')
        self.assertEqual(hardware.get('nut_quantity'), 3)
        self.assertEqual(hardware.get('nut_across_flats_mm'), 5.5)
        self.assertEqual(hardware.get('nut_thickness_mm'), 2.4)
        self.assertEqual(hardware.get('nut_pocket_across_flats_mm'), 5.8)
        self.assertEqual(hardware.get('nut_pocket_axial_depth_mm'), 2.8)
        self.assertEqual(hardware.get('nut_insertion'),
                         'Radially through collar OD before screw installation')

        shaft_box = frame.shaft_reference.val().BoundingBox()
        shaft_axis_y = (shaft_box.ymin + shaft_box.ymax) / 2
        shaft_axis_z = (shaft_box.zmin + shaft_box.zmax) / 2
        for index, nut in enumerate(nuts):
            box = nut.val().BoundingBox()
            radial_y = (box.ymin + box.ymax) / 2 - shaft_axis_y
            radial_z = (box.zmin + box.zmax) / 2 - shaft_axis_z
            radial_length = (radial_y ** 2 + radial_z ** 2) ** 0.5
            unit_y = radial_y / radial_length
            unit_z = radial_z / radial_length
            for travel_mm in range(0, 11):
                with self.subTest(nut=index + 1, travel_mm=travel_mm):
                    translated = nut.translate(
                        (0, travel_mm * unit_y, travel_mm * unit_z))
                    self.assertLess(
                        translated.intersect(
                            frame.head_retaining_collar).val().Volume(),
                        1e-6,
                    )

    def test_preload_screw_envelopes_match_the_bom_hardware(self):
        frame = self.frame
        hardware = frame.metadata['preload_hardware']
        self.assertEqual(hardware.get('screw_nominal_diameter_mm'), 3.0)
        self.assertEqual(hardware.get('screw_length_mm'), 10.0)
        self.assertEqual(hardware.get('screw_head_diameter_mm'), 5.5)
        self.assertEqual(hardware.get('screw_head_height_mm'), 3.0)

        expected_volume = pi * (1.5 ** 2 * 10.0 + 2.75 ** 2 * 3.0)
        for index, screw in enumerate(frame.preload_screw_references):
            with self.subTest(screw=index + 1):
                self.assertAlmostEqual(
                    screw.val().Volume(), expected_volume, places=5)

    def test_hex_socket_is_a_coaxial_six_sided_physical_void(self):
        frame = self.frame
        gauge = frame.hex_socket_gauge_reference
        shaft_box = frame.shaft_reference.val().BoundingBox()
        gauge_box = gauge.val().BoundingBox()

        self.assertEqual(len(gauge.val().Faces()), 8)
        self.assertAlmostEqual((gauge_box.ymin + gauge_box.ymax) / 2, 0.0)
        self.assertAlmostEqual(
            (gauge_box.zmin + gauge_box.zmax) / 2,
            (shaft_box.zmin + shaft_box.zmax) / 2,
        )
        self.assertLess(frame.crank.intersect(gauge).val().Volume(), 1e-6)
        self.assertGreater(
            frame.crank.intersect(gauge.translate((0, 0.2, 0))).val().Volume(),
            0,
        )

    def test_hex_socket_keeps_a_loaded_wall_before_the_shaft_pocket(self):
        frame = self.frame
        gauge_box = frame.hex_socket_gauge_reference.val().BoundingBox()
        shaft_box = frame.shaft_reference.val().BoundingBox()
        wall_probe = (cq.Workplane('XY').circle(3.0).extrude(3.0)
                      .rotate((0, 0, 0), (0, 1, 0), 90)
                      .translate((gauge_box.xmin - 3.55, 0,
                                  (shaft_box.zmin + shaft_box.zmax) / 2)))

        self.assertGreaterEqual(
            frame.metadata['hex_socket_end_wall_mm'],
            DEFAULT_PARAMETERS.manufacturing.minimum_loaded_wall_mm,
        )
        self.assertAlmostEqual(
            frame.crank.intersect(wall_probe).val().Volume(),
            wall_probe.val().Volume(),
            places=5,
        )

    def test_crank_grip_has_running_clearance_and_axial_retention(self):
        frame = self.frame
        grip = frame.crank_grip_reference
        self.assertLess(grip.intersect(frame.crank).val().Volume(), 1e-6)
        self.assertLess(
            grip.intersect(frame.grip_pin_reference).val().Volume(), 1e-6)
        for washer in frame.grip_washer_references:
            self.assertLess(grip.intersect(washer).val().Volume(), 1e-6)

        self.assertGreater(
            grip.translate((0.4, 0, 0))
            .intersect(frame.grip_washer_references[0]).val().Volume(),
            0,
        )
        self.assertGreater(
            grip.translate((-0.4, 0, 0))
            .intersect(frame.grip_washer_references[1]).val().Volume(),
            0,
        )

    def test_complete_crank_sweep_clears_every_stationary_frame_body(self):
        frame = self.frame
        axis_start = (0, 0, 95.0)
        axis_end = (1, 0, 95.0)
        moving = {
            'crank': frame.crank,
            'grip': frame.crank_grip_reference,
            'grip_pin': frame.grip_pin_reference,
            'grip_washer_1': frame.grip_washer_references[0],
            'grip_washer_2': frame.grip_washer_references[1],
        }
        stationary = {
            'base': frame.base,
            'left_upright': frame.uprights[0],
            'right_upright': frame.uprights[1],
            'left_bearing': frame.bearings[0],
            'right_bearing': frame.bearings[1],
        }

        for angle in range(0, 360, 10):
            for moving_name, moving_shape in moving.items():
                rotated = moving_shape.rotate(axis_start, axis_end, angle)
                for stationary_name, stationary_shape in stationary.items():
                    with self.subTest(angle=angle, moving=moving_name,
                                      stationary=stationary_name):
                        self.assertLess(
                            rotated.intersect(stationary_shape).val().Volume(),
                            1e-6,
                        )

    def test_bench_holes_are_through_and_clamp_lands_are_clear(self):
        frame = self.frame
        self.assertEqual(len(frame.bench_fastener_references), 4)
        for index, fastener in enumerate(frame.bench_fastener_references):
            with self.subTest(bench_hole=index + 1):
                self.assertLess(frame.base.intersect(fastener).val().Volume(), 1e-6)
                self.assertGreater(
                    frame.base.intersect(
                        fastener.translate((0.3, 0, 0))).val().Volume(),
                    0,
                )

        self.assertEqual(len(frame.clamp_lands), 2)
        for index, land in enumerate(frame.clamp_lands):
            land_box = land.val().BoundingBox()
            clear_space = (cq.Workplane('XY')
                           .box(land_box.xlen, land_box.ylen, 32.0,
                                centered=(True, True, False))
                           .translate(((land_box.xmin + land_box.xmax) / 2,
                                       (land_box.ymin + land_box.ymax) / 2,
                                       land_box.zmax + 0.05)))
            with self.subTest(clamp_land=index + 1):
                self.assertAlmostEqual(
                    frame.base.intersect(land).val().Volume(),
                    land.val().Volume(),
                    places=5,
                )
                for name, part in frame.printable_parts.items():
                    if name != 'base':
                        self.assertLess(
                            part.intersect(clear_space).val().Volume(),
                            1e-6,
                            name,
                        )

    def test_powered_operation_remains_explicitly_unvalidated(self):
        metadata = self.frame.metadata
        self.assertFalse(metadata['powered_operation_validated'])
        for unsupported_claim in ('powered_speed_rpm', 'motor_mount', 'guarded'):
            self.assertNotIn(unsupported_claim, metadata)


if __name__ == '__main__':
    unittest.main()
