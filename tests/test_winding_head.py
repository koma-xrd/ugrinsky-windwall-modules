import unittest
from itertools import combinations
from math import cos, radians, sin

import cadquery as cq

from windwall.winding_head import build_winding_head, tape_station_angles
from windwall.winding_tool_parameters import DEFAULT_WINDING_TOOL_PARAMETERS as P


class WindingHeadTests(unittest.TestCase):
    def test_six_ribs_remain_concentric_at_range_samples(self):
        for diameter in (110.0, 127.0, 145.0):
            head = build_winding_head(P, diameter)
            self.assertEqual(len(head.ribs), 6)
            self.assertTrue(all(abs(radius - diameter / 2) < 1e-6
                                for radius in head.state.rib_contact_radii_mm))
            self.assertEqual(head.state.requested_diameter_mm, diameter)

    def test_tape_layout_and_release_are_explicit(self):
        self.assertEqual(tape_station_angles(P), tuple(range(0, 360, 20)))
        head = build_winding_head(P, 127.0)
        self.assertEqual(head.state.tape_passage_width_mm, 12.0)
        self.assertEqual(head.state.tape_station_count, 18)
        self.assertGreaterEqual(head.state.release_travel_mm, 2.0)

    def test_invalid_diameter_is_rejected(self):
        for diameter in (109.9, 145.1, float('nan')):
            with self.subTest(diameter=diameter), self.assertRaisesRegex(ValueError, 'diameter'):
                build_winding_head(P, diameter)

    def test_printable_parts_are_valid_single_solids(self):
        head = build_winding_head(P, 127.0)
        self.assertEqual(
            tuple(head.printable_parts),
            ('backplate', 'cam', 'clamp',
             'slider_1', 'slider_2', 'slider_3', 'slider_4', 'slider_5', 'slider_6',
             'rib_1', 'rib_2', 'rib_3', 'rib_4', 'rib_5', 'rib_6'),
        )
        for name, shape in head.printable_parts.items():
            with self.subTest(part=name):
                self.assertTrue(shape.val().isValid())
                self.assertEqual(len(shape.val().Solids()), 1)
                self.assertGreater(shape.val().Volume(), 0)

    def test_each_tape_station_is_a_physical_clearance_through_a_rib(self):
        head = build_winding_head(P, 127.0)
        ribs = head.ribs[0]
        for rib in head.ribs[1:]:
            ribs = ribs.union(rib)
        radius = head.state.requested_diameter_mm / 2
        for angle in tape_station_angles(P):
            passage_probe = (cq.Workplane('XY')
                             .box(10.0, P.tape_passage_width_mm - 0.2, 14.0,
                                  centered=(False, True, False))
                             .translate((radius - 7.0, 0, 13.0))
                             .rotate((0, 0, 0), (0, 0, 1), angle))
            with self.subTest(angle=angle):
                self.assertLess(ribs.intersect(passage_probe).val().Volume(), 1e-6)

    def test_cam_tracks_physically_clear_every_slider_follower(self):
        for diameter in (110.0, 127.0, 145.0):
            head = build_winding_head(P, diameter)
            follower_centres = []
            for slider in head.sliders:
                circles = [edge for edge in slider.val().Edges()
                           if edge.geomType() == 'CIRCLE']
                self.assertEqual(len(circles), 2)
                follower_centres.append(circles[0].Center())
            for centre in follower_centres:
                probe = (cq.Workplane('XY').circle(1.5).extrude(10.0)
                         .translate((centre.x, centre.y, 8.0)))
                with self.subTest(diameter=diameter, x=centre.x, y=centre.y):
                    self.assertLess(head.cam.intersect(probe).val().Volume(), 1e-6)

    def test_wire_contact_ribs_have_rounded_surfaces(self):
        head = build_winding_head(P, 127.0)
        for index, rib in enumerate(head.ribs, start=1):
            with self.subTest(rib=index):
                self.assertTrue(any(face.geomType() == 'CYLINDER'
                                    for face in rib.val().Faces()))

    def test_separate_printable_members_do_not_interpenetrate(self):
        for diameter in (110.0, 127.0, 145.0):
            parts = build_winding_head(P, diameter).printable_parts
            for (first_name, first), (second_name, second) in combinations(parts.items(), 2):
                first_box = first.val().BoundingBox()
                second_box = second.val().BoundingBox()
                boxes_overlap = (
                    first_box.xmin <= second_box.xmax
                    and second_box.xmin <= first_box.xmax
                    and first_box.ymin <= second_box.ymax
                    and second_box.ymin <= first_box.ymax
                    and first_box.zmin <= second_box.zmax
                    and second_box.zmin <= first_box.zmax
                )
                if boxes_overlap:
                    with self.subTest(diameter=diameter,
                                      first=first_name, second=second_name):
                        self.assertLess(first.intersect(second).val().Volume(), 1e-6)

    def test_minimum_setting_has_physical_release_overtravel_and_hard_stops(self):
        minimum_head = build_winding_head(P, P.minimum_diameter_mm)
        for index, slider in enumerate(minimum_head.sliders):
            angle = radians(index * 60)
            release = P.release_travel_mm
            released_slider = slider.translate(
                (-release * cos(angle), -release * sin(angle), 0))
            past_stop_slider = slider.translate(
                (-(release + 0.3) * cos(angle),
                 -(release + 0.3) * sin(angle), 0))
            with self.subTest(end='release', slider=index + 1):
                self.assertLess(
                    minimum_head.backplate.intersect(released_slider).val().Volume(),
                    1e-6,
                )
                self.assertGreater(
                    minimum_head.backplate.intersect(past_stop_slider).val().Volume(),
                    0,
                )

        released_circles = [
            edge for edge in minimum_head.sliders[0]
            .translate((-P.release_travel_mm, 0, 0)).val().Edges()
            if edge.geomType() == 'CIRCLE'
        ]
        released_centre = released_circles[0].Center()
        released_follower = (cq.Workplane('XY').circle(1.5).extrude(10.0)
                             .translate((released_centre.x, released_centre.y, 8.0)))
        cam_reaches_release = any(
            minimum_head.cam.rotate((0, 0, 0), (0, 0, 1), step / 10)
            .intersect(released_follower).val().Volume() < 1e-6
            for step in range(1, 51)
        )
        self.assertTrue(cam_reaches_release)

        maximum_head = build_winding_head(P, P.maximum_diameter_mm)
        for index, slider in enumerate(maximum_head.sliders):
            angle = radians(index * 60)
            past_stop_slider = slider.translate(
                (0.3 * cos(angle), 0.3 * sin(angle), 0))
            with self.subTest(end='maximum', slider=index + 1):
                self.assertGreater(
                    maximum_head.backplate.intersect(past_stop_slider).val().Volume(),
                    0,
                )
