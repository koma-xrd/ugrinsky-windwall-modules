"""Horizontal tool service and continuous straight-line collision checks.

The actual taped winding lifts +Z after the removable crank is parked above it.
All six shoes remain seated. The independently defined fixture has 9 mm axial
width, 1 mm radial winding build and eighteen closed 10 mm tape loops.
No deformation is assumed; physical fit, force and powered use are unvalidated.
"""

from functools import lru_cache
from math import isfinite

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
    return shape.translate((0, 0, height))


@lru_cache(maxsize=4096)
def local_shape(shape, height):
    return shape.translate((0, 0, -height))


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
    # The full winding sits above the lower support on the nominal-radius runout.
    # Its 0.02 mm inner gap is geometric clearance, not an allowance for
    # deforming the winding to lift it over a trapping lip.
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
    # Find the gravity seat from actual reference solids, not a floating nominal
    # height. Congruent shoes share the same support, so one suffices here; the
    # production audit independently checks all six actual occurrences below.
    coil, support = shapes['coil'], head.shoes[0]
    if not clear(coil, support):
        raise ValueError('Winding fixture starts inside its supporting shoe')
    low, high = 0.0, 8.0
    if clear(translated(coil, (0, 0, -high)), support):
        raise ValueError('Winding fixture has no lower supporting shoulder')
    for _ in range(13):
        middle = (low + high) / 2
        if intersection_volume(translated(coil, (0, 0, -middle)), support) <= 1e-8:
            low = middle
        else:
            high = middle
    # Keep two microns off the mathematical tangent so OCCT boundary prisms do
    # not report tolerance-sized overlap. The independent 0.02 mm support probe
    # still rejects a floating winding or a missing lower shoulder.
    return {name: translated(shape, (0, 0, -low + .002)) for name, shape in shapes.items()}


def coil_removal_stages(model):
    """Keep every occurrence while lifting the crank, then the closed taped coil."""
    diameter, height = head_datum(model)
    parts = dict(model.winding_jig)
    fixture = _winding_fixture(model.parameters, diameter)
    parts.update({name: installed_shape(shape, height) for name, shape in fixture.items()})
    groups = {name: owner['group'] for name, owner in model.ownership['winding_jig'].items()}
    groups.update({name: 'held_winding' for name in fixture})
    stages = []
    for name, names, vector in (
        ('wound_friction_fit', (), (0, 0, 0)),
        ('remove_crank', ('crank', 'grip'), (0, 0, 160)),
        ('remove_taped_coil', tuple(fixture), (0, 0, 120)),
    ):
        moving = {key: parts[key] for key in names}
        stages.append({'name': name, 'moving': moving,
                       'fixed': {key: value for key, value in parts.items() if key not in names},
                       'translation_mm': vector, 'groups': dict(groups),
                       'released': {}, 'restored': {}})
        for key, shape in moving.items():
            parts[key] = translated(shape, vector)
        if name == 'remove_crank':
            groups.update(crank='service_detached', grip='service_detached')
    return tuple(stages)


def audit_snap_access(model):
    """The winder has no snaps: reserve a clear upward path for its top drive."""
    parts = model.winding_jig
    return all(_linear_collision(parts[moving], parts[fixed], (0, 0, 160)) <= VOLUME_TOLERANCE
               for moving in ('crank', 'grip')
               for fixed in parts if fixed not in ('crank', 'grip'))


def _motion_ownership(model, stages):
    diameter, _ = head_datum(model)
    fixture = set(_winding_fixture(model.parameters, diameter))
    if len(stages) != 3:
        return False
    groups = {name: owner['group'] for name, owner in model.ownership['winding_jig'].items()}
    groups.update({name: 'held_winding' for name in fixture})
    for stage, (name, moving, vector) in zip(stages, (
        ('wound_friction_fit', set(), (0, 0, 0)),
        ('remove_crank', {'crank', 'grip'}, (0, 0, 160)),
        ('remove_taped_coil', fixture, (0, 0, 120)),
    )):
        if (stage['name'] != name or set(stage['moving']) != moving
                or tuple(stage['translation_mm']) != vector or stage['groups'] != groups
                or stage.get('released') or stage.get('restored')):
            return False
        if name == 'remove_crank':
            groups.update(crank='service_detached', grip='service_detached')
    return True


def audit_winding_tool_service(model, stages=None):
    """Continuously sweep actual solids, retaining the shoes and parked crank."""
    checks = {name: False for name in (
        'snap_access', 'winding_supported', 'wound_closed_tape', 'route_continuity', 'motion_ownership',
        'all_shoes_seated', 'complete_coil_removal')}
    result = {'checks': checks, 'collisions': [], 'errors': [],
              'continuous_translation_checks': True,
              'release_direction': '+Z', 'shoes_removed': False,
              'fixture_mm': {'winding_radial_build': 1, 'winding_axial_width': 9,
                             'tape_radial_span': 4, 'tape_axial_span': 10,
                             'tape_tangential_width': 10, 'tape_wall': .25}}
    try:
        diameter, height = head_datum(model)
        stages = coil_removal_stages(model) if stages is None else tuple(stages)
        checks['motion_ownership'] = _motion_ownership(model, stages)
        checks['snap_access'] = audit_snap_access(model)
        expected = dict(model.winding_jig)
        fixture = {name: installed_shape(shape, height)
                   for name, shape in _winding_fixture(model.parameters, diameter).items()}
        expected.update(fixture)
        checks['winding_supported'] = all(
            clear(fixture['coil'], model.winding_jig[f'shoe_{index}'])
            and _linear_collision(fixture['coil'], model.winding_jig[f'shoe_{index}'],
                                  (0, 0, -.02)) > VOLUME_TOLERANCE
            for index in range(1, 7))
        result['fixture_mm']['seated_coil_bottom_local_z'] = bounds(fixture['coil']).zmin - height
        checks['wound_closed_tape'] = all(clear(shape, body)
            for shape in fixture.values() for body in model.winding_jig.values())
        continuous = bool(stages)
        for stage in stages:
            present = {**stage['fixed'], **stage['moving']}
            continuous &= (not stage['fixed'].keys() & stage['moving'].keys()
                           and present.keys() == expected.keys()
                           and all(_same_shape(present[name], body) for name, body in expected.items()))
            vector = tuple(stage['translation_mm'])
            if len(vector) != 3 or not all(isfinite(v) for v in vector):
                raise ValueError('Service translation must be a finite three-vector')
            for name, moving in stage['moving'].items():
                for fixed_name, fixed in stage['fixed'].items():
                    volume = _linear_collision(moving, fixed, vector)
                    if volume > VOLUME_TOLERANCE:
                        result['collisions'].append({'stage': stage['name'], 'moving': name,
                            'fixed': fixed_name, 'overlap_mm3': volume})
                        break
                expected[name] = translated(moving, vector)
            continuous &= not stage.get('released') and not stage.get('restored')
        checks['route_continuity'] = bool(continuous)
        final = stages[-1]
        checks['all_shoes_seated'] = all(
            name in final['fixed'] and _same_shape(final['fixed'][name], model.winding_jig[name])
            and final['groups'][name] == model.ownership['winding_jig'][name]['group']
            for name in (f'shoe_{i}' for i in range(1, 7)))
        checks['complete_coil_removal'] = bool(
            all(checks[name] for name in checks if name != 'complete_coil_removal')
            and not result['collisions'] and set(final['moving']) == set(fixture)
            and tuple(final['translation_mm']) == (0, 0, 120))
    except (KeyError, ValueError, RuntimeError, TypeError, IndexError) as error:
        result['errors'].append(f'{type(error).__name__}: {error}')
    return result
