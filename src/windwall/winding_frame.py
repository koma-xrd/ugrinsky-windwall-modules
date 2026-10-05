"""Horizontal manual winder on the unchanged payoff base and canonical 51105.

The bearing carries axial load; a long printed clearance pilot guides radial
load. Wheel torque uses its existing polygon socket. The crank plugs into a
standard across-flats hex and lifts out without a latch. Physical PLA fit and
powered operation remain unvalidated. All returned occurrences use bench Z up.
"""
from dataclasses import dataclass
from math import cos, radians

import cadquery as cq

from windwall.parameters import DesignParameters
from windwall.winding_tool_parameters import WindingToolParameters
from windwall.wire_payoff import build_wire_payoff


@dataclass(frozen=True)
class WindingFrameParts:
    base: cq.Workplane
    lower_washer: cq.Workplane
    bearing: cq.Workplane
    upper_washer: cq.Workplane
    hub: cq.Workplane
    crank: cq.Workplane
    grip: cq.Workplane
    metadata: dict


def _cylinder(radius, bottom, height):
    return cq.Workplane('XY').circle(radius).extrude(height).translate((0, 0, bottom))


def _hex_across_flats(width, bottom, height):
    return (cq.Workplane('XY').polygon(6, width / cos(radians(30)))
            .extrude(height).translate((0, 0, bottom)))


def build_winding_frame(tool_parameters: WindingToolParameters,
                        design_parameters: DesignParameters) -> WindingFrameParts:
    """Build a gravity-seated horizontal hub, straight-plug crank and loose grip."""
    payoff = build_wire_payoff(tool_parameters, design_parameters)
    bearing_top = payoff.upper_washer.val().BoundingBox().zmax
    wheel_bottom = 33.0
    if bearing_top >= wheel_bottom:
        raise ValueError('The canonical bearing stack must fit below the wheel stop')
    pilot_radius = design_parameters.bearings.thrust_rotating_pilot_diameter_mm / 2
    hub_top = wheel_bottom + 9.0
    socket_bottom = hub_top - 10.0
    # The 0.5 mm gap to the blind floor ensures the washer, not the pilot tip,
    # carries weight. The wheel shoulder is above every stationary base boss.
    hub = _cylinder(pilot_radius, 1.5, bearing_top - 1.5)
    hub = hub.union(_cylinder(18, bearing_top, wheel_bottom - bearing_top))
    wheel_drive = (cq.Workplane('XY').polygon(6, 14).extrude(hub_top - wheel_bottom)
                   .translate((0, 0, wheel_bottom)))
    hub = hub.union(wheel_drive).cut(_hex_across_flats(6.45, socket_bottom, 11))
    # Chamfer only the six internal mouth edges, never the wheel-drive stop.
    mouth_edges = [edge for edge in hub.edges().vals()
                   if abs(edge.Center().z - hub_top) < 1e-6
                   and edge.Center().x ** 2 + edge.Center().y ** 2 < 20]
    hub = hub.newObject(mouth_edges).chamfer(.25).clean()

    # Keep the arm above the tallest shoe and wound bundle at every setting.
    arm_bottom = wheel_bottom + 33
    lever = 70.0
    crank = _hex_across_flats(6.35, socket_bottom, hub_top - socket_bottom)
    crank = crank.union(_cylinder(6, hub_top, arm_bottom - hub_top))
    arm = (cq.Workplane('XY').box(lever, 14, 5, centered=False)
           .translate((0, -7, arm_bottom)))
    crank = crank.union(arm).union(_cylinder(10, arm_bottom, 5))
    crank = crank.union(_cylinder(7, arm_bottom, 5).translate((lever, 0, 0)))
    crank = crank.union(_cylinder(3, arm_bottom + 5, 20).translate((lever, 0, 0))).clean()
    grip = _cylinder(8, arm_bottom + 5, 24)
    grip = grip.cut(_cylinder(3.2, arm_bottom + 4, 22)).translate((lever, 0, 0)).clean()

    rotations = {'base': (0, 0, 0), 'hub': (0, 90, 0),
                 'crank': (0, 90, 0), 'grip': (0, 0, 0)}
    for name, shape in dict(base=payoff.base, hub=hub, crank=crank, grip=grip).items():
        value = shape.val()
        if not value.isValid() or len(value.Solids()) != 1 or value.Volume() <= 0:
            raise ValueError(f'{name} must be one valid positive-volume solid')
        printable = shape
        for axis, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), rotations[name]):
            printable = printable.rotate((0, 0, 0), axis, angle)
        bounds = printable.val().BoundingBox()
        if max(bounds.xlen, bounds.ylen) > min(220, tool_parameters.print_bed_mm):
            raise ValueError(f'{name} exceeds the documented print-bed envelope')

    metadata = {
        'wheel_bottom_z_mm': wheel_bottom,
        'axis_height_mm': wheel_bottom,
        'head_rotation_x_deg': 0,
        'head_translation_mm': (0, 0, wheel_bottom),
        'bearing_nominal_dimensions_mm': tuple(payoff.metadata['bearing_nominal_dimensions_mm']),
        'bearing_designation': '51105',
        'guide_bottom_z_mm': 1.5,
        'wheel_to_base_clearance_mm': 25.0,
        'drive_socket_bottom_z_mm': socket_bottom,
        'drive_socket_across_flats_mm': 6.45,
        'crank_across_flats_mm': 6.35,
        'grip_axis_xy_mm': (lever, 0),
        'print_rotations_deg': rotations,
        'purchased_components': {'51105': 1},
        'physical_validation_required': True,
        'powered_operation_validated': False,
        'service_sequence': ('lift crank and grip straight upward',
                             'lift taped coil over seated shoes',
                             'lift wheel and hub for bearing service'),
    }
    return WindingFrameParts(payoff.base, payoff.lower_washer, payoff.bearing,
                             payoff.upper_washer, hub, crank, grip, metadata)
