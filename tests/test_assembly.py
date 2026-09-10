"""Actual seven-stage solids, permanent joints and the enclosed generator."""

from dataclasses import replace
import unittest

import cadquery as cq

from windwall.assembly import (audit_rotor_assembly, build_exploded_rotor_assembly,
                               build_locked_rotor_assembly)
from windwall.assembly_validation import require_valid_assembly_audit
from windwall.parameters import DEFAULT_PARAMETERS


class AssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assembly = build_locked_rotor_assembly(DEFAULT_PARAMETERS)
        cls.audit = audit_rotor_assembly(cls.assembly)

    def test_locked_seven_stage_stack_preserves_registration_and_reports_axial_float(self):
        a = self.assembly
        self.assertEqual((a.base_count, a.standard_count, a.top_count), (1, 5, 1))
        self.assertEqual([round(s.z_mm, 2) for s in a.stages], [0, 70, 140, 210, 280, 350, 420])
        self.assertEqual([round(s.angle_deg, 2) for s in a.stages], [0, 60, 120, 180, 240, 300, 360])
        self.assertAlmostEqual(a.aerodynamic_height_mm(), 490, places=5)
        self.assertLess(a.maximum_stage_angle_error_deg(), 0.01)
        self.assertLess(self.audit['maximum_installed_joint_intersection_mm3'], 0.01)
        self.assertIn('joint_axial_float', self.audit)
        self.assertEqual(len(self.audit['joint_axial_float']), 6)
        for joint in self.audit['joint_axial_float']:
            self.assertLess(joint['compression_0_10_mm_intersection_mm3'], 0.01)
            self.assertGreater(joint['compression_0_20_mm_intersection_mm3'], 0.05)
            self.assertEqual(joint['contact_probe_bracket_mm'], [0.1, 0.2])
            self.assertFalse(joint['physical_load_capacity_verified'])
        self.assertEqual(self.audit['seam_phase_jump_deg'], 0)
        self.assertTrue(self.audit['aerodynamic_seam_continuous'])

    def test_continuous_m8_shaft_clears_all_rotating_and_stationary_parts(self):
        shaft = self.assembly.parts['shaft']
        box = shaft.val().BoundingBox()
        self.assertAlmostEqual(box.zmax, 501.3, places=5)
        self.assertAlmostEqual(box.xlen, 8, places=5)
        self.assertGreater(box.zmin, -50.5)
        for name, shape in self.assembly.parts.items():
            if name != 'shaft':
                self.assertLess(shape.intersect(shaft).val().Volume(), 0.01, name)

    def test_complete_assembly_has_no_unintended_intersection(self):
        self.assertLess(self.audit['unplanned_intersection_mm3'], 0.01)
        require_valid_assembly_audit(self.audit)
        bad = dict(self.audit, generator_rotating_stationary_intersection_mm3=1)
        with self.assertRaises(ValueError):
            require_valid_assembly_audit(bad)

    def test_permanent_bayonet_resists_cw_reversal_and_axial_pull(self):
        self.assertEqual(set(self.audit['joint_paths']), {'base/standard', 'standard/standard', 'standard/top'})
        for result in self.audit['joint_paths'].values():
            self.assertGreater(result['ccw_overtravel_intersection_mm3'], 0.05)
            self.assertGreater(result['cw_reverse_intersection_mm3'], 0.05)
            self.assertGreater(result['locked_pull_intersection_mm3'], 0.05)
            self.assertGreater(result['maximum_locking_intersection_mm3'], 0)
            self.assertFalse(result['elastic_snap_fit_verified'])
        self.assertFalse(self.audit['print_ready'])

    def test_top_has_only_compact_force_plate_and_exposed_serviceable_m8_clamp(self):
        a = self.assembly
        self.assertNotIn('top_closure', a.parts)
        self.assertFalse(any('retainer' in name for name in a.parts))
        self.assertNotIn('closure_removal_intersection_mm3', self.audit)
        self.assertNotIn('thread_forming_contacts', self.audit)
        self.assertLess(self.audit['top_wrench_access_intersection_mm3'], 0.01)
        self.assertLess(self.audit['top_washer_removal_intersection_mm3'], 0.01)
        self.assertAlmostEqual(a.parts['top_washer'].val().BoundingBox().zmin, 489.5, places=5)
        self.assertAlmostEqual(a.parts['top_nut'].val().BoundingBox().zmin, 491.5, places=5)
        washer = a.parts['top_washer']
        self.assertGreater(washer.translate((0, 0, -0.05)).intersect(a.parts['top']).val().Volume(), 0.05)
        top_above = cq.Workplane('XY').circle(62).extrude(20).translate((0, 0, 490.0001))
        self.assertLess(top_above.intersect(a.parts['top']).val().Volume(), 0.01)

    def test_generator_ownership_uses_full_rotor_stack_and_one_upper_carrier(self):
        a = self.assembly
        self.assertNotIn('upper_carrier', a.parts)
        self.assertTrue({s.name for s in a.stages} <= set(a.rotating_parts))
        self.assertTrue(set(a.rotating_parts).isdisjoint(a.stationary_parts))
        self.assertAlmostEqual(self.audit['upper_generator_air_gap_mm'], 1.5, places=5)
        self.assertAlmostEqual(self.audit['lower_generator_air_gap_mm'], 1.5, places=5)
        self.assertLess(self.audit['generator_rotating_stationary_intersection_mm3'], 0.01)
        self.assertEqual(self.audit['generator_collision_report']['rotating_part_count'], len(a.rotating_parts))
        self.assertEqual(self.audit.get('integral_lower_rotor_sleeve'), {
            'outer_diameter_mm': 12.0,
            'inner_diameter_mm': 8.8,
            'height_mm': 17.85,
            'separate_part_required': False,
        })

    def test_exploded_view_is_a_preassembly_view_with_phased_separate_modules(self):
        exploded = build_exploded_rotor_assembly(DEFAULT_PARAMETERS, locked=self.assembly)
        for index, stage in enumerate(exploded.stages):
            self.assertAlmostEqual(stage.z_mm, index*85, places=5)
            self.assertEqual(stage.angle_deg, index*60-18 if index else 0)
        for lower, upper in zip(exploded.stages, exploded.stages[1:]):
            self.assertGreater(exploded.parts[upper.name].val().BoundingBox().zmin,
                               exploded.parts[lower.name].val().BoundingBox().zmax)
        self.assertNotIn('top_closure', exploded.parts)

    def test_invalid_composition_and_rod_projection_fail_early(self):
        p = DEFAULT_PARAMETERS
        for changed in (replace(p, rotor=replace(p.rotor, standard_stage_count=4)),
                        replace(p, closure=replace(p.closure, rod_projection_mm=-1))):
            with self.assertRaises(ValueError):
                build_locked_rotor_assembly(changed)


if __name__ == '__main__':
    unittest.main()
