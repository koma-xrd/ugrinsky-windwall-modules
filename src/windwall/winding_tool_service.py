"""Service routes and mounting/retention gauges for the winding tools.

Consumes authoritative assembly dictionaries without rebuilding component CAD.
The coil surrogate bounds a 10 mm axial winding, 3 mm radial build and 0.5 mm
inward tape allowance. Routes assume a helper supports loose members and the
head; they do not certify hand clearance, strength or arbitrary coil sizes.
"""

from functools import lru_cache
from math import cos, radians, sin

import cadquery as cq


@lru_cache(maxsize=4096)
def _box(body):
    return body.val().BoundingBox()


def _overlap(first, second):
    a, b = _box(first), _box(second)
    if (a.xmax < b.xmin or b.xmax < a.xmin or a.ymax < b.ymin
            or b.ymax < a.ymin or a.zmax < b.zmin or b.zmax < a.zmin):
        return 0.0
    return first.intersect(second).val().Volume()


def _clear(first, second):
    return _overlap(first, second) < 1e-5


def _x_ring(outer, inner, start, length, height=95):
    return (cq.Workplane('XY').circle(outer).circle(inner).extrude(length)
            .rotate((0, 0, 0), (0, 1, 0), 90).translate((start, 0, height)))


def coil_removal_stages(model):
    """Return physical translations after release, in required service order.

    The shaft exits left after its five pins and keeper clips are removed.
    Both uprights remain bolted to the bench. A helper supports the head stack,
    crank and loose collars; the head and taped coil then lift together before
    the coil slides axially off the ribs above the frame.
    """
    parts = dict(model.winding_jig)
    p = model.parameters
    height = model.frame.shaft_reference.val().BoundingBox().center.z
    rear = model.frame.head.backplate.val().BoundingBox().xmin
    for i in range(1, 7):
        angle = radians((i - 1) * 60)
        vector = (0, -p.release_travel_mm * sin(angle), p.release_travel_mm * cos(angle))
        for prefix in ('slider', 'rib', 'cam_follower', 'cam_follower_nut',
                       'cam_follower_washer', 'rib_pin', 'rib_locknut',
                       'rib_washer_inner', 'rib_washer_outer'):
            name = f'{prefix}_{i}'
            parts[name] = parts[name].translate(vector)
    for step in range(1, 49):
        turned = parts['cam'].rotate((0, 0, height), (1, 0, height), step*.5)
        if all(_clear(turned, parts[f'cam_follower_{i}']) for i in range(1, 7)):
            parts['cam'] = turned
            break
    else:
        raise ValueError('Cam cannot reach the complete coil-removal state')
    radius = model.head.state.requested_diameter_mm / 2
    parts['coil'] = _x_ring(radius + 3, radius - .5, rear + 14, 10, height)
    stages = []

    def stage(name, members, vector, remove=False):
        moving = {key: parts[key] for key in sorted(members)}
        fixed = {key: body for key, body in parts.items() if key not in members}
        stages.append({'name': name, 'moving': moving, 'fixed': fixed,
                       'translation_mm': vector})
        for key in members:
            body = parts.pop(key)
            if not remove:
                parts[key] = body.translate(vector)

    stage('withdraw_head_and_locator_pins',
          {'head_retaining_pin_1', 'head_retaining_pin_2',
           'shaft_locator_pin_1', 'shaft_locator_pin_2'}, (0, 0, 40), remove=True)
    stage('withdraw_crank_pin', {'crank_pin'}, (0, 40, 0), remove=True)
    stage('withdraw_shaft', {'shaft'}, (-220, 0, 0), remove=True)
    head_members = set(model.head.printable_parts) | {
        'head_hub', 'head_retaining_collar', 'coil'}
    head_members |= {name for name in parts if name.startswith(
        ('preload_', 'cam_follower', 'rib_', 'guide_stop_'))}
    stage('lift_head_and_coil', head_members, (0, 0, 200))
    stage('remove_coil', {'coil'}, (50, 0, 0))
    return tuple(stages)


def _route_audit(stages):
    collisions = []
    for stage in stages:
        for step in range(21):
            vector = tuple(value * step / 20 for value in stage['translation_mm'])
            for name, body in stage['moving'].items():
                moved = body.translate(vector)
                for fixed_name, fixed in stage['fixed'].items():
                    volume = _overlap(moved, fixed)
                    if volume > 1e-5:
                        collisions.append({'stage': stage['name'], 'sample': step,
                                           'moving': name, 'fixed': fixed_name,
                                           'volume_mm3': volume})
                        return collisions
    return collisions


def _spindle_location(jig):
    bearing = jig['bearing_608_1']
    bb = bearing.val().BoundingBox()
    height = (bb.zmin + bb.zmax)/2
    evidence = []
    for index, direction in ((1, 1), (2, -1)):
        collar, pin = jig[f'shaft_locator_{index}'], jig[f'shaft_locator_pin_{index}']
        gap = collar.val().distance(bearing.val())
        outside_inner_ring = _x_ring(11, 5.25, bb.xmin-.3, bb.xlen+.6, height)
        valid = (0 <= gap <= .2 and _clear(collar, bearing)
                 and _overlap(collar.translate((direction*.25, 0, 0)), bearing) > 0
                 and _clear(collar, outside_inner_ring) and _clear(collar, pin)
                 and _clear(jig['shaft'], pin)
                 and _overlap(collar.translate((.25, 0, 0)), pin) > 0
                 and _overlap(jig['shaft'].translate((.25, 0, 0)), pin) > 0)
        evidence.append({'gap_mm': gap, 'valid': bool(valid)})
    caps_valid = True
    for index, side, inward in ((1, 'left', 1), (2, 'right', -1)):
        bearing, cap, upright = (jig[name] for name in
                                (f'bearing_608_{index}', f'{side}_bearing_cap', f'{side}_upright'))
        bearing_bounds = _box(bearing)
        # SKF 608-2RSH seal/recess exclusion, conservative flush end faces.
        seals = _x_ring(9.6, 5.25, bearing_bounds.xmin, bearing_bounds.xlen, height)
        caps_valid &= (_clear(bearing, cap)
                       and _overlap(bearing.translate((inward*.35, 0, 0)), cap) > 0
                       and _overlap(bearing.translate((-inward*.35, 0, 0)), upright) > 0
                       and _clear(seals.translate((inward*.35, 0, 0)), cap)
                       and _clear(seals.translate((-inward*.35, 0, 0)), upright))
        for screw_index in range(2*index-1, 2*index+1):
            screw = jig[f'bearing_cap_screw_{screw_index}']
            caps_valid &= (_clear(screw, cap) and _clear(screw, upright)
                           and _overlap(screw.translate((0, .3, 0)), cap) > 0
                           and _overlap(screw.translate((0, .3, 0)), upright) > 0)
    return all(row['valid'] for row in evidence) and bool(caps_valid), evidence


def _frame_mounting(jig):
    bench = cq.Workplane('XY').box(400, 400, 10, centered=(True, True, False)).translate((0, 0, -10))
    names = [f'{prefix}_{i}' for prefix, count in
             (('upright_fastener', 4), ('upright_washer', 8), ('upright_nut', 4))
             for i in range(1, count+1)]
    clear = all(_clear(jig[name], bench) and _clear(jig[name], jig['base']) for name in names)
    minimum = min(jig[name].val().BoundingBox().zmin for name in names)
    for i in range(1, 5):
        lower = jig[f'upright_washer_{2*i-1}']
        clear &= (lower.val().distance(jig['base'].val()) < 1e-5
                  and _overlap(lower.translate((0, 0, .1)), jig['base']) > 0)
    return bool(clear), minimum


def brake_access_key():
    """Nominal short 2.5 mm hex-key envelope, inserted from the open +X side."""
    stem = (cq.Workplane('XY').polygon(6, 2.4/(3**.5/2)).extrude(9.5)
            .translate((55, 0, -8)))
    arm = (cq.Workplane('XY').circle(1.5).extrude(90)
           .rotate((0, 0, 0), (0, 1, 0), 90).translate((55, 0, -8)))
    return stem.union(arm)


def _brake_service(parts):
    base, adjuster = parts['base'], parts['adjuster']
    remaining = adjuster.val().distance(parts['platter'].val()) - 1
    keyed = True
    for travel in (remaining-1, remaining):
        shifted = adjuster.translate((0, 0, travel))
        keyed &= _clear(shifted, base)
        for angle in (-10, 10):
            keyed &= _overlap(shifted.rotate((55, 0, 0), (55, 0, 1), angle), base) > .01
    bottom = base.val().BoundingBox().zmin
    bench = (cq.Workplane('XY').box(400, 400, 10, centered=(True, True, False))
             .translate((0, 0, bottom-10)))
    key = brake_access_key()
    accessible = _clear(base, bench)
    for angle in range(-30, 31, 10):
        turned = key.rotate((55, 0, 0), (55, 0, 1), angle)
        screw = parts['screw'].rotate((55, 0, 0), (55, 0, 1), angle)
        accessible &= all(_clear(turned, fixed) for fixed in (bench, base, screw))
    # Lower the key out of its socket before inserting/removing it sideways.
    for travel in range(0, 61, 10):
        accessible &= _clear(key.translate((travel, 0, -3)), base)
    return bool(keyed), bool(accessible), -9.5-bottom


def audit_winding_tool_service(model):
    """Return measured service evidence; missing or displaced hardware fails."""
    _box.cache_clear()
    checks = {name: False for name in ('spindle_axial_location', 'complete_coil_removal',
                                      'frame_flush_mounting', 'brake_anti_rotation',
                                      'brake_mounted_access')}
    result = {'checks': checks, 'route_sample_count_per_stage': 21,
              'coil_surrogate_mm': {'axial_width': 10, 'radial_build': 3,
                                     'inward_tape_allowance': .5}, 'errors': []}
    try:
        checks['spindle_axial_location'], result['shaft_locators'] = _spindle_location(model.winding_jig)
        stages = coil_removal_stages(model)
        result['coil_removal_collisions'] = _route_audit(stages)
        checks['complete_coil_removal'] = not result['coil_removal_collisions']
        result['coil_removal_translations_mm'] = {stage['name']: list(stage['translation_mm']) for stage in stages}
        checks['frame_flush_mounting'], result['upright_hardware_bench_clearance_mm'] = _frame_mounting(model.winding_jig)
        (checks['brake_anti_rotation'], checks['brake_mounted_access'],
         result['brake_key_bench_clearance_mm']) = _brake_service(model.wire_payoff)
    except (KeyError, ValueError, RuntimeError) as error:
        result['errors'].append(f'{type(error).__name__}: {error}')
    return result
