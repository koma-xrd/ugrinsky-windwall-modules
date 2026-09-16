"""Physical regressions for the reusable pin-adjustable wheel and shoes."""

import unittest
from dataclasses import fields
from itertools import combinations
from math import atan2, cos, degrees, radians, sin

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
                   if abs(edge.Center().z - 11) < .01 or abs(edge.Center().z - 23) < .01]
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
            excess = cq.Workplane('XY').circle(diameter / 2 + 30).circle(
                diameter / 2 + .001).extrude(40).translate((0, 0, 5))
            band = cq.Workplane('XY').circle(diameter / 2 + .001).circle(
                diameter / 2 - .05).extrude(40).translate((0, 0, 5))
            for shoe in head.shoes:
                self.assertTrue(shoe.val().isValid())
                self.assertLess(overlap(shoe, excess), 1e-6)
                self.assertGreater(overlap(shoe, band), .001)

    def test_wheel_has_two_keyed_rows_at_every_setting_and_physical_labels(self):
        head = build_winding_head(P, 100)
        clearances = []
        for diameter in diameter_settings_mm(P):
            x = diameter / 2 - 8
            for angle in range(0, 360, 60):
                for y in (-5, 5):
                    probe = box(x - .9, y - 1.5, -.1, 1.8, 3, 5.2).rotate(
                        (0, 0, 0), (0, 0, 1), angle)
                    clearances.append(probe.val())
                    theta = radians(angle)
                    point = ((x + 2.5) * cos(theta) - y * sin(theta),
                             (x + 2.5) * sin(theta) + y * cos(theta), 2.5)
                    self.assertTrue(head.wheel.val().isInside(point))
                glyph = cq.Workplane('XY').text(f'{diameter:g}', 2.8, .2,
                    combine=True).rotate((0, 0, 0), (0, 0, 1), 90).translate(
                    (x, 10, 4.65)).rotate((0, 0, 0), (0, 0, 1), angle)
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

    def test_pins_are_present_and_latches_retain_until_released(self):
        head = build_winding_head(P, 150)
        shoe = head.shoes[0]
        for y in (-5, 5):
            core = box(66.2, y - .5 if y > 0 else y + .1, .2, 1.6, .4, 4.5)
            self.assertAlmostEqual(overlap(shoe, core), core.val().Volume(), places=5)
            missing = shoe.cut(box(65, y - 3, -5, 4, 6, 10.2))
            self.assertLess(overlap(missing, core), 1e-6)
        self.assertLess(overlap(head.wheel, shoe), 1e-6)
        self.assertGreater(overlap(head.wheel, shoe.translate((0, 0, 1))), .01)
        missing_latches = shoe.cut(box(65, -8, -2, 4, 16, 2))
        self.assertLess(overlap(head.wheel, missing_latches.translate((0, 0, 1))), 1e-6)
        self.assertGreater(overlap(head.wheel, shoe.rotate(
            (67, 0, 0), (67, 0, 1), 10)), .01)
        # Both tabs project behind the wheel; a finger probe reaches each tail.
        for y in (-5, 5):
            access = box(65, y - 3, -8, 4, 6, 4)
            self.assertLess(overlap(head.wheel, access), 1e-6)
        partial = shoe.translate((0, 0, 6))
        self.assertLess(overlap(partial, box(66.2, 4.5, .2, 1.6, .4, 1)), .01)

    def test_retention_beams_have_filled_root_radii(self):
        master = build_winding_head(P, 150).shoe_master
        for row in (-5, 5):
            y = row + .43 if row > 0 else row - .49
            root = box(-8.5, y, 4.43, 1, .06, .06)
            self.assertGreater(overlap(master, root), .002)

    def test_mismatched_position_is_detected_by_physical_envelope(self):
        head = build_winding_head(P, 150)
        mismatched = head.shoes[0].translate((5, 0, 0))
        excess = cq.Workplane('XY').circle(90).circle(75.1).extrude(40)
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

    def test_complete_removal_releases_coil_and_preserves_six_service_occurrences(self):
        for diameter in (100, 150, 200):
            head = build_winding_head(P, diameter, released=True)
            self.assertEqual(head.shoes, ())
            self.assertEqual(len(head.metadata['detached_shoes']), 6)
            self.assertGreaterEqual(diameter / 2 - head.state.release_radius_mm, 2)
            for shoe in head.metadata['detached_shoes']:
                self.assertGreater(shoe.val().BoundingBox().zmin, 30)
                self.assertLess(overlap(shoe, head.wheel), 1e-6)
            for first, second in combinations(head.metadata['detached_shoes'], 2):
                self.assertLess(overlap(first, second), 1e-6)
            outer = cq.Workplane('XY').circle(diameter / 2 + 20).circle(
                diameter / 2 - 2).extrude(40)
            insufficient = build_winding_head(P, diameter).shoes[0].translate((-.5, 0, 10))
            self.assertGreater(overlap(insufficient, outer), .1)

    def test_pressed_latches_allow_axial_pin_withdrawal_inside_wound_envelope(self):
        for diameter in (100, 150, 200):
            head = build_winding_head(P, diameter)
            # The interference lobe lies 0.2 mm outside the hole. Its compressed
            # envelope is bounded by trimming that 0.25 mm strip on each tab.
            compressed = head.shoes[0]
            x = diameter / 2 - 8
            for row in (-5, 5):
                y = row + 1.65 if row > 0 else row - 3
                compressed = compressed.cut(box(x - 1.1, y, -2, 2.2, 1.35, 2))
            winding = cq.Workplane('XY').circle(diameter / 2 + 1).circle(
                diameter / 2 + .02).extrude(20).translate((0, 0, 8))
            for lift in (0, 1, 3, 5, 10, 20, 40):
                moved = compressed.translate((0, 0, lift))
                self.assertLess(overlap(head.wheel, moved), 1e-6)
                self.assertLess(overlap(winding, moved), 1e-6)

    def test_final_contact_mouths_are_rounded(self):
        head = build_winding_head(P, 150)
        faces = head.shoe_master.val().Faces()
        self.assertGreaterEqual(sum(face.geomType() == 'TORUS' for face in faces), 2)
        assert_rounded_mouths(self, head.shoe_master)
        sharp = head.shoe_master.union(box(-.4, 1, 11, .4, 2, .5))
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

    def test_closed_tape_ring_clears_the_entire_forward_removal_sweep(self):
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
                # Horizontal tape legs sweep overlapping axial intervals.
                # Their exact union over 40 mm inverse withdrawal is the full
                # curved strip, rather than a 1 mm tangential surrogate.
                sweep = cq.Workplane('XY').circle(52).circle(48).extrude(50).translate((0, 0, -28))
                sweep = sweep.intersect(box(32, offset - 5, -29, 21, 10, 52))
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
