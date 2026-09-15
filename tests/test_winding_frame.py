import unittest

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
        self.assertGreater(
            frame.head.clamp.translate((0.4, 0, 0))
            .intersect(frame.head_retaining_collar).val().Volume(),
            0,
        )

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
