"""Independent winding-jig/payoff assemblies, geometric audits, and service BOM.

The component builders own mechanical design. This module places their public
parts, adds nominal follower/pin references, and checks the resulting B-reps.
Tools have separate local origins and no shared base or drive. Clearance checks
are prototype CAD checks, not approval of physical fits or powered operation.
"""

from dataclasses import dataclass, replace
from functools import lru_cache
from itertools import combinations
from math import cos, hypot, isfinite, radians, sin

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Curve

from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters
from windwall.winding_frame import WindingFrameParts, build_winding_frame
from windwall.winding_head import WindingHeadParts, build_winding_head
from windwall.winding_tool_parameters import (
    DEFAULT_WINDING_TOOL_PARAMETERS, WindingToolParameters,
    validate_winding_tool_parameters,
)
from windwall.winding_tool_service import (
    audit_winding_tool_service,
    coil_removal_stages as coil_removal_stages,
)
from windwall.wire_payoff import WirePayoffParts, build_wire_payoff


_VOLUME_TOLERANCE_MM3 = 1e-5
_JIG_PRINTABLE_NAMES = frozenset({
    'base', 'left_upright', 'right_upright', 'head_hub',
    'head_retaining_collar', 'crank', 'backplate', 'cam', 'clamp',
    'left_bearing_cap', 'right_bearing_cap',
    *[f'{prefix}_{i}' for prefix in ('slider', 'rib') for i in range(1, 7)],
})
_PAYOFF_PRINTABLE_NAMES = frozenset({'base', 'platter', 'adjuster'})
_JIG_STATIONARY_NAMES = frozenset({
    'base', 'left_upright', 'right_upright', 'bearing_608_1', 'bearing_608_2',
    'left_bearing_cap', 'right_bearing_cap',
    *[f'{prefix}_fastener_{i}' for prefix in ('bench', 'upright') for i in range(1, 5)],
    *[f'upright_washer_{i}' for i in range(1, 9)],
    *[f'upright_nut_{i}' for i in range(1, 5)],
    *[f'bearing_cap_{kind}_{i}' for kind in ('screw', 'washer', 'nut') for i in range(1, 5)],
})


@dataclass(frozen=True)
class WindingToolAssemblies:
    """Named assembly B-reps; motion sets partition each tool's members.

    Adjustable and hardware-reference sets are independent annotations. The
    dictionaries are the authoritative audit geometry, permitting inspection
    of a modified assembly without silently rebuilding its original parts.
    """

    winding_jig: dict[str, cq.Workplane]
    wire_payoff: dict[str, cq.Workplane]
    ownership: dict[str, dict[str, frozenset[str]]]
    printable_parts: dict[str, cq.Workplane]
    head: WindingHeadParts
    frame: WindingFrameParts
    payoff: WirePayoffParts
    parameters: WindingToolParameters
    metadata: dict[str, object]


@lru_cache(maxsize=8192)
def _box(shape):
    return shape.val().BoundingBox()


def _intersection(first, second):
    """Skip disjoint bounding boxes before an exact OpenCascade common."""
    a, b = _box(first), _box(second)
    if (a.xmax < b.xmin or b.xmax < a.xmin
            or a.ymax < b.ymin or b.ymax < a.ymin
            or a.zmax < b.zmin or b.zmax < a.zmin):
        return 0.0
    volume = first.intersect(second).val().Volume()
    if not isfinite(volume):
        raise ValueError('Non-finite geometric intersection')
    return volume


def _clear(first, second):
    return _intersection(first, second) <= _VOLUME_TOLERANCE_MM3


def _circle_centres(shape, radius):
    return [edge.Center() for edge in shape.val().Edges()
            if edge.geomType() == 'CIRCLE'
            and abs(BRepAdaptor_Curve(edge.wrapped).Circle().Radius()
                    - radius) < 1e-6]


def _axial_probe(outer_radius, inner_radius, start, length, centre=(0.0, 0.0)):
    """Make a cylindrical/annular gauge along local Z."""
    profile = cq.Workplane('XY').circle(outer_radius)
    if inner_radius > 0:
        profile = profile.circle(inner_radius)
    return profile.extrude(length).translate((*centre, start))


def _probe_fraction(body, probe):
    """Fraction of a dedicated positive-support gauge occupied by a B-rep."""
    return _intersection(body, probe) / probe.val().Volume()


def _bearing_608_engagement(bearing, upright, shaft, outward):
    bb = _box(bearing)
    axis_y, axis_z = (bb.ymin + bb.ymax) / 2, (bb.zmin + bb.zmax) / 2

    def probe(outer, inner, start, length):
        return (_axial_probe(outer, inner, 0, length)
                .rotate((0, 0, 0), (0, 1, 0), 90)
                .translate((start, axis_y, axis_z)))

    # Gauges sit beyond the intended 0.1 mm running/shoulder gaps, inside the
    # mating material. No exact face coincidence is needed for a positive fit.
    wall = probe(11.35, 11.15, bb.xmin + 0.4, bb.xlen - 0.8)
    shoulder_start = bb.xmin - 0.3 if outward < 0 else bb.xmax + 0.2
    shoulder = probe(10.7, 10.05, shoulder_start, 0.1)
    pilot = probe(3.8, 0, bb.xmin + 0.4, bb.xlen - 0.8)
    evidence = {
        'seat_wall_fraction': _probe_fraction(upright, wall),
        'shoulder_fraction': _probe_fraction(upright, shoulder),
        'shaft_pilot_fraction': _probe_fraction(shaft, pilot),
        'seat_gap_mm': bearing.val().distance(upright.val()),
    }
    valid = (all(evidence[name] > 0.95 for name in
                 ('seat_wall_fraction', 'shoulder_fraction', 'shaft_pilot_fraction'))
             and evidence['seat_gap_mm'] <= 0.2)
    return bool(valid), evidence


def _place_head(head, frame):
    # Recover the rigid placement from the component B-reps, not a duplicate
    # axis-height constant. The local backplate rear face is Z=0.
    shaft = _box(frame.shaft_reference)
    offset = (_box(frame.head.backplate).xmin,
              (shaft.ymin + shaft.ymax) / 2,
              (shaft.zmin + shaft.zmax) / 2)
    placed = {name: shape.rotate((0, 0, 0), (0, 1, 0), 90).translate(offset)
              for name, shape in head.printable_parts.items()}
    return replace(head, backplate=placed['backplate'], cam=placed['cam'],
                   clamp=placed['clamp'],
                   sliders=tuple(placed[f'slider_{i}'] for i in range(1, 7)),
                   ribs=tuple(placed[f'rib_{i}'] for i in range(1, 7)),
                   printable_parts=placed,
                   guide_stop_references=tuple(shape.rotate(
                       (0, 0, 0), (0, 1, 0), 90).translate(offset)
                       for shape in head.guide_stop_references),
                   guide_stop_hardware={name: shape.rotate(
                       (0, 0, 0), (0, 1, 0), 90).translate(offset)
                       for name, shape in head.guide_stop_hardware.items()})


def _head_hardware(local_head, frame):
    shaft = _box(frame.shaft_reference)
    offset = (_box(frame.head.backplate).xmin, 0,
              (shaft.zmin + shaft.zmax) / 2)
    references = {}

    def ring(outer, inner, height, bottom):
        return (cq.Workplane('XY').circle(outer).circle(inner).extrude(height)
                .translate((0, 0, bottom)))

    def nut(height, bottom):
        return (cq.Workplane('XY').polygon(6, 5.5 / cos(radians(30)))
                .extrude(height).cut(cq.Workplane('XY').circle(1.6).extrude(height))
                .translate((0, 0, bottom)))

    for i, slider in enumerate(local_head.sliders, start=1):
        centres = _circle_centres(slider, 2.1)
        if len(centres) != 2:
            raise ValueError('Each slider requires a cylindrical cam follower bore')
        centre = min(centres, key=lambda c: c.z)
        follower = (cq.Workplane('XY').circle(1.5).extrude(2.6)
                    .translate((0, 0, 5.25)))
        follower = follower.union(cq.Workplane('XY').circle(2.0).extrude(6.65)
                                  .translate((0, 0, 7.85)))
        follower = follower.union(cq.Workplane('XY').circle(2.75).extrude(3.0)
                                  .translate((0, 0, 14.5)))
        follower_members = {
            f'cam_follower_{i}': follower,
            f'cam_follower_nut_{i}': nut(2.4, 5.35),
            f'cam_follower_washer_{i}': ring(3.5, 2.1, 0.6, 13.9),
        }
        follower_members = {name: shape.translate((centre.x, centre.y, 0))
                            for name, shape in follower_members.items()}
        angle = (i - 1) * 60
        # Local Z becomes tangential +Y. End hardware is outside guide walls.
        pin = cq.Workplane('XY').circle(1.5).extrude(22).translate((0, 0, -9.1))
        pin = pin.union(cq.Workplane('XY').circle(2.75).extrude(3)
                        .translate((0, 0, -12.1)))
        rib_members = {
            f'rib_pin_{i}': pin,
            f'rib_locknut_{i}': nut(4.0, 9.1),
            f'rib_washer_inner_{i}': ring(3.0, 1.6, 0.6, -9.1),
            f'rib_washer_outer_{i}': ring(3.0, 1.6, 0.6, 8.5),
        }
        rib_members = {name: shape.rotate((0, 0, 0), (1, 0, 0), -90)
                       .translate((local_head.state.requested_diameter_mm / 2 - 7,
                                   0, 5.9))
                       .rotate((0, 0, 0), (0, 0, 1), angle)
                       for name, shape in rib_members.items()}
        for name, shape in {**follower_members, **rib_members}.items():
            references[name] = shape.rotate(
                (0, 0, 0), (0, 1, 0), 90).translate(offset)
    for name, shape in local_head.guide_stop_hardware.items():
        references[name] = shape.rotate(
            (0, 0, 0), (0, 1, 0), 90).translate(offset)
    return references


def _numbered(prefix, shapes):
    return {f'{prefix}_{i}': shape for i, shape in enumerate(shapes, start=1)}


def build_winding_tool_assemblies(
        tool_parameters: WindingToolParameters = DEFAULT_WINDING_TOOL_PARAMETERS,
        design_parameters: DesignParameters = DEFAULT_PARAMETERS,
        diameter_mm: float | None = None,
        brake_setting: float = 0.0,
) -> WindingToolAssemblies:
    """Build and audit two independent tools; fail closed on any invariant."""
    validate_winding_tool_parameters(tool_parameters)
    diameter = (tool_parameters.reference_diameter_mm
                if diameter_mm is None else diameter_mm)
    frame = build_winding_frame(tool_parameters, design_parameters)
    local_head = build_winding_head(tool_parameters, diameter)
    head = _place_head(local_head, frame)
    frame = replace(frame, head=head)
    payoff = build_wire_payoff(tool_parameters, design_parameters, brake_setting)
    head_hardware = _head_hardware(local_head, frame)
    frame_hardware = {
        'shaft': frame.shaft_reference,
        'crank_pin': frame.crank_pin_reference,
        'crank_grip': frame.crank_grip_reference,
        'grip_pin': frame.grip_pin_reference,
        **_numbered('bearing_608', frame.bearings),
        **_numbered('bench_fastener', frame.bench_fastener_references),
        **_numbered('upright_fastener', frame.upright_fastener_references),
        **_numbered('upright_washer', frame.upright_washer_references),
        **_numbered('upright_nut', frame.upright_nut_references),
        **_numbered('shaft_locator', frame.shaft_locator_references),
        **_numbered('shaft_locator_pin', frame.shaft_locator_pin_references),
        **frame.bearing_cap_hardware,
        **_numbered('head_retaining_pin', frame.head_retaining_pin_references),
        **_numbered('preload_screw', frame.preload_screw_references),
        **_numbered('preload_nut', frame.preload_nut_references),
        **_numbered('grip_washer', frame.grip_washer_references),
    }
    jig = {**frame.printable_parts, **head.printable_parts,
           **frame_hardware, **head_hardware}
    supply = {**payoff.rotating_parts, **payoff.stationary_parts,
              **payoff.bearing_internal_parts,
              **_numbered('bench_fastener', payoff.bench_fastener_references)}
    jig_stationary = _JIG_STATIONARY_NAMES
    ownership = {
        'winding_jig': {
            'rotating': frozenset(jig) - jig_stationary,
            'stationary': jig_stationary,
            # A 608 is a sealed catalog envelope; its internals are not modeled.
            'bearing_internal': frozenset(),
            'adjustable': frozenset({'cam', 'clamp',
                                    *[f'slider_{i}' for i in range(1, 7)],
                                    *[f'rib_{i}' for i in range(1, 7)]}),
            'hardware_reference': frozenset(frame_hardware) | frozenset(head_hardware),
        },
        'wire_payoff': {
            'rotating': frozenset(payoff.rotating_parts),
            'stationary': frozenset(payoff.stationary_parts) | frozenset(
                f'bench_fastener_{i}' for i in range(1, 5)),
            'bearing_internal': frozenset(payoff.bearing_internal_parts),
            'adjustable': frozenset(payoff.brake_parts),
            'hardware_reference': frozenset(supply) - frozenset(payoff.printable_parts),
        },
    }
    printable = {f'winding_jig/{name}': shape for name, shape in
                 {**frame.printable_parts, **head.printable_parts}.items()}
    printable.update({f'wire_payoff/{name}': shape
                      for name, shape in payoff.printable_parts.items()})
    model = WindingToolAssemblies(
        jig, supply, ownership, printable, head, frame, payoff, tool_parameters,
        {'mechanically_synchronized': False, 'shared_base': False,
         'powered_operation_validated': False, 'physical_fit_verified': False,
         'fastener_lengths': 'nominal CAD selections; physical fit unverified'},
    )
    audit = audit_winding_tool_assemblies(model)
    if not audit['valid']:
        failed = ', '.join(name for name, passed in audit['checks'].items() if not passed)
        raise ValueError(f'Winding-tool assembly invariants failed: {failed}')
    return model


def _ownership_checks(model):
    partition = True
    for tool, parts in (('winding_jig', model.winding_jig),
                        ('wire_payoff', model.wire_payoff)):
        sets = model.ownership.get(tool, {})
        groups = [sets.get(name, frozenset()) for name in
                  ('rotating', 'stationary', 'bearing_internal')]
        partition &= (set().union(*groups) == set(parts)
                      and all(not a & b for a, b in combinations(groups, 2))
                      and sets.get('adjustable', frozenset()) <= set(parts)
                      and sets.get('hardware_reference', frozenset()) <= set(parts))
    owners = model.ownership.get('wire_payoff', {})
    jig_owners = model.ownership.get('winding_jig', {})
    partition &= (jig_owners.get('stationary') == _JIG_STATIONARY_NAMES
                  and jig_owners.get('rotating') ==
                  frozenset(model.winding_jig) - _JIG_STATIONARY_NAMES
                  and jig_owners.get('bearing_internal') == frozenset())
    thrust = (owners.get('rotating') == frozenset({'platter', 'shaft_washer'})
              and 'housing_washer' in owners.get('stationary', ())
              and owners.get('bearing_internal') == frozenset({'rolling_envelope'})
              and 'housing_washer' not in owners.get('rotating', ()))
    return bool(partition), bool(thrust)


def _local_jig(model):
    # The frame establishes the datum independently of a potentially displaced
    # shaft, backplate, or rib in the dictionary being audited.
    shaft = _box(model.frame.shaft_reference)
    rear = _box(model.frame.head.backplate).xmin
    height = (shaft.zmin + shaft.zmax) / 2
    return {name: shape.translate((-rear, 0, -height)).rotate(
        (0, 0, 0), (0, 1, 0), -90)
        for name, shape in model.winding_jig.items()}


def _tape_audit(local, diameter):
    widths = []
    # A 10-mm-high rectangular gauge traverses the full radial rib wall at
    # each of the 18 rays. Report a measured lower bound, never a label width.
    for angle in range(0, 360, 20):
        def fits(width):
            probe = (cq.Workplane('XY').box(10, width, 10,
                     centered=(False, True, False))
                     .translate((diameter / 2 - 7, 0, 14))
                     .rotate((0, 0, 0), (0, 0, 1), angle))
            return all(_clear(probe, body) for body in local.values())
        if not fits(12.0):
            widths.append(0.0)
            continue
        low, high = 12.0, 14.0
        for _ in range(5):
            mid = (low + high) / 2
            if fits(mid):
                low = mid
            else:
                high = mid
        widths.append(low)
    return widths


def _head_audit(local, p, diameter):
    backplate, cam, clamp = (local[name] for name in ('backplate', 'cam', 'clamp'))
    retention = release_clear = follower_clear = True
    for i in range(1, 7):
        slider, rib = local[f'slider_{i}'], local[f'rib_{i}']
        angle = radians((i - 1) * 60)
        unit = (cos(angle), sin(angle))
        release_vector = (-p.release_travel_mm * unit[0],
                          -p.release_travel_mm * unit[1], 0)
        released = (slider.translate(release_vector), rib.translate(release_vector))
        release_clear &= all(_clear(body, fixed) for body in released
                             for fixed in (backplate, clamp))
        release_clear &= _clear(released[1], cam)
        retention &= _intersection(slider.translate((0, 0, 0.5)), backplate) > 0
        for radial_travel, stop in (
                ((p.minimum_diameter_mm - diameter) / 2 - p.release_travel_mm - 0.3,
                 backplate),
                ((p.maximum_diameter_mm - diameter) / 2 + 0.3,
                 local[f'guide_stop_screw_{i}'])):
            displaced = slider.translate((radial_travel * unit[0],
                                          radial_travel * unit[1], 0))
            retention &= _intersection(displaced, stop) > 0
        follower_clear &= _clear(local[f'cam_follower_{i}'], cam)
        follower_clear &= _clear(local[f'cam_follower_{i}'], slider)

    # Releasing a coil requires turning the common cam. Find a physical track
    # position admitting all six followers after radial retraction.
    released_followers = [local[f'cam_follower_{i}'].translate(
        (-p.release_travel_mm * cos(radians((i - 1) * 60)),
         -p.release_travel_mm * sin(radians((i - 1) * 60)), 0))
        for i in range(1, 7)]
    cam_releases = False
    for step in range(1, 49):
        turned = cam.rotate((0, 0, 0), (0, 0, 1), step * 0.5)
        if all(_clear(turned, pin) for pin in released_followers):
            cam_releases = True
            break
    gap = _box(clamp).zmin - _box(cam).zmax
    shoulder_gap = _box(cam).zmin - _box(backplate).zmax
    lock = (0 <= gap <= 0.1 and abs(shoulder_gap) < 1e-5
            and _clear(clamp, cam)
            and _intersection(clamp.translate((0, 0, -gap - 0.05)), cam) > 0)
    return {'slider_retention': bool(retention),
            'head_release': bool(release_clear and cam_releases),
            'cam_lock_clearance': bool(lock and follower_clear)}, gap


def _moving_fixed_audit(model):
    collisions = []
    shaft_box = _box(model.frame.shaft_reference)
    height = (shaft_box.zmin + shaft_box.zmax) / 2
    # Sample full revolutions; list resolution in the returned audit so this
    # result cannot be confused with a certified continuous motion analysis.
    for tool, parts in (('winding_jig', model.winding_jig),
                        ('wire_payoff', model.wire_payoff)):
        owners = model.ownership[tool]
        start, end = (((0, 0, height), (1, 0, height)) if tool == 'winding_jig'
                      else ((0, 0, 0), (0, 0, 1)))
        for angle in range(0, 360, 30):
            for moving in sorted(owners['rotating']):
                rotated = parts[moving].rotate(start, end, angle)
                for fixed in sorted(owners['stationary']):
                    volume = _intersection(rotated, parts[fixed])
                    if volume > _VOLUME_TOLERANCE_MM3:
                        collisions.append({'tool': tool, 'moving': moving,
                                           'fixed': fixed, 'angle_deg': angle,
                                           'volume_mm3': volume})
    return collisions


def _head_hardware_audit(local, diameter, p):
    printed = [local[name] for name in ('backplate', 'cam', 'clamp',
               *[f'{prefix}_{i}' for prefix in ('slider', 'rib') for i in range(1, 7)])]
    prefixes = ('cam_follower', 'cam_follower_nut', 'cam_follower_washer',
                'rib_pin', 'rib_locknut', 'rib_washer_inner', 'rib_washer_outer',
                'guide_stop_screw', 'guide_stop_nut', 'guide_stop_washer')
    hardware_clear = all(_clear(local[f'{prefix}_{i}'], body)
                         for prefix in prefixes for i in range(1, 7) for body in printed)
    service_clear = True
    for i in range(1, 7):
        angle = radians((i - 1) * 60)
        for travel in range(0, 51, 10):
            distance = (p.maximum_diameter_mm - diameter) / 2 + travel
            vector = (distance * cos(angle), distance * sin(angle), 0)
            for prefix in ('slider', 'rib', 'rib_pin', 'rib_locknut',
                           'rib_washer_inner', 'rib_washer_outer'):
                service_clear &= _clear(local[f'{prefix}_{i}'].translate(vector),
                                         local['backplate'])
        # Removing all follower screws/washers allows the cam to lift off.
        for travel in (0, 5, 15, 30):
            lifted = local['cam'].translate((0, 0, travel))
            service_clear &= _clear(lifted, local[f'rib_{i}'])
        for travel in (0, 4, 8, 16, 24):
            stop_vector = (travel * cos(angle + radians(59)),
                           travel * sin(angle + radians(59)), 0)
            stop = local[f'guide_stop_screw_{i}'].translate(stop_vector)
            service_clear &= all(_clear(stop, body) for body in printed)
    return bool(hardware_clear), bool(service_clear)


def _follower_engagement_audit(local):
    """Require shoulders, threads, and retention heads in their mating voids."""
    evidence = []
    cam = local['cam']
    cam_box = _box(cam)
    for i in range(1, 7):
        slider, follower, nut, washer = (local[f'{name}_{i}'] for name in
                                         ('slider', 'cam_follower',
                                          'cam_follower_nut', 'cam_follower_washer'))
        bore_edges = _circle_centres(slider, 2.1)
        if len(bore_edges) != 2:
            raise ValueError(f'Slider {i} requires two follower-bore rim circles')
        lower, upper = sorted(bore_edges, key=lambda centre: centre.z)
        centre = (lower.x, lower.y)
        nb, wb = _box(nut), _box(washer)

        def probe(outer, inner, bottom, height):
            return _axial_probe(outer, inner, bottom, height, centre)

        slider_core = probe(1.9, 0, lower.z + 0.05, upper.z - lower.z - 0.1)
        cam_core = probe(1.9, 0, cam_box.zmin + 0.15, cam_box.zlen - 0.3)
        washer_core = probe(1.9, 0, wb.zmin + 0.1, wb.zlen - 0.2)
        nut_core = probe(1.4, 0, nb.zmin + 0.1, nb.zlen - 0.2)
        values = {
            'slider_shoulder_fraction': _probe_fraction(follower, slider_core),
            'cam_shoulder_fraction': _probe_fraction(follower, cam_core),
            'washer_shoulder_fraction': _probe_fraction(follower, washer_core),
            'nut_thread_fraction': _probe_fraction(follower, nut_core),
            'washer_body_fraction': _probe_fraction(
                washer, probe(3.3, 2.2, wb.zmin + 0.1, wb.zlen - 0.2)),
            'nut_body_fraction': _probe_fraction(
                nut, probe(2.5, 1.7, nb.zmin + 0.1, nb.zlen - 0.2)),
            'nut_roof_fraction': _probe_fraction(
                slider, probe(2.65, 2.2, nb.zmax + 0.2, 0.1)),
            'retaining_head_fraction': _probe_fraction(
                follower, probe(2.65, 2.2, wb.zmax + 0.1, 0.1)),
            'cam_track_wall_fraction': _probe_fraction(
                cam, probe(3.5, 3.0, cam_box.zmin + 0.2, cam_box.zlen - 0.4)),
            'washer_cam_gap_mm': washer.val().distance(cam.val()),
            'nut_pocket_gap_mm': nut.val().distance(slider.val()),
            'nut_thread_gap_mm': nut.val().distance(follower.val()),
        }
        values['valid'] = (
            all(value > 0.95 for name, value in values.items()
                if name.endswith('_fraction') and name != 'cam_track_wall_fraction')
            and values['cam_track_wall_fraction'] > 0.05
            and 0.05 <= values['washer_cam_gap_mm'] <= 0.35
            and values['nut_pocket_gap_mm'] <= 0.2
            and values['nut_thread_gap_mm'] <= 0.2
            and _clear(slider_core, slider) and _clear(cam_core, cam)
            and _clear(follower, nut) and _clear(follower, washer))
        evidence.append(values)
    return all(item['valid'] for item in evidence), evidence


def _drive_audit(model):
    jig = model.winding_jig
    shaft = jig['shaft']
    box = _box(shaft)
    shaft_axis = ((box.ymin + box.ymax) / 2, (box.zmin + box.zmax) / 2)
    nested = abs(box.ylen - 8) < 1e-5 and abs(box.zlen - 8) < 1e-5
    bearing_evidence = []
    for i, upright in ((1, 'left_upright'), (2, 'right_upright')):
        bearing = jig[f'bearing_608_{i}']
        bb = _box(bearing)
        nested &= (abs((bb.ymin + bb.ymax) / 2 - shaft_axis[0]) < 1e-5
                   and abs((bb.zmin + bb.zmax) / 2 - shaft_axis[1]) < 1e-5
                   and box.xmin < bb.xmin < bb.xmax < box.xmax
                   and abs(bb.ylen - 22) < 1e-5 and abs(bb.xlen - 7) < 1e-5
                   and _clear(shaft, bearing) and _clear(bearing, jig[upright]))
        # A missing bore/oversized bore cannot pass merely by not colliding.
        nested &= _intersection(shaft.translate((0, 0.05, 0)), bearing) > 0
        engaged, evidence = _bearing_608_engagement(
            bearing, jig[upright], shaft, -1 if i == 1 else 1)
        nested &= engaged
        bearing_evidence.append(evidence)
    coaxial = all(_clear(shaft, jig[name]) and
                  _intersection(shaft.translate((0, 0.4, 0)), jig[name]) > 0
                  for name in ('backplate', 'cam', 'clamp', 'head_hub',
                               'head_retaining_collar', 'crank'))
    grip = _box(jig['crank_grip'])
    grip_y, grip_z = ((grip.ymin + grip.ymax) / 2,
                       (grip.zmin + grip.zmax) / 2)
    orbit = hypot(grip_y - shaft_axis[0], grip_z - shaft_axis[1])
    hand_radius = 20.0
    hand = (cq.Workplane('XY').circle(orbit + hand_radius)
            .circle(max(0.1, orbit - hand_radius))
            .extrude(grip.xlen + 10)
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((grip.xmin - 5, *shaft_axis)))
    stationary = [jig[name] for name in model.ownership['winding_jig']['stationary']]
    hand_clearance = min(hand.val().distance(body.val()) for body in stationary)
    return bool(nested), bool(coaxial), hand_clearance, bearing_evidence


def _bearing_51105_engagement(parts):
    housing, rolling, shaft = (_box(parts[name]) for name in
                               ('housing_washer', 'rolling_envelope', 'shaft_washer'))
    centre = ((housing.xmin + housing.xmax) / 2, (housing.ymin + housing.ymax) / 2)
    base_support = _axial_probe(20.8, 12.7, housing.zmin - 0.3, 0.1, centre)
    housing_wall = _axial_probe(21.35, 21.15, housing.zmin + 0.2,
                                housing.zlen - 0.4, centre)
    platter_pilot = _axial_probe(12.3, 0, housing.zmin + 0.3,
                                 shaft.zmax - housing.zmin - 0.4, centre)
    platter_support = _axial_probe(17.8, 12.7, shaft.zmax + 0.2, 0.1, centre)
    rolling_middle = (housing.zmax + shaft.zmin) / 2
    rolling_probe = _axial_probe(19.0, 14.0, rolling_middle - 0.05, 0.1, centre)
    evidence = {
        'base_support_fraction': _probe_fraction(parts['base'], base_support),
        'housing_wall_fraction': _probe_fraction(parts['base'], housing_wall),
        'platter_pilot_fraction': _probe_fraction(parts['platter'], platter_pilot),
        'platter_support_fraction': _probe_fraction(parts['platter'], platter_support),
        'rolling_stack_fraction': _probe_fraction(parts['rolling_envelope'], rolling_probe),
        'housing_base_gap_mm': parts['housing_washer'].val().distance(parts['base'].val()),
        'shaft_platter_gap_mm': parts['shaft_washer'].val().distance(parts['platter'].val()),
        'housing_rolling_gap_mm': rolling.zmin - housing.zmax,
        'rolling_shaft_gap_mm': shaft.zmin - rolling.zmax,
    }
    supported = all(value > 0.95 for name, value in evidence.items()
                    if name.endswith('_fraction'))
    supported &= all(-1e-5 <= value <= 0.2 for name, value in evidence.items()
                     if name.endswith('_gap_mm'))
    return bool(supported), evidence


def _brake_audit(model):
    parts = model.wire_payoff
    adjuster, platter, base = (parts[name] for name in ('adjuster', 'platter', 'base'))
    # Minimum distance evaluates the actual underside over the pad, avoiding
    # the platter's lower bearing pilot bounding-box minimum.
    clearance = min(parts[name].val().distance(platter.val())
                    for name in ('adjuster', 'screw', 'nut', 'washer', 'spring'))
    # The felt bounds specify the current contact plane; travel to 1 mm rigid
    # clearance must end against the base's physical flange stop.
    remaining = adjuster.val().distance(platter.val()) - 1.0
    at_stop = adjuster.translate((0, 0, remaining))
    stop = (remaining >= -1e-5 and clearance >= 1 - 1e-5
            and _clear(adjuster, base) and _clear(at_stop, base)
            and _intersection(at_stop.translate((0, 0, 0.1)), base) > 0
            and parts['felt'].val().distance(platter.val()) < 1e-5
            and _clear(parts['felt'], platter))
    bearing_clear = all(_clear(parts[a], parts[b]) for a, b in (
        ('platter', 'housing_washer'), ('platter', 'rolling_envelope'),
        ('platter', 'shaft_washer'), ('base', 'shaft_washer'),
        ('base', 'rolling_envelope'), ('base', 'housing_washer')))
    washers = [_box(parts[name]) for name in
               ('housing_washer', 'rolling_envelope', 'shaft_washer')]
    bearing_clear &= all(abs((b.xmin + b.xmax) / 2) < 1e-5
                         and abs((b.ymin + b.ymax) / 2) < 1e-5 for b in washers)
    supported, evidence = _bearing_51105_engagement(parts)
    return bool(stop), clearance, bool(bearing_clear and supported), evidence


def audit_winding_tool_assemblies(model: WindingToolAssemblies) -> dict:
    """Return JSON-safe numeric evidence and named fail-closed checks.

    Re-audits dictionary geometry on every call. Sampling is 30 degrees for
    winding motion and 0.5 degrees when finding cam release. The hand envelope
    is a continuous annular sweep, with a 20 mm radial hand allowance.
    """
    _box.cache_clear()
    checks = {name: False for name in (
        'required_members', 'ownership_partition', 'valid_solids',
        'independent_tools', 'moving_fixed_clearance', 'tape_passages',
        'slider_retention', 'cam_lock_clearance', 'head_release',
        'shaft_608_nesting', 'drive_coaxiality', 'crank_hand_envelope',
        'head_hardware_clearance', 'head_service_access', 'cam_follower_engagement',
        'bearing_51105_ownership', 'bearing_51105_nesting',
        'brake_hard_stop', 'print_bed', 'spindle_axial_location',
        'complete_coil_removal', 'frame_flush_mounting',
        'brake_anti_rotation', 'brake_mounted_access')}
    audit = {'valid': False, 'checks': checks, 'rib_count': 0,
             'tape_station_count': 0, 'minimum_tape_clearance_mm': 0.0,
             'maximum_print_xy_mm': 0.0, 'head_release_travel_mm': 0.0,
             'motion_sample_step_deg': 30, 'collisions': [], 'errors': []}
    try:
        jig, supply = model.winding_jig, model.wire_payoff
        required_jig = {'base', 'left_upright', 'right_upright', 'shaft',
                        'backplate', 'cam', 'clamp', 'head_hub',
                        'head_retaining_collar', 'crank', 'crank_grip',
                        'bearing_608_1', 'bearing_608_2',
                        'left_bearing_cap', 'right_bearing_cap',
                        *[f'{prefix}_{i}' for prefix in
                          ('rib', 'slider', 'cam_follower', 'cam_follower_nut',
                           'cam_follower_washer', 'rib_pin', 'rib_locknut',
                           'rib_washer_inner', 'rib_washer_outer',
                           'guide_stop_screw', 'guide_stop_washer', 'guide_stop_nut')
                          for i in range(1, 7)]}
        required_supply = {'base', 'platter', 'adjuster', 'spring', 'washer',
                           'screw', 'nut', 'felt', 'housing_washer',
                           'shaft_washer', 'rolling_envelope'}
        required_jig |= {'crank_pin', 'grip_pin'}
        for prefix, count in (('bench_fastener', 4), ('upright_fastener', 4),
                              ('head_retaining_pin', 2), ('preload_screw', 3),
                              ('preload_nut', 3), ('grip_washer', 2),
                              ('upright_washer', 8), ('upright_nut', 4),
                              ('shaft_locator', 2), ('shaft_locator_pin', 2),
                              ('bearing_cap_screw', 4), ('bearing_cap_washer', 4),
                              ('bearing_cap_nut', 4)):
            required_jig.update(f'{prefix}_{i}' for i in range(1, count + 1))
        required_supply.update(f'bench_fastener_{i}' for i in range(1, 5))
        checks['required_members'] = (required_jig == jig.keys()
                                      and required_supply == supply.keys())
        expected_prints = {f'winding_jig/{name}' for name in _JIG_PRINTABLE_NAMES}
        expected_prints |= {f'wire_payoff/{name}' for name in _PAYOFF_PRINTABLE_NAMES}
        checks['required_members'] &= set(model.printable_parts) == expected_prints
        checks['ownership_partition'], checks['bearing_51105_ownership'] = (
            _ownership_checks(model))
        if not checks['required_members'] or not checks['ownership_partition']:
            return audit
        checks['valid_solids'] = all(
            shape.val().isValid() and len(shape.val().Solids()) == 1
            and isfinite(shape.val().Volume()) and shape.val().Volume() > 0
            for shape in (*jig.values(), *supply.values()))
        if not checks['valid_solids']:
            return audit
        checks['independent_tools'] = (jig['base'] is not supply['base']
                                      and not any(a.val().isSame(b.val())
                                                  for a in jig.values()
                                                  for b in supply.values()))
        local = _local_jig(model)
        diameter = model.head.state.requested_diameter_mm
        audit['rib_count'] = sum(name.startswith('rib_') and name[4:].isdigit()
                                  for name in jig)
        widths = _tape_audit(local, diameter)
        audit['tape_station_count'] = sum(width >= 12.0 for width in widths)
        audit['minimum_tape_clearance_mm'] = min(widths)
        audit['tape_clearances_mm'] = widths
        checks['tape_passages'] = len(widths) == 18 and min(widths) >= 12
        head_checks, gap = _head_audit(local, model.parameters, diameter)
        checks.update(head_checks)
        (checks['head_hardware_clearance'], checks['head_service_access']) = (
            _head_hardware_audit(local, diameter, model.parameters))
        (checks['cam_follower_engagement'], audit['cam_follower_engagement']) = (
            _follower_engagement_audit(local))
        audit['cam_lock_axial_gap_mm'] = gap
        audit['head_release_travel_mm'] = (model.parameters.release_travel_mm
                                            if checks['head_release'] else 0.0)
        audit['collisions'] = _moving_fixed_audit(model)
        checks['moving_fixed_clearance'] = not audit['collisions']
        (checks['shaft_608_nesting'], checks['drive_coaxiality'],
         audit['crank_hand_clearance_mm'], audit['bearing_608_engagement']) = _drive_audit(model)
        checks['crank_hand_envelope'] = audit['crank_hand_clearance_mm'] > 0
        (checks['brake_hard_stop'], audit['brake_rigid_clearance_mm'],
         checks['bearing_51105_nesting'], audit['bearing_51105_engagement']) = _brake_audit(model)
        service = audit_winding_tool_service(model)
        checks.update(service.pop('checks'))
        audit['service'] = service
        envelopes = {}
        for path in model.printable_parts:
            tool, name = path.split('/')
            body = (jig if tool == 'winding_jig' else supply)[name]
            box = _box(body)
            envelopes[path] = [box.xlen, box.ylen]
        audit['print_xy_envelopes_mm'] = envelopes
        audit['maximum_print_xy_mm'] = max(max(size) for size in envelopes.values())
        checks['print_bed'] = (audit['maximum_print_xy_mm']
                               <= model.parameters.print_bed_size_mm + 1e-5)
        audit['valid'] = all(checks.values())
    except (ValueError, KeyError, TypeError, RuntimeError) as error:
        audit['errors'].append(f'{type(error).__name__}: {error}')
    return audit


def winding_tool_bom(model: WindingToolAssemblies) -> tuple[dict, ...]:
    """Literal purchasing/service rows; one 51105 includes all three envelopes.

    Bench bolts and clamps are alternatives within each choice group. Pin and
    screw lengths are nominal CAD selections, to be checked on a prototype.
    """
    frame, payoff = model.frame, model.payoff
    rows = []

    def add(item, quantity, specification, service_note, **extra):
        rows.append({'item': item, 'quantity': quantity,
                     'specification': specification, 'service_note': service_note,
                     'physical_fit_verified': False,
                     'length_selection': 'nominal CAD selection', **extra})

    add('608 bearing', len(frame.bearings), '8 x 22 x 7 mm, sealed radial bearing',
        'Two independent upright seats; withdraw shaft to replace.')
    add('51105 thrust bearing', 1, '25 x 42 x 11 mm, complete purchased bearing',
        'Lift platter; keep both washers and rolling assembly as one bearing set.')
    add('8 mm shaft', 1, f'8 mm steel shaft, {_box(frame.shaft_reference).xlen:.1f} mm long',
        'Three 4.2 mm drive holes plus two 3.2 mm locator holes; remove all five pins before withdrawal.')
    add('shaft shoulder collar', 2, 'Steel: 8.2 mm bore, 10.4 mm OD x 6 mm nose, 16 mm OD x 8 mm body',
        'Locate only the left 608 inner ring with 0.1 mm face clearance each side; verify purchased ring lands.')
    add('shaft locator pin', 2, '3 mm diameter x 20 mm removable cross-pin',
        'Cross-drill shaft/collars together at the modeled axes; deburr for shaft withdrawal.')
    add('shaft locator pin keeper', 2, 'Keeper clip matched to 3 mm locator cross-pin',
        'Remove with the other three keepers for supported coil removal.')
    add('M3 bearing cap screw', 4, 'M3 x 22 mm socket-head screw',
        'Two per outer-ring cap; nuts and washers remain accessible outside each upright.')
    add('M3 bearing cap nut', 4, 'ISO 4032 M3, 5.5 mm AF x 2.4 mm',
        'Hold with a wrench while tightening the cap; do not clamp an inner ring or seal.')
    add('M3 bearing cap washer', 4, '6 mm OD x 3.2 mm ID x 0.6 mm',
        'Under each cap nut on the outside of the upright.')
    add('metal cam follower', 6,
        '4 mm shoulder x 6.65 mm, M3 threaded tip x 2.6 mm, 5.5 x 3 mm head',
        'Nominal custom shoulder screw; captive nut loads from slider underside '
        'before guide insertion. Shoulder preserves cam running clearance.')
    add('cam follower captive nut', 6, 'ISO 4032 M3, 5.5 mm AF x 2.4 mm',
        'Insert from underside before installing sliders; pocket blocks rotation.')
    add('cam follower washer', 6, '7 mm OD x 4.2 mm ID x 0.6 mm',
        'Fit above cam; retain 0.2 mm nominal axial clearance to cam.')
    add('M3 rib attachment pin', 6, 'M3 x 22 mm socket-head through-bolt',
        'Head and locknut lie outside guide walls; remove nut then withdraw tangentially.')
    add('rib attachment locknut', 6, 'M3 locking nut, 5.5 mm AF x 4 mm',
        'Retains rib bolt; do not tighten across and deform the guide channel.')
    add('rib attachment washer', 12, '6 mm OD x 3.2 mm ID x 0.6 mm',
        'One washer at each rib-bolt end, outside guide walls.')
    add('M3 guide stop screw', 6, 'M3 x 20 mm socket-head screw',
        'Remove from the outboard nut boss before sliding a rib/slider out.')
    add('M3 guide stop nut', 6, 'ISO 4032 M3, 5.5 mm AF x 2.4 mm',
        'Load from above into the outboard boss; install before winding, verify tightness.')
    add('M3 guide stop washer', 6, '6 mm OD x 3.2 mm ID x 0.6 mm',
        'Fit beneath the outboard stop screw head.')
    hardware = frame.metadata['preload_hardware']
    add(hardware['screw_designation'], hardware['screw_quantity'],
        'ISO 4762 M3 x 20, 5.5 mm head diameter, 3 mm head height',
        'Back off all three screws before cam adjustment or head release.')
    add('ISO 4032 M3 preload nut', hardware['nut_quantity'],
        'M3, 5.5 mm across flats, 2.4 mm thick',
        'Load radially into collar pockets before fitting preload screws.')
    add('head hub retaining pin', 1, '4 mm diameter x 26 mm removable cross-pin',
        'Withdraw to slide hub away from the three printed torque pins.')
    add('head collar retaining pin', 1, '4 mm diameter x 32 mm removable cross-pin',
        'Withdraw after releasing the preload screws.')
    add('crank shaft retaining pin', 1, '4 mm diameter x 30 mm removable cross-pin',
        'Withdraw before removing the manual crank.')
    add('M4 upright bolt', len(frame.upright_fastener_references), 'M4 x 20 mm socket-head bolt, 7 mm OD x 4 mm head',
        'Install from below before mounting: head and lower washer lie inside the base recess.')
    add('M4 upright nut', 4, 'M4 locking nut, 7 mm AF x 5 mm', 'Above upright foot; inspect tightness before winding.')
    add('M4 upright washer', 8, '9 mm OD x 4.3 mm ID x 0.8 mm', 'One washer under each bolt head and nut.')
    add('crank grip', 1, '22 mm OD x 24 mm long, 6.6 mm running bore',
        'Purchased freely rotating grip; verify no seizure under hand load.')
    add('crank grip axle', 1, '6 mm diameter x 41 mm retained axle',
        'Provide removable end retention outside the two washers; verify fit.')
    add('crank grip washer', len(frame.grip_washer_references),
        '6.1 mm ID x 14 mm OD x 0.6 mm', 'One at each end of the free-running grip.')
    add('crank grip axle retaining ring', 2, 'External retaining ring for 6 mm grooved axle',
        'Machine grooves beyond washers; nominal references do not model grooves.')
    add('removable cross-pin keeper', 3, 'Keeper clip matched to each 4 mm cross-pin',
        'Fit to hub, collar, and crank cross-pins; verify retention and hand clearance.')
    add('felt brake pad', 1, '14 mm OD x 3.4 mm ID x 2 mm uncompressed felt',
        'Lower adjuster and remove brake screw to replace pad radially.')
    add('brake compression spring', 1, '8 mm OD, 4 mm ID, 9.2 mm free length',
        'Spring sits on base cavity floor; choose rate by measured payoff drag.')
    add('brake spring washer', 1, '10 mm OD x 3.4 mm ID x 0.6 mm',
        'Install between spring and printed adjuster.')
    screw_length = _box(payoff.screw).zlen - 3.0
    add('M3 brake adjustment screw', 1, f'M3 socket-head screw, {screw_length:.1f} mm shank',
        'Trim/select length to preserve 1 mm rigid platter gap at hard stop.')
    add('M3 brake-adjuster nut', 1, 'ISO 4032 M3, 5.5 mm across flats, 2.4 mm thick',
        'Load into adjuster pocket before inserting adjuster into base; keep screw engaged.')
    for tool, count in (('winding_jig', len(frame.bench_fastener_references)),
                        ('wire_payoff', len(payoff.bench_fastener_references))):
        allowance = 18 + (payoff.metadata['base_foot_height_mm'] if tool == 'wire_payoff' else 0)
        add(f'{tool} bench bolt', count, f'M5 through-bolt; length = bench thickness + {allowance:g} mm',
            'Bolted mounting alternative; measure bench and verify underside access.',
            choice_group=f'{tool}_bench', alternative='bolts')
        add(f'{tool} bench washer', count * 2, 'M5 flat washer',
            'One under each bolt head and nut when choosing bolted mounting.',
            choice_group=f'{tool}_bench', alternative='bolts')
        add(f'{tool} bench nut', count, 'M5 locking nut',
            'Use with bench bolts and washers.',
            choice_group=f'{tool}_bench', alternative='bolts')
        add(f'{tool} bench clamp', 2, 'Small bench clamp for 13 x 60 mm clamp land',
            'Alternative to bench bolts; check jaw access and resistance to tipping.',
            choice_group=f'{tool}_bench', alternative='clamps')
    return tuple(rows)
