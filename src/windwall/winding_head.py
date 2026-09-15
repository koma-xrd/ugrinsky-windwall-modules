"""Parametric six-rib winding head for round serpentine-coil blanks.

The backplate, cam, clamp, six sliders, and six ribs remain independent
printable bodies.  Identical slider/rib masters are rotated in 60-degree
increments, while identical Archimedean cam tracks provide synchronous radial
motion across the supported diameter range. Purchased guide-stop hardware is
published separately; removing it permits radial slider/rib service.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from math import cos, hypot, isfinite, radians, sin

import cadquery as cq

from windwall.winding_tool_parameters import (
    WindingToolParameters,
    validate_winding_tool_parameters,
)


_BACKPLATE_RADIUS_MM = 76.0
_BACKPLATE_THICKNESS_MM = 5.0
_SLIDER_INNER_RADIUS_AT_REFERENCE_MM = 24.0
_FOLLOWER_RADIUS_AT_REFERENCE_MM = 32.0
_SLIDER_BOTTOM_Z_MM = 3.5
_SLIDER_TOP_Z_MM = 9.2
_CAM_BOTTOM_Z_MM = 9.7
_CAM_THICKNESS_MM = 4.0
_CAM_RADIUS_MM = 48.0
_TRACK_HALF_SWEEP_DEG = 12.0
_RIB_RADIAL_DEPTH_MM = 4.5
_RIB_TANGENTIAL_WIDTH_MM = 52.0
_RIB_BOTTOM_Z_MM = _SLIDER_TOP_Z_MM
_RIB_HEIGHT_MM = 20.0
_FRAME_DRIVE_PIN_RADIUS_MM = 13.5
_FRAME_DRIVE_PIN_HOLE_DIAMETER_MM = 3.4
_RIB_PIN_Z_MM = 5.9


@dataclass(frozen=True)
class WindingHeadState:
    requested_diameter_mm: float
    rib_contact_radii_mm: tuple[float, ...]
    tape_station_count: int
    tape_passage_width_mm: float
    release_travel_mm: float
    frame_drive_pin_centres_xy_mm: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class WindingHeadParts:
    backplate: cq.Workplane
    cam: cq.Workplane
    clamp: cq.Workplane
    sliders: tuple[cq.Workplane, ...]
    ribs: tuple[cq.Workplane, ...]
    printable_parts: dict[str, cq.Workplane]
    state: WindingHeadState
    guide_stop_references: tuple[cq.Workplane, ...] = ()
    guide_stop_hardware: dict[str, cq.Workplane] = field(default_factory=dict)


def tape_station_angles(p: WindingToolParameters) -> tuple[float, ...]:
    """Return the equally spaced tape-station angles around the winding axis."""
    validate_winding_tool_parameters(p)
    return tuple(index * 360 / p.tape_station_count
                 for index in range(p.tape_station_count))


def _valid_single_solid(shape: cq.Workplane, name: str) -> cq.Workplane:
    """Clean and validate one independently printable connected body."""
    cleaned = shape.clean()
    value = cleaned.val()
    volume = value.Volume()
    if (not value.isValid() or len(value.Solids()) != 1
            or not isfinite(volume) or volume <= 0):
        raise ValueError(f'{name} must be one valid connected solid')
    return cleaned


def _disc(radius: float, bottom_z: float, height: float) -> cq.Workplane:
    return (cq.Workplane('XY').circle(radius).extrude(height)
            .translate((0, 0, bottom_z)))


def _radial_box(inner_radius: float, length: float, width: float,
                bottom_z: float, height: float) -> cq.Workplane:
    return (cq.Workplane('XY')
            .box(length, width, height, centered=(False, True, False))
            .translate((inner_radius, 0, bottom_z)))


def _rotate(shape: cq.Workplane, angle_deg: float) -> cq.Workplane:
    return shape.rotate((0, 0, 0), (0, 0, 1), angle_deg)


def _frame_drive_pin_centres() -> tuple[tuple[float, float], ...]:
    return tuple(
        (_FRAME_DRIVE_PIN_RADIUS_MM * cos(radians(angle)),
         _FRAME_DRIVE_PIN_RADIUS_MM * sin(radians(angle)))
        for angle in (30.0, 150.0, 270.0)
    )


@lru_cache(maxsize=8)
def _guide_stop(p: WindingToolParameters):
    """Outboard captive-nut boss and removable oblique M3 guide stop.

    The boss is below the rib shell and outside the bolted slider's service
    corridor. The tip, rather than a trapped screw head, limits slider travel.
    """
    angle = 59.0
    tip_x = (p.maximum_diameter_mm / 2 - _RIB_RADIAL_DEPTH_MM
             + 0.15 + 1.5 * sin(radians(angle)))

    def axial(shape, start):
        return shape.rotate((0, 0, 0), (0, 1, 0), 90).translate((start, 0, 6.35))

    boss = _radial_box(13.2, 6.2, 8.0, 2.5, 6.6)
    bore = axial(cq.Workplane('XY').circle(1.7).extrude(8.0), 12.5)
    pocket = axial(cq.Workplane('XY').polygon(6, 5.8 / cos(radians(30)))
                   .extrude(2.8), 14.4)
    loading = _radial_box(14.4, 2.8, 6.8, 6.35, 5.0)
    boss = boss.cut(bore).cut(pocket).cut(loading)
    screw = axial(cq.Workplane('XY').circle(1.5).extrude(20), 0)
    screw = screw.union(axial(cq.Workplane('XY').circle(2.75).extrude(3), 20))
    washer = axial(cq.Workplane('XY').circle(3).circle(1.6).extrude(0.6), 19.4)
    nut = axial(cq.Workplane('XY').polygon(6, 5.5 / cos(radians(30)))
                .extrude(2.4).cut(cq.Workplane('XY').circle(1.6).extrude(2.4)), 14.6)
    clearance = axial(cq.Workplane('XY').circle(1.7).extrude(22), -1)
    return {name: _rotate(shape, angle).translate((tip_x, 4.0, 0))
            for name, shape in {'boss': boss, 'screw': screw,
                                'washer': washer, 'nut': nut,
                                'clearance': clearance}.items()}


@lru_cache(maxsize=8)
def _build_backplate(p: WindingToolParameters) -> cq.Workplane:
    body = _disc(_BACKPLATE_RADIUS_MM, 0, _BACKPLATE_THICKNESS_MM)

    # Each guide has a broad lower flange pocket and two overhanging lips.  The
    # flange cannot lift through the narrow upper opening. The inner cross-bar
    # and removable outer screw stop act independently of the cam followers.
    guide = _radial_box(14.0, 57.0, 2.4, 4.9, 3.6).translate((0, 7.0, 0))
    guide = guide.union(
        _radial_box(14.0, 57.0, 1.4, 7.05, 1.45).translate((0, 5.65, 0)))
    guide = guide.union(
        _radial_box(14.0, 57.0, 2.4, 4.9, 3.6).translate((0, -7.0, 0)))
    guide = guide.union(
        _radial_box(14.0, 57.0, 1.4, 7.05, 1.45).translate((0, -5.65, 0)))
    minimum_slider_inner = (
        _SLIDER_INNER_RADIUS_AT_REFERENCE_MM
        + p.minimum_diameter_mm / 2 - p.reference_diameter_mm / 2)
    inner_stop_end = minimum_slider_inner - p.release_travel_mm - 0.15
    guide = guide.union(
        _radial_box(inner_stop_end - 2.85, 2.85, 16.4, 4.9, 4.1))
    for index in range(p.rib_count):
        body = body.union(_rotate(guide, index * 360 / p.rib_count))

    guide_floor = _radial_box(inner_stop_end + 0.01,
                              78 - inner_stop_end, 11.6, 3.35, 1.7)
    for index in range(p.rib_count):
        angle = index * 360 / p.rib_count
        body = body.cut(_rotate(guide_floor, angle))

    # A retained M3 rib bolt crosses both guide walls. Its shank needs a
    # continuous travel slot; outboard head/nut reliefs leave the guide end
    # stops intact and keep the inner guide length available for retention.
    pin_min = p.minimum_diameter_mm / 2 - 7 - p.release_travel_mm
    bolt_travel = _radial_box(pin_min - 1.75, 80 - pin_min,
                              17.0, 4.15, 3.5)
    for y in (-10.9, 10.9):
        bolt_travel = bolt_travel.union(_radial_box(
            pin_min - 3.4, 82 - pin_min, 5.2, 2.5, 7.0
        ).translate((0, y, 0)))
    for index in range(p.rib_count):
        angle = index * 360 / p.rib_count
        body = body.cut(_rotate(bolt_travel, angle))
        body = body.union(_rotate(_guide_stop(p)['boss'], angle))
        body = body.cut(_rotate(_guide_stop(p)['clearance'], angle))

    # The cam seats on this integral annular shoulder. Clamp compression thus
    # returns directly into the backplate rather than through sliders or guide
    # lips. Its outer radius stays clear of a fully released slider.
    body = body.union(_disc(11.5, 4.9, _CAM_BOTTOM_Z_MM - 4.9))
    body = body.cut(_disc(p.shaft_diameter_mm / 2 + 0.25, -0.5,
                           _CAM_BOTTOM_Z_MM + 1))

    # Three frame-side drive pins pass through the backplate independently of
    # clamp friction. Their centres lie outside the clamp-reaction shoulder and
    # between the six radial slider guides.
    for x, y in _frame_drive_pin_centres():
        drive_hole = (_disc(_FRAME_DRIVE_PIN_HOLE_DIAMETER_MM / 2,
                            -0.5, _BACKPLATE_THICKNESS_MM + 1.0)
                      .translate((x, y, 0)))
        body = body.cut(drive_hole)

    # Fixed witness line for the three calibrated diameter engravings on cam.
    pointer = (_radial_box(49.5, 7.0, 0.9, 4.45, 0.7)
               .rotate((0, 0, 0), (0, 0, 1), 180.0))
    body = body.cut(pointer)

    # Station numerals sit outside the maximum rib radius and are tangent to
    # their corresponding passage rays, so all 18 remain visible in assembly.
    for station, angle in enumerate(tape_station_angles(p), start=1):
        body = body.cut(_engraved_text(
            str(station), 73.3, angle, _BACKPLATE_THICKNESS_MM,
            character_height=2.4, depth=0.55))
    return body


def _track_radius_limits(p: WindingToolParameters) -> tuple[float, float]:
    reference_radius = p.reference_diameter_mm / 2
    minimum = (_FOLLOWER_RADIUS_AT_REFERENCE_MM
               + p.minimum_diameter_mm / 2 - reference_radius
               - p.release_travel_mm)
    maximum = (_FOLLOWER_RADIUS_AT_REFERENCE_MM
               + p.maximum_diameter_mm / 2 - reference_radius)
    return minimum, maximum


def _track_angle_for_radius(p: WindingToolParameters, radius: float) -> float:
    minimum, maximum = _track_radius_limits(p)
    fraction = (radius - minimum) / (maximum - minimum)
    return -_TRACK_HALF_SWEEP_DEG + fraction * 2 * _TRACK_HALF_SWEEP_DEG


def _master_cam_track(p: WindingToolParameters) -> cq.Workplane:
    minimum, maximum = _track_radius_limits(p)
    points: list[tuple[float, float]] = []
    for index in range(17):
        fraction = index / 16
        radius = minimum + fraction * (maximum - minimum)
        angle = radians(-_TRACK_HALF_SWEEP_DEG
                        + fraction * 2 * _TRACK_HALF_SWEEP_DEG)
        points.append((radius * cos(angle), radius * sin(angle)))

    tangents: list[tuple[float, float]] = []
    for index in range(len(points)):
        previous = points[max(0, index - 1)]
        following = points[min(len(points) - 1, index + 1)]
        dx = following[0] - previous[0]
        dy = following[1] - previous[1]
        length = hypot(dx, dy)
        tangents.append((dx / length, dy / length))

    # Extend the square ends beyond the adjustment limits so a round follower
    # remains fully enclosed at both hard stops.
    half_width = 2.4
    points[0] = (points[0][0] - tangents[0][0] * half_width,
                 points[0][1] - tangents[0][1] * half_width)
    points[-1] = (points[-1][0] + tangents[-1][0] * half_width,
                  points[-1][1] + tangents[-1][1] * half_width)
    left = [(point[0] - tangent[1] * half_width,
             point[1] + tangent[0] * half_width)
            for point, tangent in zip(points, tangents)]
    right = [(point[0] + tangent[1] * half_width,
              point[1] - tangent[0] * half_width)
             for point, tangent in zip(points, tangents)]
    return (cq.Workplane('XY').polyline(left + list(reversed(right))).close()
            .extrude(_CAM_THICKNESS_MM + 1)
            .translate((0, 0, _CAM_BOTTOM_Z_MM - 0.5)))


def _engraved_text(label: str, radius: float, angle_deg: float,
                   top_z: float, character_height: float = 3.2,
                   depth: float = 0.65) -> cq.Workplane:
    angle = radians(angle_deg)
    text = (cq.Workplane('XY').text(
                label, character_height, depth, combine=True)
            .rotate((0, 0, 0), (0, 0, 1), angle_deg + 90)
            .translate((radius * cos(angle), radius * sin(angle), top_z - 0.5)))
    return text


def _build_cam(p: WindingToolParameters, follower_radius: float) -> cq.Workplane:
    cam = _disc(_CAM_RADIUS_MM, _CAM_BOTTOM_Z_MM, _CAM_THICKNESS_MM)
    master_track = _master_cam_track(p)
    for index in range(p.rib_count):
        cam = cam.cut(_rotate(master_track, index * 360 / p.rib_count))
    cam = cam.cut(_disc(p.shaft_diameter_mm / 2 + 0.3,
                        _CAM_BOTTOM_Z_MM - 0.5, _CAM_THICKNESS_MM + 1))

    for label, diameter in (
            ('110', p.minimum_diameter_mm),
            ('127', p.reference_diameter_mm),
            ('145', p.maximum_diameter_mm)):
        label_follower_radius = (
            _FOLLOWER_RADIUS_AT_REFERENCE_MM
            + diameter / 2 - p.reference_diameter_mm / 2)
        label_angle = 180.0 + _track_angle_for_radius(p, label_follower_radius)
        cam = cam.cut(_engraved_text(
            label, 46.0, label_angle, _CAM_BOTTOM_Z_MM + _CAM_THICKNESS_MM))

    setting_angle = -_track_angle_for_radius(p, follower_radius)
    return _rotate(cam, setting_angle)


def _build_clamp(p: WindingToolParameters) -> cq.Workplane:
    # Tightening this hand wheel on the shaft compresses the cam against the
    # backplate, so the lock is independent of follower friction.  Six scallops
    # make the separate pressure ring operable without a tool.
    body = _disc(16.0, 13.75, 4.5)
    for index in range(6):
        angle = radians(index * 60)
        scallop = (_disc(2.5, 13.25, 5.5)
                   .translate((16.0 * cos(angle), 16.0 * sin(angle), 0)))
        body = body.cut(scallop)
    body = body.cut(_disc(p.shaft_diameter_mm / 2 + 0.3, 13.25, 5.5))
    return body.edges('|Z').fillet(0.7)


def _tangential_hole(radial_position: float, height_position: float,
                     radius: float, length: float) -> cq.Workplane:
    return (cq.Workplane('XY').circle(radius).extrude(length)
            .rotate((0, 0, 0), (1, 0, 0), 90)
            .translate((radial_position, length / 2, height_position)))


def _build_master_slider(p: WindingToolParameters) -> cq.Workplane:
    reference_contact_radius = p.reference_diameter_mm / 2
    inner = _SLIDER_INNER_RADIUS_AT_REFERENCE_MM
    outer = reference_contact_radius - _RIB_RADIAL_DEPTH_MM
    height = _SLIDER_TOP_Z_MM - _SLIDER_BOTTOM_Z_MM
    slider = _radial_box(inner, outer - inner, 10.5,
                         _SLIDER_BOTTOM_Z_MM, height)
    top_rebate_height = 2.45
    for y in (-4.5, 4.5):
        rebate = _radial_box(inner - 0.5, outer - inner + 1,
                             1.5, _SLIDER_TOP_Z_MM - top_rebate_height,
                             top_rebate_height + 0.5).translate((0, y, 0))
        slider = slider.cut(rebate)

    # The outer fork receives the rib's keyed tongue. A tangential 3 mm pin
    # crosses both fork arms and the tongue, positively retaining the rib while
    # keeping the fastener ends inside the wire-contact radius.
    socket = _radial_box(
        outer - 5.8, 6.3, 6.4,
        _SLIDER_BOTTOM_Z_MM - 0.1, height + 0.2)
    slider = slider.cut(socket)
    attachment_pin_radius = reference_contact_radius - 7.0
    slider = slider.cut(_tangential_hole(
        attachment_pin_radius, _RIB_PIN_Z_MM, 1.7, 14.0))

    follower_hole = _disc(2.1, _SLIDER_BOTTOM_Z_MM - 0.5,
                           height + 1).translate(
                               (_FOLLOWER_RADIUS_AT_REFERENCE_MM, 0, 0))
    nut_pocket = (cq.Workplane('XY').polygon(6, 5.8 / cos(radians(30)))
                  .extrude(4.45).translate(
                      (_FOLLOWER_RADIUS_AT_REFERENCE_MM, 0,
                       _SLIDER_BOTTOM_Z_MM - 0.1)))
    return slider.cut(follower_hole).cut(nut_pocket)


def _edge_sort_key(edge: cq.Edge) -> tuple[float, ...]:
    centre = edge.Center()
    return tuple(round(value, 8) for value in
                 (centre.z, centre.y, centre.x, edge.Length()))


def _fillet_edges_stably(shape: cq.Workplane, selector: str,
                         radius: float) -> cq.Workplane:
    # OCCT contour processing follows input edge order. Geometric ordering
    # keeps boundary loops, STEP entities and STL triangles reproducible.
    edges = sorted(shape.edges(selector).vals(), key=_edge_sort_key)
    return shape.newObject(edges).fillet(radius)


def _build_master_rib(p: WindingToolParameters) -> cq.Workplane:
    minimum_contact_radius = p.minimum_diameter_mm / 2
    inner_radius = minimum_contact_radius - _RIB_RADIAL_DEPTH_MM
    annulus = _disc(minimum_contact_radius, _RIB_BOTTOM_Z_MM, _RIB_HEIGHT_MM)
    annulus = annulus.cut(_disc(
        inner_radius, _RIB_BOTTOM_Z_MM - 0.5, _RIB_HEIGHT_MM + 1))
    window = _radial_box(
        0, minimum_contact_radius + 1, _RIB_TANGENTIAL_WIDTH_MM,
        _RIB_BOTTOM_Z_MM - 0.5, _RIB_HEIGHT_MM + 1)
    # Unequal corner/edge radii avoid spherical pole triangles collapsing in
    # binary STL. The winding-contact cylinder and tape-mouth radii stay fixed.
    rib = _fillet_edges_stably(annulus.intersect(window), '|Z', 1.5)
    rib = _fillet_edges_stably(rib, '>Z or <Z', 1.2)

    # A low keyed tongue fits the slider fork below the cam plane. The outer
    # riser joins it to the rib shell beyond the cam radius. Both parts share a
    # tangential pin bore for a removable M3-class fastener.
    tongue = _radial_box(inner_radius - 5.6, 7.0, 6.0, 3.6, 5.3)
    riser = _radial_box(inner_radius, 1.4, 6.0, 3.6, 7.2)
    rib = rib.union(tongue).union(riser)
    rib = rib.cut(_tangential_hole(
        minimum_contact_radius - 7.0, _RIB_PIN_Z_MM, 1.7, 14.0))

    # Three rounded, outward-running grooves in each invariant master create
    # all 18 tape stations after polar copying. Top and bottom contact bands
    # remain connected; the open radial mouth releases tape after retraction.
    groove_bottom = _RIB_BOTTOM_Z_MM + 3.8
    groove_height = _RIB_HEIGHT_MM - 7.6
    adjustment_offsets = (
        0.0,
        (p.reference_diameter_mm - p.minimum_diameter_mm) / 2,
        (p.maximum_diameter_mm - p.minimum_diameter_mm) / 2,
    )
    for relative_angle in (-20.0, 0.0, 20.0):
        groove = None
        for offset in adjustment_offsets:
            aligned_cutter = _rotate(
                _radial_box(
                    minimum_contact_radius + offset - 14.0, 15.5,
                    p.tape_passage_width_mm, groove_bottom, groove_height)
                .edges().fillet(0.8),
                relative_angle,
            ).translate((-offset, 0, 0))
            groove = (aligned_cutter if groove is None
                      else groove.union(aligned_cutter))
        if groove is None:
            raise ValueError('Tape groove sweep requires adjustment samples')
        rib = rib.cut(groove)

    # Cutter fillets round the inside corners, but the cutter/outer-cylinder
    # intersection otherwise leaves a sharp 90-degree mouth. Select those six
    # final circular boundaries on the true contact cylinder and fillet the
    # finished B-rep so the wire sees a tangent 0.8 mm transition.
    groove_boundaries = (groove_bottom, groove_bottom + groove_height)
    mouth_edges = [
        edge for edge in rib.val().Edges()
        if (edge.geomType() == 'CIRCLE'
            and any(abs(edge.Center().z - boundary) < 0.01
                    for boundary in groove_boundaries)
            and max(hypot(vertex.X, vertex.Y)
                    for vertex in edge.Vertices()) > minimum_contact_radius - 0.1
            and edge.Length() > 5.0)
    ]
    if len(mouth_edges) != 6:
        raise ValueError('Rib must expose six roundable tape-groove mouth edges')
    rib = rib.newObject(sorted(mouth_edges, key=_edge_sort_key)).fillet(0.8)
    return rib


def build_winding_head(p: WindingToolParameters,
                       diameter_mm: float) -> WindingHeadParts:
    """Build the independently printable head parts at one winding diameter."""
    validate_winding_tool_parameters(p)
    if (isinstance(diameter_mm, bool)
            or not isinstance(diameter_mm, (int, float))
            or not isfinite(diameter_mm)
            or not p.minimum_diameter_mm <= diameter_mm <= p.maximum_diameter_mm):
        raise ValueError('diameter must be finite and within the supported range')

    requested_diameter = float(diameter_mm)
    contact_radius = requested_diameter / 2
    radial_offset = contact_radius - p.reference_diameter_mm / 2
    follower_radius = _FOLLOWER_RADIUS_AT_REFERENCE_MM + radial_offset

    backplate = _valid_single_solid(_build_backplate(p), 'backplate')
    cam = _valid_single_solid(_build_cam(p, follower_radius), 'cam')
    clamp = _valid_single_solid(_build_clamp(p), 'clamp')

    master_slider = _build_master_slider(p).translate((radial_offset, 0, 0))
    master_rib = _build_master_rib(p).translate(
        (contact_radius - p.minimum_diameter_mm / 2, 0, 0))
    sliders = tuple(
        _valid_single_solid(_rotate(master_slider, index * 360 / p.rib_count),
                            f'slider_{index + 1}')
        for index in range(p.rib_count)
    )
    ribs = tuple(
        _valid_single_solid(_rotate(master_rib, index * 360 / p.rib_count),
                            f'rib_{index + 1}')
        for index in range(p.rib_count)
    )

    printable_parts: dict[str, cq.Workplane] = {
        'backplate': backplate,
        'cam': cam,
        'clamp': clamp,
    }
    printable_parts.update(
        (f'slider_{index + 1}', slider)
        for index, slider in enumerate(sliders))
    printable_parts.update(
        (f'rib_{index + 1}', rib)
        for index, rib in enumerate(ribs))

    state = WindingHeadState(
        requested_diameter_mm=requested_diameter,
        rib_contact_radii_mm=(contact_radius,) * p.rib_count,
        tape_station_count=p.tape_station_count,
        tape_passage_width_mm=p.tape_passage_width_mm,
        release_travel_mm=p.release_travel_mm,
        frame_drive_pin_centres_xy_mm=_frame_drive_pin_centres(),
    )
    hardware = {f'guide_stop_{name}_{i + 1}': _rotate(shape, i * 360 / p.rib_count)
                for name, shape in _guide_stop(p).items() if name in ('screw', 'washer', 'nut')
                for i in range(p.rib_count)}
    stops = tuple(hardware[f'guide_stop_screw_{i + 1}'] for i in range(p.rib_count))
    return WindingHeadParts(backplate, cam, clamp, sliders, ribs,
                            printable_parts, state, stops, hardware)
