"""Passive wire-spool payoff turntable and serviceable felt drag brake.

The 51105 load path is split into its real motion owners: the housing washer
stays in the base, the shaft washer turns with the removable platter, and the
rolling envelope remains bearing-internal. The model is a manually adjusted,
passive supply only; it does not couple or synchronize with the winding frame.
"""

from dataclasses import dataclass
from functools import lru_cache
from math import isfinite, sqrt
from numbers import Real

import cadquery as cq

from windwall.bearings import BearingReference, build_51105_reference
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters
from windwall.winding_tool_parameters import (
    WindingToolParameters,
    validate_winding_tool_parameters,
)


_BASE_SIZE_MM = 190.0
_BASE_THICKNESS_MM = 8.0
_FOOT_HEIGHT_MM = 24.0
_BEARING_PEDESTAL_DIAMETER_MM = 62.0
_PLATTER_THICKNESS_MM = 4.0
_PLATTER_BASE_CLEARANCE_MM = 2.0
_BRAKE_X_MM = 55.0
_BRAKE_TOWER_DIAMETER_MM = 24.0
_ADJUSTER_STEM_DIAMETER_MM = 12.0
_ADJUSTER_FLANGE_DIAMETER_MM = 16.0
_ADJUSTER_HEIGHT_MM = 4.8
_ADJUSTER_FLANGE_HEIGHT_MM = 2.8
_ADJUSTER_TRAVEL_MM = 1.0
_FELT_DIAMETER_MM = 14.0
_FELT_UNCOMPRESSED_THICKNESS_MM = 2.0
_HARD_STOP_CLEARANCE_MM = 1.0
_BENCH_HOLE_DIAMETER_MM = 5.4
_BRAKE_SCREW_CLEARANCE_DIAMETER_MM = 3.4
_M3_NUT_ACROSS_FLATS_MM = 5.5
_M3_NUT_THICKNESS_MM = 2.4
_M3_NUT_POCKET_ACROSS_FLATS_MM = 5.8
_M3_NUT_POCKET_HEIGHT_MM = 2.6
_SPRING_FREE_LENGTH_MM = 9.2


@dataclass(frozen=True)
class WirePayoffParts:
    """Placed printable members and purchased brake/bearing references."""

    base: cq.Workplane
    platter: cq.Workplane
    adjuster: cq.Workplane
    spring: cq.Workplane
    washer: cq.Workplane
    screw: cq.Workplane
    nut: cq.Workplane
    felt: cq.Workplane
    bearing: BearingReference
    bench_fastener_references: tuple[cq.Workplane, ...]
    clamp_lands: tuple[cq.Workplane, cq.Workplane]
    rotating_parts: dict[str, cq.Workplane]
    stationary_parts: dict[str, cq.Workplane]
    bearing_internal_parts: dict[str, cq.Workplane]
    brake_parts: dict[str, cq.Workplane]
    printable_parts: dict[str, cq.Workplane]
    metadata: dict[str, object]


def _vertical_cylinder(
        radius_mm: float,
        bottom_z_mm: float,
        height_mm: float,
        x_mm: float = 0.0,
        y_mm: float = 0.0,
) -> cq.Workplane:
    return (cq.Workplane('XY').center(x_mm, y_mm).circle(radius_mm)
            .extrude(height_mm).translate((0, 0, bottom_z_mm)))


def _ring(
        outer_radius_mm: float,
        inner_radius_mm: float,
        bottom_z_mm: float,
        height_mm: float,
        x_mm: float = 0.0,
        y_mm: float = 0.0,
) -> cq.Workplane:
    return (cq.Workplane('XY').center(x_mm, y_mm)
            .circle(outer_radius_mm).circle(inner_radius_mm)
            .extrude(height_mm).translate((0, 0, bottom_z_mm)))


def _hex_prism(
        across_flats_mm: float,
        bottom_z_mm: float,
        height_mm: float,
        x_mm: float,
        y_mm: float = 0.0,
) -> cq.Workplane:
    circumscribed_diameter = 2 * across_flats_mm / sqrt(3)
    return (cq.Workplane('XY').center(x_mm, y_mm)
            .polygon(6, circumscribed_diameter)
            .extrude(height_mm).translate((0, 0, bottom_z_mm)))


def _valid_single_solid(shape: cq.Workplane, name: str) -> cq.Workplane:
    cleaned = shape.clean()
    value = cleaned.val()
    volume = value.Volume()
    if (not value.isValid() or len(value.Solids()) != 1
            or not isfinite(volume) or volume <= 0):
        raise ValueError(f'{name} must be one valid connected solid')
    return cleaned


def _validate_brake_setting(brake_setting: float) -> float:
    if (isinstance(brake_setting, bool)
            or not isinstance(brake_setting, Real)
            or not isfinite(brake_setting)
            or not 0.0 <= brake_setting <= 1.0):
        raise ValueError('brake setting must be finite and between 0.0 and 1.0')
    return float(brake_setting)


def _build_base(
        design_parameters: DesignParameters,
        bearing_floor_z_mm: float,
        platter_underside_z_mm: float,
) -> tuple[cq.Workplane, tuple[cq.Workplane, ...],
           tuple[cq.Workplane, cq.Workplane]]:
    bearing_parameters = design_parameters.bearings
    seat_top_z = (bearing_floor_z_mm
                  + bearing_parameters.thrust_housing_seat_depth_mm)
    tower_top_z = platter_underside_z_mm - _PLATTER_BASE_CLEARANCE_MM
    stem_above_flange_mm = (_ADJUSTER_HEIGHT_MM
                            - _ADJUSTER_FLANGE_HEIGHT_MM)
    stop_z = (platter_underside_z_mm - _HARD_STOP_CLEARANCE_MM
              - stem_above_flange_mm)

    plate = cq.Workplane('XY').box(
        _BASE_SIZE_MM,
        _BASE_SIZE_MM,
        _BASE_THICKNESS_MM,
        centered=(True, True, False),
    )
    # Open space between four integral feet admits a short hex key from +X.
    for x in (-80.0, 80.0):
        for y in (-65.0, 65.0):
            foot = (cq.Workplane('XY').box(30, 40, _FOOT_HEIGHT_MM,
                                          centered=(True, True, False))
                    .translate((x, y, -_FOOT_HEIGHT_MM)))
            plate = plate.union(foot)
    bearing_pedestal = _vertical_cylinder(
        _BEARING_PEDESTAL_DIAMETER_MM / 2,
        _BASE_THICKNESS_MM,
        seat_top_z - _BASE_THICKNESS_MM,
    )
    brake_tower = _vertical_cylinder(
        _BRAKE_TOWER_DIAMETER_MM / 2,
        _BASE_THICKNESS_MM,
        tower_top_z - _BASE_THICKNESS_MM,
        _BRAKE_X_MM,
    )
    base = plate.union(bearing_pedestal).union(brake_tower)

    bearing_seat = _vertical_cylinder(
        bearing_parameters.thrust_housing_seat_diameter_mm / 2,
        bearing_floor_z_mm,
        bearing_parameters.thrust_housing_seat_depth_mm + 0.1,
    )
    base = base.cut(bearing_seat)

    lower_brake_cavity = _vertical_cylinder(
        _ADJUSTER_FLANGE_DIAMETER_MM / 2 + 0.2,
        _BASE_THICKNESS_MM + 1.0,
        stop_z - (_BASE_THICKNESS_MM + 1.0),
        _BRAKE_X_MM,
    )
    upper_brake_guide = _vertical_cylinder(
        _ADJUSTER_STEM_DIAMETER_MM / 2 + 0.2,
        stop_z,
        tower_top_z - stop_z + 0.1,
        _BRAKE_X_MM,
    )
    service_bottom_z = (platter_underside_z_mm
                        - _FELT_UNCOMPRESSED_THICKNESS_MM
                        - _ADJUSTER_HEIGHT_MM)
    adjuster_service_slot = (cq.Workplane('XY').box(
        25.0,
        _ADJUSTER_FLANGE_DIAMETER_MM + 0.4,
        _ADJUSTER_HEIGHT_MM + 0.2,
        centered=(False, True, False),
    ).translate((_BRAKE_X_MM, 0, service_bottom_z - 0.1)))
    screw_passage = _vertical_cylinder(
        _BRAKE_SCREW_CLEARANCE_DIAMETER_MM / 2,
        -0.1,
        platter_underside_z_mm + 0.2,
        _BRAKE_X_MM,
    )
    screw_head_recess = _vertical_cylinder(
        design_parameters.manufacturing.screw_head_diameter_mm / 2 + 0.1,
        -0.1,
        design_parameters.manufacturing.screw_head_height_mm + 0.2,
        _BRAKE_X_MM,
    )
    base = (base.cut(lower_brake_cavity).cut(upper_brake_guide)
            .cut(adjuster_service_slot).cut(screw_passage)
            .cut(screw_head_recess))

    bench_fasteners = tuple(
        _vertical_cylinder(2.5, -_FOOT_HEIGHT_MM - 1.0,
                           _FOOT_HEIGHT_MM + _BASE_THICKNESS_MM + 2.0, x, y)
        for x in (-72.0, 72.0)
        for y in (-72.0, 72.0)
    )
    for x in (-72.0, 72.0):
        for y in (-72.0, 72.0):
            base = base.cut(_vertical_cylinder(
                _BENCH_HOLE_DIAMETER_MM / 2,
                -_FOOT_HEIGHT_MM - 1.0,
                _FOOT_HEIGHT_MM + _BASE_THICKNESS_MM + 2.0,
                x,
                y,
            ))

    clamp_lands = tuple(
        cq.Workplane('XY').box(
            13.0, 60.0, 2.0, centered=(True, True, False))
        .translate((x, 0, _BASE_THICKNESS_MM - 2.0))
        for x in (-88.5, 88.5)
    )
    return (
        _valid_single_solid(base, 'payoff base'),
        bench_fasteners,
        (clamp_lands[0], clamp_lands[1]),
    )


def _build_platter(
        tool_parameters: WindingToolParameters,
        design_parameters: DesignParameters,
        bearing_floor_z_mm: float,
        platter_underside_z_mm: float,
) -> cq.Workplane:
    bearing_parameters = design_parameters.bearings
    platter_top_z = platter_underside_z_mm + _PLATTER_THICKNESS_MM
    rotating_pilot_bottom_z = bearing_floor_z_mm + 0.2

    disc = (cq.Workplane('XY')
            .circle(tool_parameters.platter_diameter_mm / 2)
            .extrude(_PLATTER_THICKNESS_MM)
            .edges().fillet(1.0)
            .translate((0, 0, platter_underside_z_mm)))
    bearing_support = _vertical_cylinder(
        18.0,
        bearing_floor_z_mm + bearing_parameters.thrust_height_mm,
        _PLATTER_BASE_CLEARANCE_MM,
    )
    rotating_pilot = _vertical_cylinder(
        bearing_parameters.thrust_rotating_pilot_diameter_mm / 2,
        rotating_pilot_bottom_z,
        platter_top_z - rotating_pilot_bottom_z,
    )

    pilot_radius = tool_parameters.spool_pilot_diameter_mm / 2
    chamfer_height = min(1.0, tool_parameters.spool_pilot_height_mm / 4)
    straight_height = tool_parameters.spool_pilot_height_mm - chamfer_height
    spool_pilot = (cq.Workplane('XY').circle(pilot_radius)
                   .extrude(straight_height + 0.1)
                   .translate((0, 0, platter_top_z - 0.1)))
    lead_in = (cq.Workplane('XY').circle(pilot_radius)
               .workplane(offset=chamfer_height)
               .circle(max(0.5, pilot_radius - chamfer_height))
               .loft(combine=True)
               .faces('>Z').edges().fillet(chamfer_height * 0.4)
               .translate((0, 0, platter_top_z + straight_height)))
    platter = (disc.union(bearing_support).union(rotating_pilot)
               .union(spool_pilot).union(lead_in))
    return _valid_single_solid(platter, 'payoff platter')


def _place_bearing(
        design_parameters: DesignParameters,
        bearing_floor_z_mm: float,
) -> BearingReference:
    reference = build_51105_reference(design_parameters)
    return BearingReference(
        reference.designation,
        reference.nominal_dimensions_mm,
        {name: shape.translate((0, 0, bearing_floor_z_mm))
         for name, shape in reference.parts.items()},
    )


def _build_brake(
        compression_mm: float,
        platter_underside_z_mm: float,
        design_parameters: DesignParameters,
) -> dict[str, cq.Workplane]:
    """Place the screw-controlled, spring-loaded brake in its assembled state.

    The screw head stays seated in the base while its captured nut moves the
    adjuster axially. Removing the screw releases both radial service routes.
    """
    adjuster_top_z = (platter_underside_z_mm
                      - _FELT_UNCOMPRESSED_THICKNESS_MM
                      + compression_mm)
    adjuster_bottom_z = adjuster_top_z - _ADJUSTER_HEIGHT_MM
    adjuster = _ring(
        _ADJUSTER_STEM_DIAMETER_MM / 2,
        _BRAKE_SCREW_CLEARANCE_DIAMETER_MM / 2,
        adjuster_bottom_z,
        _ADJUSTER_HEIGHT_MM,
        _BRAKE_X_MM,
    ).union(_ring(
        _ADJUSTER_FLANGE_DIAMETER_MM / 2,
        _BRAKE_SCREW_CLEARANCE_DIAMETER_MM / 2,
        adjuster_bottom_z,
        _ADJUSTER_FLANGE_HEIGHT_MM,
        _BRAKE_X_MM,
    ))
    # Two straight flange edges slide between the existing service-slot walls.
    # Their overlap restrains rotation at both endpoints without closing the
    # radial loading route when the screw has been removed.
    adjuster = adjuster.union(cq.Workplane('XY').box(
        8, 16, _ADJUSTER_FLANGE_HEIGHT_MM, centered=(False, True, False))
        .translate((_BRAKE_X_MM + 4, 0, adjuster_bottom_z)))
    nut_pocket_bottom_z = adjuster_bottom_z + 0.1
    nut_pocket = _hex_prism(
        _M3_NUT_POCKET_ACROSS_FLATS_MM,
        nut_pocket_bottom_z,
        _M3_NUT_POCKET_HEIGHT_MM,
        _BRAKE_X_MM,
    )
    nut_loading_slot = (cq.Workplane('XY').box(
        12.2,
        6.8,
        _M3_NUT_POCKET_HEIGHT_MM,
        centered=(False, True, False),
    ).translate((_BRAKE_X_MM, 0, nut_pocket_bottom_z)))
    adjuster = adjuster.cut(nut_pocket).cut(nut_loading_slot)
    adjuster = _valid_single_solid(adjuster, 'brake adjuster')

    nut = _hex_prism(
        _M3_NUT_ACROSS_FLATS_MM,
        adjuster_bottom_z + 0.2,
        _M3_NUT_THICKNESS_MM,
        _BRAKE_X_MM,
    ).cut(_vertical_cylinder(
        1.6,
        adjuster_bottom_z + 0.1,
        _M3_NUT_POCKET_HEIGHT_MM,
        _BRAKE_X_MM,
    ))
    nut = _valid_single_solid(nut, 'captive brake-adjuster nut')

    felt = _valid_single_solid(_ring(
        _FELT_DIAMETER_MM / 2,
        _BRAKE_SCREW_CLEARANCE_DIAMETER_MM / 2,
        adjuster_top_z,
        _FELT_UNCOMPRESSED_THICKNESS_MM - compression_mm,
        _BRAKE_X_MM,
    ), 'felt brake pad')

    washer_bottom_z = adjuster_bottom_z - 0.6
    washer = _valid_single_solid(_ring(
        5.0,
        _BRAKE_SCREW_CLEARANCE_DIAMETER_MM / 2,
        washer_bottom_z,
        0.6,
        _BRAKE_X_MM,
    ), 'brake washer')
    spring_bottom_z = _BASE_THICKNESS_MM + 1.0
    spring = _valid_single_solid(_ring(
        4.0,
        2.0,
        spring_bottom_z,
        washer_bottom_z - spring_bottom_z,
        _BRAKE_X_MM,
    ), 'brake spring envelope')

    manufacturing = design_parameters.manufacturing
    screw_head_top_z = manufacturing.screw_head_height_mm + 0.1
    screw_shaft_bottom_z = screw_head_top_z - 0.1
    screw_shaft = _vertical_cylinder(
        manufacturing.screw_nominal_diameter_mm / 2,
        screw_shaft_bottom_z,
        (platter_underside_z_mm - _HARD_STOP_CLEARANCE_MM
         - screw_shaft_bottom_z),
        _BRAKE_X_MM,
    )
    screw_head = _vertical_cylinder(
        manufacturing.screw_head_diameter_mm / 2,
        0.1,
        manufacturing.screw_head_height_mm,
        _BRAKE_X_MM,
    )
    screw_head = screw_head.cut(_hex_prism(2.5, 0.0, 1.8, _BRAKE_X_MM))
    screw = _valid_single_solid(
        screw_head.union(screw_shaft), 'brake screw reference')
    return {
        'adjuster': adjuster,
        'spring': spring,
        'washer': washer,
        'screw': screw,
        'nut': nut,
        'felt': felt,
    }


def build_wire_payoff(
        tool_parameters: WindingToolParameters,
        design_parameters: DesignParameters = DEFAULT_PARAMETERS,
        brake_setting: float = 0.0,
) -> WirePayoffParts:
    """Build the independent payoff and map normalized setting to felt drag."""
    validate_winding_tool_parameters(tool_parameters)
    setting = _validate_brake_setting(brake_setting)
    return _build_wire_payoff_cached(tool_parameters, design_parameters, setting)


@lru_cache(maxsize=16)
def _build_wire_payoff_cached(tool_parameters, design_parameters, setting):
    bearing_floor_z = (_BASE_THICKNESS_MM
                       + design_parameters.manufacturing.minimum_loaded_wall_mm)
    bearing = _place_bearing(design_parameters, bearing_floor_z)
    platter_underside_z = (bearing_floor_z
                            + bearing.nominal_dimensions_mm[2]
                            + _PLATTER_BASE_CLEARANCE_MM)
    if (tool_parameters.spool_pilot_diameter_mm
            >= design_parameters.bearings.thrust_rotating_pilot_diameter_mm):
        raise ValueError('Spool pilot must remain inside the 51105 rotating pilot')

    base, bench_fasteners, clamp_lands = _build_base(
        design_parameters, bearing_floor_z, platter_underside_z)
    platter = _build_platter(
        tool_parameters, design_parameters, bearing_floor_z,
        platter_underside_z)
    compression_mm = setting * _ADJUSTER_TRAVEL_MM
    brake = _build_brake(
        compression_mm, platter_underside_z, design_parameters)

    rotating_parts = {
        'platter': platter,
        'shaft_washer': bearing.parts['shaft_washer'],
    }
    stationary_parts = {
        'base': base,
        'housing_washer': bearing.parts['housing_washer'],
        **brake,
    }
    bearing_internal_parts = {
        'rolling_envelope': bearing.parts['rolling_envelope'],
    }
    printable_parts = {
        'base': base,
        'platter': platter,
        'adjuster': brake['adjuster'],
    }
    metadata: dict[str, object] = {
        'platter_diameter_mm': tool_parameters.platter_diameter_mm,
        'spool_pilot_mm': [
            tool_parameters.spool_pilot_diameter_mm,
            tool_parameters.spool_pilot_height_mm,
        ],
        'spool_pilot_has_lead_in_chamfer': True,
        'bearing_nominal_dimensions_mm': list(bearing.nominal_dimensions_mm),
        'bearing_housing_seat_diameter_mm': (
            design_parameters.bearings.thrust_housing_seat_diameter_mm),
        'bearing_housing_seat_depth_mm': (
            design_parameters.bearings.thrust_housing_seat_depth_mm),
        'bearing_rotating_pilot_diameter_mm': (
            design_parameters.bearings.thrust_rotating_pilot_diameter_mm),
        'bearing_physical_fit_verified': False,
        'platter_removable_without_disturbing_seat': True,
        'brake_setting': setting,
        'felt_compression_mm': compression_mm,
        'felt_replaceable': True,
        'hard_stop_clearance_mm': _HARD_STOP_CLEARANCE_MM,
        'normal_adjustment_can_lock_platter': False,
        'spring_preload_remaining_mm': round(
            _SPRING_FREE_LENGTH_MM
            - brake['spring'].val().BoundingBox().zlen,
            4,
        ),
        'spring_lower_reaction': 'printed base cavity floor',
        'screw_nut_engagement_mm': _M3_NUT_THICKNESS_MM,
        'adjuster_retention': 'M3 screw and captive ISO 4032 M3 nut',
        'adjuster_service_setting': 0.0,
        'adjuster_service_direction': '+X after screw removal',
        'adjuster_anti_rotation': 'two flange flats guided by service-slot walls',
        'base_foot_height_mm': _FOOT_HEIGHT_MM,
        'brake_tool_access': 'short 2.5 mm hex key from +X; 60 degree stroke below base',
        'brake_load_path': [
            'base spring seat',
            'spring',
            'washer',
            'adjuster',
            'felt',
            'platter',
        ],
        'brake_adjustment_path': [
            'base screw-head seat',
            'screw',
            'captive nut',
            'adjuster',
        ],
        'bench_hole_count': len(bench_fasteners),
        'clamp_land_count': len(clamp_lands),
        'mechanically_synchronized_with_winder': False,
        'powered_operation_validated': False,
    }
    return WirePayoffParts(
        base=base,
        platter=platter,
        adjuster=brake['adjuster'],
        spring=brake['spring'],
        washer=brake['washer'],
        screw=brake['screw'],
        nut=brake['nut'],
        felt=brake['felt'],
        bearing=bearing,
        bench_fastener_references=bench_fasteners,
        clamp_lands=clamp_lands,
        rotating_parts=rotating_parts,
        stationary_parts=stationary_parts,
        bearing_internal_parts=bearing_internal_parts,
        brake_parts=brake,
        printable_parts=printable_parts,
        metadata=metadata,
    )
