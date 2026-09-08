"""Analytic dual magnet carriers and conservative stationary clearance solids.

The base blade starts at Z=0; its upper carrier hangs below the shaft flange.
Magnet pockets face the stator, and one spacer crosses its central passage.
Reference solids reserve occupied volume without defining windings, magnets,
bearing procurement/retention, or electrical performance. All fits need coupons.
No mesh is imported here. Assembly building imports rotor_modules lazily to
allow that module to fuse the independent upper-carrier builder into its base.
"""

from dataclasses import dataclass, fields
from math import ceil, cos, hypot, isfinite, pi, sin, sqrt
from typing import TYPE_CHECKING

import cadquery as cq

from windwall.parameters import DesignParameters

if TYPE_CHECKING:
    from windwall.rotor_modules import RotorModuleModel


def _ring(outer_radius: float, inner_radius: float, bottom: float, height: float) -> cq.Workplane:
    return cq.Workplane('XY').circle(outer_radius).circle(inner_radius).extrude(height).translate((0,0,bottom))


def _hex(across_flats: float, bottom: float, height: float) -> cq.Workplane:
    return cq.Workplane('XY').polygon(6,2*across_flats/sqrt(3)).extrude(height).translate((0,0,bottom))


def _validate(p: DesignParameters) -> None:
    g, m, s = p.generator, p.manufacturing, p.shaft
    if any(not isfinite(getattr(g,f.name)) or getattr(g,f.name) <= 0 for f in fields(g)):
        raise ValueError('Generator dimensions, counts and air gaps must be positive and finite')
    for count in (g.magnet_pocket_count,g.rib_count):
        if type(count) is not int or count < 3:
            raise ValueError('Magnet-pocket and rib counts must be integers of at least three')
    if not all(isfinite(v) and v > 0 for v in (s.nominal_diameter_mm, s.clearance_hole_diameter_mm,
            m.minimum_loaded_wall_mm,m.nut_pocket_across_flats_mm,m.nut_pocket_depth_mm,
            m.washer_outer_diameter_mm,p.modules.base_shaft_flange_depth_mm)):
        raise ValueError('Generator shaft, flange and clamp dimensions must be positive and finite')
    wall = m.minimum_loaded_wall_mm
    if s.clearance_hole_diameter_mm <= s.nominal_diameter_mm:
        raise ValueError('Rotating carrier bore must clear the M8 shaft')
    pocket_radius = g.magnet_pocket_diameter_mm/2
    if g.carrier_diameter_mm/2-g.magnet_pitch_radius_mm-pocket_radius < wall-1e-8:
        raise ValueError('Magnet pockets must retain the loaded outer rim')
    if 2*g.magnet_pitch_radius_mm*sin(pi/g.magnet_pocket_count)-2*pocket_radius < wall:
        raise ValueError('Adjacent magnet pockets must retain a loaded ligament')
    if g.magnet_pitch_radius_mm-pocket_radius < g.carrier_hub_diameter_mm/2+wall:
        raise ValueError('Magnet pockets must clear the reinforced shaft hub')
    if (g.carrier_disc_thickness_mm-g.magnet_pocket_depth_mm < wall
            or g.carrier_height_mm-g.carrier_disc_thickness_mm < wall
            or g.rib_width_mm < wall):
        raise ValueError('Pocket floors and rear ribs must retain the loaded wall')
    if hypot(g.carrier_diameter_mm/2-wall,g.rib_width_mm/2) > g.carrier_diameter_mm/2:
        raise ValueError('Rear rib corners must stay inside the carrier diameter')
    if (g.carrier_height_mm-m.nut_pocket_depth_mm < wall
            or g.carrier_hub_diameter_mm/2-m.nut_pocket_across_flats_mm/sqrt(3) < wall
            or g.carrier_hub_diameter_mm < m.washer_outer_diameter_mm+2*wall):
        raise ValueError('Carrier hub must support the captive nut ceiling and washer load path')
    if not s.clearance_hole_diameter_mm < g.clamp_nut_across_flats_mm < m.nut_pocket_across_flats_mm:
        raise ValueError('Nominal M8 nut must surround the bore and fit its coupon-gated pocket')
    if not s.clearance_hole_diameter_mm < g.spacer_outer_diameter_mm < g.coil_former_bore_diameter_mm:
        raise ValueError('Central spacer must clear the shaft and stationary stator bore')
    if g.bearing_bore_diameter_mm < s.nominal_diameter_mm:
        raise ValueError('Provisional bearing envelope must clear the nominal shaft')
    if not g.bearing_bore_diameter_mm < g.bearing_outer_diameter_mm < g.bearing_seat_diameter_mm:
        raise ValueError('Provisional bearing must fit inside its measured seat envelope')
    if (g.bearing_support_diameter_mm-g.bearing_seat_diameter_mm)/2 < wall:
        raise ValueError('Stationary bearing support must retain its wall')
    if (g.base_diameter_mm-g.base_cavity_diameter_mm)/2 < wall or g.base_floor_mm < wall:
        raise ValueError('Stationary base must retain its wall and floor')
    if max(g.carrier_diameter_mm, g.bearing_support_diameter_mm) >= g.base_cavity_diameter_mm:
        raise ValueError('Stationary cup cavity must clear the complete rotating carrier')
    if not (g.coil_former_bore_diameter_mm < g.stator_cover_bore_diameter_mm
            < g.stator_cover_diameter_mm <= g.coil_former_diameter_mm <= g.base_diameter_mm):
        raise ValueError('Stationary stator and cover envelopes must nest radially')
    free_below_rotor = g.base_height_mm-g.lower_air_gap_mm-g.carrier_height_mm
    if free_below_rotor <= max(g.base_floor_mm,g.bearing_length_mm)+g.clamp_washer_thickness_mm+m.nut_pocket_depth_mm:
        raise ValueError('Base cavity must leave clearance below the lower clamp and bearing')
    if not 0 < g.coupon_diameter_step_mm < g.magnet_pocket_diameter_mm:
        raise ValueError('Coupon variation must leave a positive smallest pocket')


def _carrier(p: DesignParameters, captive_nut: bool) -> cq.Workplane:
    """Local pocket face Z=0; ribs and axial clamping face point toward +Z."""
    _validate(p)
    g, m = p.generator,p.manufacturing
    bore = p.shaft.clearance_hole_diameter_mm/2
    body = _ring(g.carrier_diameter_mm/2,bore,0,g.carrier_disc_thickness_mm)
    body = body.union(_ring(g.carrier_hub_diameter_mm/2,bore,0,g.carrier_height_mm))
    rib_start = g.carrier_hub_diameter_mm/2-1
    rib_end = g.carrier_diameter_mm/2-m.minimum_loaded_wall_mm
    for index in range(g.rib_count):
        rib = (cq.Workplane('XY').box(rib_end-rib_start,g.rib_width_mm,
                g.carrier_height_mm-g.carrier_disc_thickness_mm,centered=(False,True,False))
               .translate((rib_start,0,g.carrier_disc_thickness_mm))
               .rotate((0,0,0),(0,0,1),index*360/g.rib_count))
        body = body.union(rib)
    centers = [(g.magnet_pitch_radius_mm*cos(2*pi*i/g.magnet_pocket_count),
                g.magnet_pitch_radius_mm*sin(2*pi*i/g.magnet_pocket_count)) for i in range(g.magnet_pocket_count)]
    pockets = cq.Workplane('XY').pushPoints(centers).circle(g.magnet_pocket_diameter_mm/2).extrude(g.magnet_pocket_depth_mm)
    body = body.cut(pockets)
    if captive_nut:
        body = body.cut(_hex(m.nut_pocket_across_flats_mm,0,m.nut_pocket_depth_mm))
    body = body.clean()
    if not body.val().isValid() or len(body.val().Solids()) != 1:
        raise ValueError('Magnet carrier must be one valid connected solid')
    return body


def upper_magnet_face_z_mm(p: DesignParameters) -> float:
    _validate(p)
    return -p.modules.base_shaft_flange_depth_mm-p.generator.carrier_height_mm


def lower_magnet_face_z_mm(p: DesignParameters) -> float:
    g = p.generator
    return (upper_magnet_face_z_mm(p)-g.upper_air_gap_mm-g.coil_former_height_mm
            -g.stator_cover_height_mm-g.lower_air_gap_mm)


def build_upper_magnet_carrier(parameters: DesignParameters) -> cq.Workplane:
    """Down-facing carrier with an open-bottom captive M8 torque-nut pocket."""
    return _carrier(parameters,True).translate((0,0,upper_magnet_face_z_mm(parameters)))


def build_lower_magnet_rotor(parameters: DesignParameters) -> cq.Workplane:
    """Separate up-facing rotor; its rear hub is clamped by washer and M8 nut."""
    return _carrier(parameters,False).mirror('XY').translate((0,0,lower_magnet_face_z_mm(parameters)))


@dataclass(frozen=True)
class StationaryGeneratorReference:
    coil_former: cq.Workplane
    stator_cover: cq.Workplane
    base: cq.Workplane
    bearing: cq.Workplane

    @property
    def parts(self) -> dict[str,cq.Workplane]:
        return {name:getattr(self,name) for name in ('coil_former','stator_cover','base','bearing')}


def build_stationary_generator_reference(parameters: DesignParameters) -> StationaryGeneratorReference:
    """Conservative winding-zone annulus, separate cover, cup and provisional sleeve.

    The cover is placed above the full 12 mm former, reserving 14 mm total.
    Filled coil volume is a clearance keep-out, not winding/potting construction.
    The bearing support is bored through: axial bearing retention is unresolved.
    """
    p,g = parameters,parameters.generator
    _validate(p)
    cover_bottom = upper_magnet_face_z_mm(p)-g.upper_air_gap_mm-g.stator_cover_height_mm
    coil_bottom = cover_bottom-g.coil_former_height_mm
    base_bottom = coil_bottom-g.base_height_mm
    coil = _ring(g.coil_former_diameter_mm/2,g.coil_former_bore_diameter_mm/2,coil_bottom,g.coil_former_height_mm)
    cover = _ring(g.stator_cover_diameter_mm/2,g.stator_cover_bore_diameter_mm/2,cover_bottom,g.stator_cover_height_mm)
    base = _ring(g.base_diameter_mm/2,g.bearing_seat_diameter_mm/2,base_bottom,g.base_floor_mm)
    base = base.union(_ring(g.base_diameter_mm/2,g.base_cavity_diameter_mm/2,
                          base_bottom+g.base_floor_mm,g.base_height_mm-g.base_floor_mm))
    base = base.union(_ring(g.bearing_support_diameter_mm/2,g.bearing_seat_diameter_mm/2,
                          base_bottom,g.bearing_length_mm)).clean()
    bearing = _ring(g.bearing_outer_diameter_mm/2,g.bearing_bore_diameter_mm/2,base_bottom,g.bearing_length_mm)
    return StationaryGeneratorReference(coil,cover,base,bearing)


@dataclass(frozen=True)
class GeneratorAssembly:
    base_module: 'RotorModuleModel'
    upper_carrier: cq.Workplane
    lower_rotor: cq.Workplane
    stationary: StationaryGeneratorReference
    shaft: cq.Workplane
    spacer: cq.Workplane
    clamp_hardware: dict[str,cq.Workplane]
    rotating_axis_diameter_mm: float

    @property
    def magnet_rotor_count(self) -> int:
        return len(self.upper_carrier.val().Solids())+len(self.lower_rotor.val().Solids())

    @property
    def upper_rotor_integrated_with_base(self) -> bool:
        return (len(self.base_module.shape.val().Solids()) == 1
                and self.upper_carrier.cut(self.base_module.shape).val().Volume() < 0.01)

    def upper_air_gap_mm(self) -> float:
        return self.upper_carrier.val().BoundingBox().zmin-self.stationary.stator_cover.val().BoundingBox().zmax

    def lower_air_gap_mm(self) -> float:
        return self.stationary.coil_former.val().BoundingBox().zmin-self.lower_rotor.val().BoundingBox().zmax

    def rotor_stator_intersection_volume_mm3(self) -> float:
        return sum(rotor.intersect(stator).val().Volume()
                   for rotor in (self.base_module.shape,self.lower_rotor)
                   for stator in self.stationary.parts.values())


def build_generator_assembly(parameters: DesignParameters) -> GeneratorAssembly:
    """Build a base-stage assembly with nominal rod, clamp and spacer envelopes.

    The rod extends 15 mm above this base stage for inspection. Full-stack rod
    length belongs to the seven-stage assembly. Nut heights reserve the complete
    coupon pocket depth; actual hardware and protruding magnets need measurement.
    """
    from windwall.rotor_modules import build_base_module

    p,g,m = parameters,parameters.generator,parameters.manufacturing
    _validate(p)
    upper_face,lower_face = upper_magnet_face_z_mm(p),lower_magnet_face_z_mm(p)
    stationary = build_stationary_generator_reference(p)
    bottom = stationary.base.val().BoundingBox().zmin-5
    shaft = cq.Workplane('XY').circle(p.shaft.nominal_diameter_mm/2).extrude(p.rotor.stage_height_mm+15-bottom).translate((0,0,bottom))
    spacer = _ring(g.spacer_outer_diameter_mm/2,p.shaft.clearance_hole_diameter_mm/2,
                   lower_face,upper_face-lower_face)
    rear = lower_face-g.carrier_height_mm
    washer_bottom = rear-g.clamp_washer_thickness_mm
    hardware = {'upper_nut':_hex(g.clamp_nut_across_flats_mm,upper_face,m.nut_pocket_depth_mm),
                'lower_nut':_hex(g.clamp_nut_across_flats_mm,washer_bottom-m.nut_pocket_depth_mm,m.nut_pocket_depth_mm),
                'lower_washer':_ring(m.washer_outer_diameter_mm/2,p.shaft.clearance_hole_diameter_mm/2,washer_bottom,g.clamp_washer_thickness_mm)}
    for name in ('upper_nut','lower_nut'):
        hardware[name] = hardware[name].cut(shaft)
    return GeneratorAssembly(build_base_module(p),build_upper_magnet_carrier(p),build_lower_magnet_rotor(p),
                             stationary,shaft,spacer,hardware,p.shaft.nominal_diameter_mm)


def build_magnet_pocket_coupon(parameters: DesignParameters) -> cq.Workplane:
    """Open-top blind pockets, increasing diameter left-to-right; never auto-print."""
    _validate(parameters)
    g,m = parameters.generator,parameters.manufacturing
    spacing = ceil(g.magnet_pocket_diameter_mm+g.coupon_diameter_step_mm+2*m.minimum_loaded_wall_mm)
    depth = g.magnet_pocket_depth_mm+m.minimum_loaded_wall_mm
    body = cq.Workplane('XY').box(3*spacing,spacing,depth,centered=(True,True,False))
    for index in (-1,0,1):
        hole = (cq.Workplane('XY').center(index*spacing,0)
                .circle((g.magnet_pocket_diameter_mm+index*g.coupon_diameter_step_mm)/2)
                .extrude(g.magnet_pocket_depth_mm).translate((0,0,m.minimum_loaded_wall_mm)))
        body = body.cut(hole)
    return body.clean()
