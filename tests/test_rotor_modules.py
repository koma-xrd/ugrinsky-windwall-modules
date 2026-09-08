"""Actual solids catch obstructed joints, lost blade shape, and false fit metadata."""

from dataclasses import FrozenInstanceError, replace
import unittest

import cadquery as cq

from windwall.blade_profile import build_blade_stage
from windwall.drivers import build_joint_interface
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

    def test_outer_skin_is_retained_and_added_pads_stay_in_the_end_fitting_envelope(self):
        source = build_blade_stage(DEFAULT_PARAMETERS)
        outer = cq.Workplane('XY').circle(62).circle(36.001).extrude(69.2998).translate((0,0,0.7001))
        # The support disc is radius 36; the independently measured rounded
        # receiver pads extend to radius 36.352. Retain their loaded walls.
        outside_fittings = cq.Workplane('XY').circle(62).circle(36.4).extrude(69.2998).translate((0,0,0.7001))
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

    def test_top_closure_pilots_have_material_and_open_access(self):
        top = self.modules['top'].shape
        for x in (-24,24):
            pilot = cq.Workplane('XY').center(x,0).circle(1.1499).extrude(7.9999).translate((0,0,62.0001))
            self.assertLess(top.intersect(pilot).val().Volume(), 0.01)
            self.assertTrue(top.val().isInside((x+3,0,66)))
            self.assertTrue(top.val().isInside((x,0,61.99)))

    def test_base_has_carrier_fused_below_its_shaft_flange(self):
        base = self.modules['base'].shape
        self.assertAlmostEqual(base.val().BoundingBox().zmin, -13, places=5)
        self.assertTrue(base.val().isInside((12,0,-1.5)))
        self.assertTrue(base.val().isInside((44.5,0,-8.5)))

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

    def test_locked_adjacent_modules_and_actual_screwdriver_access_are_clear(self):
        depth = module_joint_depth_mm(DEFAULT_PARAMETERS)
        for lower_name, upper_name in (('base','standard'), ('standard','standard'), ('standard','top')):
            lower = self.modules[lower_name].shape
            upper = self.modules[upper_name].shape.translate((0,0,70))
            self.assertLess(lower.intersect(upper).val().Volume(), 0.01)
            for axis in self.joint.screw_axes:
                access = axis.access.rotate((0,0,0), (0,0,1), 100).translate((0,0,70-depth))
                for part in (lower, upper):
                    self.assertLess(part.intersect(access).val().Volume(), 0.01,
                                    f'{lower_name}/{upper_name}: tool angle {axis.angle_deg}')

    def test_male_pilots_and_female_clearance_holes_survive_integration(self):
        depth = module_joint_depth_mm(DEFAULT_PARAMETERS)
        for axis in self.joint.screw_axes:
            for name in ('standard','top'):
                self.assertLess(self.modules[name].shape.intersect(
                    axis.pilot.rotate((0,0,0), (0,0,1), 100).translate((0,0,-depth))).val().Volume(), 0.01)
            for name in ('base','standard'):
                self.assertLess(self.modules[name].shape.intersect(
                    axis.clearance.rotate((0,0,0), (0,0,1), 100).translate((0,0,70-depth))).val().Volume(), 0.01)

    def test_whole_module_lock_path_is_clear(self):
        lower = self.modules['standard'].shape
        upper = self.modules['top'].shape
        for travel in (0, 0.5, 6, 12, 17.5, 18):
            moving = upper.rotate((0,0,0), (0,0,1), travel-18).translate((0,0,70+0.45*(travel/18-1)))
            self.assertLess(lower.intersect(moving).val().Volume(), 0.01, f'travel {travel}')
        for lift in (1,4,8,16,24):
            moving = upper.rotate((0,0,0), (0,0,1), -18).translate((0,0,69.55+lift))
            self.assertLess(lower.intersect(moving).val().Volume(), 0.01, f'lift {lift}')

    def test_invalid_module_fit_or_blocked_tool_parameters_are_rejected(self):
        p = DEFAULT_PARAMETERS
        for changed in (
            replace(p, shaft=replace(p.shaft, clearance_hole_diameter_mm=8.2)),
            replace(p, modules=replace(p.modules, end_support_thickness_mm=2)),
            replace(p, modules=replace(p.modules, washer_seat_depth_mm=-1)),
            replace(p, modules=replace(p.modules, washer_seat_depth_mm=4)),
            replace(p, rotor=replace(p.rotor, stage_height_mm=20)),
            replace(p, modules=replace(p.modules, joint_phase_deg=0)),
        ):
            with self.assertRaises(ValueError):
                build_standard_module(changed)


if __name__ == '__main__':
    unittest.main()
