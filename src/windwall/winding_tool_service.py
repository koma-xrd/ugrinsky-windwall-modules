"""Tool-free service poses and continuous straight-line collision checks.

The authoritative assembly solids remain in every pose. A bounded compressed
hook envelope represents released PLA tabs; it is not an elastic/force model.
The explicit fixture is a 9 mm axial winding with 1 mm radial build and eighteen
closed tape loops, each 10 mm wide tangentially. It does not certify larger
coils, fit, fatigue or hand force.
"""

from functools import lru_cache
from math import cos, isfinite, radians, sin

import cadquery as cq
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Vec

from windwall.winding_head import build_winding_head


VOLUME_TOLERANCE = 1e-5


@lru_cache(maxsize=16384)
def bounds(shape):
    return shape.val().BoundingBox()


def _boxes_overlap(a, b):
    return not (a.xmax < b.xmin or b.xmax < a.xmin or a.ymax < b.ymin
                or b.ymax < a.ymin or a.zmax < b.zmin or b.zmax < a.zmin)


@lru_cache(maxsize=32768)
def intersection_volume(first, second):
    if not _boxes_overlap(bounds(first), bounds(second)):
        return 0.0
    volume = first.intersect(second).val().Volume()
    if not isfinite(volume):
        raise ValueError('Non-finite CAD intersection')
    return volume


def clear(first, second):
    return intersection_volume(first, second) <= VOLUME_TOLERANCE


def box(x, y, z, dx, dy, dz):
    return cq.Workplane('XY').box(dx, dy, dz, centered=False).translate((x, y, z))


def ring(outer, inner, bottom, height):
    sketch = cq.Workplane('XY').circle(outer)
    if inner:
        sketch = sketch.circle(inner)
    return sketch.extrude(height).translate((0, 0, bottom))


@lru_cache(maxsize=4096)
def installed_shape(shape, height):
    return shape.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, 0, height))


@lru_cache(maxsize=4096)
def local_shape(shape, height):
    return shape.translate((0, 0, -height)).rotate((0, 0, 0), (1, 0, 0), -90)


def head_datum(model):
    record = model.ownership['winding_jig']['wheel']
    return record['diameter_mm'], record['axis_height_mm']


@lru_cache(maxsize=32)
def head_reference(parameters, diameter):
    """Use component-owned dimensions only to construct independent gauges."""
    return build_winding_head(parameters, diameter)


@lru_cache(maxsize=2048)
def translated(shape, vector):
    return shape.translate(vector)


def _same_shape(first, second):
    if first is second or first.val().isSame(second.val()):
        return True
    a, b = bounds(first), bounds(second)
    if any(abs(getattr(a, key) - getattr(b, key)) > 1e-6
           for key in ('xmin', 'ymin', 'zmin', 'xmax', 'ymax', 'zmax')):
        return False
    return (abs(first.val().Volume() - second.val().Volume()) < VOLUME_TOLERANCE
            and first.cut(second).val().Volume() < VOLUME_TOLERANCE)


@lru_cache(maxsize=4096)
def _linear_collision(moving, fixed, vector):
    """Exact boundary-prism union for an entire translation, including endpoints.

    Any newly occupied point crosses an original boundary face. Sweeping every
    face therefore covers the translated solid continuously; parallel faces
    yield zero-volume shells. Bounding boxes only reject disjoint candidates.
    """
    end = translated(moving, vector)
    a, b, c = bounds(moving), bounds(end), bounds(fixed)
    swept_bounds = a.add(b)
    if not _boxes_overlap(swept_bounds, c):
        return 0.0
    # Trim remote detail (especially wheel markings) before testing each face.
    # No point of the translation can leave this enclosing box.
    if len(fixed.val().Faces()) > max(64, 2 * len(moving.val().Faces())):
        mask = box(swept_bounds.xmin - .001, swept_bounds.ymin - .001, swept_bounds.zmin - .001,
                   swept_bounds.xlen + .002, swept_bounds.ylen + .002, swept_bounds.zlen + .002)
        fixed = fixed.intersect(mask)
        if fixed.val().Volume() <= VOLUME_TOLERANCE:
            return 0.0
        c = bounds(fixed)
    for pose in (moving, end):
        overlap = intersection_volume(pose, fixed)
        if overlap > VOLUME_TOLERANCE:
            return overlap
    if not any(vector):
        return 0.0
    # Sweeping the simpler fixed body in the inverse direction describes the
    # same relative motion, often reducing a shoe/tape check to twelve faces.
    if len(fixed.val().Faces()) < len(moving.val().Faces()):
        return _linear_collision(fixed, moving, tuple(-value for value in vector))
    for face in moving.val().Faces():
        first = face.BoundingBox()
        last = face.translate(vector).BoundingBox()
        if not _boxes_overlap(first.add(last), c):
            continue
        swept = cq.Shape.cast(BRepPrimAPI_MakePrism(face.wrapped, gp_Vec(*vector)).Shape())
        solids = [solid for solid in swept.Solids() if solid.Volume() > VOLUME_TOLERANCE]
        if not solids:
            continue
        probe = cq.Workplane('XY').newObject([cq.Compound.makeCompound(solids)])
        overlap = intersection_volume(probe, fixed)
        if overlap > VOLUME_TOLERANCE:
            return overlap
    return 0.0


@lru_cache(maxsize=256)
def _compressed_shoe(shoe, parameters, diameter, index):
    # Same bounded hook-clearance envelope proven by the head regressions.
    # Only the outer 0.25 mm interference strip changes; keyed posts remain.
    shape = shoe.rotate((0, 0, 0), (0, 0, 1), -index * 60)
    metadata = head_reference(parameters, diameter).metadata
    pin_x = diameter / 2 - metadata['pin_setback_mm']
    for row in metadata['pin_rows_y_mm']:
        y = row + 1.65 if row > 0 else row - 3
        shape = shape.cut(box(pin_x - 1.1, y, -2, 2.2, 1.35, 2))
    return shape.rotate((0, 0, 0), (0, 0, 1), index * 60)


@lru_cache(maxsize=32)
def _winding_band(parameters, diameter, inner_offset, outer_offset, bottom, height):
    """Offset the convex hull of the six translated circular contact arcs.

    The arc centers form a regular hexagon; its circular offset gives both the
    contact arcs and the taut straight spans. At the minimum setting it reduces
    to a circle. A nominal-diameter circular ring misses those inward spans.
    """
    contact_radius = parameters.minimum_diameter_mm / 2
    center_radius = diameter / 2 - contact_radius
    if abs(center_radius) < 1e-8:
        return ring(contact_radius + outer_offset, contact_radius + inner_offset, bottom, height)

    def envelope(offset, depth, z):
        return (cq.Workplane('XY').polygon(6, center_radius * 2)
                .offset2D(contact_radius + offset, kind='arc').extrude(depth)
                .translate((0, 0, z)))

    return envelope(outer_offset, height, bottom).cut(envelope(inner_offset, height + 2, bottom - 1))


@lru_cache(maxsize=32)
def _winding_fixture(parameters, diameter):
    head = head_reference(parameters, diameter)
    radius = diameter / 2
    contact_radius = parameters.minimum_diameter_mm / 2
    shapes = {'coil': _winding_band(parameters, diameter, .02, 1, 12.5, 9)}
    # Follow the same circular contact arc as the winding. A straight rectangle
    # at each old slot center intersects the curved bundle when widened to a
    # real strip. Keep a conservative 4 mm radial envelope so the cavity also
    # surrounds the inward chords where wire bridges the wide tape slots.
    tape_envelope = ring(contact_radius + 2, contact_radius - 2, 12, 10).cut(
        ring(contact_radius + 1.75, contact_radius - 1.75, 12.25, 9.5))
    tape_envelope = tape_envelope.translate((radius - contact_radius, 0, 0))
    for index, corridor in enumerate(head.metadata['tape_passage_probes']):
        local = corridor.rotate((0, 0, 0), (0, 0, 1), -(index // 3) * 60)
        offset = local.val().Center().y
        tape = tape_envelope.intersect(box(radius - 12, offset - 5, 11, 14, 10, 12))
        shapes[f'tape_{index + 1}'] = tape.rotate((0, 0, 0), (0, 0, 1), (index // 3) * 60)
    return shapes


def coil_removal_stages(model):
    """Return drawing-ready poses with explicit motion and service ownership.

    Each shoe is unlatched, withdrawn 40 mm forward, then parked radially
    outside the winding. The taped coil stays put until all six shoes are
    detached. Fixed members, including parked shoes, are never discarded.
    Positive local Z is world negative Y. A helper supports the taped winding.
    """
    diameter, height = head_datum(model)
    head = head_reference(model.parameters, diameter)
    parts = dict(model.winding_jig)
    parts.update({name: installed_shape(shape, height)
                  for name, shape in _winding_fixture(model.parameters, diameter).items()})
    groups = {name: owner['group'] for name, owner in model.ownership['winding_jig'].items()}
    groups.update({name: 'held_winding' for name in parts if name not in groups})
    stages = []

    def stage(name, names=(), vector=(0, 0, 0), released=None, restored=None):
        moving = {key: parts[key] for key in names}
        stages.append({'name': name, 'moving': moving,
                       'fixed': {key: value for key, value in parts.items() if key not in names},
                       'translation_mm': vector, 'groups': dict(groups),
                       'released': {} if released is None else released,
                       'restored': {} if restored is None else restored})
        for key, value in moving.items():
            parts[key] = translated(value, vector)
        if released:
            parts.update(released)
        if restored:
            parts.update(restored)

    stage('wound_latched')
    lift = head.metadata['release_lift_mm']
    for index in range(model.parameters.spoke_count):
        name = f'shoe_{index + 1}'
        compressed = installed_shape(_compressed_shoe(
            local_shape(parts[name], height), model.parameters, diameter, index), height)
        stage(f'release_{name}', (name,), released={name: compressed})
        stage(f'withdraw_{name}', (name,), (0, -lift, 0))
        groups[name] = 'service_detached'
        stage(f'relax_{name}', (name,), restored={
            name: translated(model.winding_jig[name], (0, -lift, 0))})
        angle = radians(index * 60)
        stage(f'park_{name}', (name,), (lift * cos(angle), 0, lift * sin(angle)))
    stage('shoes_detached')
    winding = tuple(_winding_fixture(model.parameters, diameter))
    stage('remove_taped_coil', winding, (0, -120, 0))
    return tuple(stages)


def audit_snap_access(model):
    diameter, height = head_datum(model)
    setback = head_reference(model.parameters, diameter).metadata['pin_setback_mm']
    local = {name: local_shape(shape, height) for name, shape in model.winding_jig.items()}
    access = []
    for index in range(6):
        probe = box(diameter / 2 - setback - 2, -9, -16, 4, 18, 12).rotate(
            (0, 0, 0), (0, 0, 1), index * 60)
        access.append((probe, ('base', 'tower', 'wheel', 'shaft', 'crank')))
    for name in ('snap_collar_1', 'snap_collar_2'):
        z = bounds(local[name]).zmin
        access.append((box(-8, 5.2, z - .1, 16, 18, 2), ('base', 'tower', 'wheel', 'crank')))
    for name in ('bearing_retainer_1', 'bearing_retainer_2'):
        z = bounds(local[name]).zmin
        access.append((box(-5, 12, z, 10, 12, 1.5), ('tower', 'base')))
    for x in (-24, 17):
        access.append((box(x, -height + 18, -40, 7, 12, 18), ('base',)))
    access.append((box(-9, -4, 7.5, 18, 8, 12), ('base', 'tower', 'wheel')))
    access.append((box(-2, 5, -68, 4, 10, 12), ('base', 'tower', 'shaft')))
    access.append((box(47, -5, -95, 10, 10, 10), ('base', 'tower', 'grip')))
    return all(clear(probe, local[name]) for probe, names in access for name in names)


def _motion_ownership(model, stages):
    """Permit only shoe release/parking and the final held-winding translation."""
    diameter, _ = head_datum(model)
    lift = head_reference(model.parameters, diameter).metadata['release_lift_mm']
    winding = set(_winding_fixture(model.parameters, diameter))
    states = {f'shoe_{i}': 'latched' for i in range(1, 7)}
    initial_groups = {name: owner['group'] for name, owner in model.ownership['winding_jig'].items()}
    initial_groups.update({name: 'held_winding' for name in winding})
    transitions = {'release': ('latched', 'released'), 'withdraw': ('released', 'withdrawn'),
                   'relax': ('withdrawn', 'relaxed'), 'park': ('relaxed', 'parked')}
    valid = bool(stages)
    for index, stage in enumerate(stages):
        groups = dict(initial_groups)
        groups.update({name: 'service_detached' for name, state in states.items()
                       if state in ('withdrawn', 'relaxed', 'parked')})
        valid &= stage['groups'] == groups
        vector = tuple(stage['translation_mm'])
        if len(vector) != 3 or not all(isfinite(value) for value in vector):
            return False
        name = stage['name']
        moving, released, restored = set(stage['moving']), set(stage.get('released', {})), set(stage.get('restored', {}))
        expected_moving = expected_released = expected_restored = set()
        expected_vector = (0, 0, 0)
        if name == 'wound_latched':
            valid &= index == 0 and all(state == 'latched' for state in states.values())
        elif name == 'shoes_detached':
            valid &= all(state == 'parked' for state in states.values())
        elif name == 'remove_taped_coil':
            valid &= index == len(stages) - 1 and all(state == 'parked' for state in states.values())
            valid &= vector[1] < -100
            expected_moving = winding
            expected_vector = (0, vector[1], 0)
        else:
            action, _, shoe = name.partition('_')
            if action not in transitions or shoe not in states:
                valid = False
                continue
            before, after = transitions[action]
            valid &= states[shoe] == before
            states[shoe] = after
            expected_moving = {shoe}
            if action == 'release':
                expected_released = {shoe}
            elif action == 'withdraw':
                expected_vector = (0, -lift, 0)
            elif action == 'relax':
                expected_restored = {shoe}
            else:
                angle = radians((int(shoe.split('_')[1]) - 1) * 60)
                expected_vector = (lift * cos(angle), 0, lift * sin(angle))
        valid &= (moving == expected_moving and released == expected_released and restored == expected_restored
                  and all(abs(actual - expected) <= 1e-6 for actual, expected in zip(vector, expected_vector)))
    return bool(valid and all(state == 'parked' for state in states.values()))


def audit_winding_tool_service(model, stages=None):
    """Inspect the standard route or a supplied drawing/service route.

    The supplied route is validated against the model's first pose, bounded
    latch-state changes, every intervening pose and the final removal motion.
    The return is JSON-safe; the pose builder itself intentionally returns CAD.
    """
    checks = {name: False for name in ('snap_access', 'wound_closed_tape',
        'route_continuity', 'motion_ownership', 'all_shoes_detached', 'radial_support_clearance',
        'complete_coil_removal')}
    result = {'checks': checks, 'collisions': [], 'errors': [],
              'radial_support_clearance_mm': 0.0,
              'continuous_translation_checks': True,
              'fixture_mm': {'winding_radial_build': 1, 'winding_axial_width': 9,
                             'tape_radial_span': 4, 'tape_axial_span': 10,
                             'tape_tangential_width': 10,
                             'tape_wall': .25}}
    try:
        diameter, height = head_datum(model)
        stages = coil_removal_stages(model) if stages is None else tuple(stages)
        checks['motion_ownership'] = _motion_ownership(model, stages)
        checks['snap_access'] = audit_snap_access(model)
        expected = dict(model.winding_jig)
        fixture = {name: installed_shape(shape, height)
                   for name, shape in _winding_fixture(model.parameters, diameter).items()}
        expected.update(fixture)
        checks['wound_closed_tape'] = all(clear(shape, body)
            for shape in fixture.values() for body in model.winding_jig.values())
        continuous = bool(stages and stages[0]['name'] == 'wound_latched'
                          and stages[-1]['name'] == 'remove_taped_coil')
        for stage in stages:
            present = {**stage['fixed'], **stage['moving']}
            continuous &= (not stage['fixed'].keys() & stage['moving'].keys()
                           and present.keys() == expected.keys()
                           and all(_same_shape(present[name], body) for name, body in expected.items()))
            vector = tuple(stage['translation_mm'])
            for name, moving in stage['moving'].items():
                for fixed_name, fixed in stage['fixed'].items():
                    overlap = _linear_collision(moving, fixed, vector)
                    if overlap > VOLUME_TOLERANCE:
                        result['collisions'].append({'stage': stage['name'], 'moving': name,
                            'fixed': fixed_name, 'overlap_mm3': overlap})
                        break
                expected[name] = translated(moving, vector)
            for name, released in stage.get('released', {}).items():
                index = int(name.split('_')[-1]) - 1
                permitted = installed_shape(_compressed_shoe(
                    local_shape(expected[name], height), model.parameters, diameter, index), height)
                continuous &= (stage['name'] == f'release_{name}' and not any(vector)
                               and _same_shape(released, permitted))
                expected[name] = released
            for name, restored in stage.get('restored', {}).items():
                index = int(name.split('_')[-1]) - 1
                original = model.winding_jig[name]
                lift = head_reference(model.parameters, diameter).metadata['release_lift_mm']
                permitted = translated(original, (0, -lift, 0))
                compressed = installed_shape(_compressed_shoe(local_shape(original, height),
                    model.parameters, diameter, index), height)
                continuous &= (stage['name'] == f'relax_{name}' and not any(vector)
                               and _same_shape(restored, permitted)
                               and _same_shape(expected[name], translated(compressed, (0, -lift, 0))))
                # The relaxed solid contains the entire bounded tab-relaxation
                # envelope, so an obstacle cannot hide in the restored strip.
                for fixed_name, fixed in stage['fixed'].items():
                    overlap = intersection_volume(restored, fixed)
                    if overlap > VOLUME_TOLERANCE:
                        result['collisions'].append({'stage': stage['name'], 'moving': name,
                            'fixed': fixed_name, 'overlap_mm3': overlap})
                expected[name] = restored
        checks['route_continuity'] = bool(continuous)
        final = stages[-1]
        shoes = [f'shoe_{i}' for i in range(1, 7)]
        checks['all_shoes_detached'] = all(
            final['groups'].get(name) == 'service_detached'
            and local_shape(final['fixed'][name], height).val().BoundingBox().zmin > 30
            for name in shoes)
        # Enlarge the entire closed taped winding inward and outward by the
        # required radial margin, over its axial span. Any retained shoe or
        # obstructing structural member then fails before winding motion.
        margin = model.parameters.release_clearance_mm
        support_band = installed_shape(_winding_band(model.parameters, diameter,
            -4 - margin, 4 + margin, 12, 10), height)
        winding_pose_known = set(final['moving']) == set(fixture)
        if winding_pose_known:
            offset = final['moving']['coil'].val().Center().sub(fixture['coil'].val().Center()).toTuple()
            winding_pose_known = all(_same_shape(final['moving'][name], translated(shape, offset))
                                     for name, shape in fixture.items())
            support_band = translated(support_band, offset)
        clearance = winding_pose_known and all(clear(support_band, shape) for shape in final['fixed'].values())
        checks['radial_support_clearance'] = bool(clearance and checks['all_shoes_detached'])
        result['radial_support_clearance_mm'] = margin if checks['radial_support_clearance'] else 0.0
        checks['complete_coil_removal'] = bool(
            checks['wound_closed_tape'] and checks['route_continuity'] and checks['motion_ownership']
            and checks['all_shoes_detached'] and checks['radial_support_clearance']
            and not result['collisions']
            and set(final['moving']) == set(fixture)
            and final['translation_mm'][1] < -100)
    except (KeyError, ValueError, RuntimeError, TypeError, IndexError) as error:
        result['errors'].append(f'{type(error).__name__}: {error}')
    return result
