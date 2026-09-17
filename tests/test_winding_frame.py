"""Physical engagement and service checks for the screwless printed stand."""

import unittest
from dataclasses import fields, replace
from math import pi

import cadquery as cq

from windwall.parameters import DEFAULT_PARAMETERS
from windwall.winding_frame import WindingFrameParts, build_winding_frame
from windwall.winding_tool_parameters import WindingToolParameters
from windwall.winding_head import build_winding_head
from windwall.winding_tool_service import _linear_collision


P = WindingToolParameters()


def local(shape):
    return shape.translate((0, 0, -130)).rotate((0, 0, 0), (1, 0, 0), -90)


def box(x, y, z, dx, dy, dz):
    return cq.Workplane('XY').box(dx, dy, dz, centered=False).translate((x, y, z))


def cylinder(radius, z, length):
    return cq.Workplane('XY').circle(radius).extrude(length).translate((0, 0, z))


def overlap(a, b):
    return a.intersect(b).val().Volume()


def signature(shape):
    solid = shape.val()
    return (round(solid.Volume(), 5), len(solid.Edges()),
            tuple(sorted((f.geomType(), round(f.Area(), 5)) for f in solid.Faces())))


class WindingFrameTests(unittest.TestCase):
    def test_contract_exposes_only_printed_mechanism_and_two_bearings(self):
        self.assertEqual(tuple(field.name for field in fields(WindingFrameParts)),
                         ('base', 'tower', 'bearing_retainers', 'bearings', 'shaft',
                          'snap_collars', 'crank', 'grip', 'metadata'))

    @classmethod
    def setUpClass(cls):
        cls.frame = build_winding_frame(P, DEFAULT_PARAMETERS)

    def test_every_print_master_is_single_solid_and_fits_documented_orientation(self):
        f = self.frame
        shapes = dict(base=f.base, tower=f.tower, bearing_retainer=f.bearing_retainers[0],
                      shaft=f.shaft, snap_collar=f.snap_collars[0], crank=f.crank, grip=f.grip)
        for name, shape in shapes.items():
            with self.subTest(name=name):
                self.assertTrue(shape.val().isValid())
                self.assertEqual(len(shape.val().Solids()), 1)
                self.assertGreater(shape.val().Volume(), 0)
                pose = f.metadata['print_rotations_deg'][name]
                printed = local(shape)
                for axis, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), pose):
                    printed = printed.rotate((0, 0, 0), axis, angle)
                bounds = printed.val().BoundingBox()
                self.assertLessEqual(max(bounds.xlen, bounds.ylen), 220)
        self.assertEqual(signature(f.bearing_retainers[0]), signature(f.bearing_retainers[1]))
        self.assertEqual(signature(f.snap_collars[0]), signature(f.snap_collars[1]))

    def assert_bearing_retained(self, bearing, tower, retainers, outward):
        self.assertLess(overlap(bearing, tower), 1e-6)
        self.assertGreater(overlap(bearing.translate((.3, 0, 0)), tower), .01)
        self.assertGreater(overlap(bearing.translate((0, 0, -outward)), tower), .01)
        self.assertGreater(sum(overlap(bearing.translate((0, 0, outward)), r)
                               for r in retainers), .01)

    def test_bearings_have_radial_seats_shoulders_and_removable_outer_ring_clips(self):
        f = self.frame
        self.assertEqual(len(f.bearings), 2)
        tower = local(f.tower)
        clips = tuple(local(r) for r in f.bearing_retainers)
        for bearing, outward in zip(f.bearings, (-1, 1)):
            bearing = local(bearing)
            self.assertAlmostEqual(bearing.val().Volume(), pi * (11**2 - 4**2) * 7, places=4)
            self.assert_bearing_retained(bearing, tower, clips, outward)
            with self.assertRaises(AssertionError):
                self.assert_bearing_retained(bearing, tower, (), outward)
            with self.assertRaises(AssertionError):
                self.assert_bearing_retained(bearing, tower,
                    tuple(r.translate((30, 0, 0)) for r in clips), outward)
            with self.assertRaises(AssertionError):
                self.assert_bearing_retained(bearing.translate((0, 0, 3)), tower, clips, outward)
        for clip in clips:
            self.assertLess(overlap(clip, tower), 1e-6)
            for dz in (-.4, .4):
                self.assertGreater(overlap(clip.translate((0, 0, dz)), tower), .01)
            # Squeeze ears through the top service opening before axial removal.
            self.assertLess(overlap(tower, box(-5, 12, clip.val().BoundingBox().zmin, 10, 12, 1.5)), 1e-6)

    def test_only_outer_ring_lands_and_inner_ring_collars_receive_axial_load(self):
        tower = local(self.frame.tower)
        for bearing in self.frame.bearings:
            z = local(bearing).val().BoundingBox().zmin
            seal = cylinder(9.6, z - .6, 8.2).cut(cylinder(5.25, z - .7, 8.4))
            for shape in (tower, *(local(r) for r in self.frame.bearing_retainers),
                          *(local(c) for c in self.frame.snap_collars)):
                self.assertLess(overlap(seal, shape), 1e-6)
        rear = local(self.frame.bearings[0])
        for dz in (-.5, .5):
            self.assertLess(overlap(rear.translate((0, 0, dz)), tower), 1e-6)
            self.assertLess(sum(overlap(rear.translate((0, 0, dz)), local(r))
                                for r in self.frame.bearing_retainers), 1e-6)

    def assert_shaft_located(self, shaft, collars):
        bearing = local(self.frame.bearings[1])
        self.assertEqual(len(collars), 2)
        for collar, direction in zip(collars, (1, -1)):
            self.assertLess(overlap(shaft, collar), 1e-6)
            self.assertGreater(overlap(shaft.translate((0, 0, direction * .4)), collar), .01)
            self.assertGreater(overlap(collar.translate((0, 0, direction * .4)), bearing), .01)

    def test_two_accessible_snap_collars_locate_one_bearing_bidirectionally(self):
        shaft = local(self.frame.shaft)
        collars = tuple(local(c) for c in self.frame.snap_collars)
        self.assert_shaft_located(shaft, collars)
        with self.assertRaises(AssertionError):
            self.assert_shaft_located(shaft.translate((0, 0, 3)), collars)
        with self.assertRaises(AssertionError):
            self.assert_shaft_located(shaft, ())
        for collar in collars:
            z = collar.val().BoundingBox().zmin
            access = box(-8, 5.2, z - .1, 16, 18, 2)
            self.assertLess(overlap(local(self.frame.tower), access), 1e-6)
            with self.assertRaises(AssertionError):
                self.assertLess(overlap(local(self.frame.tower).union(access), access), 1e-6)

    def test_journals_are_unbroken_eight_mm_and_shaft_can_exit_forward(self):
        shaft = local(self.frame.shaft)
        for z in (-40, -28):
            core = cylinder(4, z, 7)
            self.assertAlmostEqual(overlap(shaft, core), core.val().Volume(), places=5)
            weakened = shaft.cut(box(-5, -.5, z + 3, 10, 1, 1))
            with self.assertRaises(AssertionError):
                self.assertAlmostEqual(overlap(weakened, core), core.val().Volume(), places=5)
        # Every shaft point behind the front shoulder fits through an 8 mm bore.
        rear_stock = shaft.intersect(box(-20, -20, -90, 40, 40, 71.5))
        outside_bore = cylinder(20, -90, 71.5).cut(cylinder(4.001, -91, 74))
        self.assertLess(overlap(rear_stock, outside_bore), 1e-6)

    def test_wheel_and_crank_have_positive_drives_and_releasable_axial_hooks(self):
        shaft = local(self.frame.shaft)
        wheel = build_winding_head(P, 150).wheel
        crank = local(self.frame.crank)
        for driven in (wheel, crank):
            self.assertLess(overlap(shaft, driven), 1e-6)
            self.assertGreater(overlap(shaft, driven.rotate((0, 0, 0), (0, 0, 1), 30)), .1)
            self.assertLess(overlap(shaft.translate((0, 0, 100)), driven), 1e-6)
            with self.assertRaises(AssertionError):
                self.assertGreater(overlap(shaft.translate((0, 0, 100)),
                    driven.rotate((0, 0, 0), (0, 0, 1), 30)), .1)
        self.assertGreater(overlap(wheel.translate((0, 0, .6)), shaft), .01)
        self.assertGreater(overlap(wheel.translate((0, 0, -.6)), shaft), .01)
        self.assertGreater(overlap(crank.translate((0, 0, -.6)), shaft), .01)
        self.assertGreater(overlap(crank.translate((0, 0, .6)), shaft), .01)

    def test_base_tower_joint_has_positive_keys_and_releasable_snap_hooks(self):
        base, tower = local(self.frame.base), local(self.frame.tower)
        self.assertLess(overlap(base, tower), 1e-6)
        for movement in ((.5, 0, 0), (-.5, 0, 0), (0, 0, .5), (0, 0, -.5), (0, .5, 0)):
            self.assertGreater(overlap(base, tower.translate(movement)), .01)
        separated = tower.translate((0, 30, 0))
        with self.assertRaises(AssertionError):
            self.assertGreater(overlap(base, separated.translate((0, .5, 0))), .01)
        for x in (-24, 17):
            self.assertLess(overlap(base, box(x, -112, -40, 7, 12, 18)), 1e-6)

    def test_rear_shoe_latches_and_complete_withdrawal_clear_the_stand(self):
        fixed = (local(self.frame.base), local(self.frame.tower))
        for diameter in (100, 150, 200):
            head = build_winding_head(P, diameter)
            for angle in range(0, 360, 60):
                access = box(diameter / 2 - 10, -9, -16, 4, 18, 12).rotate(
                    (0, 0, 0), (0, 0, 1), angle)
                for part in fixed:
                    self.assertLess(overlap(part, access), 1e-6)
            # Entire continuous withdrawal lies forward of the stand's front plane.
            front_limit = min(local(self.frame.base).val().BoundingBox().ymax, 0)
            self.assertLess(front_limit, -110)
            self.assertLess(local(self.frame.tower).val().BoundingBox().zmax, -16)
            for shoe in head.shoes:
                self.assertGreater(shoe.val().BoundingBox().zmin, -5)
                for part in fixed:
                    self.assertLess(overlap(part, shoe), 1e-6)
                    self.assertLess(_linear_collision(shoe, part, (0, 0, 40)), 1e-6)

    def test_full_crank_grip_sweep_clears_stand_wheel_clamps_and_bench(self):
        # Exact rotational superset: discs cover the arm and grip at every angle.
        sweep = cylinder(63, -87, 34)
        fixed = (local(self.frame.base), local(self.frame.tower),
                 build_winding_head(P, 200).wheel,
                 box(-80, -140, -75, 20, 40, 55), box(60, -140, -75, 20, 40, 55),
                 box(-200, -145, -120, 400, 15, 200))
        for part in fixed:
            self.assertLess(overlap(sweep, part), 1e-6)
        for shape in (local(self.frame.crank), local(self.frame.grip)):
            self.assertLess(shape.cut(sweep).val().Volume(), 1e-6)
        collision = local(self.frame.tower).translate((0, 0, -35))
        with self.assertRaises(AssertionError):
            self.assertLess(overlap(sweep, collision), 1e-6)

    def test_grip_rotates_and_is_retained_by_compressible_printed_journal_end(self):
        crank, grip = local(self.frame.crank), local(self.frame.grip)
        self.assertLess(overlap(crank, grip), 1e-6)
        for angle in (30, 90, 180):
            self.assertLess(overlap(crank, grip.rotate((52, 0, 0), (52, 0, 1), angle)), 1e-6)
        for direction in (-1, 1):
            self.assertGreater(overlap(crank, grip.translate((0, 0, direction * 1.5))), .01)
        release_slot = box(51, -5, -85, 2, 10, 15)
        self.assertLess(overlap(crank, release_slot), 1e-6)

    def test_fresh_frame_geometry_has_stable_export_signatures(self):
        fresh = build_winding_frame(P, DEFAULT_PARAMETERS)
        for name in ('base', 'tower', 'shaft', 'crank', 'grip'):
            self.assertEqual(signature(getattr(self.frame, name)), signature(getattr(fresh, name)))
        for name in ('bearing_retainers', 'snap_collars'):
            self.assertEqual(tuple(map(signature, getattr(self.frame, name))),
                             tuple(map(signature, getattr(fresh, name))))

    def test_snap_ends_compress_within_their_release_bores(self):
        shaft, crank = local(self.frame.shaft), local(self.frame.crank)
        # Bounded deflection surrogate for each free tip, preserving its solid
        # cross-section. This is a clearance proof, not an elastic simulation.
        for side in (-1, 1):
            tip_box = box(6, -2, 5, 3, 4, 3)
            if side < 0:
                tip_box = tip_box.mirror('YZ')
            tip = shaft.intersect(tip_box).translate((-side * .6, 0, 0))
            wheel_socket = cq.Workplane('XY').polygon(6, 14.4).extrude(10)
            with self.subTest(part='wheel', side=side):
                self.assertLess(tip.cut(wheel_socket).val().Volume(), 1e-6)
            grip_tip = crank.intersect(box(52 + (1.25 if side > 0 else -6), -6, -85,
                                          4.75, 12, 3)).translate((-side * .6, 0, 0))
            grip_bore = cylinder(4.3, -86, 6).translate((52, 0, 0))
            with self.subTest(part='grip', side=side):
                self.assertLess(grip_tip.cut(grip_bore).val().Volume(), 1e-6)

    def test_base_hooks_clear_after_low_deflection_and_keys_withdraw_vertically(self):
        base, tower = local(self.frame.base), local(self.frame.tower)
        for side in (-1, 1):
            hook = tower.intersect(box(16 if side > 0 else -18, -120, -32, 2, 6, 8))
            released = hook.translate((-side * .3, .5, 0))
            self.assertLess(overlap(base, released), 1e-6)

    def test_clamp_lands_are_solid_and_four_optional_holes_are_open(self):
        base = local(self.frame.base)
        for x in (-68, 68):
            for z in (-64, 12):
                bore = cylinder(3.4, 0, 10).rotate((0, 0, 0), (1, 0, 0), 90).translate((x, -121, z))
                self.assertLess(overlap(base, bore), 1e-6)
            land = box(x - 5, -129, -48, 10, 6, 20)
            self.assertAlmostEqual(overlap(base, land), land.val().Volume(), places=5)

    def test_shaft_and_grip_flexures_have_filled_root_radii(self):
        shaft, crank = local(self.frame.shaft), local(self.frame.crank)
        self.assertGreater(overlap(shaft, box(5.91, -.5, -9.95, .05, 1, .04)), .001)
        self.assertGreater(overlap(crank, box(53.16, -.5, -63.09, .04, 1, .04)), .001)

    def test_grip_and_crank_latches_have_long_open_deflection_spans(self):
        crank = local(self.frame.crank)
        self.assertLess(overlap(crank, box(51.5, -1, -70, 1, 2, 6.5)), 1e-6)
        self.assertLess(overlap(crank, box(-1, 5, -62, 2, .5, 6)), 1e-6)

    def test_crank_snap_beams_have_filled_root_radii(self):
        crank = local(self.frame.crank)
        for side in (-1, 1):
            probe = box(-.5, 4.82, -55.58, 1, .03, .04)
            if side < 0:
                probe = probe.mirror('XZ')
            self.assertGreater(overlap(crank, probe), .001)

    def test_oversize_seat_cannot_silently_remove_positive_clip_engagement(self):
        invalid = replace(DEFAULT_PARAMETERS, bearings=replace(DEFAULT_PARAMETERS.bearings,
                          radial_housing_seat_diameter_mm=26))
        with self.assertRaisesRegex(ValueError, 'seat'):
            build_winding_frame(P, invalid)

    def test_compressed_bearing_clips_clear_the_entire_outward_withdrawal(self):
        tower = local(self.frame.tower)
        for installed, direction, outer_face in zip(
                self.frame.bearing_retainers, (-1, 1), (-44, -18.5)):
            clip = local(installed)
            bounds = clip.val().BoundingBox()
            # A bounded planar contraction of the actual CAD clip reduces the
            # 11.9 mm ring radius by 0.9 mm. Preserve the actual uncompressed
            # ears as an additional conservative envelope; squeezing them
            # inward cannot need a wider or taller opening.
            scale = 11 / 11.9
            contraction = cq.Matrix([[scale, 0, 0, 0], [0, scale, 0, 0],
                                    [0, 0, 1, 0], [0, 0, 0, 1]])
            compressed = cq.Workplane('XY').newObject([
                clip.val().transformGeometry(contraction)])
            ears = clip.intersect(box(-5, 10, bounds.zmin, 10, 5, bounds.zlen))
            compressed = compressed.union(ears)
            self.assertAlmostEqual(compressed.val().BoundingBox().ymax, 14.4, places=6)
            final = compressed.translate((0, 0, direction * 6))
            if direction < 0:
                self.assertLess(final.val().BoundingBox().zmax, outer_face)
            else:
                self.assertGreater(final.val().BoundingBox().zmin, outer_face)
            # The clip is a constant-section extrusion: extending its axial
            # thickness produces the exact continuous six-millimeter sweep.
            stretch = cq.Matrix([[1, 0, 0, 0], [0, 1, 0, 0],
                                 [0, 0, (bounds.zlen + 6) / bounds.zlen, 0],
                                 [0, 0, 0, 1]])
            sweep = cq.Workplane('XY').newObject([
                compressed.translate((0, 0, -bounds.zmin)).val().transformGeometry(stretch)
            ]).translate((0, 0, bounds.zmin + min(0, direction * 6)))
            with self.subTest(direction=direction):
                self.assertLess(overlap(tower, sweep), 1e-6)
            # Restoring a thin lip at the exit must break the same path check.
            blocked = tower.union(box(-5, 11.1, outer_face - .1, 10, 4, .2))
            with self.assertRaises(AssertionError):
                self.assertLess(overlap(blocked, sweep), 1e-6)


if __name__ == '__main__':
    unittest.main()
