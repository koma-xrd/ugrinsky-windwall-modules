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
            self.assertAlmostEqual(model.shape.val().BoundingBox().zmax, 70, places=5)

    def test_active_middle_is_open_except_for_small_m8_guide(self):
        for name, model in self.modules.items():
            self.assertFalse(model.shape.val().isInside((0,9,35)), name)
            self.assertFalse(model.shape.val().isInside((5.2,0,35)), name)
            self.assertTrue(model.shape.val().isInside((5.2,0,2)), name)
        joint_z = 70-module_joint_depth_mm(DEFAULT_PARAMETERS)
        self.assertTrue(self.modules['base'].shape.val().isInside((5.2,0,joint_z-1)))
        self.assertTrue(self.modules['standard'].shape.val().isInside((5.2,0,joint_z-1)))
        self.assertTrue(self.modules['top'].shape.val().isInside((5.2,0,69)))

    def test_outer_skin_is_retained_and_added_pads_stay_in_the_end_fitting_envelope(self):
        source = build_blade_stage(DEFAULT_PARAMETERS)
        # Sample exterior blade-wall material away from the end fittings.
        outer = cq.Workplane('XY').circle(62).circle(36.001).extrude(68.9498).translate((0,0,1.0501))
        outside_fittings = cq.Workplane('XY').circle(62).circle(36.4).extrude(68.9498).translate((0,0,1.0501))
        for name, model in self.modules.items():
            with self.subTest(module=name):
                self.assertLess(source.cut(model.shape).intersect(outer).val().Volume(), 0.01)
                self.assertLess(model.shape.cut(source).intersect(outside_fittings).val().Volume(), 0.01)

    def test_top_washer_bears_on_a_flat_upper_plate_below_an_exposed_nut(self):
        top = self.modules['top']
        self.assertIsNone(top.nut_pocket_across_flats_mm)
        self.assertAlmostEqual(top.washer_seat_diameter_mm, 24.6)
        # The full washer annulus bears on the common z=70 top plane; only
        # the M8 clearance bore interrupts that planar support surface.
        top_layer = (cq.Workplane('XY').circle(11.9999).circle(4.4001)
                     .extrude(0.1).translate((0,0,69.9)))
        above_top = top_layer.translate((0,0,0.1001))
        self.assertLess(top_layer.cut(top.shape).val().Volume(), 0.01)
        self.assertLess(top.shape.intersect(above_top).val().Volume(), 0.01)
        wrench = cq.Workplane('XY').circle(11.5).extrude(15).translate((0,0,70.0001))
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

    def test_base_has_closed_0_4_mm_bearing_labyrinth(self):
        p = DEFAULT_PARAMETERS
        base = self.modules['base'].shape
        interface = base_bearing_interface(p)
        plate_bottom = upper_magnet_face_z_mm(p)
        plate_top = plate_bottom + p.generator.carrier_disc_thickness_mm

        self.assertAlmostEqual(interface['labyrinth_inner_radius_mm'], 24.5)
        self.assertAlmostEqual(interface['labyrinth_outer_radius_mm'], 27.0)
        self.assertAlmostEqual(
            interface['labyrinth_inner_radius_mm']
            - p.bearings.thrust_housing_seat_diameter_mm / 2 - 3,
            0.4,
        )

        cover_boss = (cq.Workplane('XY')
                      .circle(p.bearings.thrust_housing_seat_diameter_mm / 2 + 3)
                      .circle(p.bearings.thrust_housing_seat_diameter_mm / 2)
                      .extrude(interface['boss_clearance_top_z_mm']
                               - interface['bearing_floor_z_mm'])
                      .translate((0, 0, interface['bearing_floor_z_mm'])))
        self.assertLess(base.intersect(cover_boss).val().Volume(), 0.01)

        for angle in range(0, 360, 10):
            direction = angle * pi / 180
            wall_radius = 25.5
            x, y = wall_radius * cos(direction), wall_radius * sin(direction)
            for z in (plate_top - 0.1, -7.0, -4.0, interface['shoulder_z_mm'] + 0.1):
                with self.subTest(angle=angle, z=z):
                    self.assertTrue(base.val().isInside((x, y, z)))

        cap_probe_z = interface['boss_clearance_top_z_mm'] + 0.1
        upper_plate_probe = (cq.Workplane('XY').circle(26.9).circle(26.0)
                             .extrude(0.2).translate((0, 0, cap_probe_z)))
        self.assertGreater(base.intersect(upper_plate_probe).val().Volume(), 4)
        cap_bridge_probe = (cq.Workplane('XY')
                            .circle(interface['labyrinth_inner_radius_mm'] + 0.1)
                            .circle(p.bearings.thrust_outer_diameter_mm / 2 + 0.1)
                            .extrude(0.2).translate((0, 0, cap_probe_z)))
        self.assertLess(cap_bridge_probe.cut(base).val().Volume(), 0.01)

    def test_base_blade_walls_reach_the_magnet_plate_for_torque_transfer(self):
        base = self.modules['base'].shape.val()
        for x,y in ((-5,30),(0,-35),(0,35),(5,-30)):
            self.assertTrue(base.isInside((x,y,-7.9)),(x,y,'plate contact'))
            self.assertTrue(base.isInside((x,y,-4.0)),(x,y,'continuous wall'))

    def test_base_blade_roots_are_supported_to_plate_print_plane(self):
        """The actual root contour reaches the print plane without broad ribs."""
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

        for source_z in (0.01,):
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

    def test_base_carrier_disc_keeps_its_nominal_axial_thickness(self):
        """Catch a blade-support workaround that thickens the circular plate."""
        p = DEFAULT_PARAMETERS
        source = build_blade_stage(p).val()
        base = self.modules['base'].shape.val()
        plate_bottom = upper_magnet_face_z_mm(p)
        plate_top = plate_bottom+p.generator.carrier_disc_thickness_mm
        radius = p.generator.carrier_diameter_mm/2-1
        probes = []
        for angle in range(0,360,2):
            x = radius*cos(angle*pi/180)
            y = radius*sin(angle*pi/180)
            if not source.isInside((x,y,0.01)):
                probes.append((x,y))
        self.assertTrue(probes)
        self.assertTrue(any(base.isInside((x,y,plate_top-0.2)) for x,y in probes))
        self.assertTrue(all(not base.isInside((x,y,plate_top+0.2)) for x,y in probes))

    def test_base_blade_reinforcement_reaches_the_central_carrier_ring(self):
        # The 51105 cover boss reserves the bearing keepout; blade-form walls
        # join the annular carrier immediately outside that stationary keepout.
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

    def test_locked_modules_use_plain_flush_blade_ends(self):
        """Catch tongue additions and groove cuts at the exterior blade interface."""
        p = DEFAULT_PARAMETERS
        height = p.rotor.stage_height_mm
        source = build_blade_stage(p)
        outer = cq.Workplane('XY').circle(62).circle(36).extrude(.05)
        for lower_name, upper_name in (('base', 'standard'), ('standard', 'standard'),
                                       ('standard', 'top')):
            lower = self.modules[lower_name].shape.val()
            upper = self.modules[upper_name].shape.rotate(
                (0, 0, 0), (0, 0, 1), p.blade.twist_deg
            ).translate((0, 0, height)).val()
            for phase in (64, 244):
                angle = phase*pi/180
                x = 59.5*cos(angle)-.5*sin(angle)
                y = 59.5*sin(angle)+.5*cos(angle)
                with self.subTest(pair=(lower_name, upper_name), phase=phase):
                    self.assertTrue(lower.isInside((x, y, height-.001)))
                    self.assertFalse(lower.isInside((x, y, height+.001)))
            for phase in (p.blade.twist_deg, p.blade.twist_deg+180):
                angle = phase*pi/180
                x = 59.5*cos(angle)-.5*sin(angle)
                y = 59.5*sin(angle)+.5*cos(angle)
                with self.subTest(pair=(lower_name, upper_name), phase=phase):
                    self.assertFalse(upper.isInside((x, y, height-.001)))
                    self.assertTrue(upper.isInside((x, y, height+.001)))
            lower_slice = lower.intersect(outer.translate((0, 0, height-.05)).val()).Volume()
            upper_slice = upper.intersect(outer.translate((0, 0, height)).val()).Volume()
            source_lower_slice = source.intersect(
                outer.translate((0, 0, height-.05))
            ).val().Volume()
            source_upper_slice = source.rotate(
                (0, 0, 0), (0, 0, 1), p.blade.twist_deg
            ).translate((0, 0, height)).intersect(outer.translate((0, 0, height))).val().Volume()
            self.assertAlmostEqual(lower_slice, source_lower_slice, places=2)
            self.assertAlmostEqual(upper_slice, source_upper_slice, places=2)

    def test_raised_ccw_locking_then_axial_seating_only_meets_elastic_latch(self):
        lower = self.modules['standard'].shape
        upper = self.modules['top'].shape
        snap = (cq.Workplane('XY').circle(22).circle(20.4).extrude(3)
                .translate((0,0,70-module_joint_depth_mm(DEFAULT_PARAMETERS)+3.9)))
        for travel in (0, .5, 3, 6, 9, 12, 15, 17.5, 18):
            moving = upper.rotate((0,0,0), (0,0,1), 42+travel).translate((0,0,71))
            collision = lower.intersect(moving).val()
            if collision.Volume() >= .01:
                self.assertLess(collision.cut(snap.val()).Volume(), .01, travel)
        for lift in (1, .8, .5, .25, 0):
            moving = upper.rotate((0,0,0),(0,0,1),60).translate((0,0,70+lift))
            collision = lower.intersect(moving).val()
            if collision.Volume() >= .01:
                self.assertLess(collision.cut(snap.val()).Volume(), .01, lift)
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
