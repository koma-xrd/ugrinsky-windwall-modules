"""Integrated geometry and service regressions for the two manual tools."""

import unittest
from dataclasses import fields, replace
from functools import lru_cache
from math import sqrt
from unittest.mock import patch
import cadquery as cq

from windwall.winding_tool_assembly import (
    WindingToolAssemblies, audit_winding_tool_assemblies,
    build_winding_tool_assemblies, winding_tool_bom,
)
from windwall.winding_tool_service import coil_removal_stages, audit_winding_tool_service
from windwall.winding_head import build_winding_head
from windwall.wire_payoff import build_wire_payoff
from windwall.winding_tool_parameters import DEFAULT_WINDING_TOOL_PARAMETERS
from windwall.parameters import DEFAULT_PARAMETERS
from windwall import winding_tool_assembly as assembly_module
from windwall import winding_tool_service as service_module


@lru_cache(maxsize=3)
def model_at(diameter=150):
    if diameter == 150:
        return build_winding_tool_assemblies()
    reference = model_at()
    head = build_winding_head(reference.parameters, diameter)
    members = {**reference.winding_jig,
               **{f'shoe_{i}': installed(shape) for i, shape in enumerate(head.shoes, 1)}}
    owners = {tool: dict(records) for tool, records in reference.ownership.items()}
    owners['winding_jig']['wheel'] = {**owners['winding_jig']['wheel'], 'diameter_mm': diameter,
        'actual_tape_angles_deg': head.metadata['actual_tape_angles_deg']}
    return replace(reference, winding_jig=members, ownership=owners, audit={})


def installed(shape):
    return shape.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, 0, 130))


def box(x, y, z, dx, dy, dz):
    return cq.Workplane('XY').box(dx, dy, dz, centered=False).translate((x, y, z))


def changed(model, tool, name, shape):
    members = dict(getattr(model, tool))
    members[name] = shape
    return replace(model, **{tool: members})


class WindingToolAssemblyTests(unittest.TestCase):
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

    def test_shaft_and_collar_rotation_cannot_cross_stationary_tower_material(self):
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies', return_value={}):
            model = build_winding_tool_assemblies()
        original = {name: service_module.local_shape(shape, 130)
                    for name, shape in model.winding_jig.items()}
        nominal = assembly_module._frame_checks(tuple(original.items()), 130,
            DEFAULT_PARAMETERS.bearings.radial_nominal_dimensions_mm)
        self.assertTrue(all(nominal.values()), nominal)
        collar_wall = box(-1, 4.3, -30, 2, 11.7, .4).union(
            box(-1, 14, -31.2, 2, 2, 1.6))
        for name, obstacle, angle in (
            ('shaft', box(-1, 6.5, -18.6, 8, 2.5, 1.6), 30),
            ('snap_collar_1', collar_wall, 90),
        ):
            with self.subTest(rotating=name):
                parts = {**original, 'tower': original['tower'].union(obstacle)}
                self.assertEqual(len(parts['tower'].val().Solids()), 1)
                self.assertLess(parts[name].intersect(parts['tower']).val().Volume(), 1e-6)
                rotated = parts[name].rotate((0, 0, 0), (0, 0, 1), angle)
                self.assertGreater(rotated.intersect(parts['tower']).val().Volume(), .1)
                checks = assembly_module._frame_checks(tuple(parts.items()), 130,
                    DEFAULT_PARAMETERS.bearings.radial_nominal_dimensions_mm)
                self.assertFalse(all(checks.values()), checks)

    def test_each_rear_shoe_hook_must_retain_its_own_pin(self):
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies', return_value={}):
            model = build_winding_tool_assemblies()
        missing_hook = model.winding_jig['shoe_1'].cut(installed(box(65.9, 6.7, -2, 2.2, .4, 2)))
        parts = {name: service_module.local_shape(shape, 130)
                 for name, shape in changed(model, 'winding_jig', 'shoe_1', missing_hook).winding_jig.items()}
        checks, _ = assembly_module._head_checks(tuple(parts.items()), model.parameters, 150)
        self.assertFalse(checks['two_pin_engagement'])

    def test_608_inner_ring_requires_actual_journal_contact(self):
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies', return_value={}):
            model = build_winding_tool_assemblies()
        parts = {name: service_module.local_shape(shape, 130) for name, shape in model.winding_jig.items()}
        bearing = parts['bearing_608_1']
        bb = bearing.val().BoundingBox()
        loose_bore = cq.Workplane('XY').circle(
            DEFAULT_PARAMETERS.bearings.radial_bore_diameter_mm / 2 + .8).extrude(bb.zlen + 2).translate((0, 0, bb.zmin - 1))
        parts['bearing_608_1'] = bearing.cut(loose_bore)
        checks = assembly_module._frame_checks(tuple(parts.items()), 130,
            DEFAULT_PARAMETERS.bearings.radial_nominal_dimensions_mm)
        self.assertFalse(checks['bearing_608_engagement'])

    def test_bom_contains_only_simple_wheel_and_free_payoff(self):
        try:
            model = model_at()
        except AttributeError as error:
            self.fail(f'The simplified component records must assemble: {error}')
        rows = winding_tool_bom(model)
        names = {row['name'] for row in rows}
        self.assertIn('608 bearing', names)
        self.assertIn('51105 thrust bearing', names)
        self.assertFalse(any(token in name.lower() for name in names for token in
            ('cam', 'rib bolt', 'follower', 'brake', 'm3', 'm4', 'm8',
             'felt', 'spring', 'adjuster', 'metal shaft', 'screw', 'nut', 'adhesive')))
        purchased = {row['name']: row['quantity'] for row in rows
                     if row['source'] == 'purchased'}
        self.assertEqual(purchased, {'608 bearing': 2, '51105 thrust bearing': 1})

    def test_reference_build_has_exact_occurrence_ownership_and_derived_print_quantities(self):
        model = model_at()
        self.assertEqual(tuple(f.name for f in fields(WindingToolAssemblies)),
                         ('winding_jig', 'wire_payoff', 'ownership', 'parameters', 'audit'))
        self.assertEqual(len(model.winding_jig), 18)
        self.assertEqual(len(model.wire_payoff), 6)
        self.assertIsNot(model.winding_jig['base'], model.wire_payoff['base'])
        for tool in ('winding_jig', 'wire_payoff'):
            self.assertEqual(set(model.ownership[tool]), set(getattr(model, tool)))
            self.assertTrue(all(owner['group'] in
                ('rotating', 'stationary', 'bearing_internal', 'service_detached')
                for owner in model.ownership[tool].values()))
        rows = [row for row in winding_tool_bom(model) if row['source'] == 'printed']
        self.assertEqual(len(rows), 12)
        self.assertEqual(sum(row['quantity'] for row in rows), 19)
        quantities = {row['master']: row['quantity'] for row in rows}
        self.assertEqual(quantities['winding_jig/contact_shoe'], 6)
        self.assertEqual(quantities['winding_jig/bearing_retainer'], 2)
        self.assertEqual(quantities['winding_jig/snap_collar'], 2)
        self.assertEqual(model.ownership['winding_jig']['wheel']['diameter_mm'], 150)

    def test_all_eleven_integrated_settings_are_physically_audited(self):
        audit = model_at().audit
        self.assertTrue(all(audit.values()), audit)
        self.assertTrue(all(type(value) is bool for value in audit.values()))
        for diameter in range(100, 201, 10):
            self.assertTrue(audit[f'setting_{diameter}_geometry'])
        for diameter in (100, 150, 200):
            self.assertTrue(audit[f'removal_{diameter}'])

    def test_nominal_runout_and_front_shoulder_have_separate_physical_gauges(self):
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies', return_value={}):
            model = build_winding_tool_assemblies()
        parts = {name: service_module.local_shape(shape, 130)
                 for name, shape in model.winding_jig.items()}
        for diameter in (100, 150, 200):
            head = build_winding_head(model.parameters, diameter)
            parts.update({f'shoe_{i}': shoe for i, shoe in enumerate(head.shoes, 1)})
            checks, _ = assembly_module._head_checks(tuple(parts.items()), model.parameters, diameter)
            self.assertTrue(all(checks.values()), (diameter, checks))
        original = parts['shoe_1']
        for case, protrusion in (
            ('nominal runout', box(99, 7.2, 16, 2, .5, .5)),
            ('front shoulder', box(101.9, 7.2, 26.5, 1.5, .5, .5)),
        ):
            with self.subTest(case=case):
                mutant = original.union(protrusion)
                # Preserve the position gauge's center so that the independent
                # physical radial limit, rather than a centroid shift, fails.
                mutant = mutant.translate(original.val().Center().sub(mutant.val().Center()).toTuple())
                self.assertTrue(mutant.val().isValid())
                self.assertEqual(len(mutant.val().Solids()), 1)
                modified = {**parts, 'shoe_1': mutant}
                checks, _ = assembly_module._head_checks(tuple(modified.items()), model.parameters, 200)
                self.assertFalse(checks['wire_contact_envelope'], checks)

    def test_audit_rejects_a_shoe_in_a_different_numbered_position(self):
        model = model_at()
        mutant = changed(model, 'winding_jig', 'shoe_1',
                         model.winding_jig['shoe_1'].translate((5, 0, 0)))
        self.assertFalse(audit_winding_tool_assemblies(mutant)['equal_shoe_positions'])

    def test_audit_rejects_a_missing_pin_and_an_unlatched_shoe(self):
        model = model_at()
        for shape in (model.winding_jig['shoe_1'].cut(installed(box(65, 2, -5, 4, 6, 10))),
                      model.winding_jig['shoe_1'].translate((0, -6, 0))):
            with self.subTest(shape=shape):
                checks = audit_winding_tool_assemblies(changed(model, 'winding_jig', 'shoe_1', shape))
                self.assertFalse(checks['two_pin_engagement'])

    def test_audit_rejects_blocked_tape_and_false_actual_angles(self):
        model = model_at()
        plugged = model.winding_jig['shoe_1'].union(installed(box(71, -2, 10, 4, 4, 14)))
        self.assertFalse(audit_winding_tool_assemblies(changed(
            model, 'winding_jig', 'shoe_1', plugged))['tape_corridors'])
        owners = {tool: {name: dict(owner) for name, owner in records.items()}
                  for tool, records in model.ownership.items()}
        owners['winding_jig']['wheel']['actual_tape_angles_deg'] = tuple(range(0, 360, 20))
        self.assertFalse(audit_winding_tool_assemblies(replace(model, ownership=owners))['actual_tape_angles'])

    def test_audit_rejects_missing_member_even_if_ownership_is_also_removed(self):
        model = model_at()
        members = dict(model.winding_jig)
        del members['snap_collar_1']
        owners = {tool: dict(records) for tool, records in model.ownership.items()}
        del owners['winding_jig']['snap_collar_1']
        checks = audit_winding_tool_assemblies(replace(model, winding_jig=members, ownership=owners))
        self.assertFalse(checks['required_members'])

    def test_audit_rejects_missing_or_wrong_motion_ownership(self):
        model = model_at()
        owners = {tool: {name: dict(owner) for name, owner in records.items()}
                  for tool, records in model.ownership.items()}
        del owners['winding_jig']['shoe_6']
        self.assertFalse(audit_winding_tool_assemblies(replace(model, ownership=owners))['ownership'])
        owners = {tool: {name: dict(owner) for name, owner in records.items()}
                  for tool, records in model.ownership.items()}
        owners['wire_payoff']['lower_washer']['group'] = 'rotating'
        self.assertFalse(audit_winding_tool_assemblies(replace(model, ownership=owners))['bearing_51105_ownership'])

    def test_audit_rejects_displaced_bearings_and_lost_axial_restraint(self):
        model = model_at()
        checks = audit_winding_tool_assemblies(changed(model, 'winding_jig', 'bearing_608_1',
            model.winding_jig['bearing_608_1'].translate((0, 20, 0))))
        self.assertFalse(checks['bearing_608_engagement'])
        members = dict(model.wire_payoff)
        for name in ('lower_washer', 'bearing', 'upper_washer'):
            members[name] = members[name].translate((0, 0, 100))
        self.assertFalse(audit_winding_tool_assemblies(replace(model, wire_payoff=members))['bearing_51105_load_path'])
        for name in ('snap_collar_1', 'snap_collar_2'):
            mutant = changed(model, 'winding_jig', name, model.winding_jig[name].translate((30, 0, 0)))
            self.assertFalse(audit_winding_tool_assemblies(mutant)['shaft_axial_restraint'])

    def test_audit_rejects_disengaged_wheel_or_crank_drive(self):
        model = model_at()
        enlarged_socket = installed(cq.Workplane('XY').circle(11).extrude(7).translate((0, 0, -1)))
        for name, shape in (
            ('wheel', model.winding_jig['wheel'].cut(enlarged_socket)),
            ('crank', model.winding_jig['crank'].translate((0, -100, 0)))):
            mutant = changed(model, 'winding_jig', name, shape)
            self.assertEqual(len(shape.val().Solids()), 1)
            self.assertFalse(audit_winding_tool_assemblies(mutant)['positive_polygon_drives'])

    def test_audit_rejects_rotating_fixed_and_bench_interference(self):
        model = model_at()
        obstacle = installed(box(40, -5, -60, 20, 10, 8).union(
            box(14, -2, -55, 28, 4, 19)))
        mutant = changed(model, 'winding_jig', 'tower', model.winding_jig['tower'].union(obstacle))
        self.assertEqual(len(mutant.winding_jig['tower'].val().Solids()), 1)
        self.assertFalse(audit_winding_tool_assemblies(mutant)['crank_full_rotation'])
        obstacle = box(55, -5, 8, 10, 10, 20)
        mutant = changed(model, 'wire_payoff', 'base', model.wire_payoff['base'].union(obstacle))
        self.assertFalse(audit_winding_tool_assemblies(mutant)['payoff_free_rotation'])

    def test_audit_rejects_inaccessible_snap_and_oversized_finished_print(self):
        model = model_at()
        obstacle = installed(box(-8, 5.2, -30.2, 16, 18, 2))
        mutant = changed(model, 'winding_jig', 'tower', model.winding_jig['tower'].union(obstacle))
        self.assertFalse(audit_winding_tool_assemblies(mutant)['snap_access'])
        enlarged = model.wire_payoff['base'].union(box(-120, -5, 0, 240, 10, 2))
        self.assertFalse(audit_winding_tool_assemblies(changed(
            model, 'wire_payoff', 'base', enlarged))['print_bed'])


class WindingToolServiceTests(unittest.TestCase):
    def test_tape_passages_cut_through_both_cradle_shoulders(self):
        for diameter in (100, 150, 200):
            head = build_winding_head(DEFAULT_WINDING_TOOL_PARAMETERS, diameter)
            for index, probe in enumerate(head.metadata['tape_passage_probes']):
                with self.subTest(diameter=diameter, passage=index + 1):
                    self.assertLess(head.shoes[index // 3].intersect(probe).val().Volume(), 1e-6)

    def test_declared_winding_and_full_width_closed_tape_clear_every_seated_shoe(self):
        for diameter in (100, 150, 200):
            head = build_winding_head(DEFAULT_WINDING_TOOL_PARAMETERS, diameter)
            fixture = service_module._winding_fixture(DEFAULT_WINDING_TOOL_PARAMETERS, diameter)
            for name, shape in fixture.items():
                for index, shoe in enumerate(head.shoes):
                    with self.subTest(diameter=diameter, fixture=name, shoe=index + 1):
                        self.assertLess(shape.intersect(shoe).val().Volume(), 1e-6)

    def test_tape_fixtures_are_ten_mm_tangential_closed_strips_around_the_winding(self):
        for diameter in (100, 150, 200):
            fixture = service_module._winding_fixture(DEFAULT_WINDING_TOOL_PARAMETERS, diameter)
            for index in range(18):
                with self.subTest(diameter=diameter, tape=index + 1):
                    tape = fixture[f'tape_{index + 1}']
                    local = tape.rotate((0, 0, 0), (0, 0, 1), -(index // 3) * 60)
                    bounds = local.val().BoundingBox()
                    self.assertAlmostEqual(bounds.ylen, 10)
                    self.assertAlmostEqual(bounds.zlen, 10)
                    self.assertTrue(tape.val().isValid())
                    self.assertEqual(len(tape.val().Solids()), 1)
                    self.assertLess(tape.intersect(fixture['coil']).val().Volume(), 1e-5)
                    offset = (-15, 0, 15)[index % 3]
                    center_x = diameter / 2 - 50
                    # Wide reliefs let taut wire bridge slightly inside the
                    # nominal arc. The conservative loop must surround that
                    # chord envelope as well as the ideal circular bundle.
                    for radius, height, occupied in ((48.1, 17, True), (49.8, 17, False),
                                                      (50.5, 17, False), (51.9, 17, True),
                                                      (50.5, 12.1, True)):
                        point = (center_x + sqrt(radius ** 2 - offset ** 2), offset, height)
                        self.assertEqual(local.val().isInside(point), occupied)

    def test_moving_the_entire_tool_cannot_hide_insufficient_tape_clearance(self):
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies', return_value={}):
            model = build_winding_tool_assemblies()
        wall = installed(box(77.2, -130, 12, 1, 131, 10))
        model = changed(model, 'winding_jig', 'base', model.winding_jig['base'].union(wall))
        self.assertEqual(len(model.winding_jig['base'].val().Solids()), 1)
        stages = list(coil_removal_stages(model))
        tape = stages[0]['fixed']['tape_2']
        self.assertAlmostEqual(model.winding_jig['base'].val().distance(tape.val()), .2, places=5)
        final = stages[-1]
        all_members = {**final['fixed'], **final['moving']}
        stages.insert(-1, {'name': 'translate_entire_tool', 'moving': all_members,
            'fixed': {}, 'translation_mm': (250, 0, 0), 'groups': dict(final['groups']),
            'released': {}, 'restored': {}})
        stages[-1] = {**final, **{role: {name: shape.translate((250, 0, 0))
            for name, shape in final[role].items()} for role in ('fixed', 'moving')}}
        service = audit_winding_tool_service(model, stages)
        self.assertFalse(service['errors'], service)
        self.assertTrue(service['checks']['route_continuity'], service)
        with self.subTest(requirement='permitted motion ownership'):
            self.assertFalse(service['checks'].get('motion_ownership', True), service)
        with self.subTest(requirement='clearance at actual winding pose'):
            self.assertFalse(service['checks']['radial_support_clearance'], service)
            self.assertEqual(service['radial_support_clearance_mm'], 0)
        self.assertFalse(service['checks']['complete_coil_removal'], service)

    def test_coil_surrogate_includes_the_taut_spans_between_rounded_shoes(self):
        # At 150/200 mm the unsupported spans lie inside the nominal circle.
        for diameter, point in ((100, (50.5, 0, 17)),
                                (150, (62.353829, 36, 17)),
                                (200, (81.232183, 46.9, 17))):
            with self.subTest(diameter=diameter):
                coil = service_module._winding_fixture(DEFAULT_WINDING_TOOL_PARAMETERS, diameter)['coil']
                self.assertTrue(coil.val().isInside(point))

    def test_payoff_snap_access_rejects_a_guard_above_the_platter(self):
        payoff = build_wire_payoff(DEFAULT_WINDING_TOOL_PARAMETERS)
        members = {name: getattr(payoff, name) for name in
                   ('base', 'spindle', 'platter', 'lower_washer', 'bearing', 'upper_washer')}
        members['base'] = members['base'].union(box(85, -3, 8, 5, 6, 53)).union(
            box(-30, -3, 60, 120, 6, 1))
        self.assertEqual(len(members['base'].val().Solids()), 1)
        self.assertLess(members['base'].intersect(members['platter']).val().Volume(), 1e-6)
        checks = assembly_module._payoff_checks(tuple(members.items()),
            DEFAULT_PARAMETERS.bearings.thrust_rotating_pilot_diameter_mm)
        self.assertFalse(checks.get('payoff_top_access', True))

    def test_parked_shoes_recover_full_relaxed_geometry(self):
        # Isolate pose generation from the costly all-settings validation,
        # which the separate positive assembly test exercises in full.
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies', return_value={}):
            model = build_winding_tool_assemblies()
        stages = coil_removal_stages(model)
        for index in range(1, 7):
            name = f'shoe_{index}'
            self.assertAlmostEqual(stages[-1]['fixed'][name].val().Volume(),
                                   model.winding_jig[name].val().Volume(), places=5)

    def test_taped_winding_is_retained_until_six_shoes_are_parked_then_exits_forward(self):
        for diameter in (100, 150, 200):
            model = model_at(diameter)
            stages = coil_removal_stages(model)
            self.assertEqual(stages[0]['name'], 'wound_latched')
            self.assertEqual(stages[-1]['name'], 'remove_taped_coil')
            self.assertEqual(len([name for name in stages[0]['fixed'] if name.startswith('tape_')]), 18)
            withdrawal = [s for s in stages if s['name'].startswith('withdraw_shoe_')]
            self.assertEqual(len(withdrawal), 6)
            self.assertTrue(all(s['translation_mm'] == (0, -40, 0) for s in withdrawal))
            last = stages[-1]
            self.assertEqual(set(last['moving']), {'coil', *(f'tape_{i}' for i in range(1, 19))})
            self.assertEqual(sum(group == 'service_detached' for group in last['groups'].values()), 6)
            service = audit_winding_tool_service(model, stages)
            self.assertEqual(service['fixture_mm'], {
                'winding_radial_build': 1, 'winding_axial_width': 9,
                'tape_radial_span': 4, 'tape_axial_span': 10,
                'tape_tangential_width': 10, 'tape_wall': .25,
            })
            self.assertTrue(all(service['checks'].values()), service)
            self.assertGreaterEqual(service['radial_support_clearance_mm'], 2)
            self.assertFalse(service['collisions'])
            self.assertTrue(service['continuous_translation_checks'])

    def test_one_shoe_left_latched_cannot_pass_the_release_audit(self):
        model = model_at()
        stages = list(coil_removal_stages(model))
        stages = [s for s in stages if not s['name'].endswith('shoe_6')]
        last = dict(stages[-1])
        last['fixed'] = {**last['fixed'], 'shoe_6': model.winding_jig['shoe_6']}
        last['groups'] = {**last['groups'], 'shoe_6': 'rotating'}
        stages[-1] = last
        service = audit_winding_tool_service(model, stages)
        self.assertFalse(service['checks']['all_shoes_detached'])
        self.assertFalse(service['checks']['radial_support_clearance'])

    def test_front_obstruction_is_detected_between_initial_and_final_poses(self):
        model = model_at()
        # Thin connected gate lies strictly between the winding's endpoints.
        gate = installed(box(-105, -105, 85, 210, 210, .2))
        stem = installed(box(-80, -130, -75, 4, 30, 161))
        mutant = changed(model, 'winding_jig', 'base', model.winding_jig['base'].union(stem).union(gate))
        self.assertEqual(len(mutant.winding_jig['base'].val().Solids()), 1)
        service = audit_winding_tool_service(mutant)
        self.assertFalse(service['checks']['complete_coil_removal'])
        self.assertTrue(service['collisions'])

    def test_closed_tape_blockage_and_teleported_shoe_are_rejected(self):
        model = model_at()
        # Restoring a rear rim crosses the inner leg of a closed tape loop.
        lip = installed(box(71.5, -16, 6, 3, 32, 1))
        mutant = changed(model, 'winding_jig', 'shoe_1', model.winding_jig['shoe_1'].union(lip))
        self.assertFalse(audit_winding_tool_service(mutant)['checks']['complete_coil_removal'])
        stages = list(coil_removal_stages(model))
        index = next(i for i, stage in enumerate(stages) if stage['name'] == 'park_shoe_1')
        stages[index] = {**stages[index], 'moving': {
            'shoe_1': stages[index]['moving']['shoe_1'].translate((250, 0, 0))}}
        self.assertFalse(audit_winding_tool_service(model, stages)['checks']['route_continuity'])


if __name__ == '__main__':
    unittest.main()
