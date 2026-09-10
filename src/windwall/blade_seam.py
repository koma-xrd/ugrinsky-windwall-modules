"""Two shallow blade-wall seam pairs, independent of central bayonet fittings.

The shared bottom-section frame has z=0 at the aerodynamic seam. Module
builders rotate this frame by the blade twist at upper ends. Grooves remain
inside the original wall through their full depth; the bayonet owns locking.
"""

from dataclasses import dataclass
from math import isfinite

import cadquery as cq

from windwall.blade_profile import build_blade_section_faces
from windwall.parameters import DesignParameters


@dataclass(frozen=True)
class BladeSeamInterface:
    tongues: cq.Workplane
    groove_clearance: cq.Workplane
    tongue_count: int
    groove_count: int
    transverse_clearance_mm: float


def build_blade_seam(parameters: DesignParameters) -> BladeSeamInterface:
    """Inset one connected outer section per blade and extrude matching pairs.

    The overlap of inset sections through the groove depth reserves skin despite
    the blade twist. The largest connected region outside the joint is the
    outer small arc of each wall; the inner return remains unkeyed. Rounded
    wire offsets provide the same normal clearance in every transverse direction.
    """
    p, fit = parameters, parameters.blade_seam
    dimensions = (fit.tongue_height_mm, fit.groove_depth_mm,
                  fit.transverse_clearance_mm, fit.skin_thickness_mm)
    if any(not isfinite(value) or value <= 0 for value in dimensions):
        raise ValueError('Blade seam dimensions must be positive and finite')
    if fit.groove_depth_mm <= fit.tongue_height_mm:
        raise ValueError('Blade groove depth must exceed tongue height')
    if not .1 <= fit.transverse_clearance_mm <= .3:
        raise ValueError('PLA blade seam transverse clearance must be 0.1 to 0.3 mm')
    if 2*(fit.skin_thickness_mm+fit.transverse_clearance_mm) >= p.blade.wall_thickness_mm:
        raise ValueError('Blade skin and clearance must leave a positive tongue wall')
    if not isfinite(p.bayonet.seating_headroom_mm) or p.bayonet.seating_headroom_mm <= fit.tongue_height_mm:
        raise ValueError('Bayonet seating headroom must be finite and clear the blade tongues')
    keepout = p.bayonet.hub_outer_diameter_mm/2+p.bayonet.lug_radial_depth_mm+2*p.manufacturing.minimum_loaded_wall_mm
    annulus = cq.Face.makeFromWires(cq.Workplane('XY').circle(p.blade.rotor_radius_mm).val(),
                                  [cq.Workplane('XY').circle(keepout).val()])
    sections = [build_blade_section_faces(p, z) for z in (0, fit.groove_depth_mm/2, fit.groove_depth_mm)]
    tongues, grooves = [], []
    for blade_index in range(2):
        region = annulus
        for pair in sections:
            face = pair[blade_index]
            planar = face.translate((0,0,-face.Center().z))
            outer_face = max(planar.intersect(annulus).Faces(), key=lambda item: item.Area())
            outline = outer_face.outerWire()
            inset = cq.Face.makeFromWires(outline.offset2D(-fit.skin_thickness_mm)[0])
            region = region.intersect(inset)
        if not region.Faces():
            raise ValueError('Blade groove must retain a connected wall section')
        outer = max(region.Faces(), key=lambda face: face.Area()).outerWire()
        tongue_wire = outer.offset2D(-fit.transverse_clearance_mm)[0]
        groove_wire = tongue_wire.offset2D(fit.transverse_clearance_mm)[0]
        tongues.append(cq.Solid.extrudeLinear(tongue_wire, [], cq.Vector(0,0,fit.tongue_height_mm)))
        grooves.append(cq.Solid.extrudeLinear(groove_wire, [], cq.Vector(0,0,fit.groove_depth_mm)))
    tongue_shape = cq.Compound.makeCompound(tongues)
    groove_shape = cq.Compound.makeCompound(grooves)
    if any(not shape.isValid() or len(shape.Solids()) != 2 for shape in (tongue_shape, groove_shape)):
        raise ValueError('Blade seam must contain exactly two valid tongue and groove regions')
    return BladeSeamInterface(cq.Workplane(obj=tongue_shape), cq.Workplane(obj=groove_shape),
                              2, 2, fit.transverse_clearance_mm)
