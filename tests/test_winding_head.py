import unittest
from itertools import combinations
from math import cos, radians, sin

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface

from windwall.winding_head import build_winding_head, tape_station_angles
from windwall.winding_tool_parameters import DEFAULT_WINDING_TOOL_PARAMETERS as P


class WindingHeadTests(unittest.TestCase):
    @staticmethod
    def _follower_centres(slider):
        circles = [
            edge for edge in slider.val().Edges()
            if (edge.geomType() == 'CIRCLE'
                and abs(BRepAdaptor_Curve(
                    edge.wrapped).Circle().Radius() - 2.1) < 1e-6)
        ]
        if len(circles) != 2:
            raise AssertionError(f'Expected two follower edges, got {len(circles)}')
        return [edge.Center() for edge in circles]

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
        for diameter in (110.0, 127.0, 145.0):
            head = build_winding_head(P, diameter)
            ribs = head.ribs[0]
            for rib in head.ribs[1:]:
                ribs = ribs.union(rib)
            radius = head.state.requested_diameter_mm / 2
            for angle in tape_station_angles(P):
                passage_probe = (cq.Workplane('XY')
                                 .box(10.0, P.tape_passage_width_mm - 0.2,
                                      10.0,
                                      centered=(False, True, False))
                                 .translate((radius - 7.0, 0, 14.0))
                                 .rotate((0, 0, 0), (0, 0, 1), angle))
                with self.subTest(diameter=diameter, angle=angle):
                    self.assertLess(ribs.intersect(passage_probe).val().Volume(), 1e-6)

    def test_cam_tracks_physically_clear_every_slider_follower(self):
        for diameter in (110.0, 127.0, 145.0):
            head = build_winding_head(P, diameter)
            follower_centres = []
            for slider in head.sliders:
                follower_centres.append(self._follower_centres(slider)[0])
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

        released_slider = minimum_head.sliders[0].translate(
            (-P.release_travel_mm, 0, 0))
        released_centre = self._follower_centres(released_slider)[0]
        released_follower = (cq.Workplane('XY').circle(1.5).extrude(10.0)
                             .translate(
                                 (released_centre.x, released_centre.y, 8.0)))
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

    def test_rib_and_slider_accept_a_shared_pin_that_blocks_radial_separation(self):
        head = build_winding_head(P, 127.0)
        pin_radius = head.state.requested_diameter_mm / 2 - 7.0
        pin = (cq.Workplane('XY').circle(1.4).extrude(16.0)
               .rotate((0, 0, 0), (1, 0, 0), 90)
               .translate((pin_radius, 8.0, 7.15)))
        bearing_shell = (cq.Workplane('XY').circle(2.2).circle(1.8).extrude(16.0)
                         .rotate((0, 0, 0), (1, 0, 0), 90)
                         .translate((pin_radius, 8.0, 7.15)))

        self.assertLess(head.sliders[0].intersect(pin).val().Volume(), 1e-6)
        self.assertLess(head.ribs[0].intersect(pin).val().Volume(), 1e-6)
        self.assertGreater(
            head.sliders[0].intersect(bearing_shell).val().Volume(), 0)
        self.assertGreater(head.ribs[0].intersect(bearing_shell).val().Volume(), 0)
        self.assertGreater(
            head.ribs[0].translate((0.4, 0, 0)).intersect(pin).val().Volume(),
            0,
        )

    def test_each_printed_rib_is_congruent_across_diameter_settings(self):
        reference = build_winding_head(P, P.reference_diameter_mm).ribs[0]
        for diameter in (P.minimum_diameter_mm, P.maximum_diameter_mm):
            aligned = build_winding_head(P, diameter).ribs[0].translate(
                ((P.reference_diameter_mm - diameter) / 2, 0, 0))
            symmetric_difference = (
                reference.cut(aligned).val().Volume()
                + aligned.cut(reference).val().Volume()
            )
            with self.subTest(diameter=diameter):
                self.assertLess(symmetric_difference, 1e-5)

    def test_physical_rib_surfaces_do_not_exceed_requested_contact_radius(self):
        for diameter in (110.0, 127.0, 145.0):
            head = build_winding_head(P, diameter)
            radius = diameter / 2
            outer_excess = (cq.Workplane('XY').circle(radius + 20)
                            .circle(radius + 0.01).extrude(30)
                            .translate((0, 0, 5)))
            contact_band = (cq.Workplane('XY').circle(radius + 0.01)
                            .circle(radius - 0.05).extrude(30)
                            .translate((0, 0, 5)))
            for index, rib in enumerate(head.ribs):
                with self.subTest(diameter=diameter, rib=index + 1):
                    self.assertLess(rib.intersect(outer_excess).val().Volume(), 1e-6)
                    self.assertGreater(rib.intersect(contact_band).val().Volume(), 0)

    def test_clamp_compression_reacts_through_a_central_backplate_shoulder(self):
        head = build_winding_head(P, 127.0)
        reaction_probe = (cq.Workplane('XY').circle(11.5).circle(5.0)
                          .extrude(4.7).translate((0, 0, 5.0)))
        self.assertAlmostEqual(
            head.backplate.intersect(reaction_probe).val().Volume(),
            reaction_probe.val().Volume(),
            places=5,
        )
        self.assertLess(
            abs(head.backplate.val().BoundingBox().zmax
                - head.cam.val().BoundingBox().zmin),
            0.01,
        )
        self.assertLess(
            head.clamp.val().BoundingBox().zmin - head.cam.val().BoundingBox().zmax,
            0.1,
        )

    def test_tape_groove_contact_boundaries_include_rounding_faces(self):
        head = build_winding_head(P, 127.0)
        for index, rib in enumerate(head.ribs):
            rounding_faces = [
                face for face in rib.val().Faces()
                if (face.geomType() == 'CYLINDER'
                    and 0.6 <= BRepAdaptor_Surface(face.wrapped).Cylinder().Radius() <= 1.0)
            ]
            with self.subTest(rib=index + 1):
                self.assertGreaterEqual(len(rounding_faces), 3)

    def test_all_tape_stations_have_aligned_physical_number_engraving(self):
        head = build_winding_head(P, 127.0)
        for station, angle in enumerate(tape_station_angles(P), start=1):
            engraving_patch = (cq.Workplane('XY')
                               .box(3.0, 7.0, 0.35,
                                    centered=(False, True, False))
                               .translate((71.8, 0, 4.65))
                               .rotate((0, 0, 0), (0, 0, 1), angle))
            removed_volume = (
                engraving_patch.val().Volume()
                - head.backplate.intersect(engraving_patch).val().Volume()
            )
            with self.subTest(station=station, angle=angle):
                self.assertGreater(removed_volume, 0.02)
