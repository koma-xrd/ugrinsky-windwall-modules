"""Horizontal manual frame for the adjustable serpentine-coil winding head.

The printable base, two uprights, removable head retainers, and crank are kept
as separate bodies. Purchased fasteners, shaft, bearings, grip, and retention
pins are geometric references only. The 6.35 mm socket is provided for future
experiments; this module does not validate powered winding.
"""

from dataclasses import dataclass
from functools import lru_cache
from math import cos, isfinite, radians, sin, sqrt

import cadquery as cq

from windwall.bearings import build_608_reference
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters
from windwall.winding_head import WindingHeadParts, build_winding_head
from windwall.winding_tool_parameters import (
    WindingToolParameters,
    validate_winding_tool_parameters,
)


_BASE_LENGTH_MM = 210.0
_BASE_WIDTH_MM = 190.0
_BASE_THICKNESS_MM = 8.0
_AXIS_HEIGHT_MM = 95.0
_UPRIGHT_CENTRES_X_MM = (-72.0, 72.0)
_UPRIGHT_THICKNESS_MM = 14.0
_UPRIGHT_FOOT_LENGTH_MM = 36.0
_UPRIGHT_FOOT_WIDTH_MM = 110.0
_UPRIGHT_FOOT_HEIGHT_MM = 8.0
_UPRIGHT_PLATE_WIDTH_MM = 76.0
_UPRIGHT_PLATE_HEIGHT_MM = 96.0
_PART_GAP_MM = 0.2
_BENCH_HOLE_DIAMETER_MM = 5.4
_UPRIGHT_BOLT_HOLE_DIAMETER_MM = 4.4
_PIN_HOLE_DIAMETER_MM = 4.2
_CRANK_SOCKET_DEPTH_MM = 7.0
_CRANK_OUTER_FACE_X_MM = 106.0
_M3_NUT_ACROSS_FLATS_MM = 5.5
_M3_NUT_THICKNESS_MM = 2.4
_M3_NUT_POCKET_ACROSS_FLATS_MM = 5.8
_M3_NUT_POCKET_AXIAL_DEPTH_MM = 2.8
_PRELOAD_SCREW_LENGTH_MM = 10.0


@dataclass(frozen=True)
class WindingFrameParts:
    """Printable frame members and non-printable assembly references."""

    base: cq.Workplane
    uprights: tuple[cq.Workplane, cq.Workplane]
    head: WindingHeadParts
    head_hub: cq.Workplane
    head_retaining_collar: cq.Workplane
    crank: cq.Workplane
    bearings: tuple[cq.Workplane, cq.Workplane]
    shaft_reference: cq.Workplane
    bench_fastener_references: tuple[cq.Workplane, ...]
    upright_fastener_references: tuple[cq.Workplane, ...]
    head_retaining_pin_references: tuple[cq.Workplane, cq.Workplane]
    preload_screw_references: tuple[cq.Workplane, ...]
    preload_nut_references: tuple[cq.Workplane, ...]
    crank_pin_reference: cq.Workplane
    crank_grip_reference: cq.Workplane
    grip_pin_reference: cq.Workplane
    grip_washer_references: tuple[cq.Workplane, cq.Workplane]
    hex_socket_gauge_reference: cq.Workplane
    clamp_lands: tuple[cq.Workplane, cq.Workplane]
    printable_parts: dict[str, cq.Workplane]
    metadata: dict[str, object]


def _valid_single_solid(shape: cq.Workplane, name: str) -> cq.Workplane:
    cleaned = shape.clean()
    value = cleaned.val()
    volume = value.Volume()
    if (not value.isValid() or len(value.Solids()) != 1
            or not isfinite(volume) or volume <= 0):
        raise ValueError(f'{name} must be one valid connected solid')
    return cleaned


def _vertical_cylinder(radius_mm: float, bottom_z_mm: float,
                       height_mm: float, x_mm: float = 0.0,
                       y_mm: float = 0.0) -> cq.Workplane:
    return (cq.Workplane('XY').center(x_mm, y_mm).circle(radius_mm)
            .extrude(height_mm).translate((0, 0, bottom_z_mm)))


def _x_cylinder(radius_mm: float, start_x_mm: float, length_mm: float,
                axis_z_mm: float = _AXIS_HEIGHT_MM,
                direction: int = 1,
                axis_y_mm: float = 0.0) -> cq.Workplane:
    if direction not in (-1, 1):
        raise ValueError('Horizontal cylinder direction must be -1 or 1')
    angle = 90.0 * direction
    return (cq.Workplane('XY').circle(radius_mm).extrude(length_mm)
            .rotate((0, 0, 0), (0, 1, 0), angle)
            .translate((start_x_mm, axis_y_mm, axis_z_mm)))


def _x_ring(outer_radius_mm: float, inner_radius_mm: float,
            start_x_mm: float, length_mm: float,
            axis_z_mm: float = _AXIS_HEIGHT_MM,
            direction: int = 1) -> cq.Workplane:
    angle = 90.0 * direction
    return (cq.Workplane('XY').circle(outer_radius_mm).circle(inner_radius_mm)
            .extrude(length_mm)
            .rotate((0, 0, 0), (0, 1, 0), angle)
            .translate((start_x_mm, 0, axis_z_mm)))


def _x_hex_prism(across_flats_mm: float, start_x_mm: float,
                 length_mm: float, axis_y_mm: float,
                 axis_z_mm: float) -> cq.Workplane:
    circumscribed_diameter = 2 * across_flats_mm / sqrt(3)
    return (cq.Workplane('XY').polygon(6, circumscribed_diameter)
            .extrude(length_mm)
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((start_x_mm, axis_y_mm, axis_z_mm)))


def _radial_slot(start_x_mm: float, axial_length_mm: float,
                 radial_start_mm: float, radial_length_mm: float,
                 tangential_width_mm: float, angle_deg: float
                 ) -> cq.Workplane:
    return (cq.Workplane('XY')
            .box(axial_length_mm, radial_length_mm, tangential_width_mm,
                 centered=(False, False, True))
            .translate((start_x_mm, radial_start_mm, 0))
            .rotate((0, 0, 0), (1, 0, 0), angle_deg)
            .translate((0, 0, _AXIS_HEIGHT_MM)))


def _y_cylinder(radius_mm: float, start_y_mm: float, length_mm: float,
                x_mm: float, z_mm: float) -> cq.Workplane:
    return (cq.Workplane('XY').circle(radius_mm).extrude(length_mm)
            .rotate((0, 0, 0), (1, 0, 0), -90)
            .translate((x_mm, start_y_mm, z_mm)))


def _build_base() -> tuple[cq.Workplane, tuple[cq.Workplane, ...],
                           tuple[cq.Workplane, cq.Workplane]]:
    base = cq.Workplane('XY').box(
        _BASE_LENGTH_MM, _BASE_WIDTH_MM, _BASE_THICKNESS_MM,
        centered=(True, True, False),
    )

    bench_fasteners = tuple(
        _vertical_cylinder(2.5, -2.0, 14.0, x, y)
        for x in (-45.0, 45.0)
        for y in (-75.0, 75.0)
    )
    for x in (-45.0, 45.0):
        for y in (-75.0, 75.0):
            base = base.cut(_vertical_cylinder(
                _BENCH_HOLE_DIAMETER_MM / 2, -1.0,
                _BASE_THICKNESS_MM + 2.0, x, y,
            ))

    for x in _UPRIGHT_CENTRES_X_MM:
        for y in (-45.0, 45.0):
            base = base.cut(_vertical_cylinder(
                _UPRIGHT_BOLT_HOLE_DIAMETER_MM / 2, -1.0,
                _BASE_THICKNESS_MM + 2.0, x, y,
            ))

    clamp_lands = tuple(
        cq.Workplane('XY').box(13.0, 60.0, 2.0,
                               centered=(True, True, False))
        .translate((x, 0, _BASE_THICKNESS_MM - 2.0))
        for x in (-98.5, 98.5)
    )
    return (_valid_single_solid(base, 'base'), bench_fasteners,
            (clamp_lands[0], clamp_lands[1]))


def _build_upright(center_x_mm: float, inward_direction: int,
                    design_parameters: DesignParameters) -> cq.Workplane:
    foot_bottom = _BASE_THICKNESS_MM + _PART_GAP_MM
    foot = (cq.Workplane('XY')
            .box(_UPRIGHT_FOOT_LENGTH_MM, _UPRIGHT_FOOT_WIDTH_MM,
                 _UPRIGHT_FOOT_HEIGHT_MM, centered=(True, True, False))
            .translate((center_x_mm, 0, foot_bottom)))
    plate = (cq.Workplane('XY')
             .box(_UPRIGHT_THICKNESS_MM, _UPRIGHT_PLATE_WIDTH_MM,
                  _UPRIGHT_PLATE_HEIGHT_MM, centered=(True, True, False))
             .translate((center_x_mm, 0,
                         foot_bottom + _UPRIGHT_FOOT_HEIGHT_MM)))
    upright = foot.union(plate)

    for y in (-45.0, 45.0):
        upright = upright.cut(_vertical_cylinder(
            _UPRIGHT_BOLT_HOLE_DIAMETER_MM / 2,
            foot_bottom - 1.0, _UPRIGHT_FOOT_HEIGHT_MM + 2.0,
            center_x_mm, y,
        ))

    half_thickness = _UPRIGHT_THICKNESS_MM / 2
    inner_face_x = center_x_mm - inward_direction * half_thickness
    seat_depth = design_parameters.bearings.radial_housing_seat_depth_mm
    seat = _x_cylinder(
        design_parameters.bearings.radial_housing_seat_diameter_mm / 2,
        inner_face_x - inward_direction * 0.1,
        seat_depth + 0.1,
        direction=inward_direction,
    )
    shaft_passage = _x_cylinder(
        design_parameters.shaft.clearance_hole_diameter_mm / 2,
        center_x_mm - half_thickness - 1.0,
        _UPRIGHT_THICKNESS_MM + 2.0,
    )
    return _valid_single_solid(
        upright.cut(seat).cut(shaft_passage),
        'left upright' if center_x_mm < 0 else 'right upright',
    )


def _place_head_horizontally(head: WindingHeadParts) -> WindingHeadParts:
    rotated_parts = {
        name: shape.rotate((0, 0, 0), (0, 1, 0), 90)
        for name, shape in head.printable_parts.items()
    }
    axial_min = min(shape.val().BoundingBox().xmin
                    for shape in rotated_parts.values())
    axial_max = max(shape.val().BoundingBox().xmax
                    for shape in rotated_parts.values())
    translation = (-(axial_min + axial_max) / 2, 0, _AXIS_HEIGHT_MM)
    placed = {name: shape.translate(translation)
              for name, shape in rotated_parts.items()}
    return WindingHeadParts(
        backplate=placed['backplate'],
        cam=placed['cam'],
        clamp=placed['clamp'],
        sliders=tuple(placed[f'slider_{index + 1}']
                      for index in range(len(head.sliders))),
        ribs=tuple(placed[f'rib_{index + 1}']
                   for index in range(len(head.ribs))),
        printable_parts=placed,
        state=head.state,
    )


def _build_head_retainers(
        tool_parameters: WindingToolParameters,
        head: WindingHeadParts,
        design_parameters: DesignParameters,
) -> tuple[cq.Workplane, cq.Workplane,
           tuple[cq.Workplane, cq.Workplane], tuple[cq.Workplane, ...],
           tuple[cq.Workplane, ...]]:
    shaft_clearance_radius = tool_parameters.shaft_diameter_mm / 2 + 0.2
    backplate_rear_x = head.backplate.val().BoundingBox().xmin
    clamp_front_x = head.clamp.val().BoundingBox().xmax

    hub = _x_ring(12.0, shaft_clearance_radius, -30.0, 12.0)
    flange_start_x = -18.0
    hub = hub.union(_x_ring(
        16.0, shaft_clearance_radius,
        flange_start_x, backplate_rear_x - flange_start_x))
    for local_x, local_y in head.state.frame_drive_pin_centres_xy_mm:
        pin_y = local_y
        pin_z = _AXIS_HEIGHT_MM - local_x
        drive_pin = _x_cylinder(
            1.5, backplate_rear_x - 0.2, 4.9,
            axis_z_mm=pin_z, axis_y_mm=pin_y,
        )
        hub = hub.union(drive_pin)
    hub_pin_hole = _vertical_cylinder(
        _PIN_HOLE_DIAMETER_MM / 2, _AXIS_HEIGHT_MM - 14.0,
        28.0, -25.0, 0,
    )
    hub = _valid_single_solid(hub.cut(hub_pin_hole), 'head hub')

    collar_start_x = clamp_front_x + 1.35
    collar_length = 8.0
    collar = _x_ring(
        14.0, shaft_clearance_radius, collar_start_x, collar_length)

    preload_axes = tuple(
        (angle,
         9.0 * cos(radians(angle)),
         _AXIS_HEIGHT_MM + 9.0 * sin(radians(angle)))
        for angle in (0.0, 120.0, 240.0)
    )
    nut_pocket_start_x = collar_start_x + 3.6
    for angle, y, z in preload_axes:
        collar = collar.cut(_x_cylinder(
            1.7, collar_start_x - 0.5, collar_length + 1.0,
            axis_z_mm=z, axis_y_mm=y,
        ))
        collar = collar.cut(_x_hex_prism(
            _M3_NUT_POCKET_ACROSS_FLATS_MM,
            nut_pocket_start_x, _M3_NUT_POCKET_AXIAL_DEPTH_MM,
            y, z,
        ))
        collar = collar.cut(_radial_slot(
            nut_pocket_start_x, _M3_NUT_POCKET_AXIAL_DEPTH_MM,
            8.0, 7.0, 6.8, angle,
        ))
    collar_pin_hole = _vertical_cylinder(
        _PIN_HOLE_DIAMETER_MM / 2, _AXIS_HEIGHT_MM - 12.0,
        24.0, 8.0, 0,
    )
    collar = _valid_single_solid(
        collar.cut(collar_pin_hole), 'head retaining collar')

    pins = (
        _vertical_cylinder(2.0, _AXIS_HEIGHT_MM - 13.0, 26.0, -25.0, 0),
        _vertical_cylinder(2.0, _AXIS_HEIGHT_MM - 11.0, 22.0, 8.0, 0),
    )

    preload_screws = []
    preload_nuts = []
    manufacturing = design_parameters.manufacturing
    for _, y, z in preload_axes:
        shaft = _x_cylinder(
            manufacturing.screw_nominal_diameter_mm / 2,
            clamp_front_x, _PRELOAD_SCREW_LENGTH_MM,
            axis_z_mm=z, axis_y_mm=y,
        )
        screw_head = _x_cylinder(
            manufacturing.screw_head_diameter_mm / 2,
            clamp_front_x + _PRELOAD_SCREW_LENGTH_MM,
            manufacturing.screw_head_height_mm,
            axis_z_mm=z, axis_y_mm=y,
        )
        preload_screws.append(
            _valid_single_solid(
                shaft.union(screw_head), 'preload screw reference'))
        nut = _x_hex_prism(
            _M3_NUT_ACROSS_FLATS_MM,
            nut_pocket_start_x + 0.2, _M3_NUT_THICKNESS_MM,
            y, z,
        ).cut(_x_cylinder(
            1.6, nut_pocket_start_x,
            _M3_NUT_POCKET_AXIAL_DEPTH_MM,
            axis_z_mm=z, axis_y_mm=y,
        ))
        preload_nuts.append(
            _valid_single_solid(nut, 'preload nut reference'))
    return (hub, collar, pins, tuple(preload_screws),
            tuple(preload_nuts))


def _place_crank_local(shape: cq.Workplane) -> cq.Workplane:
    return (shape.rotate((0, 0, 0), (0, 1, 0), -90)
            .translate((_CRANK_OUTER_FACE_X_MM, 0, _AXIS_HEIGHT_MM)))


def _local_y_cylinder(radius_mm: float, center_x_mm: float,
                      center_z_mm: float, length_mm: float = 40.0
                      ) -> cq.Workplane:
    return (cq.Workplane('XY').circle(radius_mm).extrude(length_mm)
            .rotate((0, 0, 0), (1, 0, 0), -90)
            .translate((center_x_mm, -length_mm / 2, center_z_mm)))


def _crank_drive_dimensions(
        design_parameters: DesignParameters,
) -> tuple[float, float, float, float, float]:
    end_wall = max(
        4.0, design_parameters.manufacturing.minimum_loaded_wall_mm)
    shaft_engagement = 7.0
    shaft_pocket_start = _CRANK_SOCKET_DEPTH_MM + end_wall
    crank_hub_length = shaft_pocket_start + shaft_engagement
    crank_pin_local_z = shaft_pocket_start + shaft_engagement / 2
    crank_pin_x = _CRANK_OUTER_FACE_X_MM - crank_pin_local_z
    return (end_wall, shaft_pocket_start, crank_hub_length,
            crank_pin_local_z, crank_pin_x)


def _build_crank(tool_parameters: WindingToolParameters,
                 design_parameters: DesignParameters,
                 ) -> tuple[cq.Workplane, cq.Workplane, cq.Workplane,
                            cq.Workplane, tuple[cq.Workplane, cq.Workplane],
                            cq.Workplane]:
    (_, shaft_pocket_start, crank_hub_length,
     crank_pin_local_z, _) = _crank_drive_dimensions(design_parameters)
    local_hub = (cq.Workplane('XY').circle(14.0)
                 .extrude(crank_hub_length))
    local_arm = (cq.Workplane('XY')
                 .box(60.0, 12.0, 8.0, centered=(False, True, False))
                 .translate((0, 0, 4.0)))
    local_crank = local_hub.union(local_arm)

    shaft_socket = (cq.Workplane('XY')
                    .circle(tool_parameters.shaft_diameter_mm / 2 + 0.1)
                    .extrude(7.1)
                    .translate((0, 0, shaft_pocket_start)))
    hex_diameter = (2 * tool_parameters.hex_socket_across_flats_mm
                    / sqrt(3))
    hex_socket = (cq.Workplane('XY').polygon(6, hex_diameter)
                  .extrude(_CRANK_SOCKET_DEPTH_MM + 0.1)
                  .translate((0, 0, -0.1)))
    crank_pin_hole = _local_y_cylinder(
        _PIN_HOLE_DIAMETER_MM / 2, 0, crank_pin_local_z)
    grip_pin_hole = (cq.Workplane('XY').center(52.0, 0).circle(3.3)
                     .extrude(10.0).translate((0, 0, 3.0)))
    local_crank = (local_crank.cut(shaft_socket).cut(hex_socket)
                   .cut(crank_pin_hole).cut(grip_pin_hole))
    crank = _valid_single_solid(_place_crank_local(local_crank), 'crank')

    local_gauge = (cq.Workplane('XY').polygon(6, hex_diameter)
                   .extrude(_CRANK_SOCKET_DEPTH_MM - 0.1)
                   .translate((0, 0, 0.05)))
    gauge = _place_crank_local(local_gauge)

    # Keep the complete handle stack on the outboard side of the crank arm.
    # This leaves the rotating grip clear of the right upright at every angle.
    local_grip = (cq.Workplane('XY').center(52.0, 0)
                  .circle(11.0).circle(3.3).extrude(24.0)
                  .translate((0, 0, -26.0)))
    local_grip_pin = (cq.Workplane('XY').center(52.0, 0).circle(3.0)
                      .extrude(41.0).translate((0, 0, -28.0)))
    local_washers = tuple(
        (cq.Workplane('XY').center(52.0, 0)
         .circle(7.0).circle(3.05).extrude(0.6)
         .translate((0, 0, start_z)))
        for start_z in (-26.8, -1.8)
    )
    local_crank_pin = _local_y_cylinder(
        2.0, 0, crank_pin_local_z, 30.0)
    return (
        crank,
        _place_crank_local(local_grip),
        _place_crank_local(local_grip_pin),
        _place_crank_local(local_crank_pin),
        (_place_crank_local(local_washers[0]),
         _place_crank_local(local_washers[1])),
        gauge,
    )


def _build_shaft(tool_parameters: WindingToolParameters,
                 crank_pin_x_mm: float,
                 shaft_end_x_mm: float) -> cq.Workplane:
    shaft = _x_cylinder(
        tool_parameters.shaft_diameter_mm / 2,
        -100.0, shaft_end_x_mm + 100.0)
    for x, length in ((-25.0, 28.0), (8.0, 24.0)):
        shaft = shaft.cut(_vertical_cylinder(
            _PIN_HOLE_DIAMETER_MM / 2,
            _AXIS_HEIGHT_MM - length / 2, length, x, 0,
        ))
    shaft = shaft.cut(_y_cylinder(
        _PIN_HOLE_DIAMETER_MM / 2, -15.0, 30.0,
        crank_pin_x_mm, _AXIS_HEIGHT_MM,
    ))
    return _valid_single_solid(shaft, 'shaft reference')


def _bearing_shape(design_parameters: DesignParameters,
                   center_x_mm: float) -> cq.Workplane:
    reference = build_608_reference(design_parameters)
    envelope = reference.parts['sealed_envelope']
    height = reference.nominal_dimensions_mm[2]
    return (envelope.rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((center_x_mm - height / 2, 0, _AXIS_HEIGHT_MM)))


@lru_cache(maxsize=8)
def build_winding_frame(
        tool_parameters: WindingToolParameters,
        design_parameters: DesignParameters = DEFAULT_PARAMETERS,
) -> WindingFrameParts:
    """Build the prototype-only horizontal frame and manual drive assembly."""
    validate_winding_tool_parameters(tool_parameters)
    bearing_reference = build_608_reference(design_parameters)
    bore, _, bearing_width = bearing_reference.nominal_dimensions_mm
    if (tool_parameters.shaft_diameter_mm != bore
            or design_parameters.shaft.nominal_diameter_mm != bore):
        raise ValueError('Winding shaft and design shaft must match the 608 bore')

    base, bench_fasteners, clamp_lands = _build_base()
    left_upright = _build_upright(
        _UPRIGHT_CENTRES_X_MM[0], -1, design_parameters)
    right_upright = _build_upright(
        _UPRIGHT_CENTRES_X_MM[1], 1, design_parameters)
    uprights = (left_upright, right_upright)

    seat_depth = design_parameters.bearings.radial_housing_seat_depth_mm
    bearing_offset = (_UPRIGHT_THICKNESS_MM / 2
                      - seat_depth + bearing_width / 2 + 0.1)
    bearing_centres = (
        _UPRIGHT_CENTRES_X_MM[0] + bearing_offset,
        _UPRIGHT_CENTRES_X_MM[1] - bearing_offset,
    )
    bearings = (
        _bearing_shape(design_parameters, bearing_centres[0]),
        _bearing_shape(design_parameters, bearing_centres[1]),
    )

    head = _place_head_horizontally(build_winding_head(
        tool_parameters, tool_parameters.reference_diameter_mm))
    (head_hub, head_collar, head_pins,
     preload_screws, preload_nuts) = _build_head_retainers(
         tool_parameters, head, design_parameters)
    (end_wall, shaft_pocket_start, _, _,
     crank_pin_x) = _crank_drive_dimensions(design_parameters)
    crank, grip, grip_pin, crank_pin, washers, hex_gauge = _build_crank(
        tool_parameters, design_parameters)
    shaft_end_x = _CRANK_OUTER_FACE_X_MM - shaft_pocket_start - 0.1
    shaft = _build_shaft(tool_parameters, crank_pin_x, shaft_end_x)

    upright_fasteners = tuple(
        _vertical_cylinder(
            2.0, -2.0,
            _BASE_THICKNESS_MM + _PART_GAP_MM + _UPRIGHT_FOOT_HEIGHT_MM + 4.0,
            x, y,
        )
        for x in _UPRIGHT_CENTRES_X_MM
        for y in (-45.0, 45.0)
    )
    printable_parts = {
        'base': base,
        'left_upright': left_upright,
        'right_upright': right_upright,
        'head_hub': head_hub,
        'head_retaining_collar': head_collar,
        'crank': crank,
    }
    metadata: dict[str, object] = {
        'coordinate_frame': 'X is the horizontal winding axis; base bottom is Z=0',
        'shaft_diameter_mm': tool_parameters.shaft_diameter_mm,
        'bearing_nominal_dimensions_mm': list(
            bearing_reference.nominal_dimensions_mm),
        'bearing_seat_diameter_mm': (
            design_parameters.bearings.radial_housing_seat_diameter_mm),
        'bearing_seat_depth_mm': seat_depth,
        'bearing_axis_positions_x_mm': list(bearing_centres),
        'drive_interfaces_coaxial': True,
        'hex_socket_across_flats_mm': (
            tool_parameters.hex_socket_across_flats_mm),
        'hex_socket_depth_mm': _CRANK_SOCKET_DEPTH_MM,
        'hex_socket_end_wall_mm': end_wall,
        'positive_head_retention': True,
        'head_retaining_pin_count': len(head_pins),
        'head_torque_pin_count': len(head.state.frame_drive_pin_centres_xy_mm),
        'preload_adjustment_screw_count': len(preload_screws),
        'preload_adjustment_travel_mm': 0.3,
        'preload_hardware': {
            'screw_designation': 'M3 x 10 mm socket-head cap screw',
            'screw_quantity': len(preload_screws),
            'screw_nominal_diameter_mm': (
                design_parameters.manufacturing.screw_nominal_diameter_mm),
            'screw_length_mm': _PRELOAD_SCREW_LENGTH_MM,
            'screw_head_diameter_mm': (
                design_parameters.manufacturing.screw_head_diameter_mm),
            'screw_head_height_mm': (
                design_parameters.manufacturing.screw_head_height_mm),
            'nut_standard': 'ISO 4032 M3',
            'nut_quantity': len(preload_nuts),
            'nut_across_flats_mm': _M3_NUT_ACROSS_FLATS_MM,
            'nut_thickness_mm': _M3_NUT_THICKNESS_MM,
            'nut_pocket_across_flats_mm': _M3_NUT_POCKET_ACROSS_FLATS_MM,
            'nut_pocket_axial_depth_mm': _M3_NUT_POCKET_AXIAL_DEPTH_MM,
            'nut_insertion': (
                'Radially through collar OD before screw installation'),
        },
        'upright_bolt_count': len(upright_fasteners),
        'bench_hole_count': len(bench_fasteners),
        'clamp_land_count': len(clamp_lands),
        'manual_crank_grip_rotates_freely': True,
        'powered_operation_validated': False,
    }
    return WindingFrameParts(
        base=base,
        uprights=uprights,
        head=head,
        head_hub=head_hub,
        head_retaining_collar=head_collar,
        crank=crank,
        bearings=bearings,
        shaft_reference=shaft,
        bench_fastener_references=bench_fasteners,
        upright_fastener_references=upright_fasteners,
        head_retaining_pin_references=head_pins,
        preload_screw_references=preload_screws,
        preload_nut_references=preload_nuts,
        crank_pin_reference=crank_pin,
        crank_grip_reference=grip,
        grip_pin_reference=grip_pin,
        grip_washer_references=washers,
        hex_socket_gauge_reference=hex_gauge,
        clamp_lands=clamp_lands,
        printable_parts=printable_parts,
        metadata=metadata,
    )
