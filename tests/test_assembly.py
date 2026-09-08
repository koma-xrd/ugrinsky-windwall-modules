"""Real assembly solids catch wrong placements, hidden collisions and blocked service."""

from dataclasses import replace
import unittest

import cadquery as cq

from windwall.assembly import (audit_rotor_assembly, build_exploded_rotor_assembly,
                               build_locked_rotor_assembly)
from windwall.parameters import DEFAULT_PARAMETERS
from windwall.top_closure import build_top_closure


class AssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assembly = build_locked_rotor_assembly(DEFAULT_PARAMETERS)
        cls.audit = audit_rotor_assembly(cls.assembly)

    def test_loaded_locked_stack_seats_on_printed_bodies_with_retainer_clearance(self):
        a = self.assembly
        self.assertEqual((a.base_count, a.standard_count, a.top_count), (1, 5, 1))
        self.assertEqual(a.aerodynamic_stage_count, 7)
        self.assertEqual([round(s.z_mm, 2) for s in a.stages],
                         [0, 69.65, 139.3, 208.95, 278.6, 348.25, 417.9])
        self.assertLess(a.maximum_stage_angle_error_deg(), 0.01)
        self.assertAlmostEqual(a.aerodynamic_height_mm(), 487.9, places=5)
        self.assertAlmostEqual(self.audit['joint_seating_travel_mm'], 0.35, places=5)
        self.assertLess(self.audit['maximum_seated_joint_intersection_mm3'], 0.01)
        self.assertLess(self.audit['maximum_preseat_retainer_intersection_mm3'], 0.01)
        self.assertLess(self.audit['maximum_seated_retainer_intersection_mm3'], 0.01)
        self.assertGreater(self.audit['minimum_pilot_thread_engagement_mm3'], 0.05)
        self.assertEqual(len(a.parts), 34)
        self.assertEqual(len(a.parts['base'].val().Solids()), 1)

    def test_continuous_m8_shaft_clears_all_rotating_and_stationary_parts(self):
        shaft = self.assembly.parts['shaft'].val()
        box = shaft.BoundingBox()
        self.assertAlmostEqual(box.zmin, -60.5, places=5)
        self.assertAlmostEqual(box.zmax, 499.2, places=5)
        self.assertAlmostEqual(box.xlen, 8, places=5)
        self.assertAlmostEqual(box.ylen, 8, places=5)
        for name, shape in self.assembly.parts.items():
            if name != 'shaft':
                self.assertLess(shape.intersect(self.assembly.parts['shaft']).val().Volume(), 0.01, name)

    def test_complete_assembly_has_only_explicit_thread_forming_overlap(self):
        self.assertLess(self.audit['unplanned_intersection_mm3'], 0.01)
        self.assertEqual(len(self.audit['thread_forming_contacts']), 14)
        self.assertTrue(all(v > 0 for v in self.audit['thread_forming_contacts'].values()))

    def test_every_unique_joint_inserts_and_locks_with_actual_module_bodies(self):
        self.assertEqual(set(self.audit['joint_paths']), {'base/standard','standard/standard','standard/top'})
        for result in self.audit['joint_paths'].values():
            self.assertGreaterEqual(result['insertion_sample_count'], 17)
            self.assertGreaterEqual(result['locking_sample_count'], 37)
            self.assertLess(result['maximum_insertion_intersection_mm3'], 0.01)
            self.assertLess(result['maximum_locking_intersection_mm3'], 0.01)
            self.assertGreater(result['ccw_overtravel_intersection_mm3'], 0.05)
            self.assertLess(result['cw_release_intersection_mm3'], 0.01)
            self.assertGreater(result['locked_pull_intersection_mm3'], 0.05)
        self.assertGreater(self.audit['driver_ccw_stop_intersection_mm3'], 0.05)
        self.assertGreater(self.audit['bayonet_ccw_stop_intersection_mm3'], 0.05)
        self.assertLess(self.audit['driver_cw_release_intersection_mm3'], 0.01)
        self.assertGreaterEqual(self.audit['bayonet_running_clearance_mm'], 0.25)

    def test_twelve_radial_retainers_have_shaft_head_and_tool_access(self):
        self.assertEqual(len(self.audit['radial_retainer_access']), 12)
        for result in self.audit['radial_retainer_access']:
            self.assertIn(result['angle_deg'], (170,280))
            self.assertLess(result['tool_intersection_mm3'], 0.01)
            self.assertLess(result['head_intersection_mm3'], 0.01)
            self.assertLess(result['unplanned_shank_intersection_mm3'], 0.01)

    def test_closure_ties_both_blade_ends_and_uses_existing_pilot_centers(self):
        closure = self.assembly.parts['top_closure']
        self.assertTrue(closure.val().isValid())
        self.assertEqual(len(closure.val().Solids()),1)
        self.assertLess(closure.cut(closure.rotate((0,0,0),(0,0,1),180)).val().Volume(), 0.01)
        for x in (-24,24):
            hole = cq.Workplane('XY').center(x,0).circle(1.6499).extrude(5).translate((0,0,487.9))
            self.assertLess(closure.intersect(hole).val().Volume(), 0.01)
            self.assertTrue(closure.val().isInside((x+3,0,489.9)))
        # Intersect a thin slice lowered onto the top: material must connect to
        # both outer blade tips, beyond the hub/closure screw pads.
        contact = closure.translate((0,0,-0.01)).intersect(self.assembly.parts['top'])
        for sign in (-1,1):
            half = cq.Workplane('XY').box(100,200,1,centered=(False,True,False)).translate((0 if sign == 1 else -100,0,487.4))
            outside = cq.Workplane('XY').circle(62).circle(36).extrude(1).translate((0,0,487.4))
            self.assertGreater(contact.intersect(half).intersect(outside).val().Volume(),0.05)

    def test_closure_preserves_independent_washer_load_and_upward_service(self):
        self.assertLess(self.audit['closure_removal_intersection_mm3'],0.01)
        self.assertLess(self.audit['top_wrench_access_intersection_mm3'],0.01)
        self.assertLess(self.audit['top_washer_removal_intersection_mm3'],0.01)
        self.assertGreaterEqual(self.audit['closure_hardware_clearance_mm'],0.249)
        self.assertAlmostEqual(self.assembly.parts['top_washer'].val().BoundingBox().zmin,487.4,places=5)
        self.assertAlmostEqual(self.assembly.parts['top_nut'].val().BoundingBox().zmin,489.4,places=5)
        self.assertEqual(len(self.audit['closure_retainer_access']),2)
        for item in self.audit['closure_retainer_access']:
            self.assertLess(item['tool_intersection_mm3'],0.01)
            self.assertAlmostEqual(item['pilot_engagement_mm'],7,places=5)

    def test_generator_keeps_gaps_and_no_duplicate_upper_carrier(self):
        self.assertNotIn('upper_carrier',self.assembly.parts)
        self.assertAlmostEqual(self.audit['upper_generator_air_gap_mm'],1.5,places=5)
        self.assertAlmostEqual(self.audit['lower_generator_air_gap_mm'],1.5,places=5)
        self.assertLess(self.audit['generator_rotating_stationary_intersection_mm3'],0.01)

    def test_exploded_stages_are_withdrawn_at_entry_angle(self):
        exploded = build_exploded_rotor_assembly(DEFAULT_PARAMETERS, locked=self.assembly)
        for index, stage in enumerate(exploded.stages):
            self.assertAlmostEqual(stage.z_mm, index*(70+15-0.45),places=5)
            self.assertEqual(stage.angle_deg, -18 if index else 0)
        for lower, upper in zip(exploded.stages,exploded.stages[1:]):
            self.assertLess(exploded.parts[lower.name].intersect(exploded.parts[upper.name]).val().Volume(),0.01)
            self.assertGreater(exploded.parts[upper.name].val().BoundingBox().zmin,
                               exploded.parts[lower.name].val().BoundingBox().zmax)

    def test_report_exposes_twist_discontinuity_and_unverified_physical_fits(self):
        self.assertEqual(self.audit['internal_blade_twist_deg'],60)
        self.assertEqual(self.audit['seam_phase_jump_deg'],-60)
        self.assertFalse(self.audit['aerodynamic_seam_continuous'])
        self.assertFalse(self.audit['physical_fit_verified'])
        self.assertFalse(self.audit['print_ready'])

    def test_invalid_composition_and_unsafe_closure_parameters_fail_early(self):
        p = DEFAULT_PARAMETERS
        with self.assertRaises(ValueError):
            build_locked_rotor_assembly(replace(p,rotor=replace(p.rotor,standard_stage_count=4)))
        for changed in (replace(p.closure,plate_thickness_mm=3),
                        replace(p.closure,rod_projection_mm=-1),
                        replace(p.closure,roof_thickness_mm=2)):
            with self.assertRaises(ValueError):
                build_top_closure(replace(p,closure=changed))

    def test_longer_rod_projection_raises_cover_roof_without_loading_washer(self):
        p = DEFAULT_PARAMETERS
        closure = build_top_closure(replace(p,closure=replace(p.closure,rod_projection_mm=9)))
        self.assertAlmostEqual(closure.val().BoundingBox().zmax,90.55,places=5)
        keepout = cq.Workplane('XY').circle(12).extrude(17.8).translate((0,0,69.5))
        self.assertLess(closure.intersect(keepout).val().Volume(),0.01)


if __name__ == '__main__':
    unittest.main()
