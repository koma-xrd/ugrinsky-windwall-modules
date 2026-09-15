import unittest
from dataclasses import replace
from unittest.mock import patch

import cadquery as cq

from windwall.winding_tool_assembly import (
    audit_winding_tool_assemblies, build_winding_tool_assemblies, winding_tool_bom,
)
from windwall.winding_tool_parameters import DEFAULT_WINDING_TOOL_PARAMETERS as P
from windwall import winding_tool_assembly as assembly_module


class WindingToolAssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = {diameter: build_winding_tool_assemblies(diameter_mm=diameter)
                      for diameter in (110.0, 127.0, 145.0)}

    def test_minimum_reference_and_maximum_states_pass_clearance_audits(self):
        for diameter, model in self.models.items():
            with self.subTest(diameter=diameter):
                audit = audit_winding_tool_assemblies(model)
                self.assertTrue(audit['valid'], audit['checks'])
                self.assertEqual(audit['rib_count'], 6)
                self.assertEqual(audit['tape_station_count'], 18)
                self.assertGreaterEqual(audit['minimum_tape_clearance_mm'], 12.0)
                self.assertLessEqual(audit['maximum_print_xy_mm'], 220.0)
                self.assertGreaterEqual(audit['head_release_travel_mm'], 2.0)
                self.assertTrue(all(audit['checks'].values()))

    def test_assemblies_are_independent_and_ownership_covers_each_member(self):
        model = self.models[127.0]
        for tool, members in (('winding_jig', model.winding_jig),
                              ('wire_payoff', model.wire_payoff)):
            owners = model.ownership[tool]
            motion = [owners[key] for key in
                      ('rotating', 'stationary', 'bearing_internal')]
            self.assertEqual(set().union(*motion), set(members))
            for i, names in enumerate(motion):
                for other in motion[i + 1:]:
                    self.assertFalse(names & other)
            self.assertTrue(owners['hardware_reference'] <= set(members))
        self.assertIn('housing_washer', model.ownership['wire_payoff']['stationary'])
        self.assertIn('shaft_washer', model.ownership['wire_payoff']['rotating'])
        self.assertEqual(model.ownership['wire_payoff']['bearing_internal'],
                         frozenset({'rolling_envelope'}))
        self.assertIsNot(model.winding_jig['base'], model.wire_payoff['base'])
        self.assertFalse(model.metadata['mechanically_synchronized'])

    def test_audit_detects_moving_fixed_collision_without_trusting_metadata(self):
        model = self.models[127.0]
        parts = dict(model.winding_jig)
        parts['base'] = parts['base'].translate((0, 0, 80))
        audit = audit_winding_tool_assemblies(replace(model, winding_jig=parts))
        self.assertFalse(audit['valid'])
        self.assertFalse(audit['checks']['moving_fixed_clearance'])

    def test_audit_detects_physically_blocked_tape_passage(self):
        model = self.models[127.0]
        parts = dict(model.winding_jig)
        # First rib lies along -Z after the head's 90-degree Y rotation.
        plug = cq.Workplane('XY').box(10, 12, 6).translate((4.6, 0, 33.5))
        parts['rib_1'] = parts['rib_1'].union(plug)
        audit = audit_winding_tool_assemblies(replace(model, winding_jig=parts))
        self.assertFalse(audit['valid'])
        self.assertFalse(audit['checks']['tape_passages'])

    def test_audit_detects_missing_member_and_wrong_thrust_ownership(self):
        model = self.models[127.0]
        parts = dict(model.winding_jig)
        del parts['slider_6']
        self.assertFalse(audit_winding_tool_assemblies(
            replace(model, winding_jig=parts))['valid'])
        ownership = {tool: dict(sets) for tool, sets in model.ownership.items()}
        ownership['wire_payoff']['rotating'] |= {'housing_washer'}
        audit = audit_winding_tool_assemblies(replace(model, ownership=ownership))
        self.assertFalse(audit['checks']['bearing_51105_ownership'])
        self.assertFalse(audit['valid'])

    def test_audit_detects_misplaced_shaft_and_brake_hard_stop(self):
        model = self.models[127.0]
        jig = dict(model.winding_jig)
        jig['shaft'] = jig['shaft'].translate((0, 30, 0))
        audit = audit_winding_tool_assemblies(replace(model, winding_jig=jig))
        self.assertFalse(audit['checks']['shaft_608_nesting'])
        payoff = dict(model.wire_payoff)
        payoff['adjuster'] = payoff['adjuster'].translate((0, 0, 3))
        audit = audit_winding_tool_assemblies(replace(model, wire_payoff=payoff))
        self.assertFalse(audit['checks']['brake_hard_stop'])

    def test_builder_rejects_unconstructible_print_bed(self):
        with self.assertRaisesRegex(ValueError, 'print_bed'):
            build_winding_tool_assemblies(replace(P, print_bed_size_mm=200.0))

    def test_bom_contains_exact_bearing_shaft_and_service_inventory(self):
        rows = winding_tool_bom(self.models[127.0])
        quantities = {row['item']: row['quantity'] for row in rows}
        self.assertEqual(quantities['608 bearing'], 2)
        self.assertEqual(quantities['51105 thrust bearing'], 1)
        self.assertEqual(quantities['8 mm shaft'], 1)
        self.assertEqual(quantities['metal cam follower'], 6)
        self.assertEqual(quantities['felt brake pad'], 1)
        self.assertEqual(quantities['brake compression spring'], 1)
        self.assertEqual(quantities['M3 x 20 mm socket-head cap screw'], 3)
        self.assertEqual(quantities['ISO 4032 M3 preload nut'], 3)
        self.assertEqual(quantities['M3 brake-adjuster nut'], 1)
        self.assertEqual(quantities['M3 rib attachment pin'], 6)
        self.assertEqual(quantities['M4 upright bolt'], 4)
        self.assertEqual(quantities['crank grip washer'], 2)
        self.assertFalse(any(row['item'] in ('shaft_washer', 'housing_washer',
                                            'rolling_envelope') for row in rows))
        for row in rows:
            self.assertFalse(row['physical_fit_verified'])
            self.assertTrue(row['service_note'])
        choices = {row['choice_group'] for row in rows if row.get('choice_group')}
        self.assertEqual(choices, {'winding_jig_bench', 'wire_payoff_bench'})


class WindingToolEngagementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = build_winding_tool_assemblies()

    def test_audit_rejects_608_displaced_twenty_mm_along_shaft(self):
        jig = dict(self.model.winding_jig)
        jig['bearing_608_1'] = jig['bearing_608_1'].translate((20, 0, 0))
        audit = audit_winding_tool_assemblies(replace(self.model, winding_jig=jig))
        self.assertFalse(audit['valid'])
        self.assertFalse(audit['checks']['shaft_608_nesting'])

    def test_audit_rejects_entire_51105_stack_displaced_one_hundred_mm_upward(self):
        payoff = dict(self.model.wire_payoff)
        for name in ('housing_washer', 'rolling_envelope', 'shaft_washer'):
            payoff[name] = payoff[name].translate((0, 0, 100))
        audit = audit_winding_tool_assemblies(replace(self.model, wire_payoff=payoff))
        self.assertFalse(audit['valid'])
        self.assertFalse(audit['checks']['bearing_51105_nesting'])

    def test_audit_rejects_follower_withdrawn_one_hundred_mm_along_head_axis(self):
        jig = dict(self.model.winding_jig)
        jig['cam_follower_1'] = jig['cam_follower_1'].translate((100, 0, 0))
        audit = audit_winding_tool_assemblies(replace(self.model, winding_jig=jig))
        self.assertFalse(audit['valid'])
        self.assertFalse(audit['checks']['cam_follower_engagement'])

    def test_nominal_interfaces_have_positive_support_and_pilot_evidence(self):
        audit = audit_winding_tool_assemblies(self.model)
        self.assertTrue(audit['valid'], audit['checks'])
        for bearing in audit['bearing_608_engagement']:
            self.assertGreater(bearing['seat_wall_fraction'], 0.95)
            self.assertGreater(bearing['shoulder_fraction'], 0.95)
            self.assertGreater(bearing['shaft_pilot_fraction'], 0.95)
            self.assertLessEqual(bearing['seat_gap_mm'], 0.2)
        thrust = audit['bearing_51105_engagement']
        for name in ('base_support_fraction', 'housing_wall_fraction',
                     'platter_pilot_fraction', 'platter_support_fraction'):
            self.assertGreater(thrust[name], 0.95)
        for follower in audit['cam_follower_engagement']:
            for name in ('slider_shoulder_fraction', 'cam_shoulder_fraction',
                         'washer_shoulder_fraction', 'nut_thread_fraction'):
                self.assertGreater(follower[name], 0.95)


class WindingToolHardwareTests(unittest.TestCase):
    def test_complete_coil_removal_route_clears_frame_at_all_three_diameters(self):
        route_builder = getattr(assembly_module, 'coil_removal_stages', None)
        self.assertTrue(callable(route_builder), 'A complete modeled coil removal route is required')
        for diameter in (110.0, 127.0, 145.0):
            with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies',
                       return_value={'valid': True}):
                model = build_winding_tool_assemblies(diameter_mm=diameter)
            stages = route_builder(model)
            self.assertEqual([stage['name'] for stage in stages],
                             ['withdraw_head_and_locator_pins', 'withdraw_crank_pin',
                              'withdraw_shaft', 'lift_head_and_coil', 'remove_coil'])
            for stage in stages:
                vector = stage['translation_mm']
                fixed_boxes = {name: body.val().BoundingBox() for name, body in stage['fixed'].items()}
                for step in range(21):
                    for name, body in stage['moving'].items():
                        moved = body.translate(tuple(value * step / 20 for value in vector))
                        a = moved.val().BoundingBox()
                        for fixed_name, fixed in stage['fixed'].items():
                            b = fixed_boxes[fixed_name]
                            if a.xmax < b.xmin or b.xmax < a.xmin or a.ymax < b.ymin or b.ymax < a.ymin or a.zmax < b.zmin or b.zmax < a.zmin:
                                continue
                            self.assertLess(moved.intersect(fixed).val().Volume(), 1e-5,
                                            f'{diameter}, {stage["name"]}, {step}, {name}/{fixed_name}')
            last = stages[-1]
            coil = last['moving']['coil'].translate(last['translation_mm'])
            self.assertAlmostEqual(coil.val().BoundingBox().ylen, diameter + 6, places=5)
            self.assertGreater(coil.val().BoundingBox().zmin, 112.5)
            self.assertGreater(coil.val().BoundingBox().xmin, 40)

    def test_service_audits_reject_missing_locator_and_obstructed_removal(self):
        service_audit = getattr(assembly_module, 'audit_winding_tool_service', None)
        self.assertTrue(callable(service_audit), 'Service interfaces require geometric audits')
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies',
                   return_value={'valid': True}):
            model = build_winding_tool_assemblies()
        result = service_audit(model)
        self.assertTrue(all(result['checks'].values()), result)
        jig = dict(model.winding_jig)
        jig['shaft_locator_1'] = jig['shaft_locator_1'].translate((-20, 0, 0))
        self.assertFalse(service_audit(replace(model, winding_jig=jig))['checks']['spindle_axial_location'])
        jig = dict(model.winding_jig)
        # A connected overhead obstruction must invalidate the supported lift.
        post = cq.Workplane('XY').box(10, 10, 240, centered=(True, True, False)).translate((0, 85, 0))
        bridge = cq.Workplane('XY').box(100, 180, 10).translate((0, 0, 235))
        jig['base'] = jig['base'].union(post).union(bridge)
        self.assertFalse(service_audit(replace(model, winding_jig=jig))['checks']['complete_coil_removal'])

    def test_audit_rejects_removed_crank_retainer_even_if_ownership_is_updated(self):
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies',
                   return_value={'valid': True}):
            model = build_winding_tool_assemblies()
        members = dict(model.winding_jig)
        del members['crank_pin']
        ownership = {tool: {name: names - {'crank_pin'} for name, names in sets.items()}
                     for tool, sets in model.ownership.items()}
        audit = audit_winding_tool_assemblies(replace(
            model, winding_jig=members, ownership=ownership))
        self.assertFalse(audit['valid'])

    def test_isolated_rib_fasteners_withdraw_without_deforming_prints(self):
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies',
                   return_value={'valid': True}):
            model = build_winding_tool_assemblies()
        for name, direction in (('rib_pin_1', -1), ('rib_locknut_1', 1)):
            for travel in range(0, 31, 2):
                body = model.winding_jig[name]
                box = body.val().BoundingBox()
                cx, cz = (box.xmin + box.xmax) / 2, (box.zmin + box.zmax) / 2
                for angle in (0, 30, 60):
                    moving = body.rotate((cx, 0, cz), (cx, 1, cz), angle)
                    moving = moving.translate((0, direction * travel, 0))
                    for fixed in ('slider_1', 'rib_1'):
                        self.assertLess(moving.intersect(model.winding_jig[fixed])
                                        .val().Volume(), 1e-5)

    def test_complete_rib_subassembly_exits_after_cam_and_stop_removal(self):
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies',
                   return_value={'valid': True}):
            model = build_winding_tool_assemblies(diameter_mm=145.0)
        for travel in range(0, 51, 2):
            for name in ('slider_1', 'rib_1', 'rib_pin_1', 'rib_locknut_1',
                         'rib_washer_inner_1', 'rib_washer_outer_1'):
                # Local +X radial travel becomes world -Z.
                moving = model.winding_jig[name].translate((0, 0, -travel))
                self.assertLess(moving.intersect(model.winding_jig['backplate'])
                                .val().Volume(), 1e-5, f'{name}, travel={travel}')

    def test_audit_rejects_hidden_print_body_or_reclassified_rotating_parts(self):
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies',
                   return_value={'valid': True}):
            model = build_winding_tool_assemblies()
        ownership = {tool: dict(sets) for tool, sets in model.ownership.items()}
        ownership['winding_jig']['stationary'] |= ownership['winding_jig']['rotating']
        ownership['winding_jig']['rotating'] = frozenset()
        audit = audit_winding_tool_assemblies(replace(model, ownership=ownership))
        self.assertFalse(audit['checks']['ownership_partition'])
        printable = dict(model.printable_parts)
        del printable['winding_jig/base']
        self.assertFalse(audit_winding_tool_assemblies(
            replace(model, printable_parts=printable))['valid'])

    def test_retained_head_hardware_clears_printed_members(self):
        # Isolate construction here: the separate assembly tests exercise the
        # complete audit. This test checks actual retained hardware B-reps.
        with patch('windwall.winding_tool_assembly.audit_winding_tool_assemblies',
                   return_value={'valid': True}):
            model = build_winding_tool_assemblies()
        parts = model.winding_jig
        for i in range(1, 7):
            for prefix in ('cam_follower', 'cam_follower_nut',
                           'cam_follower_washer', 'rib_pin', 'rib_locknut',
                           'rib_washer_inner', 'rib_washer_outer'):
                hardware = parts[f'{prefix}_{i}']
                for name in ('backplate', 'cam', 'clamp',
                             f'slider_{i}', f'rib_{i}'):
                    with self.subTest(hardware=f'{prefix}_{i}', printed=name):
                        self.assertLess(hardware.intersect(parts[name]).val().Volume(),
                                        1e-5)
        rows = {row['item']: row['quantity'] for row in winding_tool_bom(model)}
        self.assertEqual(rows['cam follower captive nut'], 6)
        self.assertEqual(rows['cam follower washer'], 6)
        self.assertEqual(rows['rib attachment locknut'], 6)
        self.assertEqual(rows['rib attachment washer'], 12)
        self.assertNotIn('pin retaining compound', rows)


if __name__ == '__main__':
    unittest.main()
