"""Physical regressions for the reusable pin-adjustable wheel and shoes."""

import unittest
from dataclasses import fields
from itertools import combinations
from math import atan2, cos, degrees, hypot, radians, sin

import cadquery as cq

from tests.support import temporary_build_directory
from windwall.parameters import DEFAULT_PARAMETERS
from windwall.reference_mesh import analyze_binary_stl
from windwall.winding_head import (
    WindingHeadParts, WindingHeadState, build_winding_head, tape_station_angles,
)
from windwall.winding_tool_parameters import WindingToolParameters, diameter_settings_mm


P = WindingToolParameters()


def shape_signature(shape):
    """Rigid-motion invariant geometry/topology summary, not a mesh hash."""
    solid = shape.val()
    return (round(solid.Volume(), 5), len(solid.Faces()), len(solid.Edges()),
            tuple(sorted((face.geomType(), round(face.Area(), 5))
                         for face in solid.Faces())))


def box(x, y, z, dx, dy, dz):
    return cq.Workplane('XY').box(dx, dy, dz, centered=False).translate((x, y, z))


def overlap(first, second):
    return first.intersect(second).val().Volume()


def assert_rounded_mouths(test, shape):
    faces = shape.val().Faces()
    mouth_edges = [edge for edge in shape.val().Edges()
                   if abs(edge.Center().z - 10.8) < .01]
    test.assertGreater(len(mouth_edges), 0)
    for edge in mouth_edges:
        adjacent = [face for face in faces if any(edge.isSame(candidate)
                     for candidate in face.Edges())]
        test.assertTrue(any(face.geomType() in ('TORUS', 'CYLINDER', 'BSPLINE')
                            for face in adjacent))


def raw_release_mesh(shape, destination, name):
    bounds = shape.val().BoundingBox()
    printable = shape.translate((0, 0, -bounds.zmin))
    path = destination / f'{name}.stl'
    manufacturing = DEFAULT_PARAMETERS.manufacturing
    printable.val().exportStl(
        str(path), tolerance=manufacturing.export_linear_tolerance_mm,
        angularTolerance=manufacturing.export_angular_tolerance_rad,
        ascii=False, relative=False, parallel=False,
    )
    return analyze_binary_stl(path)


class WindingHeadTests(unittest.TestCase):
    def test_open_top_shoe_clears_upward_winding_sweep(self):
        # A full annulus is a conservative continuous swept volume: it covers
        # both the winding and the outer legs of closed tape loops.
        sweep = cq.Workplane('XY').circle(52).circle(50.01).extrude(60).translate((0, 0, 12.5))
        head = build_winding_head(P, 100)
        self.assertLess(overlap(head.shoes[0], sweep), 1e-6)
        self.assertEqual(head.metadata['free_shoulder_height_mm'], 0.0)
        self.assertGreater(head.metadata['rear_shoulder_height_mm'], 0.0)
        trapped = head.shoes[0].union(box(49.5, 7, 26, 3, 1, 1))
        self.assertGreater(overlap(trapped, sweep), .1)

    def test_public_contract_is_one_wheel_and_one_reusable_shoe(self):
        self.assertEqual(tuple(field.name for field in fields(WindingHeadState)),
                         ('diameter_mm', 'shoe_radius_mm', 'release_radius_mm'))
        self.assertEqual(tuple(field.name for field in fields(WindingHeadParts)),
                         ('wheel', 'shoe_master', 'shoes', 'state', 'metadata'))
        head = build_winding_head(WindingToolParameters(), 100)
        for shape in (head.wheel, head.shoe_master):
            self.assertTrue(shape.val().isValid())
            self.assertEqual(len(shape.val().Solids()), 1)
            self.assertGreater(shape.val().Volume(), 0)

    def test_contact_surface_has_rounded_lower_support_and_nominal_upper_runout(self):
        head = build_winding_head(P, 150)
        shoe = head.shoe_master

        def outer_radius_offset_at(z):
            sample = shoe.intersect(box(-6, 7.2, z - .2, 10, .6, .4))
            self.assertGreater(sample.val().Volume(), 0)
            # The sample starts off-axis at Y=7.2; X alone includes the
            # curvature of the nominal 50 mm master rather than its height.
            return hypot(sample.val().BoundingBox().xmax + 50, 7.2) - 50

        rear = outer_radius_offset_at(7.0)
        bottom = outer_radius_offset_at(16.5)
        free = outer_radius_offset_at(26.5)
        self.assertAlmostEqual(bottom, 0.0, delta=.15)
        self.assertGreater(rear - bottom, 2.0)
        self.assertLessEqual(rear - bottom, 2.7)
        self.assertAlmostEqual(free - bottom, 0.0, delta=.01)
        bounds = shoe.val().BoundingBox()
        self.assertLessEqual(bounds.xmin, -12.0)
        self.assertEqual(head.metadata['tongue_rows_y_mm'], (-7.5, 7.5))
        self.assertEqual(head.metadata['cradle_bottom_radius_offset_mm'], 0.0)
        self.assertEqual(head.metadata['rear_shoulder_height_mm'], 2.7)
        self.assertEqual(head.metadata['free_shoulder_height_mm'], 0.0)
        self.assertEqual(head.metadata['wire_guidance'],
                         'rounded lower support; open nominal-radius upper runout')

    def test_cradle_fits_a_valid_reduced_tape_clearance(self):
        p = WindingToolParameters(tape_clearance_mm=6.0)
        self.assertIn(100, diameter_settings_mm(p))
        head = build_winding_head(p, 100)
        solid = head.shoe_master.val()
        self.assertTrue(solid.isValid())
        self.assertEqual(len(solid.Solids()), 1)
        self.assertGreater(solid.Volume(), 0)
        self.assertAlmostEqual(solid.BoundingBox().zmax, 23.2, places=5)
        for shoe_index in range(6):
            for probe in head.metadata['tape_passage_probes'][3 * shoe_index:3 * shoe_index + 3]:
                self.assertLess(overlap(head.shoes[shoe_index], probe), 1e-6)

    def test_six_identical_shoes_define_each_requested_envelope(self):
        reference = None
        for diameter in diameter_settings_mm(P):
            head = build_winding_head(P, diameter)
            self.assertEqual(len(head.shoes), 6)
            self.assertEqual(head.state.diameter_mm, diameter)
            self.assertEqual(head.state.shoe_radius_mm * 2, diameter)
            signatures = {shape_signature(shoe) for shoe in head.shoes}
            self.assertEqual(len(signatures), 1)
            if reference is None:
                reference = signatures
            self.assertEqual(signatures, reference)
            rear_excess = cq.Workplane('XY').circle(diameter / 2 + 30).circle(
                diameter / 2 + .001).extrude(19).translate((0, 0, 10.2))
            front_excess = cq.Workplane('XY').circle(diameter / 2 + 30).circle(
                diameter / 2 + 2.701).extrude(5).translate((0, 0, 5.2))
            for index, shoe in enumerate(head.shoes):
                self.assertTrue(shoe.val().isValid())
                self.assertLess(overlap(shoe, rear_excess), 1e-6)
                self.assertLess(overlap(shoe, front_excess), 1e-6)
                local = shoe.rotate((0, 0, 0), (0, 0, 1), -index * 60)
                bottom = local.intersect(box(diameter / 2 - 6, 7.2, 16.49, 10, .6, .02))
                self.assertGreater(bottom.val().Volume(), 0)
                # The circular master is translated, not rescaled, at larger
                # settings. Measure from that arc's physical center.
                center_x = diameter / 2 - 50
                measured = hypot(bottom.val().BoundingBox().xmax - center_x, 7.2)
                self.assertAlmostEqual(measured, 50, delta=.01)

    def test_wheel_has_two_keyed_rows_at_every_setting_and_physical_labels(self):
        head = build_winding_head(P, 100)
        clearances = []
        for diameter in diameter_settings_mm(P):
            x = diameter / 2 - 3.625
            for angle in range(0, 360, 60):
                for y in (-7.5, 7.5):
                    probe = box(x - 1.75, y - 1.5, -.1, 3.5, 3, 5.2).rotate(
                        (0, 0, 0), (0, 0, 1), angle)
                    clearances.append(probe.val())
                    theta = radians(angle)
                    point = ((x + 2) * cos(theta) - y * sin(theta),
                             (x + 2) * sin(theta) + y * cos(theta), 2.5)
                    self.assertTrue(head.wheel.val().isInside(point))
                glyph = cq.Workplane('XY').text(f'{diameter:g}', 2.8, .2,
                    combine=True).rotate((0, 0, 0), (0, 0, 1), 90).translate(
                    (x, 0, 4.65)).rotate((0, 0, 0), (0, 0, 1), angle)
                self.assertGreater(glyph.val().Volume(), .01)
                clearances.append(glyph.val())
        all_clearances = cq.Workplane('XY').newObject([cq.Compound.makeCompound(clearances)])
        self.assertLess(overlap(head.wheel, all_clearances), 1e-5)

    def test_polygon_socket_transmits_torque_by_shape(self):
        wheel = build_winding_head(P, 100).wheel
        shaft = cq.Workplane('XY').polygon(6, 14).extrude(5)
        self.assertLess(overlap(wheel, shaft), 1e-6)
        self.assertGreater(overlap(wheel, shaft.rotate(
            (0, 0, 0), (0, 0, 1), 30)), .1)

    def test_middle_rails_have_minimal_lateral_clearance_and_positive_stop(self):
        head = build_winding_head(P, 150)
        shoe = head.shoes[0]
        self.assertEqual(head.metadata['wheel_slot_size_mm'], (3.5, 3.0))
        self.assertEqual(head.metadata['tongue_size_mm'], (3.4, 2.9))
        self.assertAlmostEqual(
            head.metadata['nominal_friction_clearance_per_side_mm'], .05)
        for y in (-7.5, 7.5):
            core = box(69.7, y - 1.35, -.7, 3.2, 2.7, 5.4)
            self.assertAlmostEqual(overlap(shoe, core), core.val().Volume(), places=5)
        self.assertLess(overlap(head.wheel, shoe), 1e-6)
        self.assertLess(overlap(head.wheel, shoe.translate((.049, 0, 0))), 1e-6)
        self.assertGreater(overlap(head.wheel, shoe.translate((.051, 0, 0))), .001)
        self.assertLess(overlap(head.wheel, shoe.translate((-.049, 0, 0))), 1e-6)
        self.assertGreater(overlap(head.wheel, shoe.translate((-.051, 0, 0))), .001)
        self.assertLess(overlap(head.wheel, shoe.translate((0, .049, 0))), 1e-6)
        self.assertGreater(overlap(head.wheel, shoe.translate((0, .051, 0))), .001)
        self.assertLess(overlap(head.wheel, shoe.translate((0, -.049, 0))), 1e-6)
        self.assertGreater(overlap(head.wheel, shoe.translate((0, -.051, 0))), .001)
        self.assertGreater(overlap(head.wheel, shoe.translate((0, 0, -.011))), .001)
        self.assertAlmostEqual(shoe.val().BoundingBox().zmin, -1.0, places=6)

    def test_friction_tongues_have_reduced_tip_area_for_lead_in(self):
        master = build_winding_head(P, 150).shoe_master
        for row in (-7.5, 7.5):
            tip = master.intersect(box(-6, row - 1.5, -.99, 5, 3, .1))
            body = master.intersect(box(-6, row - 1.5, -.5, 5, 3, .1))
            self.assertGreater(body.val().Volume(), .95)
            self.assertLess(tip.val().Volume(), body.val().Volume() * .9)

    def test_mismatched_position_is_detected_by_physical_envelope(self):
        head = build_winding_head(P, 150)
        mismatched = head.shoes[0].translate((5, 0, 0))
        # The nominal diameter is defined at the cradle bottom; shoulders
        # deliberately extend beyond it elsewhere in the axial profile.
        excess = (cq.Workplane('XY').circle(90).circle(75.1).extrude(.4)
                  .translate((0, 0, 16.3)))
        self.assertLess(overlap(head.shoes[0], excess), 1e-6)
        self.assertGreater(overlap(mismatched, excess), 1)

    def test_eighteen_real_tape_reliefs_are_clear_and_blockage_is_detectable(self):
        for diameter in (100, 150, 200):
            head = build_winding_head(P, diameter)
            probes = head.metadata['tape_passage_probes']
            self.assertEqual(len(probes), 18)
            for index, probe in enumerate(probes):
                self.assertGreater(probe.val().Volume(), 1)
                self.assertAlmostEqual(probe.val().BoundingBox().zlen, 12)
                local = probe.rotate((0, 0, 0), (0, 0, 1), -(index // 3) * 60)
                self.assertAlmostEqual(local.val().BoundingBox().ylen, 12)
                self.assertLess(overlap(head.shoes[index // 3], probe), 1e-6)
                blocked = head.shoes[index // 3].union(probe)
                self.assertGreater(overlap(blocked, probe), 1)

    def test_actual_tape_angles_describe_physical_corridors_without_nominal_claims(self):
        self.assertEqual(tape_station_angles(P), tuple(range(0, 360, 20)))
        actual = build_winding_head(P, 150).metadata['actual_tape_angles_deg']
        self.assertEqual(len(actual), 18)
        small = build_winding_head(P, 100).metadata['actual_tape_angles_deg']
        large = build_winding_head(P, 200).metadata['actual_tape_angles_deg']
        self.assertGreater(small[2], actual[2])
        self.assertGreater(actual[2], large[2])
        for diameter in diameter_settings_mm(P):
            head = build_winding_head(P, diameter)
            for angle, probe in zip(head.metadata['actual_tape_angles_deg'],
                                    head.metadata['tape_passage_probes']):
                centre = probe.val().Center()
                measured = degrees(atan2(centre.y, centre.x)) % 360
                self.assertAlmostEqual(angle, measured, places=6)

    def test_release_keeps_all_six_shoes_seated(self):
        for diameter in (100, 150, 200):
            head = build_winding_head(P, diameter, released=True)
            self.assertEqual(len(head.shoes), 6)
            self.assertEqual(head.metadata['detached_shoes'], ())
            self.assertEqual(head.state.shoe_radius_mm, diameter / 2)
            for shoe in head.shoes:
                self.assertAlmostEqual(shoe.val().BoundingBox().zmin, -1)
                self.assertLess(overlap(shoe, head.wheel), 1e-6)
            for first, second in combinations(head.shoes, 2):
                self.assertLess(overlap(first, second), 1e-6)

    def test_seated_shoes_allow_continuous_upward_winding_removal(self):
        from windwall.winding_tool_service import _linear_collision, _winding_fixture

        for diameter in (100, 150, 200):
            head = build_winding_head(P, diameter)
            shoe = head.shoes[0]
            # Use the declared 9 mm axial x 1 mm radial winding, including
            # taut connecting spans at larger settings. A uniform 20 mm band
            # covered the protective shoulder even before any motion.
            winding = _winding_fixture(P, diameter)['coil']
            self.assertAlmostEqual(winding.val().BoundingBox().zmin, 12.5)
            self.assertAlmostEqual(winding.val().BoundingBox().zlen, 9)
            self.assertLess(_linear_collision(winding, shoe, (0, 0, 40)), 1e-6)
            self.assertLess(_linear_collision(winding, head.wheel, (0, 0, 40)), 1e-6)
            for neighbor in head.shoes[1:]:
                self.assertLess(_linear_collision(winding, neighbor, (0, 0, 40)), 1e-6)
            for lift in (0, 1, 3, 5, 10, 20, 40):
                moved = winding.translate((0, 0, lift))
                self.assertLess(overlap(head.wheel, moved), 1e-6)
                self.assertLess(overlap(shoe, moved), 1e-6)

    def test_final_contact_mouths_are_rounded(self):
        head = build_winding_head(P, 150)
        faces = head.shoe_master.val().Faces()
        self.assertGreaterEqual(sum(face.geomType() == 'TORUS' for face in faces), 2)
        assert_rounded_mouths(self, head.shoe_master)
        sharp = head.shoe_master.union(box(-.4, 5.8, 10.8, .4, 1, .5))
        with self.assertRaises(AssertionError):
            assert_rounded_mouths(self, sharp)

    def test_print_masters_fit_declared_orientation(self):
        head = build_winding_head(P, 150)
        for shape in (head.wheel, head.shoe_master.rotate(
                (0, 0, 0), (1, 0, 0), 90)):
            bounds = shape.val().BoundingBox()
            self.assertLessEqual(bounds.xlen, 220)
            self.assertLessEqual(bounds.ylen, 220)
        self.assertIn('shoe_master', head.metadata['print_orientations'])

    def test_fresh_shoe_master_raw_release_mesh_has_no_topology_defects(self):
        shoe = build_winding_head(P, 150).shoe_master.rotate(
            (0, 0, 0), (1, 0, 0), 90)
        with temporary_build_directory() as destination:
            mesh = raw_release_mesh(shoe, destination, 'contact_shoe')
        self.assertEqual((mesh.component_count, mesh.boundary_edge_count,
                          mesh.nonmanifold_edge_count, mesh.degenerate_face_count),
                         (1, 0, 0, 0))

    def test_fresh_master_builds_have_stable_geometry_signatures(self):
        import windwall.winding_head as module
        first = build_winding_head(P, 150)
        module._build_wheel.cache_clear()
        module._build_shoe.cache_clear()
        second = build_winding_head(P, 150)
        self.assertEqual(shape_signature(first.wheel), shape_signature(second.wheel))
        self.assertEqual(shape_signature(first.shoe_master), shape_signature(second.shoe_master))

    def test_invalid_diameters_fail_before_geometry(self):
        for diameter in (99, 201, 105, float('nan'), float('inf'), True, '150'):
            with self.subTest(diameter=diameter), self.assertRaises(ValueError):
                build_winding_head(P, diameter)

    def test_closed_tape_ring_clears_the_entire_upward_removal_sweep(self):
        """Real 10 mm tangential strips must clear, including their inner legs."""
        for diameter in (100, 150, 200):
            head = build_winding_head(P, diameter)
            sweeps = []
            outer = cq.Workplane('XY').circle(52).circle(48).extrude(10).translate((0, 0, 12))
            cavity = cq.Workplane('XY').circle(51.75).circle(48.25).extrude(9.5).translate((0, 0, 12.25))
            for offset in (-15, 0, 15):
                width = box(32, offset - 5, 11, 21, 10, 12)
                tape = outer.cut(cavity).intersect(width)
                self.assertTrue(tape.val().isValid())
                self.assertEqual(len(tape.val().Solids()), 1)
                positioned = tape.translate((diameter / 2 - 50, 0, 0))
                self.assertLess(overlap(head.shoes[0], positioned), 1e-6)
                # Both horizontal legs continuously sweep upward over seated
                # shoes. The inner leg must clear every upper bridge too.
                sweep = cq.Workplane('XY').circle(52).circle(48).extrude(50).translate((0, 0, 12))
                sweep = sweep.intersect(box(32, offset - 5, 11, 21, 10, 52))
                for angle in range(0, 360, 60):
                    sweeps.append(sweep.translate((diameter / 2 - 50, 0, 0)).rotate(
                        (0, 0, 0), (0, 0, 1), angle).val())
            all_sweeps = cq.Workplane('XY').newObject([cq.Compound.makeCompound(sweeps)])
            # Rotation symmetry covers each shoe; include all 18 tape rings
            # so the check also catches a neighboring ring in the path.
            self.assertLess(overlap(head.shoes[0], all_sweeps), 1e-6)

    def test_station_identity_order_is_preserved_at_all_eleven_settings(self):
        for diameter in diameter_settings_mm(P):
            angles = build_winding_head(P, diameter).metadata['actual_tape_angles_deg']
            ordered = (*angles[1:], angles[0], 360.0)
            for before, after in zip(ordered, ordered[1:]):
                with self.subTest(diameter=diameter, before=before, after=after):
                    self.assertLess(before, after)

    def test_neighboring_physical_passages_are_disjoint_at_all_eleven_settings(self):
        for diameter in diameter_settings_mm(P):
            head = build_winding_head(P, diameter)
            probes = head.metadata['tape_passage_probes']
            for (first_index, first), (second_index, second) in combinations(enumerate(probes), 2):
                first_box, second_box = first.val().BoundingBox(), second.val().BoundingBox()
                if (first_box.xmin > second_box.xmax or second_box.xmin > first_box.xmax
                        or first_box.ymin > second_box.ymax or second_box.ymin > first_box.ymax):
                    continue
                with self.subTest(diameter=diameter, first=first_index, second=second_index):
                    self.assertLess(overlap(first, second), 1e-6)
            all_probes = cq.Workplane('XY').newObject([
                cq.Compound.makeCompound([probe.val() for probe in probes])])
            self.assertLess(overlap(head.shoes[0], all_probes), 1e-6)
