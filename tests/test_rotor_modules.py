"""Actual solids catch obstructed joints, lost blade shape, and false fit metadata."""

from dataclasses import FrozenInstanceError, replace
from math import cos, hypot, pi, sin, sqrt
import unittest

import cadquery as cq

from windwall.blade_profile import build_blade_stage
from windwall.drivers import build_joint_interface
from windwall.generator import base_bearing_interface, upper_magnet_face_z_mm
from windwall.parameters import DEFAULT_PARAMETERS
from windwall.rotor_modules import (build_base_module, build_standard_module,
                                    build_top_module, module_joint_depth_mm)


class RotorModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = {name: builder(DEFAULT_PARAMETERS) for name, builder in (
            ('base', build_base_module), ('standard', build_standard_module),
            ('top', build_top_module))}
        cls.joint = build_joint_interface(DEFAULT_PARAMETERS)

    def test_all_module_types_are_single_valid_solids_with_frozen_metadata(self):
        for model in self.modules.values():
            self.assertTrue(model.shape.val().isValid())
            self.assertEqual(len(model.shape.val().Solids()), 1)
            with self.assertRaises(FrozenInstanceError):
                model.shaft_clearance_radial_mm = 0

    def test_shaft_hole_is_continuous_and_metadata_matches_clearance(self):
        shaft = cq.Workplane('XY').circle(4.3999).extrude(110).translate((0,0,-30))
        for model in self.modules.values():
            self.assertAlmostEqual(model.shaft_clearance_radial_mm, 0.4)
            self.assertLess(model.shape.intersect(shaft).val().Volume(), 0.01)

    def test_all_modules_preserve_shared_active_middle_and_nominal_height(self):
        source = build_blade_stage(DEFAULT_PARAMETERS)
        active = cq.Workplane('XY').circle(62).circle(20).extrude(40).translate((0,0,5))
        for name, model in self.modules.items():
            self.assertLess(source.cut(model.shape).intersect(active).val().Volume(), 0.01, name)
            self.assertLess(model.shape.cut(source).intersect(active).val().Volume(), 0.01)
            self.assertAlmostEqual(model.shape.val().BoundingBox().zmax,
                                   70 if name == 'top' else 70.8, places=5)

    def test_active_middle_is_open_except_for_small_m8_guide(self):
        for name, model in self.modules.items():
            self.assertFalse(model.shape.val().isInside((0,9,35)), name)
            self.assertFalse(model.shape.val().isInside((5.2,0,35)), name)
            self.assertTrue(model.shape.val().isInside((5.2,0,2)), name)
        joint_z = 70-module_joint_depth_mm(DEFAULT_PARAMETERS)
        self.assertTrue(self.modules['base'].shape.val().isInside((5.2,0,joint_z-1)))
        self.assertTrue(self.modules['standard'].shape.val().isInside((5.2,0,joint_z-1)))
        self.assertTrue(self.modules['top'].shape.val().isInside((5.2,0,69)))

    def test_blade_wall_is_strengthened_for_tongue_and_groove_prototype(self):
        self.assertEqual(DEFAULT_PARAMETERS.blade.wall_thickness_mm, 2.0)
        self.assertAlmostEqual(self.modules['base'].shape.val().BoundingBox().zmax,70.8,places=5)
        self.assertAlmostEqual(self.modules['standard'].shape.val().BoundingBox().zmax,70.8,places=5)

    def test_outer_skin_is_retained_and_added_pads_stay_in_the_end_fitting_envelope(self):
        source = build_blade_stage(DEFAULT_PARAMETERS)
        # V4.3's lower 0.95 mm is the mating groove; intact skin begins above it.
        outer = cq.Workplane('XY').circle(62).circle(36.001).extrude(69.0498).translate((0,0,0.9501))
        outside_fittings = cq.Workplane('XY').circle(62).circle(36.4).extrude(69.0498).translate((0,0,0.9501))
        for name, model in self.modules.items():
            with self.subTest(module=name):
                self.assertLess(source.cut(model.shape).intersect(outer).val().Volume(), 0.01)
                self.assertLess(model.shape.cut(source).intersect(outside_fittings).val().Volume(), 0.01)

    def test_top_washer_bears_below_an_exposed_serviceable_nut(self):
        top = self.modules['top']
        self.assertIsNone(top.nut_pocket_across_flats_mm)
        self.assertAlmostEqual(top.washer_seat_diameter_mm, 24.6)
        # A 24 mm washer enters from above and bears at z=69.5. A 2 mm
        # washer puts the exposed nut bottom at z=71.5, above the blade ends.
        washer_access = cq.Workplane('XY').circle(12).circle(4.4).extrude(25).translate((0,0,69.5001))
        self.assertLess(top.shape.intersect(washer_access).val().Volume(), 0.01)
        bearing = cq.Workplane('XY').circle(11.9999).circle(4.4001).extrude(2.99).translate((0,0,66.5))
        self.assertLess(bearing.cut(top.shape).val().Volume(), 0.01)
        wrench = cq.Workplane('XY').circle(11.5).extrude(15).translate((0,0,71.5))
        self.assertLess(top.shape.intersect(wrench).val().Volume(), 0.01)
        self.assertTrue(top.shape.val().isInside((6,0,68)))
        for name in ('base', 'standard'):
            self.assertIsNone(self.modules[name].washer_seat_diameter_mm)
        self.assertIsNone(self.modules['standard'].nut_pocket_across_flats_mm)

    def test_modules_have_no_retainer_screw_corridors_or_driver_keys(self):
        self.assertEqual(self.joint.screw_axes, ())
        self.assertEqual(self.joint.driver_centers, ())
        for model in self.modules.values():
            self.assertIsNone(model.retainer_screw_count)

    def test_base_has_carrier_fused_below_its_shaft_flange(self):
        base = self.modules['base'].shape
        self.assertAlmostEqual(base.val().BoundingBox().zmin, -13, places=5)
        self.assertTrue(base.val().isInside((12,0,-1.5)))
        self.assertTrue(base.val().isInside((44.5,0,-8.5)))

    def test_base_blade_walls_reach_the_magnet_plate_for_torque_transfer(self):
        base = self.modules['base'].shape.val()
        for x,y in ((-5,30),(0,-35),(0,35),(5,-30)):
            self.assertTrue(base.isInside((x,y,-7.9)),(x,y,'plate contact'))
            self.assertTrue(base.isInside((x,y,-4.0)),(x,y,'continuous wall'))

    def test_base_blade_roots_are_supported_to_plate_print_plane(self):
        """Catch a support that follows only the untwisted z=0 blade section."""
        p = DEFAULT_PARAMETERS
        source = build_blade_stage(p).val()
        base = self.modules['base'].shape.val()
        interface = base_bearing_interface(p)
        plate_bottom = upper_magnet_face_z_mm(p)
        plate_radius = p.generator.carrier_diameter_mm/2
        protected_radius = interface['boss_clearance_radius_mm']
        magnet_centers = tuple(
            (p.generator.magnet_pitch_radius_mm*cos(2*pi*index/p.generator.magnet_pocket_count),
             p.generator.magnet_pitch_radius_mm*sin(2*pi*index/p.generator.magnet_pocket_count))
            for index in range(p.generator.magnet_pocket_count)
        )

        for source_z in (1, 9, 17.5, 26, 35, 44, 52.5, 61, 69):
            section = cq.Workplane(obj=source).section(source_z).val()
            sample = cq.Compound.makeCompound([
                cq.Solid.extrudeLinear(face.outerWire(), face.innerWires(), cq.Vector(0,0,0.1))
                for face in section.Faces()])
            probes = []
            for x in range(-50, 51, 5):
                for y in range(-50, 51, 5):
                    if not protected_radius + 1 < hypot(x, y) < plate_radius - 1:
                        continue
                    if any(hypot(x-center_x, y-center_y) < p.generator.magnet_pocket_diameter_mm/2+1
                           for center_x,center_y in magnet_centers):
                        continue
                    if sample.isInside((x, y, source_z+0.05)):
                        probes.append((x,y))
            self.assertGreater(len(probes), 0, source_z)
            for x,y in probes:
                with self.subTest(source_z=source_z, point=(x,y)):
                    for support_z in (plate_bottom+0.1, plate_bottom/2, -0.1):
                        self.assertTrue(base.isInside((x,y,support_z)), support_z)

        shaft = cq.Workplane('XY').circle(p.shaft.clearance_hole_diameter_mm/2).extrude(-plate_bottom+2).translate((0,0,plate_bottom-1))
        nut = (cq.Workplane('XY').polygon(6,2*p.manufacturing.nut_pocket_across_flats_mm/sqrt(3))
               .extrude(p.manufacturing.nut_pocket_depth_mm)
               .translate((0,0,interface['nut_bottom_z_mm'])))
        boss = (cq.Workplane('XY').circle(protected_radius)
                .circle(p.bearings.thrust_rotating_pilot_diameter_mm/2)
                .extrude(interface['shoulder_z_mm']-plate_bottom)
                .translate((0,0,plate_bottom)))
        boss = boss.union(cq.Workplane('XY').circle(protected_radius)
                          .circle(p.bearings.thrust_outer_diameter_mm/2)
                          .extrude(interface['boss_clearance_top_z_mm']-interface['shoulder_z_mm'])
                          .translate((0,0,interface['shoulder_z_mm'])))
        pockets = (cq.Workplane('XY').pushPoints(magnet_centers)
                   .circle(p.generator.magnet_pocket_diameter_mm/2)
                   .extrude(p.generator.magnet_pocket_depth_mm)
                   .translate((0,0,plate_bottom)))
        for name, protected_volume in (('shaft bore',shaft), ('nut pocket',nut),
                                       ('bearing-boss keepout',boss), ('magnet pockets',pockets)):
            with self.subTest(protected_volume=name):
                self.assertLess(base.intersect(protected_volume.val()).Volume(), 0.01)

    def test_base_blade_reinforcement_reaches_the_central_carrier_ring(self):
        # The 51105 cover boss reserves radius 24.45; blade-form walls join
        # the annular carrier immediately outside that stationary keepout.
        connection_zone = (cq.Workplane('XY').circle(25.6).circle(24.6)
                           .extrude(4).translate((0,0,-7.5)))
        contact = self.modules['base'].shape.intersect(connection_zone)
        self.assertGreater(contact.val().Volume(),20)
        boss_zone = (cq.Workplane('XY').circle(24.4).circle(12.5)
                     .extrude(4).translate((0,0,-7.5)))
        self.assertLess(self.modules['base'].shape.intersect(boss_zone).val().Volume(), 0.01)

    def test_deeper_base_flange_keeps_the_bore_open_to_its_bottom(self):
        p = DEFAULT_PARAMETERS
        changed = replace(p, modules=replace(p.modules, base_shaft_flange_depth_mm=20))
        base = build_base_module(changed).shape
        shaft = cq.Workplane('XY').circle(4.3999).extrude(95).translate((0,0,-21))
        self.assertLess(base.intersect(shaft).val().Volume(), 0.01)

    def test_joint_depth_rejects_invalid_travel_before_calculation(self):
        p = DEFAULT_PARAMETERS
        with self.assertRaises(ValueError):
            module_joint_depth_mm(replace(p, bayonet=replace(p.bayonet, insertion_offset_deg=0)))

    def test_locked_adjacent_modules_are_clear_and_blades_continue_at_sixty_degrees(self):
        for lower_name, upper_name in (('base','standard'), ('standard','standard'), ('standard','top')):
            lower = self.modules[lower_name].shape
            upper = self.modules[upper_name].shape.rotate((0,0,0),(0,0,1),60).translate((0,0,70))
            self.assertLess(lower.intersect(upper).val().Volume(), 0.01)

        source = build_blade_stage(DEFAULT_PARAMETERS)
        lower_tip = source.intersect(cq.Workplane('XY').circle(62).circle(20).extrude(.05).translate((0,0,69.95)))
        upper_root = source.rotate((0,0,0),(0,0,1),60).translate((0,0,70)).intersect(
            cq.Workplane('XY').circle(62).circle(20).extrude(.05).translate((0,0,70)))
        self.assertAlmostEqual(lower_tip.val().Volume(), upper_root.val().Volume(), places=2)

    def test_installed_joint_is_clear_but_rigid_lock_path_requires_physical_validation(self):
        lower = self.modules['standard'].shape
        upper = self.modules['top'].shape
        overlaps = []
        for travel in (0, 0.5, 6, 12, 17.5):
            moving = upper.rotate((0,0,0), (0,0,1), 42+travel).translate((0,0,71))
            overlaps.append(lower.intersect(moving).val().Volume())
        # The tongue-clearing lift also meets the lug roof. This is an observed
        # rigid-envelope limitation, not a simulated elastic insertion proof.
        self.assertGreater(max(overlaps), 0.01)
        locked = upper.rotate((0,0,0), (0,0,1), 60).translate((0,0,70))
        self.assertLess(lower.intersect(locked).val().Volume(), 0.01)
        for lift in (1,4,8,16,24):
            moving = upper.rotate((0,0,0), (0,0,1), 42).translate((0,0,70+lift))
            self.assertLess(lower.intersect(moving).val().Volume(), 0.01, f'lift {lift}')

    def test_invalid_module_fit_or_blocked_tool_parameters_are_rejected(self):
        p = DEFAULT_PARAMETERS
        for changed in (
            replace(p, shaft=replace(p.shaft, clearance_hole_diameter_mm=8.2)),
            replace(p, modules=replace(p.modules, end_support_thickness_mm=2)),
            replace(p, modules=replace(p.modules, washer_seat_depth_mm=-1)),
            replace(p, modules=replace(p.modules, washer_seat_depth_mm=4)),
            replace(p, rotor=replace(p.rotor, stage_height_mm=20)),
        ):
            with self.assertRaises(ValueError):
                build_standard_module(changed)


if __name__ == '__main__':
    unittest.main()
