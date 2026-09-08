"""Load-bearing base, standard and top stages in a common nominal blade frame.

The source blade frame spans z=0 to stage_height_mm with its +60-degree twist;
only its outer bottom edge is relieved for the axial locking motion. The upper
receiver is recessed into a local end-support region;
the next stage's male extends below zero into it. The support plate bridges
the phase difference structurally. Identical module transforms do not produce
a continuous aerodynamic surface across the seam. The base fuses the analytic
upper generator carrier; the removable top closure is owned by its own module.
"""

from dataclasses import dataclass
from math import isfinite

import cadquery as cq

from windwall.blade_profile import build_blade_stage
from windwall.drivers import build_joint_interface, joint_interface_height_mm
from windwall.generator import build_upper_magnet_carrier
from windwall.parameters import DesignParameters


@dataclass(frozen=True)
class RotorModuleModel:
    """Immutable metadata wrapper; shape is the one printable CadQuery solid."""

    shape: cq.Workplane
    shaft_clearance_radial_mm: float
    nut_pocket_across_flats_mm: float | None = None
    washer_seat_diameter_mm: float | None = None


def module_joint_depth_mm(parameters: DesignParameters) -> float:
    """Distance from the nominal seam to the receiver bottom in the lower stage."""
    return joint_interface_height_mm(parameters)


def _validate(p: DesignParameters) -> None:
    s, m, end = p.shaft, p.manufacturing, p.modules
    values = (s.nominal_diameter_mm, s.clearance_hole_diameter_mm,
              end.end_support_radius_mm, end.end_support_thickness_mm,
              end.base_shaft_flange_depth_mm, end.washer_seat_depth_mm,
              end.closure_screw_radius_mm, end.closure_pilot_depth_mm,
              m.washer_outer_diameter_mm)
    if any(not isfinite(value) or value <= 0 for value in values):
        raise ValueError('Module, shaft and clamping dimensions must be positive and finite')
    if not isfinite(end.joint_phase_deg):
        raise ValueError('Common joint phase must be finite')
    if (s.clearance_hole_diameter_mm-s.nominal_diameter_mm)/2 < 0.35:
        raise ValueError('Module shaft bore requires at least 0.35 mm radial clearance')
    if min(end.end_support_thickness_mm, end.base_shaft_flange_depth_mm) < m.minimum_loaded_wall_mm:
        raise ValueError('End supports and base flange must retain the loaded wall')
    if end.washer_seat_depth_mm > m.minimum_loaded_wall_mm:
        raise ValueError('Washer centering recess must stay shallow for exposed-nut access')
    if not 35 <= end.end_support_radius_mm < p.blade.rotor_radius_mm:
        raise ValueError('End support must bridge the joint structure and stay inside the blade radius')
    if p.rotor.stage_height_mm <= 2*module_joint_depth_mm(p)+2*end.end_support_thickness_mm:
        raise ValueError('Stage height must leave an active blade region between end fittings')
    if end.closure_screw_radius_mm <= m.washer_outer_diameter_mm/2 + m.minimum_loaded_wall_mm:
        raise ValueError('Closure screws must be outside the washer load path')
    if end.closure_screw_radius_mm + m.screw_pilot_diameter_mm/2 + m.minimum_loaded_wall_mm >= end.end_support_radius_mm:
        raise ValueError('Closure pilots must retain a loaded wall inside the support')
    if end.closure_pilot_depth_mm+m.minimum_loaded_wall_mm >= module_joint_depth_mm(p):
        raise ValueError('Closure pilots must retain a blind floor in the upper end region')


def _disc(radius: float, bottom: float, depth: float) -> cq.Workplane:
    return cq.Workplane('XY').circle(radius).extrude(depth).translate((0,0,bottom))


def _build(parameters: DesignParameters, kind: str) -> RotorModuleModel:
    _validate(parameters)
    p, end, m = parameters, parameters.modules, parameters.manufacturing
    height = p.rotor.stage_height_mm
    depth = module_joint_depth_mm(p)
    joint_z = height-depth
    joint = build_joint_interface(p)
    body = build_blade_stage(p)
    # The upper stage starts below its locked height and rises during locking.
    # Relieve the outer bottom edge for its lower insertion/early-travel poses.
    relief = p.bayonet.ramp_rise_mm+m.axial_clearance_mm
    edge = (cq.Workplane('XY').circle(p.blade.rotor_radius_mm+1)
            .circle(end.end_support_radius_mm).extrude(relief))
    body = body.cut(edge)
    body = body.union(_disc(end.end_support_radius_mm, 0, end.end_support_thickness_mm))
    if kind == 'base':
        # The annular flange joins the carrier's rear clamping face to the blade.
        body = body.union(_disc(p.bayonet.hub_outer_diameter_mm/2,
                                -end.base_shaft_flange_depth_mm, end.base_shaft_flange_depth_mm))
        body = body.union(build_upper_magnet_carrier(p))
    else:
        body = body.union(joint.male.rotate((0,0,0), (0,0,1), end.joint_phase_deg).translate((0,0,-depth)))
    if kind != 'top':
        # Remove the source hub/skin only inside the localized receiver envelope.
        # The floor connects the explicitly phased pads to the twisted blade.
        body = body.cut(_disc(end.end_support_radius_mm, joint_z, depth+1))
        body = body.union(_disc(end.end_support_radius_mm,
                                joint_z-end.end_support_thickness_mm, end.end_support_thickness_mm))
        body = body.union(joint.female.rotate((0,0,0), (0,0,1), end.joint_phase_deg).translate((0,0,joint_z)))
    else:
        washer_floor = height-end.washer_seat_depth_mm
        pad_bottom = height-end.closure_pilot_depth_mm-m.minimum_loaded_wall_mm
        hub_radius = max(p.bayonet.hub_outer_diameter_mm/2,
                         m.washer_outer_diameter_mm/2+m.radial_clearance_mm+m.minimum_loaded_wall_mm)
        # Carry reinforcement through the bridge root to avoid enclosed slivers
        # where the twisted skin meets the otherwise narrower source hub.
        hub_bottom = min(pad_bottom, washer_floor-m.minimum_loaded_wall_mm)
        body = body.union(_disc(hub_radius, hub_bottom, height-hub_bottom))
        # Opposite pads and a bridge carry closure screws independently of M8 load.
        pad_radius = m.screw_pilot_diameter_mm/2+m.minimum_loaded_wall_mm
        bridge = cq.Workplane('XY').box(2*end.closure_screw_radius_mm, 2*pad_radius,
                    height-pad_bottom, centered=(True,True,False)).translate((0,0,pad_bottom))
        body = body.union(bridge)
        for x in (-end.closure_screw_radius_mm,end.closure_screw_radius_mm):
            body = body.union(_disc(pad_radius, pad_bottom, height-pad_bottom).translate((x,0,0)))
            body = body.cut(_disc(m.screw_pilot_diameter_mm/2,
                            height-end.closure_pilot_depth_mm, end.closure_pilot_depth_mm+1).translate((x,0,0)))
        # The nut stays exposed above the washer. A buried hex would put the
        # washer above the nut and defeat its intended load-spreading function.
        body = body.cut(_disc(m.washer_outer_diameter_mm/2+m.radial_clearance_mm,
                         height-end.washer_seat_depth_mm, end.washer_seat_depth_mm+1))
    bottom = -max(depth,end.base_shaft_flange_depth_mm)-1
    body = body.cut(_disc(p.shaft.clearance_hole_diameter_mm/2, bottom, height-bottom+1)).clean()
    if not body.val().isValid() or len(body.val().Solids()) != 1:
        raise ValueError(f'{kind.capitalize()} module must be one valid connected solid')
    if kind != 'top':
        for axis in joint.screw_axes:
            access = axis.access.rotate((0,0,0), (0,0,1), end.joint_phase_deg).translate((0,0,joint_z))
            if body.intersect(access).val().Volume() >= 0.01:
                raise ValueError('Common joint phase blocks a radial screwdriver corridor through the blade')
    return RotorModuleModel(body, (p.shaft.clearance_hole_diameter_mm-p.shaft.nominal_diameter_mm)/2,
                            m.nut_pocket_across_flats_mm if kind == 'base' else None,
                            m.washer_outer_diameter_mm+2*m.radial_clearance_mm if kind == 'top' else None)


def build_base_module(parameters: DesignParameters) -> RotorModuleModel:
    """Base blade, upper receiver and fused down-facing magnet carrier/torque nut."""
    return _build(parameters, 'base')


def build_standard_module(parameters: DesignParameters) -> RotorModuleModel:
    """Shared blade, lower male/drivers and upper female/pockets with two retainers."""
    return _build(parameters, 'standard')


def build_top_module(parameters: DesignParameters) -> RotorModuleModel:
    """Lower male/drivers, washer-bearing hub for an exposed nut, and closure seats."""
    return _build(parameters, 'top')
