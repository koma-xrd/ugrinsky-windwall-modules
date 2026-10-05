"""Integrated horizontal-winder ownership, load-path and upward-release regressions."""
import unittest
from dataclasses import replace
from functools import lru_cache
from unittest.mock import patch

import cadquery as cq

from windwall.parameters import DEFAULT_PARAMETERS
from windwall.winding_head import build_winding_head
from windwall.winding_tool_assembly import (
    audit_winding_tool_assemblies, build_winding_tool_assemblies, winding_tool_bom)
from windwall.winding_tool_service import (
    audit_winding_tool_service, coil_removal_stages, installed_shape, local_shape)
from windwall.wire_payoff import build_wire_payoff
from windwall import winding_tool_assembly as assembly_module


@lru_cache(maxsize=1)
def model_at():
    return build_winding_tool_assemblies()


def box(x, y, z, dx, dy, dz):
    return cq.Workplane('XY').box(dx, dy, dz, centered=False).translate((x, y, z))


def changed(model, tool, name, shape):
    parts = dict(getattr(model, tool))
    parts[name] = shape
    return replace(model, **{tool: parts}, audit={})


def frame_checks(model):
    height = model.ownership['winding_jig']['wheel']['axis_height_mm']
    local = tuple((name, local_shape(shape, height)) for name, shape in model.winding_jig.items())
    return assembly_module._frame_checks(local, height, (25, 42, 11))


class WindingToolAssemblyTests(unittest.TestCase):
    def test_horizontal_inventory_and_upward_release(self):
        model = model_at()
        self.assertEqual(set(model.winding_jig), {
            'base', 'hub', 'wheel', 'crank', 'grip', 'lower_washer', 'bearing',
            'upper_washer', *(f'shoe_{i}' for i in range(1, 7))})
        self.assertEqual(model.ownership['winding_jig']['base']['canonical_master'], 'wire_payoff/base')
        purchase_sets = []
        for tool in ('winding_jig', 'wire_payoff'):
            sets = {model.ownership[tool][n]['purchase_set'] for n in ('lower_washer', 'bearing', 'upper_washer')}
            self.assertEqual(len(sets), 1)
            purchase_sets.extend(sets)
        self.assertEqual(len(set(purchase_sets)), 2)
        stages = coil_removal_stages(model)
        self.assertEqual(tuple(s['name'] for s in stages),
                         ('wound_friction_fit', 'remove_crank', 'remove_taped_coil'))
        self.assertEqual(stages[-1]['translation_mm'], (0, 0, 120))
        self.assertTrue(all(f'shoe_{i}' in stages[-1]['fixed'] for i in range(1, 7)))

    def test_all_eleven_settings_and_three_taped_release_sweeps_pass(self):
        model = model_at()
        self.assertTrue(all(model.audit.values()), model.audit)
        for diameter in range(100, 201, 10):
            self.assertTrue(model.audit[f'setting_{diameter}_geometry'])
        for diameter in (100, 150, 200):
            self.assertTrue(model.audit[f'removal_{diameter}'])

    def test_bom_has_eight_masters_two_bases_and_two_bearing_sets(self):
        rows = winding_tool_bom(model_at())
        prints = [r for r in rows if r['source'] == 'printed']
        self.assertEqual(len(prints), 8)
        self.assertEqual(sum(r['quantity'] for r in prints), 14)
        self.assertEqual(next(r for r in prints if r['master'] == 'wire_payoff/base')['quantity'], 2)
        self.assertEqual(next(r for r in rows if r['source'] == 'purchased')['quantity'], 2)

    def test_service_audit_rejects_removed_gravity_support_even_with_clear_tape(self):
        from windwall.winding_tool_service import _winding_band

        model = model_at()
        service = audit_winding_tool_service(model)
        self.assertTrue(service['checks']['winding_supported'], service)
        diameter = model.ownership['winding_jig']['wheel']['diameter_mm']
        height = model.ownership['winding_jig']['wheel']['axis_height_mm']
        shoulder = installed_shape(_winding_band(
            model.parameters, diameter, .001, 4, 5, 7.5), height)
        parts = dict(model.winding_jig)
        for index in range(1, 7):
            name = f'shoe_{index}'
            parts[name] = parts[name].cut(shoulder)
        unsupported = replace(model, winding_jig=parts, audit={})
        result = audit_winding_tool_service(unsupported)
        self.assertTrue(result['checks']['wound_closed_tape'], result)
        self.assertFalse(result['checks']['winding_supported'], result)
        self.assertFalse(result['checks']['complete_coil_removal'], result)

    def test_payoff_geometry_is_unchanged(self):
        model = model_at()
        payoff = build_wire_payoff(model.parameters)
        for name, shape in model.wire_payoff.items():
            expected = getattr(payoff, name)
            self.assertLess(shape.cut(expected).val().Volume(), 1e-6)
            self.assertLess(expected.cut(shape).val().Volume(), 1e-6)

    def test_displaced_washer_is_rejected_even_with_success_metadata(self):
        model = model_at()
        mutant = changed(model, 'winding_jig', 'upper_washer',
                         model.winding_jig['upper_washer'].translate((0, 0, .3)))
        with self.assertRaisesRegex(ValueError, '51105'):
            winding_tool_bom(mutant)
        self.assertFalse(audit_winding_tool_assemblies(mutant)['bearing_catalog_dimensions'])

    def test_short_pilot_and_unseated_wheel_fail_physical_load_checks(self):
        model = model_at()
        short = model.winding_jig['hub'].cut(box(-30, -30, 0, 60, 60, 9))
        checks = frame_checks(changed(model, 'winding_jig', 'hub', short))
        self.assertFalse(checks['hub_radial_guidance'])
        raised = model.winding_jig['wheel'].translate((0, 0, 1))
        self.assertFalse(frame_checks(changed(model, 'winding_jig', 'wheel', raised))['winder_51105_load_path'])

    def test_modified_base_and_stationary_collision_are_rejected(self):
        model = model_at()
        base = model.winding_jig['base'].union(box(40, -10, 7, 10, 20, 100))
        checks = frame_checks(changed(model, 'winding_jig', 'base', base))
        self.assertFalse(checks['shared_base_geometry'])
        self.assertFalse(checks['jig_full_rotation_clearance'])

    def test_upper_lip_traps_taped_coil_at_all_three_diameters(self):
        model = model_at()
        for diameter in (100, 150, 200):
            candidate = assembly_module._at_setting(model, diameter)
            lip = installed_shape(box(diameter / 2 - .5, 7, 26, 2, 1, 1), 33)
            mutant = changed(candidate, 'winding_jig', 'shoe_1', candidate.winding_jig['shoe_1'].union(lip))
            audit = audit_winding_tool_service(mutant)
            self.assertFalse(audit['checks']['complete_coil_removal'])
            self.assertTrue(audit['collisions'], audit)

    def test_blocked_tape_and_missing_tongue_fail_actual_head_probes(self):
        model = model_at()
        local = {name: local_shape(shape, 33) for name, shape in model.winding_jig.items()}
        for cut_tongue in (False, True):
            shoe = local['shoe_1']
            if cut_tongue:
                shoe = shoe.cut(box(69, 6, -2, 6, 3.2, 7))
            else:
                shoe = shoe.union(box(73, 5.8, 12, 3, 2, 4))
            checks, _ = assembly_module._head_checks(
                tuple({**local, 'shoe_1': shoe}.items()), model.parameters, 150)
            self.assertFalse(checks['two_tongue_friction_fit' if cut_tongue else 'tape_corridors'])

    def test_service_cannot_move_shoes_or_teleport_fixed_members(self):
        model = model_at()
        stages = list(coil_removal_stages(model))
        final = dict(stages[-1])
        fixed = dict(final['fixed'])
        fixed['shoe_1'] = fixed['shoe_1'].translate((0, 0, 1))
        stages[-1] = {**final, 'fixed': fixed}
        self.assertFalse(audit_winding_tool_service(model, stages)['checks']['route_continuity'])
        stages = list(coil_removal_stages(model))
        stages[1] = {**stages[1], 'moving': {'shoe_1': model.winding_jig['shoe_1']}}
        self.assertFalse(audit_winding_tool_service(model, stages)['checks']['motion_ownership'])

    def test_between_endpoint_obstacle_is_detected(self):
        model = model_at()
        # This upright post is outside the seated shoes but intersects the coil
        # only midway through its upward translation.
        obstacle = model.winding_jig['base'].union(box(73, 6, 7, 4, 3, 73))
        mutant = changed(model, 'winding_jig', 'base', obstacle)
        audit = audit_winding_tool_service(mutant)
        self.assertFalse(audit['checks']['complete_coil_removal'])
        self.assertTrue(audit['collisions'])

    def test_noncanonical_51105_configuration_is_rejected_before_auditing(self):
        design = replace(DEFAULT_PARAMETERS, bearings=replace(
            DEFAULT_PARAMETERS.bearings, thrust_height_mm=12))
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies', return_value={}):
            with self.assertRaisesRegex(ValueError, '51105'):
                build_winding_tool_assemblies(design_parameters=design)

    def test_noncanonical_bearing_records_or_actual_stack_cannot_publish_a_bom(self):
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies', return_value={}):
            model = build_winding_tool_assemblies()
        valid_row = next(row for row in winding_tool_bom(model) if row['name'] == '51105 thrust bearing')
        self.assertTrue(valid_row['specification'].startswith('25 x 42 x 11 mm'))
        owners = {tool: {name: dict(owner) for name, owner in records.items()}
                  for tool, records in model.ownership.items()}
        for name in ('lower_washer', 'bearing', 'upper_washer'):
            owners['wire_payoff'][name]['nominal_dimensions_mm'] = (25, 42, 12)
        design = replace(DEFAULT_PARAMETERS, bearings=replace(
            DEFAULT_PARAMETERS.bearings, thrust_height_mm=12))
        payoff = build_wire_payoff(model.parameters, design)
        members = {name: getattr(payoff, name) for name in model.wire_payoff}
        for case, mutant in (
            ('incorrect record', replace(model, ownership=owners)),
            ('incorrect actual stack with canonical record', replace(model, wire_payoff=members)),
            ('incorrect stack and record', replace(model, wire_payoff=members, ownership=owners)),
        ):
            with self.subTest(case=case):
                with self.assertRaisesRegex(ValueError, '51105'):
                    winding_tool_bom(mutant)
                self.assertFalse(all(audit_winding_tool_assemblies(mutant).values()))


if __name__ == '__main__':
    unittest.main()
