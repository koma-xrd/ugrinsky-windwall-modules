"""Two independent manual tools, occurrence ownership, geometry gates and BOM.

Component builders own dimensions and printed masters. This module installs
their public records and audits the authoritative occurrence solids, including
mutated assemblies. Ownership has exactly one record per occurrence. A complete
51105 is one purchase whose three separately placed members retain load ownership.
These are prototype CAD gates, not physical fit or operating approval.
"""

from collections import Counter
from dataclasses import dataclass, replace
from functools import lru_cache
from itertools import combinations
from math import atan2, cos, degrees, hypot, isfinite, radians, sin

import cadquery as cq

from windwall.bearings import build_51105_reference, build_608_reference
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters
from windwall.winding_frame import build_winding_frame
from windwall.winding_head import build_winding_head
from windwall.winding_tool_parameters import (
    DEFAULT_WINDING_TOOL_PARAMETERS, WindingToolParameters, diameter_settings_mm,
)
from windwall.winding_tool_service import (
    VOLUME_TOLERANCE, audit_snap_access, audit_winding_tool_service, bounds, box, clear,
    head_datum, head_reference, installed_shape,
    intersection_volume, local_shape, ring, translated,
)
from windwall.wire_payoff import build_wire_payoff


@dataclass(frozen=True)
class WindingToolAssemblies:
    winding_jig: dict[str, cq.Workplane]
    wire_payoff: dict[str, cq.Workplane]
    ownership: dict[str, dict[str, dict]]
    parameters: WindingToolParameters
    audit: dict[str, bool]


# One identity table owns required occurrences, print grouping and motion role.
_JIG_LAYOUT = {
    'base': ('base', 'stationary'), 'tower': ('bearing_tower', 'stationary'),
    'wheel': ('coil_wheel', 'rotating'), 'shaft': ('printed_shaft', 'rotating'),
    'crank': ('hand_crank', 'rotating'), 'grip': ('rotating_grip', 'rotating'),
    **{f'shoe_{i}': ('contact_shoe', 'rotating') for i in range(1, 7)},
    **{f'bearing_retainer_{i}': ('bearing_retainer', 'stationary') for i in (1, 2)},
    **{f'snap_collar_{i}': ('snap_collar', 'rotating') for i in (1, 2)},
    **{f'bearing_608_{i}': ('608 bearing', 'stationary') for i in (1, 2)},
}
_PAYOFF_LAYOUT = {
    'base': ('base', 'stationary'), 'spindle': ('printed_spindle', 'rotating'),
    'platter': ('platter', 'rotating'),
    'lower_washer': ('51105 thrust bearing', 'stationary'),
    'bearing': ('51105 thrust bearing', 'bearing_internal'),
    'upper_washer': ('51105 thrust bearing', 'rotating'),
}
_PURCHASES = frozenset(('608 bearing', '51105 thrust bearing'))
_BEARING_DIMENSIONS = {
    '608': DEFAULT_PARAMETERS.bearings.radial_nominal_dimensions_mm,
    '51105': DEFAULT_PARAMETERS.bearings.thrust_nominal_dimensions_mm,
}


def _owners(layout):
    return {name: {'master': master, 'group': group,
                   'source': 'purchased' if master in _PURCHASES else 'printed'}
            for name, (master, group) in layout.items()}


def build_winding_tool_assemblies(
        tool_parameters: WindingToolParameters = DEFAULT_WINDING_TOOL_PARAMETERS,
        design_parameters: DesignParameters = DEFAULT_PARAMETERS,
        diameter_mm: float = 150.0,
) -> WindingToolAssemblies:
    """Install all members, evaluate every labeled setting, and fail closed."""
    for designation, dimensions in (
        ('608', design_parameters.bearings.radial_nominal_dimensions_mm),
        ('51105', design_parameters.bearings.thrust_nominal_dimensions_mm),
    ):
        if dimensions != _BEARING_DIMENSIONS[designation]:
            raise ValueError(f'{designation} requires canonical dimensions {_BEARING_DIMENSIONS[designation]} mm')
    head = build_winding_head(tool_parameters, diameter_mm)
    frame = build_winding_frame(tool_parameters, design_parameters)
    payoff = build_wire_payoff(tool_parameters, design_parameters)
    height = frame.metadata['axis_height_mm']
    jig = {name: getattr(frame, name) for name in ('base', 'tower', 'shaft', 'crank', 'grip')}
    for prefix, members in (('bearing_retainer', frame.bearing_retainers),
                            ('bearing_608', frame.bearings),
                            ('snap_collar', frame.snap_collars)):
        jig.update({f'{prefix}_{index}': body for index, body in enumerate(members, 1)})
    jig['wheel'] = installed_shape(head.wheel, height)
    jig.update({f'shoe_{index}': installed_shape(body, height)
                for index, body in enumerate(head.shoes, 1)})
    supply = {name: getattr(payoff, name) for name in _PAYOFF_LAYOUT}
    ownership = {'winding_jig': _owners(_JIG_LAYOUT), 'wire_payoff': _owners(_PAYOFF_LAYOUT)}
    for name, owner in ownership['winding_jig'].items():
        if owner['source'] == 'printed':
            component = name.rsplit('_', 1)[0] if name[-1:].isdigit() else name
            owner['print_rotations_deg'] = ((90, 0, 0) if component == 'shoe' else
                (0, 0, 0) if component == 'wheel' else frame.metadata['print_rotations_deg'][component])
    ownership['winding_jig']['wheel'].update({
        'diameter_mm': head.state.diameter_mm, 'axis_height_mm': height,
        'actual_tape_angles_deg': head.metadata['actual_tape_angles_deg'],
        'nominal_tape_angles_deg': head.metadata['nominal_tape_angles_deg'],
    })
    for name in ('bearing_608_1', 'bearing_608_2'):
        ownership['winding_jig'][name]['nominal_dimensions_mm'] = frame.metadata['bearing_nominal_dimensions_mm']
    for name in ('base', 'spindle', 'platter'):
        ownership['wire_payoff'][name]['print_rotations_deg'] = (0, 90, 0) if name == 'spindle' else (0, 0, 0)
    for name in ('lower_washer', 'bearing', 'upper_washer'):
        ownership['wire_payoff'][name]['purchase_set'] = '51105_1'
        ownership['wire_payoff'][name]['nominal_dimensions_mm'] = tuple(payoff.metadata['bearing_nominal_dimensions_mm'])
    ownership['wire_payoff']['spindle']['journal_diameter_mm'] = design_parameters.bearings.thrust_rotating_pilot_diameter_mm
    model = WindingToolAssemblies(jig, supply, ownership, tool_parameters, {})
    checks = audit_winding_tool_assemblies(model)
    if not all(checks.values()):
        raise ValueError('Winding-tool assembly invariants failed: '
                         + ', '.join(name for name, passed in checks.items() if not passed))
    return replace(model, audit=checks)


def _ownership_checks(model):
    required = set(model.winding_jig) == set(_JIG_LAYOUT) and set(model.wire_payoff) == set(_PAYOFF_LAYOUT)
    correct = set(model.ownership) == {'winding_jig', 'wire_payoff'}
    for tool, layout in (('winding_jig', _JIG_LAYOUT), ('wire_payoff', _PAYOFF_LAYOUT)):
        owners = model.ownership.get(tool, {})
        correct &= set(owners) == set(getattr(model, tool))
        for name, expected in _owners(layout).items():
            correct &= all(owners.get(name, {}).get(key) == value for key, value in expected.items())
    owners = model.ownership.get('wire_payoff', {})
    thrust = all(owners.get(name, {}).get('group') == group for name, group in (
        ('lower_washer', 'stationary'), ('bearing', 'bearing_internal'), ('upper_washer', 'rotating')))
    thrust &= {owners.get(name, {}).get('purchase_set') for name in
               ('lower_washer', 'bearing', 'upper_washer')} == {'51105_1'}
    return {'required_members': bool(required), 'ownership': bool(correct),
            'bearing_51105_ownership': bool(thrust)}


@lru_cache(maxsize=1)
def _bearing_references():
    return {'608': build_608_reference(DEFAULT_PARAMETERS),
            '51105': build_51105_reference(DEFAULT_PARAMETERS)}


def _validated_bearing_inventory(model):
    """Validate every size record and the real catalog-shaped purchased stack."""
    references = _bearing_references()
    dimensions = {}
    for designation, tool, names in (
        ('608', 'winding_jig', ('bearing_608_1', 'bearing_608_2')),
        ('51105', 'wire_payoff', ('lower_washer', 'bearing', 'upper_washer')),
    ):
        for name in names:
            record = model.ownership[tool][name].get('nominal_dimensions_mm', ())
            if not isinstance(record, (tuple, list)) or tuple(record) != _BEARING_DIMENSIONS[designation]:
                raise ValueError(f'{designation} occurrence {name} has noncanonical bearing dimensions')
            dimensions[designation] = tuple(record)
    _, height = head_datum(model)
    actual_and_gauge = []
    for name in ('bearing_608_1', 'bearing_608_2'):
        actual = local_shape(model.winding_jig[name], height)
        center = actual.val().Center()
        actual = translated(actual, (-center.x, -center.y, -bounds(actual).zmin))
        actual_and_gauge.append(('608', actual, references['608'].parts['sealed_envelope']))
    lower = model.wire_payoff['lower_washer']
    center = lower.val().Center()
    offset = (-center.x, -center.y, -bounds(lower).zmin)
    for name, reference_name in (('lower_washer', 'housing_washer'),
                                 ('bearing', 'rolling_envelope'), ('upper_washer', 'shaft_washer')):
        actual_and_gauge.append(('51105', translated(model.wire_payoff[name], offset),
                                 references['51105'].parts[reference_name]))
    for designation, actual, gauge in actual_and_gauge:
        if (actual.cut(gauge).val().Volume() > VOLUME_TOLERANCE
                or gauge.cut(actual).val().Volume() > VOLUME_TOLERANCE):
            raise ValueError(f'{designation} actual bearing geometry does not match its canonical stack')
    return dimensions


@lru_cache(maxsize=32)
def _tongue_seats(wheel, parameters):
    metadata = head_reference(parameters, parameters.minimum_diameter_mm).metadata
    rows = metadata['tongue_rows_y_mm']
    strip = box(parameters.minimum_diameter_mm / 2 - metadata['tongue_setback_mm'] - 2,
                min(rows) - 3, -1,
                (parameters.maximum_diameter_mm - parameters.minimum_diameter_mm) / 2 + 8,
                max(rows) - min(rows) + 6, metadata['wheel_thickness_mm'] + 2)
    regions = [strip.rotate((0, 0, 0), (0, 0, 1), index * 60).val() for index in range(6)]
    clipped = wheel.intersect(cq.Workplane('XY').newObject([cq.Compound.makeCompound(regions)]))
    sectors = [[] for _ in range(6)]
    for solid in clipped.val().Solids():
        center = solid.Center()
        index = round(degrees(atan2(center.y, center.x)) / 60) % 6
        sectors[index].append(solid)
    if any(not shapes for shapes in sectors):
        raise ValueError('Wheel has no tongue-seat material in one or more spoke sectors')
    return tuple(cq.Workplane('XY').newObject([cq.Compound.makeCompound(shapes)]) for shapes in sectors)


@lru_cache(maxsize=128)
def _head_checks(member_items, parameters, diameter):
    local = dict(member_items)
    reference = head_reference(parameters, diameter)
    wheel = local['wheel']
    seats = _tongue_seats(wheel, parameters)
    metadata = reference.metadata
    radius = diameter / 2
    shoes = [local[f'shoe_{i}'] for i in range(1, 7)]
    equal = envelope = friction_fit = True
    contact_radius = parameters.minimum_diameter_mm / 2
    arc_center = (radius - contact_radius, 0, 0)
    runout_end = metadata['nominal_runout_end_z_mm']
    # Check the translated master arc, not a full nominal-diameter circle:
    # off-center contact lands lie inside that circle at larger settings.
    runout_excess = translated(ring(contact_radius + 40, contact_radius + .001,
                                   5, runout_end - 5), arc_center)
    shoulder_excess = translated(ring(contact_radius + 40,
        contact_radius + metadata['free_shoulder_height_mm'] + .001,
        runout_end, 40 - runout_end), arc_center)
    contact_band = translated(ring(contact_radius + .001, contact_radius - .05,
                                  runout_end - .2, .2), arc_center)
    # Evaluate both mass centers in the same frame: OCCT's default integration
    # of curved faces differs slightly if the master is measured before moving.
    expected_center = reference.shoes[0].val().Center()
    for index, shoe in enumerate(shoes):
        seat = seats[index]
        normalized = shoe.rotate((0, 0, 0), (0, 0, 1), -index * 60)
        equal &= normalized.val().Center().sub(expected_center).Length < 1e-5
        envelope &= (clear(normalized, runout_excess) and clear(normalized, shoulder_excess)
                     and intersection_volume(normalized, contact_band) > .001)
        for row in metadata['tongue_rows_y_mm']:
            x = radius - metadata['tongue_setback_mm']
            tongue_radial, tongue_tangential = metadata['tongue_size_mm']
            core = box(x - tongue_radial / 2 + .1,
                       row - tongue_tangential / 2 + .1,
                       -.5,
                       tongue_radial - .2,
                       tongue_tangential - .2,
                       metadata['wheel_thickness_mm'] + .3)
            core = core.rotate((0, 0, 0), (0, 0, 1), index * 60)
            friction_fit &= (intersection_volume(shoe, core) > .99 * core.val().Volume()
                             and clear(seat, core))
        angle = radians(index * 60)
        radial = (.011 * cos(angle), .011 * sin(angle), 0)
        tangential = (-.011 * sin(angle), .011 * cos(angle), 0)
        friction_fit &= (clear(seat, shoe)
                         and intersection_volume(seat, translated(shoe, radial)) > .001
                         and intersection_volume(seat, translated(shoe, tangential)) > .001
                         and intersection_volume(seat, translated(shoe, (0, 0, -.011))) > .001)
    corridors = metadata['tape_passage_probes']
    all_corridors = cq.Workplane('XY').newObject([
        cq.Compound.makeCompound([shape.val() for shape in corridors])])
    tape = (len(corridors) == 18 and all(bounds(probe).zlen >= 12 - 1e-6 for probe in corridors)
            and all(clear(a, b) for a, b in combinations(corridors, 2))
            and all(clear(all_corridors, shape) for shape in local.values()))
    measured = tuple(degrees(atan2(probe.val().Center().y, probe.val().Center().x)) % 360
                     for probe in corridors)
    ordered = (*measured[1:], measured[0], 360)
    tape &= all(a < b for a, b in zip(ordered, ordered[1:]))
    pair_clear = all(clear(a, b) for a, b in combinations(shoes, 2))
    # A conservative continuous revolution contains every wheel/shoe occurrence.
    head_members = [wheel, *shoes]
    max_radius = (max(parameters.maximum_diameter_mm, diameter) / 2
                  + metadata['free_shoulder_height_mm'] + .01)
    bottom, top = min(bounds(s).zmin for s in head_members), max(bounds(s).zmax for s in head_members)
    sweep = ring(max_radius, 0, bottom, top - bottom)
    contained = all(shape.cut(sweep).val().Volume() < VOLUME_TOLERANCE for shape in head_members)
    head_clear = all(clear(sweep, local[name]) for name in ('base', 'tower', 'bearing_retainer_1',
                                                          'bearing_retainer_2', 'bearing_608_1', 'bearing_608_2'))
    return {'equal_shoe_positions': bool(equal), 'wire_contact_envelope': bool(envelope),
            'two_tongue_friction_fit': bool(friction_fit), 'tape_corridors': bool(tape),
            'head_rotation_clearance': bool(contained and head_clear and pair_clear)}, measured


@lru_cache(maxsize=128)
def _rotation_envelope(shape, split_axially=False):
    """Conservative full revolution, proven to contain the supplied solid.

    Shaft/spindle sections preserve their narrow bearing journals instead of
    extending the enlarged drive or snap radius across a bearing interface.
    Every axial interval is covered continuously; no angular samples are used.
    """
    bb = bounds(shape)
    levels = [bb.zmin]
    if split_axially:
        for z in sorted(vertex.Center().z for vertex in shape.val().Vertices()):
            if z - levels[-1] > 1e-6 and bb.zmax - z > 1e-6:
                levels.append(z)
    levels.append(bb.zmax)
    reach = hypot(max(abs(bb.xmin), abs(bb.xmax)), max(abs(bb.ymin), abs(bb.ymax)))
    cylinders = []
    section_tolerance = VOLUME_TOLERANCE / (len(levels) - 1)
    for bottom, top in zip(levels, levels[1:]):
        section = (shape.intersect(box(-reach, -reach, bottom, 2 * reach, 2 * reach, top - bottom))
                   if split_axially else shape)
        if section.val().Volume() <= VOLUME_TOLERANCE:
            continue
        sb = bounds(section)
        x, y = max(abs(sb.xmin), abs(sb.xmax)), max(abs(sb.ymin), abs(sb.ymax))
        radius = max(x, y, *(hypot(vertex.Center().x, vertex.Center().y)
                              for vertex in section.val().Vertices()))
        envelope = ring(radius, 0, bottom, top - bottom)
        maximum_radius = hypot(x, y)
        while section.cut(envelope).val().Volume() > section_tolerance:
            if radius >= maximum_radius:
                raise ValueError('Rotation envelope does not contain an axial section')
            radius = min(maximum_radius, radius * 1.05)
            envelope = ring(radius, 0, bottom, top - bottom)
        cylinders.append(envelope)
    # Fuse adjacent intervals: a compound of touching cylinders is not a valid
    # Boolean cutter at shared axial faces in OCCT.
    sweep = cylinders[0]
    for cylinder in cylinders[1:]:
        sweep = sweep.union(cylinder)
    if shape.cut(sweep).val().Volume() > VOLUME_TOLERANCE:
        raise ValueError('Rotation envelope does not contain the complete occurrence')
    return sweep


def _all_rotating_clearance(parts, layout):
    stationary = [parts[name] for name, (_, group) in layout.items() if group != 'rotating']
    for name, (_, group) in layout.items():
        if group != 'rotating':
            continue
        sweep = _rotation_envelope(parts[name], name in ('shaft', 'spindle'))
        if not all(clear(sweep, fixed) for fixed in stationary):
            return False
    return True


@lru_cache(maxsize=128)
def _frame_checks(member_items, height, bearing_dimensions):
    parts = dict(member_items)
    shaft, tower = parts['shaft'], parts['tower']
    clips = [parts[f'bearing_retainer_{i}'] for i in (1, 2)]
    collars = [parts[f'snap_collar_{i}'] for i in (1, 2)]
    bore, outer, thickness = bearing_dimensions
    bearings = [parts[f'bearing_608_{i}'] for i in (1, 2)]
    engaged = floating = seal_clear = True
    for index, (bearing, outward) in enumerate(zip(bearings, (-1, 1))):
        bb = bounds(bearing)
        core = ring(bore / 2, 0, bb.zmin, thickness)
        engaged &= (abs(bb.xlen - outer) < 1e-5 and abs(bb.ylen - outer) < 1e-5
                    and abs(bb.zlen - thickness) < 1e-5
                    and clear(shaft, bearing) and clear(tower, bearing)
                    and intersection_volume(shaft, core) > .99999 * core.val().Volume())
        for vector in ((.3, 0, 0), (-.3, 0, 0), (0, .3, 0), (0, -.3, 0)):
            engaged &= intersection_volume(translated(bearing, vector), tower) > .01
        for vector in ((.05, 0, 0), (-.05, 0, 0), (0, .05, 0), (0, -.05, 0)):
            engaged &= intersection_volume(translated(shaft, vector), bearing) > .01
        engaged &= intersection_volume(translated(bearing, (0, 0, -outward)), tower) > .01
        engaged &= sum(intersection_volume(translated(bearing, (0, 0, outward)), clip)
                       for clip in clips) > .01
        for dz in (-.4, .4):
            engaged &= intersection_volume(translated(clips[index], (0, 0, dz)), tower) > .01
        seal = ring(9.6, 5.25, bb.zmin - .6, thickness + 1.2)
        seal_clear &= all(clear(seal, shape) for shape in (tower, *clips, *collars))
        for dz in (-.5, .5):
            if index == 0:
                floating &= all(clear(translated(bearing, (0, 0, dz)), body) for body in (tower, *clips))
    located = True
    for collar, direction in zip(collars, (1, -1)):
        located &= (clear(shaft, collar) and clear(collar, bearings[1])
                    and intersection_volume(translated(shaft, (0, 0, direction * .4)), collar) > .01
                    and intersection_volume(translated(collar, (0, 0, direction * .4)), bearings[1]) > .01)
    drives = True
    for name in ('wheel', 'crank'):
        driven = parts[name]
        drives &= (clear(shaft, driven)
                   and intersection_volume(shaft, driven.rotate((0, 0, 0), (0, 0, 1), 30)) > .1)
        for dz in (-.6, .6):
            drives &= intersection_volume(shaft, translated(driven, (0, 0, dz))) > .01
    crank, grip = parts['crank'], parts['grip']
    radius = max(hypot(max(abs(bounds(s).xmin), abs(bounds(s).xmax)),
                       max(abs(bounds(s).ymin), abs(bounds(s).ymax))) for s in (crank, grip))
    bottom, top = min(bounds(s).zmin for s in (crank, grip)), max(bounds(s).zmax for s in (crank, grip))
    sweep = ring(radius, 0, bottom, top - bottom)
    crank_clear = (height > radius and all(clear(sweep, parts[name])
                   for name in ('base', 'tower', 'wheel', 'bearing_retainer_1', 'bearing_retainer_2')))
    crank_clear &= all(shape.cut(sweep).val().Volume() < VOLUME_TOLERANCE for shape in (crank, grip))
    grip_center = bounds(grip).center
    free_grip = all(clear(crank, grip.rotate((grip_center.x, grip_center.y, 0),
                    (grip_center.x, grip_center.y, 1), angle)) for angle in (0, 30, 90, 180))
    for dz in (-1.5, 1.5):
        free_grip &= intersection_volume(crank, translated(grip, (0, 0, dz))) > .01
    mount = (clear(parts['base'], tower) and abs(bounds(parts['base']).ymin + height) < 1e-6)
    for vector in ((.5, 0, 0), (-.5, 0, 0), (0, 0, .5), (0, 0, -.5), (0, .5, 0)):
        mount &= intersection_volume(parts['base'], translated(tower, vector)) > .01
    nominal_clear = all(clear(a, b) for a, b in combinations(parts.values(), 2))
    return {'bearing_608_engagement': bool(engaged),
            'locating_floating_load_path': bool(engaged and floating and seal_clear and located),
            'shaft_axial_restraint': bool(located), 'positive_polygon_drives': bool(drives),
            'crank_full_rotation': bool(crank_clear and free_grip),
            'jig_full_rotation_clearance': _all_rotating_clearance(parts, _JIG_LAYOUT),
            'stand_snap_joint': bool(mount), 'member_collision_clearance': bool(nominal_clear)}


@lru_cache(maxsize=128)
def _payoff_checks(member_items, journal_diameter):
    parts = dict(member_items)
    washer = parts['lower_washer']
    area = washer.val().Volume() / bounds(washer).zlen
    load_path = True
    for below, above in (('base', 'lower_washer'), ('lower_washer', 'bearing'),
                         ('bearing', 'upper_washer'), ('upper_washer', 'platter')):
        supporting, supported = parts[below], parts[above]
        load_path &= (clear(supporting, supported)
                      and supporting.val().distance(supported.val()) < 1e-6
                      and intersection_volume(supporting, translated(supported, (0, 0, -.05))) > .75 * area * .05)
    for vector in ((.25, 0, 0), (-.25, 0, 0), (0, .25, 0), (0, -.25, 0)):
        load_path &= intersection_volume(parts['base'], translated(washer, vector)) > .01
        load_path &= intersection_volume(parts['spindle'], translated(parts['upper_washer'], vector)) > .01
    sb, pb = bounds(parts['spindle']), bounds(parts['platter'])
    spindle_sweep = ring(journal_diameter / 2, 0, sb.zmin, sb.zlen).union(
        ring(journal_diameter / 2 + .6, 0, sb.zmin + 1.3, 2))
    platter_sweep = ring(max(pb.xlen, pb.ylen) / 2, 0, pb.zmin, pb.zlen)
    rotating = all(actual.cut(sweep).val().Volume() < VOLUME_TOLERANCE
                   and clear(sweep, parts['base']) and sweep.val().distance(parts['base'].val()) > .05
                   for actual, sweep in ((parts['spindle'], spindle_sweep), (parts['platter'], platter_sweep)))
    rotating &= all(clear(a, b) for a, b in combinations(parts.values(), 2))
    floating = all(clear(translated(parts[moving], (0, 0, .15)), parts[fixed])
                   for moving, fixed in (('platter', 'spindle'), ('spindle', 'base')))
    hanging = translated(parts['spindle'], (0, 0, -.35))
    floating &= (intersection_volume(hanging, parts['platter']) > .01 and clear(hanging, parts['base']))
    # A continuous upward envelope reserves room to lift the platter and reach
    # the upper plug. An overhead guard can block service while rotation is clear.
    access_sweep = ring(max(pb.xlen, pb.ylen) / 2, 0, pb.zmin, pb.zlen + 40)
    rotating &= _all_rotating_clearance(parts, _PAYOFF_LAYOUT)
    return {'bearing_51105_load_path': bool(load_path), 'payoff_free_rotation': bool(rotating and floating),
            'payoff_top_access': bool(clear(access_sweep, parts['base']))}


def _print_bed_check(model, height):
    limit = min(model.parameters.print_bed_mm, 220)
    for tool in ('winding_jig', 'wire_payoff'):
        for name, owner in model.ownership[tool].items():
            if owner['source'] != 'printed':
                continue
            shape = getattr(model, tool)[name]
            if tool == 'winding_jig':
                shape = local_shape(shape, height)
            for axis, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), owner['print_rotations_deg']):
                shape = shape.rotate((0, 0, 0), axis, angle)
            if max(bounds(shape).xlen, bounds(shape).ylen) > limit + 1e-6:
                return False
    return True


def _at_setting(model, diameter):
    current, height = head_datum(model)
    if diameter == current:
        return model
    delta = (diameter - current) / 2
    jig = dict(model.winding_jig)
    for index in range(6):
        angle = radians(index * 60)
        name = f'shoe_{index + 1}'
        jig[name] = translated(jig[name], (delta * cos(angle), 0, delta * sin(angle)))
    owners = {tool: dict(records) for tool, records in model.ownership.items()}
    owners['winding_jig']['wheel'] = {**owners['winding_jig']['wheel'],
        'diameter_mm': diameter,
        'actual_tape_angles_deg': head_reference(model.parameters, diameter).metadata['actual_tape_angles_deg']}
    return replace(model, winding_jig=jig, ownership=owners, audit={})


@lru_cache(maxsize=32)
def _service_checks(member_items, parameters, diameter, height):
    # The temporary model retains the actual supplied occurrence solids.
    owners = {'winding_jig': _owners(_JIG_LAYOUT)}
    owners['winding_jig']['wheel'].update({'diameter_mm': diameter, 'axis_height_mm': height})
    model = WindingToolAssemblies(dict(member_items), {}, owners, parameters, {})
    return audit_winding_tool_service(model)


def audit_winding_tool_assemblies(model: WindingToolAssemblies) -> dict[str, bool]:
    """Flat fail-closed gates; no cached model.audit flag is accepted as evidence.

    Each setting repositions the actual six shoes and physically probes them.
    Mutations therefore remain present in all settings and service checks.
    """
    checks = {name: False for name in ('required_members', 'ownership', 'valid_solids', 'bearing_catalog_dimensions',
        'independent_tools', 'equal_shoe_positions', 'wire_contact_envelope', 'two_tongue_friction_fit',
        'tape_corridors', 'actual_tape_angles', 'head_rotation_clearance', 'bearing_608_engagement',
        'locating_floating_load_path', 'shaft_axial_restraint', 'positive_polygon_drives',
        'crank_full_rotation', 'jig_full_rotation_clearance', 'stand_snap_joint', 'member_collision_clearance',
        'bearing_51105_ownership', 'bearing_51105_load_path', 'payoff_free_rotation', 'payoff_top_access',
        'snap_access', 'complete_coil_removal', 'print_bed')}
    try:
        settings = diameter_settings_mm(model.parameters)
        checks.update({f'setting_{d:g}_geometry': False for d in settings})
        release_settings = (settings[0], settings[len(settings) // 2], settings[-1])
        checks.update({f'removal_{d:g}': False for d in release_settings})
        checks.update(_ownership_checks(model))
        if not checks['required_members'] or not checks['ownership']:
            return checks
        shapes = (*model.winding_jig.values(), *model.wire_payoff.values())
        checks['valid_solids'] = all(s.val().isValid() and len(s.val().Solids()) == 1
            and isfinite(s.val().Volume()) and s.val().Volume() > 0 for s in shapes)
        if not checks['valid_solids']:
            return checks
        _validated_bearing_inventory(model)
        checks['bearing_catalog_dimensions'] = True
        diameter, height = head_datum(model)
        local = {name: local_shape(shape, height) for name, shape in model.winding_jig.items()}
        current, measured = _head_checks(tuple(local.items()), model.parameters, diameter)
        checks.update(current)
        actual = model.ownership['winding_jig']['wheel']['actual_tape_angles_deg']
        checks['actual_tape_angles'] = len(actual) == 18 and all(abs(a - b) < 1e-6 for a, b in zip(actual, measured))
        checks['print_bed'] = _print_bed_check(model, height)
        checks['snap_access'] = audit_snap_access(model)
        if not all(current.values()) or not all(checks[name] for name in
            ('actual_tape_angles', 'print_bed', 'snap_access')):
            return checks
        dimensions = tuple(model.ownership['winding_jig']['bearing_608_1']['nominal_dimensions_mm'])
        checks.update(_frame_checks(tuple(local.items()), height, dimensions))
        checks.update(_payoff_checks(tuple(model.wire_payoff.items()),
                                    model.ownership['wire_payoff']['spindle']['journal_diameter_mm']))
        checks['snap_access'] &= checks['payoff_top_access']
        checks['independent_tools'] = not any(a.val().isSame(b.val())
            for a in model.winding_jig.values() for b in model.wire_payoff.values())
        if not all(checks[name] for name in ('bearing_608_engagement', 'locating_floating_load_path',
            'shaft_axial_restraint', 'positive_polygon_drives', 'crank_full_rotation', 'jig_full_rotation_clearance',
            'stand_snap_joint', 'member_collision_clearance', 'bearing_51105_load_path',
            'payoff_free_rotation', 'payoff_top_access')):
            return checks
        for setting in settings:
            candidate = _at_setting(model, setting)
            placed = tuple((name, local_shape(shape, height)) for name, shape in candidate.winding_jig.items())
            head_checks, _ = _head_checks(placed, model.parameters, setting)
            checks[f'setting_{setting:g}_geometry'] = all(head_checks.values())
            if setting in release_settings or setting == diameter:
                service = _service_checks(tuple(candidate.winding_jig.items()), model.parameters, setting, height)
                if setting in release_settings:
                    checks[f'removal_{setting:g}'] = all(service['checks'].values())
                if setting == diameter:
                    checks['snap_access'] = service['checks']['snap_access']
                    checks['complete_coil_removal'] = service['checks']['complete_coil_removal']
    except (ValueError, KeyError, TypeError, RuntimeError):
        # A malformed or incomplete assembly cannot publish a success audit.
        return checks
    return {name: bool(value) for name, value in checks.items()}


def winding_tool_bom(model: WindingToolAssemblies) -> tuple[dict, ...]:
    """Derive printed quantities and purchased sets from occurrence ownership."""
    ownership = _ownership_checks(model)
    if not all(ownership.values()):
        raise ValueError('Cannot derive a BOM from incomplete or incorrect occurrence ownership')
    dimensions = _validated_bearing_inventory(model)
    specifications = {name: ' x '.join(f'{value:g}' for value in values) + ' mm'
                      for name, values in dimensions.items()}
    counts = Counter()
    for tool, records in model.ownership.items():
        counts.update(f'{tool}/{owner["master"]}' for owner in records.values() if owner['source'] == 'printed')
    rows = [{'name': master.replace('/', ' ').replace('_', ' '), 'master': master,
             'source': 'printed', 'quantity': quantity, 'material': 'PLA',
             'physical_fit_verified': False}
            for master, quantity in sorted(counts.items())]
    bearings = [owner for records in model.ownership.values() for owner in records.values()
                if owner['source'] == 'purchased']
    rows.append({'name': '608 bearing', 'source': 'purchased',
                 'quantity': sum(owner['master'] == '608 bearing' for owner in bearings),
                 'specification': specifications['608'], 'physical_fit_verified': False})
    rows.append({'name': '51105 thrust bearing', 'source': 'purchased',
                 'quantity': len({owner['purchase_set'] for owner in bearings if owner['master'] == '51105 thrust bearing'}),
                 'specification': specifications['51105'] + '; complete set with separate lower and upper washers',
                 'physical_fit_verified': False})
    return tuple(rows)
