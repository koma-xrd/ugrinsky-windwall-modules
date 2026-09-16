"""Independent, manually fed upright wire-roll turntable.

Three printed members surround the canonical, separately owned 51105 members.
The washer faces carry the roll; clearance-fit spindle journals center it. Two
removable plug detents retain the unloaded assembly with axial freedom. Neither
the bearing reference nor the PLA snap geometry certifies physical fit or force.
"""

from dataclasses import dataclass
from math import isfinite

import cadquery as cq

from windwall.bearings import build_51105_reference
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters
from windwall.winding_tool_parameters import (
    WindingToolParameters,
    validate_winding_tool_parameters,
)


_BASE_SIZE_MM = 190.0
_BASE_HEIGHT_MM = 8.0
_PLATTER_THICKNESS_MM = 4.0
_DRIVE_WIDTH_MM = 8.0
_DRIVE_HEIGHT_MM = 11.0
_PLUG_CLEARANCE_MM = 0.2


@dataclass(frozen=True)
class WirePayoffParts:
    """Assembled solids; bearing members remain purchased, separate shapes."""

    base: cq.Workplane
    spindle: cq.Workplane
    lower_washer: cq.Workplane
    bearing: cq.Workplane
    upper_washer: cq.Workplane
    platter: cq.Workplane
    metadata: dict[str, object]


def _cylinder(radius, bottom, height):
    return cq.Workplane('XY').circle(radius).extrude(height).translate((0, 0, bottom))


def _box(width, depth, height, x=0.0, y=0.0, bottom=0.0):
    return (cq.Workplane('XY').box(width, depth, height, centered=(True, True, False))
            .translate((x, y, bottom)))


def _single_solid(shape, name):
    cleaned = shape.clean()
    value = cleaned.val()
    if (not value.isValid() or len(value.Solids()) != 1
            or not isfinite(value.Volume()) or value.Volume() <= 0):
        raise ValueError(f'{name} must be one valid positive-volume solid')
    return cleaned


def _detent(root_x, outer_x, bottom, height, half_width):
    """Symmetric lead-in/lead-out ramps permit straight tool-free withdrawal."""
    return (cq.Workplane('XZ').polyline([
        (root_x, bottom), (outer_x, bottom + height * 0.45),
        (outer_x, bottom + height * 0.55), (root_x, bottom + height),
    ]).close().extrude(half_width, both=True))


def _build_base(bearing_parameters, lower_washer_height):
    pilot_radius = bearing_parameters.thrust_rotating_pilot_diameter_mm / 2
    seat_radius = bearing_parameters.thrust_housing_seat_diameter_mm / 2
    body = _box(_BASE_SIZE_MM, _BASE_SIZE_MM, _BASE_HEIGHT_MM)
    rim = _cylinder(seat_radius + 4, _BASE_HEIGHT_MM, lower_washer_height)
    body = body.union(rim).cut(_cylinder(
        seat_radius, _BASE_HEIGHT_MM, lower_washer_height + 1))
    # A blind bore keeps the bench-facing surface continuous. The annular
    # internal relief admits the rotating detents without touching their tips.
    body = body.cut(_cylinder(pilot_radius + _PLUG_CLEARANCE_MM, 1, 10))
    body = body.cut(_cylinder(pilot_radius + 0.8, 2, 3))
    # Opposing finger recesses expose the lower washer edge from above.
    for sign in (-1, 1):
        body = body.cut(_box(12, 10, lower_washer_height + 1,
                             x=sign * (seat_radius + 3), bottom=_BASE_HEIGHT_MM))
    return _single_solid(body, 'payoff base')


def _build_spindle(pilot_radius, bearing_top):
    spindle = _cylinder(pilot_radius, 1.5, bearing_top - 1.5)
    spindle = spindle.union(_box(_DRIVE_WIDTH_MM, _DRIVE_WIDTH_MM,
                                 _DRIVE_HEIGHT_MM, bottom=bearing_top))
    for sign in (-1, 1):
        # Long, thin outer tongues terminate below the upper washer. Rounded
        # relief ends reduce the stress concentration at their attached roots.
        relief = _box(0.8, 6, bearing_top - 4.5,
                      x=sign * (pilot_radius - 1.6), bottom=0)
        spindle = spindle.cut(relief.edges('|Y').fillet(0.3))
        for y in (-3.3, 3.3):
            spindle = spindle.cut(_box(4, 0.6, bearing_top - 4,
                x=sign * pilot_radius, y=y, bottom=0))
        detent = _detent(pilot_radius - 0.6, pilot_radius + 0.4, 2.8, 2, 2)
        spindle = spindle.union(detent if sign == 1 else detent.mirror('YZ'))

        # The keyed upper plug hangs from the platter detents. Its cavity
        # arrests downward travel before the journal reaches the base floor.
        relief = _box(0.8, 4, _DRIVE_HEIGHT_MM,
                      x=sign * 2.1, bottom=bearing_top + 2)
        spindle = spindle.cut(relief.edges('|Y').fillet(0.3))
        for y in (-2.3, 2.3):
            spindle = spindle.cut(_box(4, 0.6, _DRIVE_HEIGHT_MM,
                x=sign * 4.5, y=y, bottom=bearing_top + 2))
        detent = _detent(3.5, 4.45, bearing_top + 6.9, 2, 1.8)
        spindle = spindle.union(detent if sign == 1 else detent.mirror('YZ'))
    return _single_solid(spindle, 'payoff spindle')


def _build_platter(tool_parameters, bearing_top):
    disc = _cylinder(tool_parameters.platter_diameter_mm / 2,
                     bearing_top, _PLATTER_THICKNESS_MM)
    pilot_bottom = bearing_top + _PLATTER_THICKNESS_MM
    pilot = _cylinder(tool_parameters.spool_pilot_diameter_mm / 2,
                      pilot_bottom, tool_parameters.spool_pilot_height_mm)
    pilot = pilot.edges('>Z').chamfer(1)
    platter = disc.union(pilot)
    socket_width = _DRIVE_WIDTH_MM + 2 * _PLUG_CLEARANCE_MM
    platter = platter.cut(_box(socket_width, socket_width,
        _DRIVE_HEIGHT_MM + 0.4, bottom=bearing_top))
    for sign in (-1, 1):
        platter = platter.cut(_box(0.8, 4.6, 1.8,
            x=sign * 4.4, bottom=bearing_top + 7.3))
    return _single_solid(platter, 'payoff platter')


def build_wire_payoff(
        tool_parameters: WindingToolParameters,
        design_parameters: DesignParameters = DEFAULT_PARAMETERS,
) -> WirePayoffParts:
    """Build a fresh screwless turntable with a weight-supported bearing stack."""
    validate_winding_tool_parameters(tool_parameters)
    reference = build_51105_reference(design_parameters)
    if tool_parameters.print_bed_mm < _BASE_SIZE_MM:
        raise ValueError('The payoff base requires a 190 mm print-bed envelope')
    if (tool_parameters.spool_pilot_diameter_mm < 15
            or tool_parameters.spool_pilot_height_mm < 10):
        raise ValueError('The spool pilot must enclose the removable keyed socket')
    if tool_parameters.platter_diameter_mm > _BASE_SIZE_MM - 20:
        raise ValueError('The payoff footprint must extend beyond the platter')
    bearing_parameters = design_parameters.bearings
    bearing_top = _BASE_HEIGHT_MM + reference.nominal_dimensions_mm[2]
    pilot_radius = bearing_parameters.thrust_rotating_pilot_diameter_mm / 2
    # The snap roots and blind base groove assume the canonical 51105 stack.
    # Reject incompatible alternate bearing geometry before constructing it.
    if bearing_top < 18 or pilot_radius < 11:
        raise ValueError('51105 spindle requires an adequate journal and snap span')
    lower = reference.parts['housing_washer'].translate((0, 0, _BASE_HEIGHT_MM))
    rolling = reference.parts['rolling_envelope'].translate((0, 0, _BASE_HEIGHT_MM))
    upper = reference.parts['shaft_washer'].translate((0, 0, _BASE_HEIGHT_MM))
    base = _build_base(bearing_parameters, lower.val().BoundingBox().zlen)
    spindle = _build_spindle(pilot_radius, bearing_top)
    platter = _build_platter(tool_parameters, bearing_top)
    metadata = {
        'pilot': {'diameter_mm': tool_parameters.spool_pilot_diameter_mm,
                  'height_mm': tool_parameters.spool_pilot_height_mm},
        'owned_members': {
            'base': 'stationary', 'spindle': 'rotating',
            'lower_washer': 'stationary', 'bearing': 'bearing_internal',
            'upper_washer': 'rotating', 'platter': 'rotating',
        },
        'bearing_designation': reference.designation,
        'bearing_nominal_dimensions_mm': list(reference.nominal_dimensions_mm),
        'axial_load_path': ['platter underside', 'upper_washer', 'bearing',
                            'lower_washer', 'base floor', 'bench'],
        'radial_load_path': ['platter square socket', 'spindle journal',
                             'clearance-fit base bore and 51105 bores'],
        'washer_ownership': 'Weight-loaded faces seat the lower washer on the base '
                            'and carry the upper washer with the platter.',
        'retention': 'Two ramped, relieved PLA tongues at each spindle end; '
                     'lower detents turn freely in a continuous annular groove.',
        'axial_free_travel_mm': 0.15,
        'service_sequence': [
            'Lift the platter vertically; upper plug tongues cam inward.',
            'Grip the exposed square spindle and pull upward; lower tongues cam inward.',
            'Lift upper washer, rolling member, and lower washer in order.',
            'Use the two open finger recesses to grip the lower washer edge.',
            'Reassemble in reverse; place the upright roll over the chamfered pilot.',
        ],
        'snap_service_model': 'CAD checks use 0.4 mm upper and 0.6 mm lower '
                              'inward tongue envelopes; elastic force and life unvalidated.',
        'print_orientation': {
            'base': 'Flat bench face at Z=0 on bed; inspect the short internal groove bridge.',
            'spindle': 'Axis horizontal, rotate 90 degrees about Y; support the core, '
                       'keep tongue slots clear and smooth the journal.',
            'platter': 'Flat bearing-contact underside on bed, integral pilot upward.',
        },
        'clamp_lands_mm': [[-85, 0, 12, 50], [85, 0, 12, 50]],
        'stability_assumptions': {
            'feed_direction': 'horizontal, any azimuth',
            'feed_force_N': 1.0,
            'feed_height_mm': bearing_top + _PLATTER_THICKNESS_MM
                              + tool_parameters.spool_pilot_height_mm,
            'PLA_density_kg_per_mm3': 1.24e-6,
            'printed_volume_fraction': 0.35,
            'roll_mass_kg': 0.0,
            'minimum_overturning_margin': 2.0,
            'note': 'Quasi-static geometric estimate; clamp for taller rolls, '
                    'greater feed force, lower print mass, or sliding.',
        },
        'physical_fit_verified': False,
        'force_validated': False,
        'powered_operation_validated': False,
    }
    return WirePayoffParts(base, spindle, lower, rolling, upper, platter, metadata)
