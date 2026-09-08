"""One removable blade-tip disc with an independent, raised M8 hardware cover.

The local frame is the top module's frame. Its flat underside seats at the
blade tips and existing screw pads. A central cavity keeps the nut/washer/rod
clear, so the closure screws stiffen the blade ends without taking M8 preload.
No thread, sealing, screw fit or material strength is certified by this solid.
"""

from dataclasses import fields
from math import isfinite, sqrt

import cadquery as cq

from windwall.parameters import DesignParameters


def top_clamp_levels_mm(p: DesignParameters) -> tuple[float, float, float]:
    """Local washer bottom, nut bottom and shaft tip; nut height is an envelope."""
    washer = p.rotor.stage_height_mm-p.modules.washer_seat_depth_mm
    nut = washer+p.generator.clamp_washer_thickness_mm
    tip = nut+p.manufacturing.nut_pocket_depth_mm+p.closure.rod_projection_mm
    return washer,nut,tip


def build_top_closure(parameters: DesignParameters) -> cq.Workplane:
    """Disc with two M3 clearance holes and a blind central nut/rod cavity."""
    p,c,m = parameters,parameters.closure,parameters.manufacturing
    if any(not isfinite(getattr(c,f.name)) or getattr(c,f.name) <= 0 for f in fields(c)):
        raise ValueError('Closure dimensions, rod projections and explosion lift must be positive and finite')
    if min(c.plate_thickness_mm,c.roof_thickness_mm) < m.minimum_loaded_wall_mm:
        raise ValueError('Closure plate and roof must retain the loaded wall')
    engagement = m.screw_length_mm-c.plate_thickness_mm
    if not m.minimum_loaded_wall_mm <= engagement <= p.modules.closure_pilot_depth_mm-m.axial_clearance_mm:
        raise ValueError('Closure screw must engage the pilot without bottoming in its blind floor')
    clearance = p.drivers.screw_clearance_diameter_mm
    if (not all(isfinite(v) and v > 0 for v in (m.screw_head_diameter_mm,m.screw_head_height_mm))
            or not m.screw_nominal_diameter_mm < clearance < m.screw_head_diameter_mm
            or m.screw_head_diameter_mm > p.drivers.screwdriver_diameter_mm):
        raise ValueError('Screw head must bear outside its clearance hole and fit inside the tool corridor')
    cavity = max(m.washer_outer_diameter_mm/2,
                 p.generator.clamp_nut_across_flats_mm/sqrt(3),
                 p.shaft.nominal_diameter_mm/2)+m.radial_clearance_mm
    outside = cavity+m.minimum_loaded_wall_mm
    if outside+m.screw_head_diameter_mm/2 >= p.modules.closure_screw_radius_mm:
        raise ValueError('Central cover must clear the closure fastener heads')
    if p.modules.closure_screw_radius_mm+clearance/2+m.minimum_loaded_wall_mm >= p.blade.rotor_radius_mm:
        raise ValueError('Closure pilots must retain material inside the disc')
    bottom = p.rotor.stage_height_mm
    roof_bottom = max(bottom+c.plate_thickness_mm,
                      top_clamp_levels_mm(p)[2]+m.axial_clearance_mm)
    body = cq.Workplane('XY').circle(p.blade.rotor_radius_mm).extrude(c.plate_thickness_mm)
    body = body.union(cq.Workplane('XY').circle(outside).extrude(roof_bottom+c.roof_thickness_mm-bottom))
    body = body.cut(cq.Workplane('XY').circle(cavity).extrude(roof_bottom-bottom))
    for x in (-p.modules.closure_screw_radius_mm,p.modules.closure_screw_radius_mm):
        body = body.cut(cq.Workplane('XY').center(x,0).circle(clearance/2).extrude(c.plate_thickness_mm+1))
    body = body.translate((0,0,bottom)).clean()
    if not body.val().isValid() or len(body.val().Solids()) != 1:
        raise ValueError('Top closure must be one connected valid solid')
    return body
