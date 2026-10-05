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

from windwall.bearings import build_51105_reference
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
    'base': ('base', 'stationary'), 'hub': ('horizontal_hub', 'rotating'),
    'wheel': ('coil_wheel', 'rotating'), 'crank': ('hand_crank', 'rotating'),
    'grip': ('rotating_grip', 'rotating'),
    **{f'shoe_{i}': ('contact_shoe', 'rotating') for i in range(1, 7)},
    'lower_washer': ('51105 thrust bearing', 'stationary'),
    'bearing': ('51105 thrust bearing', 'bearing_internal'),
    'upper_washer': ('51105 thrust bearing', 'rotating'),
}
_PAYOFF_LAYOUT = {
    'base': ('base', 'stationary'), 'spindle': ('printed_spindle', 'rotating'),
    'platter': ('platter', 'rotating'),
    'lower_washer': ('51105 thrust bearing', 'stationary'),
    'bearing': ('51105 thrust bearing', 'bearing_internal'),
    'upper_washer': ('51105 thrust bearing', 'rotating'),
}
_PURCHASES = frozenset(('51105 thrust bearing',))
_BEARING_DIMENSIONS = {'51105': DEFAULT_PARAMETERS.bearings.thrust_nominal_dimensions_mm}


def _owners(layout):
    return {name: {'master': master, 'group': group,
                   'source': 'purchased' if master in _PURCHASES else 'printed'}
            for name, (master, group) in layout.items()}


def build_winding_tool_assemblies(
        tool_parameters: WindingToolParameters = DEFAULT_WINDING_TOOL_PARAMETERS,
        design_parameters: DesignParameters = DEFAULT_PARAMETERS,
        diameter_mm: float = 150.0,
) -> WindingToolAssemblies:
    """Install the horizontal wheel and independent payoff, then fail closed."""
    if design_parameters.bearings.thrust_nominal_dimensions_mm != _BEARING_DIMENSIONS['51105']:
        raise ValueError('51105 requires canonical 25 x 42 x 11 mm dimensions')
    head = build_winding_head(tool_parameters, diameter_mm)
    frame = build_winding_frame(tool_parameters, design_parameters)
    payoff = build_wire_payoff(tool_parameters, design_parameters)
    height = frame.metadata['wheel_bottom_z_mm']
    jig = {name: getattr(frame, name) for name in (
        'base', 'hub', 'crank', 'grip', 'lower_washer', 'bearing', 'upper_washer')}
    jig['wheel'] = installed_shape(head.wheel, height)
    jig.update({f'shoe_{index}': installed_shape(body, height)
                for index, body in enumerate(head.shoes, 1)})
    supply = {name: getattr(payoff, name) for name in _PAYOFF_LAYOUT}
    ownership = {'winding_jig': _owners(_JIG_LAYOUT), 'wire_payoff': _owners(_PAYOFF_LAYOUT)}
    for tool, owners in ownership.items():
        for name, owner in owners.items():
            if owner['source'] == 'printed':
                owner['canonical_master'] = 'wire_payoff/base' if name == 'base' else f'{tool}/{owner["master"]}'
            else:
                owner.update(purchase_set=f'{tool}_51105',
                             nominal_dimensions_mm=_BEARING_DIMENSIONS['51105'])
    for name, owner in ownership['winding_jig'].items():
        if owner['source'] == 'printed':
            component = 'shoe' if name.startswith('shoe_') else name
            owner['print_rotations_deg'] = ((0, -90, 0) if component == 'shoe' else
                (0, 0, 0) if component == 'wheel' else frame.metadata['print_rotations_deg'][component])
    ownership['winding_jig']['wheel'].update(
        diameter_mm=head.state.diameter_mm, axis_height_mm=height,
        actual_tape_angles_deg=head.metadata['actual_tape_angles_deg'],
        nominal_tape_angles_deg=head.metadata['nominal_tape_angles_deg'])
    for name in ('base', 'spindle', 'platter'):
        ownership['wire_payoff'][name]['print_rotations_deg'] = (0, 90, 0) if name == 'spindle' else (0, 0, 0)
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
    thrust = True
    sets = []
    for tool, layout in (('winding_jig', _JIG_LAYOUT), ('wire_payoff', _PAYOFF_LAYOUT)):
        owners = model.ownership.get(tool, {})
        correct &= set(owners) == set(getattr(model, tool))
        for name, expected in _owners(layout).items():
            actual = owners.get(name, {})
            correct &= all(actual.get(key) == value for key, value in expected.items())
            if expected['source'] == 'printed':
                identity = 'wire_payoff/base' if name == 'base' else f'{tool}/{expected["master"]}'
                correct &= actual.get('canonical_master') == identity
        purchase_sets = {owners.get(name, {}).get('purchase_set')
                         for name in ('lower_washer', 'bearing', 'upper_washer')}
        thrust &= len(purchase_sets) == 1 and None not in purchase_sets
        sets.extend(purchase_sets)
    thrust &= len(set(sets)) == 2
    return {'required_members': bool(required), 'ownership': bool(correct),
            'bearing_51105_ownership': bool(thrust)}


@lru_cache(maxsize=1)
def _bearing_references():
    return {'51105': build_51105_reference(DEFAULT_PARAMETERS)}


def _validated_bearing_inventory(model):
    """Require both purchased stacks at their canonical installed poses."""
    reference = _bearing_references()['51105']
    for tool in ('winding_jig', 'wire_payoff'):
        for name, reference_name in (('lower_washer', 'housing_washer'),
                                     ('bearing', 'rolling_envelope'), ('upper_washer', 'shaft_washer')):
            record = model.ownership[tool][name].get('nominal_dimensions_mm', ())
            if not isinstance(record, (tuple, list)) or tuple(record) != _BEARING_DIMENSIONS['51105']:
                raise ValueError(f'51105 occurrence {tool}/{name} has noncanonical dimensions')
            actual = getattr(model, tool)[name]
            gauge = translated(reference.parts[reference_name], (0, 0, 8))
            if (actual.cut(gauge).val().Volume() > VOLUME_TOLERANCE
                    or gauge.cut(actual).val().Volume() > VOLUME_TOLERANCE):
                raise ValueError(f'51105 actual member {tool}/{name} differs from its canonical pose')
    return {'51105': _BEARING_DIMENSIONS['51105']}


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
                                   metadata['nominal_runout_start_z_mm'],
                                   runout_end - metadata['nominal_runout_start_z_mm']), arc_center)
    shoulder_excess = translated(ring(contact_radius + 40,
        contact_radius + metadata['free_shoulder_height_mm'] + .001,
        runout_end, 40 - runout_end), arc_center)
    contact_band = translated(ring(contact_radius + .001, contact_radius - .05,
                                  16.3, .2), arc_center)
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
        clearance = metadata['nominal_friction_clearance_per_side_mm']
        free_offset = clearance - .001
        contact_offset = clearance + .001
        radial_free = (free_offset * cos(angle), free_offset * sin(angle), 0)
        radial_contact = (contact_offset * cos(angle), contact_offset * sin(angle), 0)
        tangential_free = (-free_offset * sin(angle), free_offset * cos(angle), 0)
        tangential_contact = (-contact_offset * sin(angle), contact_offset * cos(angle), 0)
        friction_fit &= (clear(seat, shoe)
                         and clear(seat, translated(shoe, radial_free))
                         and clear(seat, translated(shoe, tangential_free))
                         and intersection_volume(seat, translated(shoe, radial_contact)) > .001
                         and intersection_volume(seat, translated(shoe, tangential_contact)) > .001
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
                  + max(metadata['rear_shoulder_height_mm'], metadata['free_shoulder_height_mm']) + 5)
    bottom, top = min(bounds(s).zmin for s in head_members), max(bounds(s).zmax for s in head_members)
    sweep = ring(max_radius, 0, bottom, top - bottom)
    contained = all(shape.cut(sweep).val().Volume() < VOLUME_TOLERANCE for shape in head_members)
    head_clear = all(clear(sweep, local[name]) for name in ('base', 'lower_washer', 'bearing'))
    return {'equal_shoe_positions': bool(equal), 'wire_contact_envelope': bool(envelope),
            'two_tongue_friction_fit': bool(friction_fit), 'tape_corridors': bool(tape),
            'head_rotation_clearance': bool(contained and head_clear and pair_clear)}, measured


@lru_cache(maxsize=128)
def _rotation_envelope(shape, split_axially=False):
    """Conservative full revolution, proven to contain the supplied solid.

    Hub/spindle sections preserve their narrow bearing journals instead of
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
        sweep = _rotation_envelope(parts[name], name in ('hub', 'crank', 'spindle'))
        if not all(clear(sweep, fixed) for fixed in stationary):
            return False
    return True


@lru_cache(maxsize=128)
def _frame_checks(member_items, height, bearing_dimensions):
    local = dict(member_items)
    parts = {name: installed_shape(shape, height) for name, shape in local.items()}
    hub, base, upper, wheel = (parts[name] for name in ('hub', 'base', 'upper_washer', 'wheel'))
    canonical = build_wire_payoff(DEFAULT_WINDING_TOOL_PARAMETERS, DEFAULT_PARAMETERS).base
    shared_base = (base.cut(canonical).val().Volume() < VOLUME_TOLERANCE
                   and canonical.cut(base).val().Volume() < VOLUME_TOLERANCE)
    load = True
    for below, above in (('base', 'lower_washer'), ('lower_washer', 'bearing'),
                         ('bearing', 'upper_washer'), ('upper_washer', 'hub'), ('hub', 'wheel')):
        supporting, supported = parts[below], parts[above]
        load &= (clear(supporting, supported) and supporting.val().distance(supported.val()) < 1e-6
                 and intersection_volume(supporting, translated(supported, (0, 0, -.01))) > .01)
    core = ring(12, 0, 1.5, bounds(upper).zmax - 1.5)
    guide = (abs(bounds(hub).zmin - 1.5) < 1e-6 and clear(hub, base)
             and intersection_volume(hub, core) > .99999 * core.val().Volume())
    guide &= all(clear(hub, parts[name]) for name in ('lower_washer', 'bearing', 'upper_washer'))
    guide &= intersection_volume(translated(hub, (.3, 0, 0)), parts['lower_washer']) > .01
    drive = (clear(hub, wheel) and clear(hub, parts['crank'])
             and intersection_volume(hub, wheel.rotate((0, 0, 0), (0, 0, 1), 30)) > .1
             and intersection_volume(hub, parts['crank'].rotate((0, 0, 0), (0, 0, 1), 30)) > .1)
    gap = bounds(wheel).zmin - 8 >= 25 - 1e-6
    nominal = all(clear(a, b) for a, b in combinations(parts.values(), 2))
    # Separate moving subassemblies are swept against structural members only;
    # positive polygon engagements must not be interpreted as relative rotation.
    arm_clear = True
    for name in ('crank', 'grip'):
        envelope = _rotation_envelope(parts[name], split_axially=True)
        arm_clear &= all(clear(envelope, parts[fixed])
                         for fixed in ('base', 'lower_washer', 'bearing', 'wheel', *(f'shoe_{i}' for i in range(1, 7))))
    return {'shared_base_geometry': bool(shared_base), 'winder_51105_load_path': bool(load),
            'hub_radial_guidance': bool(guide), 'positive_polygon_drives': bool(drive),
            'wheel_working_gap': bool(gap), 'crank_full_rotation': bool(arm_clear),
            'jig_full_rotation_clearance': _all_rotating_clearance(parts, _JIG_LAYOUT),
            'member_collision_clearance': bool(nominal)}


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
        jig[name] = translated(jig[name], (delta * cos(angle), delta * sin(angle), 0))
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
    """Audit actual occurrences and retain mutations throughout all settings."""
    names = ('required_members', 'ownership', 'valid_solids', 'bearing_catalog_dimensions',
        'independent_tools', 'equal_shoe_positions', 'wire_contact_envelope', 'two_tongue_friction_fit',
        'tape_corridors', 'actual_tape_angles', 'head_rotation_clearance', 'shared_base_geometry',
        'winder_51105_load_path', 'hub_radial_guidance', 'positive_polygon_drives', 'wheel_working_gap',
        'crank_full_rotation', 'jig_full_rotation_clearance', 'member_collision_clearance',
        'bearing_51105_ownership', 'bearing_51105_load_path', 'payoff_free_rotation', 'payoff_top_access',
        'snap_access', 'complete_coil_removal', 'print_bed')
    checks = dict.fromkeys(names, False)
    try:
        settings = diameter_settings_mm(model.parameters)
        checks.update({f'setting_{d:g}_geometry': False for d in settings})
        release_settings = (settings[0], settings[len(settings) // 2], settings[-1])
        checks.update({f'removal_{d:g}': False for d in release_settings})
        checks.update(_ownership_checks(model))
        if not all(checks[name] for name in ('required_members', 'ownership', 'bearing_51105_ownership')):
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
        checks.update(_frame_checks(tuple(local.items()), height, _BEARING_DIMENSIONS['51105']))
        checks.update(_payoff_checks(tuple(model.wire_payoff.items()),
                                    model.ownership['wire_payoff']['spindle']['journal_diameter_mm']))
        canonical = model.wire_payoff['base']
        shared = model.winding_jig['base']
        checks['shared_base_geometry'] &= (canonical.cut(shared).val().Volume() < VOLUME_TOLERANCE
                                           and shared.cut(canonical).val().Volume() < VOLUME_TOLERANCE)
        # Identical shapes in independent assembly coordinate systems are expected.
        checks['independent_tools'] = model.winding_jig is not model.wire_payoff
        if not all(checks[name] for name in names if name not in ('snap_access', 'complete_coil_removal')):
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
    except (ValueError, KeyError, TypeError, RuntimeError, IndexError):
        return checks
    return {name: bool(value) for name, value in checks.items()}


def winding_tool_bom(model: WindingToolAssemblies) -> tuple[dict, ...]:
    """Group global printed masters and count complete purchased bearing sets."""
    if not all(_ownership_checks(model).values()):
        raise ValueError('Cannot derive a BOM from incomplete or incorrect ownership')
    dimensions = _validated_bearing_inventory(model)['51105']
    counts = Counter(owner['canonical_master'] for records in model.ownership.values()
                     for owner in records.values() if owner['source'] == 'printed')
    rows = [{'name': master.replace('/', ' ').replace('_', ' '), 'master': master,
             'source': 'printed', 'quantity': quantity, 'material': 'PLA',
             'physical_fit_verified': False} for master, quantity in sorted(counts.items())]
    purchase_sets = {owner['purchase_set'] for records in model.ownership.values()
                     for owner in records.values() if owner['source'] == 'purchased'}
    rows.append({'name': '51105 thrust bearing', 'source': 'purchased',
                 'quantity': len(purchase_sets), 'physical_fit_verified': False,
                 'specification': ' x '.join(f'{v:g}' for v in dimensions)
                 + ' mm; complete set with separate lower and upper washers'})
    return tuple(rows)
