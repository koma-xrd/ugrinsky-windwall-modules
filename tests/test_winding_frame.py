"""Physical engagement of the horizontal 51105 hub and removable hex crank."""
import unittest
from math import cos, radians

import cadquery as cq

from windwall.parameters import DEFAULT_PARAMETERS
from windwall.winding_frame import build_winding_frame
from windwall.winding_head import build_winding_head
from windwall.winding_tool_parameters import WindingToolParameters
from windwall.winding_tool_service import _linear_collision
from windwall.wire_payoff import build_wire_payoff

P = WindingToolParameters()


def overlap(a, b):
    return a.intersect(b).val().Volume()


class WindingFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = build_winding_frame(P, DEFAULT_PARAMETERS)
        cls.payoff = build_wire_payoff(P, DEFAULT_PARAMETERS)

    def test_horizontal_frame_reuses_payoff_base(self):
        for name in ('base', 'lower_washer', 'bearing', 'upper_washer'):
            actual, expected = getattr(self.frame, name), getattr(self.payoff, name)
            self.assertLess(actual.cut(expected).val().Volume(), 1e-6)
            self.assertLess(expected.cut(actual).val().Volume(), 1e-6)

    def test_hub_carries_51105_without_bottoming(self):
        f = self.frame
        self.assertAlmostEqual(f.hub.val().BoundingBox().zmin, 1.5)
        self.assertLess(overlap(f.hub, f.base), 1e-6)
        self.assertLess(overlap(f.hub, f.upper_washer), 1e-6)
        self.assertGreater(overlap(f.hub.translate((0, 0, -.01)), f.upper_washer), .01)
        core = cq.Workplane('XY').circle(12).extrude(22).translate((0, 0, 1.5))
        self.assertAlmostEqual(overlap(f.hub, core), core.val().Volume(), places=5)
        for bearing in (f.lower_washer, f.bearing, f.upper_washer):
            self.assertLess(overlap(f.hub, bearing), 1e-6)
        self.assertGreater(overlap(f.hub.translate((.3, 0, 0)), f.lower_washer), .01)

    def test_wheel_gap_is_at_least_25_mm(self):
        f = self.frame
        wheel = build_winding_head(P, 150).wheel.translate((0, 0, f.metadata['wheel_bottom_z_mm']))
        self.assertGreaterEqual(wheel.val().BoundingBox().zmin - 8, 25)
        self.assertLess(overlap(wheel, f.hub), 1e-6)
        self.assertGreater(overlap(wheel.translate((0, 0, -.01)), f.hub), .01)
        self.assertGreater(overlap(wheel.rotate((0, 0, 0), (0, 0, 1), 30), f.hub), .1)

    def test_crank_uses_removable_635_mm_across_flats_hex(self):
        f = self.frame
        bottom = f.metadata['drive_socket_bottom_z_mm']
        gauge = cq.Workplane('XY').polygon(6, 6.35 / cos(radians(30))).extrude(8).translate((0, 0, bottom))
        self.assertLess(overlap(gauge, f.hub), 1e-6)
        self.assertGreater(overlap(gauge.rotate((0, 0, 0), (0, 0, 1), 30), f.hub), .1)
        self.assertAlmostEqual(overlap(f.crank, gauge), gauge.val().Volume(), places=5)
        self.assertLess(_linear_collision(f.crank, f.hub, (0, 0, 50)), 1e-6)
        self.assertGreater(overlap(f.crank.translate((0, 0, -.01)), f.hub), .001)

    def test_every_print_master_is_single_solid_and_fits_documented_orientation(self):
        for name in ('base', 'hub', 'crank', 'grip'):
            with self.subTest(name=name):
                shape = getattr(self.frame, name)
                self.assertTrue(shape.val().isValid())
                self.assertEqual(len(shape.val().Solids()), 1)
                self.assertGreater(shape.val().Volume(), 0)
                for axis, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                                       self.frame.metadata['print_rotations_deg'][name]):
                    shape = shape.rotate((0, 0, 0), axis, angle)
                bounds = shape.val().BoundingBox()
                self.assertLessEqual(max(bounds.xlen, bounds.ylen), 220)

    def test_grip_is_free_to_rotate_and_lift_for_service(self):
        f = self.frame
        x, y = f.metadata['grip_axis_xy_mm']
        for angle in (0, 30, 90, 180):
            self.assertLess(overlap(f.grip.rotate((x, y, 0), (x, y, 1), angle), f.crank), 1e-6)
        self.assertLess(_linear_collision(f.grip, f.crank, (0, 0, 40)), 1e-6)


if __name__ == '__main__':
    unittest.main()
