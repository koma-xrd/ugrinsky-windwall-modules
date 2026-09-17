"""Printable six-spoke wheel and six congruent plug-in contact shoes.

Coordinates use the winding axis as Z: wheel rear is Z=0, front is Z=5.
The shoe master's cradle bottom is at nominal radius, X=0 on its centerline;
only its rounded shoulders extend outward. It is translated to the selected
radius before rotation. Only placement changes with diameter. Three tape
reliefs per shoe provide tangential strip width and axial bundle clearance.
Their fixed local centers and nominal 20-degree labels identify the
conceptual sequence; actual physical angles change with diameter and are never
claimed to be equally spaced. This is a rounded six-point envelope.
The frame owns the mating printed shaft; this module supplies its hex socket.
"""

from dataclasses import dataclass
from functools import lru_cache
from math import atan2, degrees, isfinite, radians, tan
from numbers import Real

import cadquery as cq

from windwall.winding_tool_parameters import WindingToolParameters, diameter_settings_mm


_WHEEL_THICKNESS = 5.0
_PIN_SETBACK = 8.0
_PIN_ROWS = (-5.0, 5.0)
_SHOE_BOTTOM = 5.2
_REAR_SHOULDER_HEIGHT = 2.7
_FREE_SHOULDER_HEIGHT = 1.3
_TAPE_BOTTOM = 11.0
_PASSAGE_INNER_X = -12.0
_PASSAGE_OUTER_X = _REAR_SHOULDER_HEIGHT + .4
_MOUTH_RADIUS = .8
_AXIAL_EDGE_RADIUS = .45
_RELEASE_LIFT = 40.0


@dataclass(frozen=True)
class WindingHeadState:
    diameter_mm: float
    shoe_radius_mm: float
    release_radius_mm: float


@dataclass(frozen=True)
class WindingHeadParts:
    wheel: cq.Workplane
    shoe_master: cq.Workplane
    shoes: tuple[cq.Workplane, ...]
    state: WindingHeadState
    metadata: dict


def tape_station_angles(p: WindingToolParameters) -> tuple[float, ...]:
    """Conceptual station labels only; these are not physical corridor angles."""
    diameter_settings_mm(p)
    return tuple(index * 360.0 / p.tape_station_count
                 for index in range(p.tape_station_count))


def _box(x, y, z, length, width, height):
    return (cq.Workplane('XY').box(length, width, height, centered=False)
            .translate((x, y, z)))


def _rotate(shape, angle):
    return shape.rotate((0, 0, 0), (0, 0, 1), angle)


def _compound(shapes):
    return cq.Workplane('XY').newObject([
        cq.Compound.makeCompound([shape.val() for shape in shapes])])


def _fillet(shape, edges, radius):
    # Stable contour order matters to OCCT topology and later mesh exports.
    ordered = sorted(edges, key=lambda edge: tuple(round(value, 8) for value in
        (*edge.Center().toTuple(), edge.Length())))
    return shape.newObject(ordered).fillet(radius)


def _print_master(shape, name, bed):
    solid = shape.val()
    if not solid.isValid() or len(solid.Solids()) != 1 or solid.Volume() <= 0:
        raise ValueError(f'{name} must be one valid positive-volume solid')
    bounds = solid.BoundingBox()
    if bounds.xlen > min(220, bed) or bounds.ylen > min(220, bed):
        raise ValueError(f'{name} exceeds the print-bed envelope')
    return shape


@lru_cache(maxsize=8)
def _build_wheel(p: WindingToolParameters) -> cq.Workplane:
    settings = diameter_settings_mm(p)
    spoke_end = p.maximum_diameter_mm / 2 - 2
    spoke = _box(12, -14, 0, spoke_end - 12, 28, _WHEEL_THICKNESS)
    spoke = _fillet(spoke, spoke.edges('|Z').vals(), 3)
    wheel = cq.Workplane('XY').circle(21).extrude(_WHEEL_THICKNESS)
    for index in range(p.spoke_count):
        wheel = wheel.union(_rotate(spoke, index * 60))
    wheel = _fillet(wheel, wheel.edges('|Z').vals(), 1)
    cutters = []
    for diameter in settings:
        position = diameter / 2 - _PIN_SETBACK
        for row in _PIN_ROWS:
            cutters.append(_box(position - 1.2, row - 1.7, -1, 2.4, 3.4, 7))
        cutters.append(cq.Workplane('XY').text(
            f'{diameter:g}', 2.8, .6, combine=True)
            .rotate((0, 0, 0), (0, 0, 1), 90).translate((position, 10, 4.5)))
    spoke_cuts = _compound(cutters)
    wheel = wheel.cut(_compound([_rotate(spoke_cuts, index * 60)
                                 for index in range(p.spoke_count)]))
    socket = cq.Workplane('XY').polygon(6, 14.4).extrude(7).translate((0, 0, -1))
    return _print_master(wheel.cut(socket).clean(), 'wheel', p.print_bed_mm)


def _passage_offsets(p):
    # The 12 mm wide feed corridors remain inside their own sectors at the
    # minimum setting when their radial probes cover only the contact shell.
    side = p.minimum_diameter_mm * .15
    return (-side, 0.0, side)


def _passage_probes(p):
    # Tape width lies along local Y (tangent), independent of the axial Z
    # winding envelope. Both directions reserve the declared clearance.
    return tuple(_box(_PASSAGE_INNER_X, offset - p.tape_clearance_mm / 2, _TAPE_BOTTOM,
                      _PASSAGE_OUTER_X - _PASSAGE_INNER_X,
                      p.tape_clearance_mm, p.tape_clearance_mm)
                 for offset in _passage_offsets(p))


def _asymmetric_shoe_shell(minimum_radius: float, bottom: float,
                           top: float) -> cq.Workplane:
    """Revolve the cradle directly, preserving the inner wall and nominal bottom.

    Cubic segments meet with vertical tangents at both shoulders and the cradle
    bottom. Fixed axial end margins let their span follow the tape clearance.
    The translated sector retains the mounting side of the old shell; tape
    passages and the unchanged foot/pins are applied by ``_build_shoe``.
    """
    inner = minimum_radius - 6
    radius = _AXIAL_EDGE_RADIUS
    # Preserve the default 6.5/16.5/26.5 mm landmarks without letting a shorter
    # accepted shoe reverse the profile between its front shoulder and end.
    rear_shoulder_z = bottom + 1.3
    free_shoulder_z = top - 2.7
    cradle_bottom_z = (rear_shoulder_z + free_shoulder_z) / 2
    outer_points = (
        (minimum_radius + _REAR_SHOULDER_HEIGHT, bottom + 1.0),
        (minimum_radius + _REAR_SHOULDER_HEIGHT, rear_shoulder_z),
        (minimum_radius, cradle_bottom_z),
        (minimum_radius + _FREE_SHOULDER_HEIGHT, free_shoulder_z),
        (minimum_radius + _FREE_SHOULDER_HEIGHT, top - 1.0),
    )
    rear_radius, free_radius = outer_points[0][0], outer_points[-1][0]
    profile = (cq.Workplane('XZ').moveTo(inner + radius, bottom)
               .lineTo(rear_radius - radius, bottom)
               .radiusArc((rear_radius, bottom + radius), radius)
               .lineTo(*outer_points[0]).lineTo(*outer_points[1]))
    for start, end in zip(outer_points[1:3], outer_points[2:4]):
        handle = (end[1] - start[1]) / 3
        profile = profile.bezier([
            (start[0], start[1] + handle),
            (end[0], end[1] - handle), end], includeCurrent=True)
    shell = (profile.lineTo(*outer_points[-1]).lineTo(free_radius, top - radius)
            .radiusArc((free_radius - radius, top), radius)
            .lineTo(inner + radius, top)
            .radiusArc((inner, top - radius), radius)
            .lineTo(inner, bottom + radius)
            .radiusArc((inner + radius, bottom), radius)
            .close().revolve(360, (0, 0), (0, 1)))
    sector = (cq.Workplane('XY').polyline([
        (0, 0), (minimum_radius + 10, -(minimum_radius + 10) * tan(radians(29.8))),
        (minimum_radius + 10, (minimum_radius + 10) * tan(radians(29.8)))])
        .close().extrude(top + 1))
    return shell.intersect(sector).translate((-minimum_radius, 0, 0))


def _mouth_lip_filler(offset, side, half_width, top):
    """Analytic concave quarter-round replacing an unstable edge fillet."""
    radius = _MOUTH_RADIUS
    overlap = .02
    filler = _box(-18, half_width - radius, top - radius - overlap,
                  20, radius + overlap, radius + 2 * overlap)
    cylinder = (cq.Workplane('YZ').center(half_width - radius, top - radius)
                .circle(radius).extrude(20).translate((-18, 0, 0)))
    filler = filler.cut(cylinder)
    if side < 0:
        filler = filler.mirror('XZ', union=False)
    return filler.translate((0, offset, 0))


def _keyed_pin(row):
    # Rigid rectangular key and separate 0.8 mm flexure share a broad root.
    # The 0.2 mm hook interference implies roughly 0.9% outer-fiber strain
    # over the 5.2 mm root-to-hook span. PLA fatigue needs prototype testing.
    post = _box(-9, -.9, -4, 2, .9, 9.7)
    beam = _box(-9, .5, -4, 2, .8, 9.7)
    root = _box(-9, -.9, 4.5, 2, 2.2, 1.2)
    hook = (cq.Workplane('YZ').polyline([
        (1.2, -1.6), (1.9, -.7), (1.9, -.2), (1.2, -.2)])
        .close().extrude(2).translate((-9, 0, 0)))
    pin = post.union(beam).union(root).union(hook)
    root_edges = [edge for edge in pin.val().Edges()
                  if abs(edge.Center().z - 4.5) < 1e-6
                  and any(abs(edge.Center().y - y) < 1e-6 for y in (0, .5))]
    pin = _fillet(pin, root_edges, .2)
    if row < 0:
        pin = pin.mirror('XZ', union=False)
    return pin.translate((0, row, 0))


@lru_cache(maxsize=8)
def _build_shoe(p: WindingToolParameters) -> cq.Workplane:
    minimum_radius = p.minimum_diameter_mm / 2
    top = _TAPE_BOTTOM + p.tape_clearance_mm + 6.2
    shell = _print_master(_asymmetric_shoe_shell(minimum_radius, _SHOE_BOTTOM, top),
                          'shoe shell', p.print_bed_mm)
    shell_envelope = shell
    passage_top = _TAPE_BOTTOM + p.tape_clearance_mm + _MOUTH_RADIUS
    half_width = p.tape_clearance_mm / 2 + .3
    for offset in _passage_offsets(p):
        # Leave the front bridge, but open every channel through the rear rim.
        # A closed tape loop's inner leg must not meet a trailing contact rim
        # when the shoe is withdrawn forward.
        shell = shell.cut(_box(-18, offset - half_width, -1,
                              _PASSAGE_OUTER_X + 18, 2 * half_width, passage_top + 1))
    # The widened side slots leave short inner returns at the sector ends.
    # Their adjacent radii must fit that 0.65 mm land; the outer wire-contact
    # exits and six upper mouth lips retain the full 0.8 mm radius.
    inner_edges = [edge for edge in shell.edges('|Z').vals() if edge.Center().x < -10]
    shell = _fillet(shell, inner_edges, .2)
    outer_edges = [edge for edge in shell.edges('|Z').vals() if edge.Center().x > -10]
    shell = _fillet(shell, outer_edges, _MOUTH_RADIUS)
    for offset in _passage_offsets(p):
        for side in (-1, 1):
            filler = _mouth_lip_filler(offset, side, half_width, passage_top)
            shell = shell.union(filler.intersect(shell_envelope))
    foot = _box(-12, -8, _SHOE_BOTTOM, 9, 16, 3)
    foot = _fillet(foot, foot.edges('|Z').vals(), 1)
    shoe = shell.union(foot)
    for row in _PIN_ROWS:
        shoe = shoe.union(_keyed_pin(row))
    return _print_master(shoe.clean(), 'shoe_master', p.print_bed_mm)


def build_winding_head(p: WindingToolParameters, diameter_mm: float,
                       released: bool = False) -> WindingHeadParts:
    """Seat all shoes at one setting, or remove all six through the open front.

    Release requires squeezing both rear tabs and withdrawing each shoe axially.
    Detached shoes are inventory/service occurrences only, excluded from the
    assembled winding support. Inward relocation is not the release method:
    neighboring shoe ends would interfere at the smallest setting.
    """
    settings = diameter_settings_mm(p)
    if (isinstance(diameter_mm, bool) or not isinstance(diameter_mm, Real)
            or not isfinite(diameter_mm) or diameter_mm not in settings):
        raise ValueError('diameter must equal one of the labeled wheel settings')
    radius = float(diameter_mm) / 2
    wheel = _build_wheel(p)
    master = _build_shoe(p)
    seated = tuple(_rotate(master.translate((radius, 0, 0)), index * 60)
                  for index in range(p.spoke_count))
    shoes = () if released else seated
    detached = tuple(shoe.translate((0, 0, _RELEASE_LIFT)) for shoe in seated) if released else ()
    probes = tuple(_rotate(probe.translate((radius, 0, 0)), index * 60)
                   for index in range(p.spoke_count) for probe in _passage_probes(p))
    passage_center_x = radius + (_PASSAGE_INNER_X + _PASSAGE_OUTER_X) / 2
    actual_angles = tuple((degrees(atan2(offset, passage_center_x))
                           + index * 60) % 360
                          for index in range(p.spoke_count)
                          for offset in _passage_offsets(p))
    metadata = {
        'diameter_labels': tuple(f'{value:g}' for value in settings),
        'pin_rows_y_mm': _PIN_ROWS,
        'pin_setback_mm': _PIN_SETBACK,
        'cradle_bottom_radius_offset_mm': 0.0,
        'rear_shoulder_height_mm': _REAR_SHOULDER_HEIGHT,
        'free_shoulder_height_mm': _FREE_SHOULDER_HEIGHT,
        'wire_guidance': 'rounded asymmetric U-cradle; lower free-front shoulder',
        'wheel_thickness_mm': _WHEEL_THICKNESS,
        'drive_socket': {'polygon_sides': 6, 'circumdiameter_mm': 14.4},
        'nominal_tape_angles_deg': tape_station_angles(p),
        'actual_tape_angles_deg': actual_angles,
        'tape_passage_probes': probes,
        'tape_clearance_mm': p.tape_clearance_mm,
        'tape_width_direction': 'tangential local Y; axial Z is bundle clearance; rear rim open',
        'release_lift_mm': _RELEASE_LIFT,
        'release_method': 'press both rear tabs and remove each shoe forward',
        'detached_shoes': detached,
        'radial_release_clearance_mm': radius if released else 0.0,
        'released': released,
        'print_orientations': {
            'wheel': 'rear XY face on bed, Z up',
            'shoe_master': 'rotate +90 degrees about X; support only inward face/foot',
        },
    }
    return WindingHeadParts(wheel, master, shoes,
        WindingHeadState(float(diameter_mm), 0.0 if released else radius, 0.0), metadata)
