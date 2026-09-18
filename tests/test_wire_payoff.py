from dataclasses import fields, replace
from math import pi
import unittest

import cadquery as cq

from tests.support import temporary_build_directory
from windwall.bearings import build_51105_reference
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters
from windwall.reference_mesh import analyze_binary_stl
from windwall.winding_tool_parameters import WindingToolParameters
from windwall.wire_payoff import build_wire_payoff


def box(x, y, z, center):
    return cq.Workplane('XY').box(x, y, z).translate(center)


def volume_overlap(first, second):
    return first.intersect(second).val().Volume()


def squeeze_tabs(spindle, lower=True):
    """Rigid displaced tongue envelopes; not a material/force simulation."""
    result = spindle
    for sign in (-1, 1):
        region = (box(6, 6, 13.5, (sign * 13.5, 0, 8.25)) if lower
                  else box(4, 4, 9, (sign * 4.5, 0, 25.5)))
        tongue = spindle.intersect(region)
        result = result.cut(region).union(tongue.translate(
            (-sign * (0.6 if lower else 0.4), 0, 0)))
    return result


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


class WirePayoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design_parameters = DesignParameters()
        cls.parts = build_wire_payoff(WindingToolParameters(), cls.design_parameters)

    def test_payoff_is_free_running_and_contains_no_brake_parts(self):
        parts = build_wire_payoff(WindingToolParameters(), DesignParameters())
        self.assertFalse(hasattr(parts, 'adjuster'))
        self.assertAlmostEqual(parts.platter.val().BoundingBox().xlen, 150.0)
        self.assertEqual(parts.metadata['pilot'],
                         {'diameter_mm': 15.0, 'height_mm': 20.0})
        self.assertNotIn('brake', ' '.join(parts.metadata['owned_members']).lower())

    def assert_inventory(self, parts):
        expected = {'base', 'spindle', 'lower_washer', 'bearing',
                    'upper_washer', 'platter'}
        self.assertEqual(set(parts.metadata['owned_members']), expected)
        self.assertEqual({field.name for field in fields(parts)}, expected | {'metadata'})
        for name in ('brake', 'felt', 'spring', 'adjuster', 'screw', 'nut'):
            self.assertNotIn(name, ' '.join(parts.metadata['owned_members']))

    def assert_load_path(self, parts):
        for supporting, supported in ((parts.base, parts.lower_washer),
                                       (parts.lower_washer, parts.bearing),
                                       (parts.bearing, parts.upper_washer),
                                       (parts.upper_washer, parts.platter)):
            self.assertLess(volume_overlap(supporting, supported), 1e-6)
            self.assertAlmostEqual(supporting.val().distance(supported.val()), 0, places=6)
            # A 0.05 mm axial probe checks actual annular face coverage.
            bearing = self.design_parameters.bearings
            area = pi * ((bearing.thrust_outer_diameter_mm / 2)**2
                         - (bearing.thrust_bore_diameter_mm / 2)**2)
            fraction = volume_overlap(
                supporting, supported.translate((0, 0, -0.05))) / (area * 0.05)
            self.assertGreater(fraction, 0.75)

    def assert_radial_support(self, parts):
        for dx, dy in ((0.25, 0), (-0.25, 0), (0, 0.25), (0, -0.25)):
            self.assertGreater(volume_overlap(parts.base,
                               parts.lower_washer.translate((dx, dy, 0))), 0.01)
            self.assertGreater(volume_overlap(parts.spindle,
                               parts.upper_washer.translate((dx, dy, 0))), 0.01)
        for washer in (parts.lower_washer, parts.upper_washer):
            self.assertLess(volume_overlap(parts.spindle, washer), 1e-6)

    def assert_free_motion(self, parts):
        # Conservative solids of revolution cover every angle, including
        # angles between the explicit rigid-motion samples below.
        pilot_radius = self.design_parameters.bearings.thrust_rotating_pilot_diameter_mm / 2
        spindle_sweep = (cq.Workplane('XY').circle(pilot_radius).extrude(28.5)
                         .translate((0, 0, 1.5)))
        spindle_sweep = spindle_sweep.union(
            cq.Workplane('XY').circle(13.0).extrude(2).translate((0, 0, 2.8)))
        platter_sweep = cq.Workplane('XY').circle(75).extrude(24).translate((0, 0, 19))
        for actual, envelope in ((parts.spindle, spindle_sweep),
                                  (parts.platter, platter_sweep)):
            self.assertLess(actual.cut(envelope).val().Volume(), 1e-6)
            self.assertLess(volume_overlap(envelope, parts.base), 1e-6)
            self.assertGreater(envelope.val().distance(parts.base.val()), 0.05)
        # The base is rotationally symmetric within the moving spindle radius;
        # the platter has an axisymmetric exterior. Include intermediate angles
        # to exercise the two detents and square drive, too.
        for angle in range(0, 360, 30):
            for moving in (parts.platter, parts.spindle, parts.upper_washer):
                rotated = moving.rotate((0, 0, 0), (0, 0, 1), angle)
                self.assertLess(volume_overlap(rotated, parts.base), 1e-6)
                self.assertGreater(rotated.val().distance(parts.base.val()), 0.05)
        # Retaining either member must leave positive axial freedom above
        # the weight-supported position, rather than clamping the bearing.
        for moving, fixed in ((parts.platter, parts.spindle),
                              (parts.spindle, parts.base)):
            self.assertLess(volume_overlap(moving, fixed), 1e-6)
            self.assertLess(volume_overlap(moving.translate((0, 0, 0.15)), fixed), 1e-6)
        self.assertLess(volume_overlap(parts.spindle.translate((0, 0, -0.3)),
                                       parts.base), 1e-6)

    def assert_service_path(self, parts):
        upper_released = squeeze_tabs(parts.spindle, lower=False)
        for distance in (0, 0.5, 1, 2, 4, 8, 12, 25):
            moved = parts.platter.translate((0, 0, distance))
            for fixed in (upper_released, parts.base, parts.upper_washer):
                self.assertLess(volume_overlap(moved, fixed), 1e-6)
        lower_released = squeeze_tabs(parts.spindle)
        for distance in (0, 0.5, 1, 2, 4, 8, 12, 20, 35):
            moved = lower_released.translate((0, 0, distance))
            for fixed in (parts.base, parts.lower_washer, parts.bearing, parts.upper_washer):
                self.assertLess(volume_overlap(moved, fixed), 1e-6)
        # With the spindle withdrawn, each purchased member lifts vertically.
        for member in (parts.upper_washer, parts.bearing, parts.lower_washer):
            for distance in (0, 0.5, 1, 3, 12, 25):
                self.assertLess(volume_overlap(member.translate((0, 0, distance)),
                                               parts.base), 1e-6)

    def assert_stable_footprint(self, parts):
        # Entire centered platter/load projection lies within the bench face.
        footprint = cq.Workplane('XY').circle(75).extrude(0.1)
        self.assertAlmostEqual(volume_overlap(parts.base, footprint),
                               footprint.val().Volume(), places=5)
        bench_face = parts.base.faces('<Z').val()
        self.assertGreater(bench_face.BoundingBox().xlen, 170)
        self.assertGreater(bench_face.BoundingBox().ylen, 170)
        mass_center = parts.base.val().Center()
        self.assertLess(abs(mass_center.x), 1e-6)
        self.assertLess(abs(mass_center.y), 1e-6)
        # With a 1 N horizontal feed at 43 mm and no wire-roll mass,
        # PLA alone must give at least twice the overturning moment.
        printed_mass_kg = sum(getattr(parts, name).val().Volume()
                              for name in ('base', 'spindle', 'platter')) * 1.24e-6 * 0.35
        arm_mm = min(bench_face.BoundingBox().xlen,
                     bench_face.BoundingBox().ylen) / 2
        self.assertGreater(printed_mass_kg * 9.81 * arm_mm, 2 * 43)

    def test_inventory_and_51105_members_are_canonical_and_separate(self):
        self.assert_inventory(self.parts)
        reference = build_51105_reference(DesignParameters())
        for output, original in (('lower_washer', 'housing_washer'),
                                 ('bearing', 'rolling_envelope'),
                                 ('upper_washer', 'shaft_washer')):
            member = getattr(self.parts, output)
            canonical = reference.parts[original].translate((0, 0, 8))
            self.assertAlmostEqual(volume_overlap(member, canonical),
                                   canonical.val().Volume(), places=5)
        self.assertEqual(self.parts.metadata['owned_members'], {
            'base': 'stationary', 'spindle': 'rotating',
            'lower_washer': 'stationary', 'bearing': 'bearing_internal',
            'upper_washer': 'rotating', 'platter': 'rotating'})

    def test_axial_contacts_and_radial_centering_are_real(self):
        self.assert_load_path(self.parts)
        self.assert_radial_support(self.parts)

    def test_full_turn_and_axial_float_are_clear(self):
        self.assert_free_motion(self.parts)

    def test_snap_retention_and_keyed_drive_are_physical(self):
        self.assertGreater(volume_overlap(self.parts.spindle.translate((0, 0, 1)),
                                          self.parts.base), 0.01)
        self.assertGreater(volume_overlap(self.parts.platter.translate((0, 0, 1.2)),
                                          self.parts.spindle), 0.01)
        turned = self.parts.platter.rotate((0, 0, 0), (0, 0, 1), 10)
        self.assertGreater(volume_overlap(turned, self.parts.spindle), 0.1)

    def test_spindle_hangs_from_platter_before_reaching_stationary_base(self):
        # Gravity must not let the floating spindle bottom on the stationary
        # blind bore and add an unintended axial rubbing face.
        hanging = self.parts.spindle.translate((0, 0, -0.35))
        self.assertGreater(volume_overlap(hanging, self.parts.platter), 0.01)
        self.assertLess(volume_overlap(hanging, self.parts.base), 1e-6)
        self.assertGreater(hanging.val().distance(self.parts.base.val()), 0.1)

    def test_top_service_routes_clear_with_released_snap_envelopes(self):
        self.assert_service_path(self.parts)

    def test_footprint_and_optional_clamp_lands_support_light_feed(self):
        self.assert_stable_footprint(self.parts)
        for x in (-85, 85):
            land = box(12, 50, 1, (x, 0, 7.5))
            self.assertAlmostEqual(volume_overlap(self.parts.base, land),
                                   land.val().Volume(), places=5)
            self.assertGreater(land.val().distance(self.parts.platter.val()), 5)

    def test_printed_masters_and_pilot_geometry(self):
        for name in ('base', 'spindle', 'platter'):
            shape = getattr(self.parts, name).val()
            self.assertTrue(shape.isValid(), name)
            self.assertEqual(len(shape.Solids()), 1, name)
            self.assertGreater(shape.Volume(), 0, name)
            bounds = shape.BoundingBox()
            self.assertLessEqual(max(bounds.xlen, bounds.ylen, bounds.zlen), 220)
            self.assertIn(name, self.parts.metadata['print_orientation'])
        pilot = cq.Workplane('XY').circle(7.5).extrude(19).translate((0, 0, 23))
        # The blind socket ends below the pilot tip and never breaks its side.
        # At least 1.5 mm of uninterrupted pilot wall surrounds the socket.
        outer_shell = pilot.cut(cq.Workplane('XY').circle(6.0).extrude(50))
        self.assertAlmostEqual(volume_overlap(outer_shell, self.parts.platter),
                               outer_shell.val().Volume(), places=5)
        self.assertAlmostEqual(self.parts.platter.val().BoundingBox().zmax, 43)
        self.assertTrue(any(face.geomType() == 'CONE'
                            for face in self.parts.platter.val().Faces()))

    def test_fresh_spindle_raw_release_mesh_is_closed_manifold(self):
        spindle = build_wire_payoff(WindingToolParameters(), DesignParameters()).spindle
        spindle = spindle.rotate((0, 0, 0), (0, 1, 0), 90)
        with temporary_build_directory() as destination:
            mesh = raw_release_mesh(spindle, destination, 'printed_spindle')
        self.assertEqual((mesh.component_count, mesh.boundary_edge_count,
                          mesh.nonmanifold_edge_count, mesh.degenerate_face_count),
                         (1, 0, 0, 0))

    def test_fresh_builds_have_stable_geometry_signatures(self):
        rebuilt = build_wire_payoff(WindingToolParameters(), DesignParameters())
        for name in ('base', 'spindle', 'platter', 'lower_washer', 'bearing', 'upper_washer'):
            first, second = getattr(self.parts, name).val(), getattr(rebuilt, name).val()
            self.assertIsNot(first, second)
            self.assertAlmostEqual(first.Volume(), second.Volume(), places=7)
            self.assertAlmostEqual(first.Area(), second.Area(), places=7)
            self.assertEqual(len(first.Faces()), len(second.Faces()))
            self.assertLess(first.cut(second).Volume(), 1e-7)

    def test_rejects_old_setting_argument(self):
        with self.assertRaises(TypeError):
            build_wire_payoff(WindingToolParameters(), brake_setting=0)

    def test_parameter_variants_preserve_buildable_interfaces(self):
        varied = build_wire_payoff(replace(WindingToolParameters(),
            platter_diameter_mm=160, spool_pilot_diameter_mm=16,
            spool_pilot_height_mm=22), DesignParameters())
        self.assertAlmostEqual(varied.platter.val().BoundingBox().xlen, 160)
        self.assertAlmostEqual(varied.platter.val().BoundingBox().zmax, 45)
        for changes in ({'spool_pilot_diameter_mm': 14},
                        {'spool_pilot_height_mm': 9},
                        {'platter_diameter_mm': 180},
                        {'print_bed_mm': 180, 'maximum_diameter_mm': 180}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                build_wire_payoff(replace(WindingToolParameters(), **changes))

    def test_rejects_completed_platter_that_exceeds_the_print_bed(self):
        for pilot_diameter, requested_bed in ((221, 220), (221, 300), (201, 200)):
            with self.subTest(pilot=pilot_diameter, bed=requested_bed):
                parameters = replace(WindingToolParameters(),
                    spool_pilot_diameter_mm=pilot_diameter, print_bed_mm=requested_bed)
                with self.assertRaisesRegex(ValueError, 'platter.*print-bed'):
                    build_wire_payoff(parameters, DesignParameters())

    def test_completed_printed_parts_fit_at_the_permitted_bed_boundary(self):
        parts = build_wire_payoff(replace(WindingToolParameters(),
            spool_pilot_diameter_mm=200, print_bed_mm=200), DesignParameters())
        self.assertAlmostEqual(parts.platter.val().BoundingBox().xlen, 200)
        self.assertAlmostEqual(parts.platter.val().BoundingBox().ylen, 200)
        printed = (parts.base, parts.spindle.rotate((0, 0, 0), (0, 1, 0), 90),
                   parts.platter)
        for shape in printed:
            bounds = shape.val().BoundingBox()
            self.assertLessEqual(bounds.xlen, 200 + 1e-6)
            self.assertLessEqual(bounds.ylen, 200 + 1e-6)

    def test_mutations_detect_displaced_washers_and_missing_support(self):
        for name in ('lower_washer', 'upper_washer'):
            for vector in ((1, 0, 0), (0, 0, 0.2)):
                with self.subTest(name=name, vector=vector), self.assertRaises(AssertionError):
                    mutated = replace(self.parts, **{
                        name: getattr(self.parts, name).translate(vector)})
                    self.assert_load_path(mutated)
                    self.assert_radial_support(mutated)
        with self.assertRaises(AssertionError):
            self.assert_load_path(replace(self.parts,
                platter=self.parts.platter.translate((0, 0, 0.3))))
        with self.assertRaises(AssertionError):
            self.assert_radial_support(replace(self.parts,
                spindle=self.parts.spindle.translate((0, 0, -20))))

    def test_mutations_detect_clamp_collision_blocked_service_and_small_base(self):
        clamped_base = self.parts.base.union(
            cq.Workplane('XY').circle(13.2).circle(12.6).extrude(0.3)
            .translate((0, 0, 4.3)))
        with self.assertRaises(AssertionError):
            self.assert_free_motion(replace(self.parts, base=clamped_base))
        with self.assertRaises(AssertionError):
            self.assert_free_motion(replace(self.parts,
                base=self.parts.base.union(box(10, 10, 15, (60, 0, 15)))))
        with self.assertRaises(AssertionError):
            self.assert_service_path(replace(self.parts,
                base=self.parts.base.union(box(60, 60, 1, (0, 0, 48)))))
        with self.assertRaises(AssertionError):
            self.assert_stable_footprint(replace(self.parts,
                base=self.parts.base.intersect(box(100, 100, 100, (0, 0, 0)))))
        for name in ('brake', 'felt', 'spring', 'adjuster', 'screw', 'nut'):
            with self.subTest(name=name), self.assertRaises(AssertionError):
                self.assert_inventory(replace(self.parts, metadata={
                    **self.parts.metadata, 'owned_members': {
                        **self.parts.metadata['owned_members'], name: 'stationary'}}))


if __name__ == '__main__':
    unittest.main()
