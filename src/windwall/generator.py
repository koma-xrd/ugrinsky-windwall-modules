"""Enclosed dual-rotor generator in the Base blade's Z=0 coordinate frame.

The cup, winding cassette and cover are stationary. The M8 rod, nut-driven
carriers and 51105 shaft washer rotate. A central Base pilot transfers axial
load to the independent bearing washers and cover. Magnet and rolling-element
solids reserve nominal envelopes; they do not certify electrical performance,
rolling contact, strength, retention or physical fit. No mesh is imported.
"""

from dataclasses import dataclass
from math import ceil, cos, hypot, isfinite, pi, sin, sqrt
from typing import TYPE_CHECKING

import cadquery as cq

from windwall.bearings import BearingReference, build_51105_reference
from windwall.generator_housing import GeneratorHousingParts, HousingDimensions, build_generator_housing
from windwall.parameters import DesignParameters

if TYPE_CHECKING:
    from windwall.rotor_modules import RotorModuleModel


def _ring(outer_radius: float, inner_radius: float, bottom: float, height: float) -> cq.Workplane:
    return cq.Workplane('XY').circle(outer_radius).circle(inner_radius).extrude(height).translate((0,0,bottom))


def _hex(across_flats: float, bottom: float, height: float) -> cq.Workplane:
    return cq.Workplane('XY').polygon(6,2*across_flats/sqrt(3)).extrude(height).translate((0,0,bottom))


def _validate(p: DesignParameters) -> None:
    g, m, s = p.generator, p.manufacturing, p.shaft
    dimensions = (g.carrier_diameter_mm, g.carrier_height_mm, g.carrier_disc_thickness_mm,
                  g.carrier_hub_diameter_mm, g.rib_count, g.rib_width_mm, g.magnet_pocket_count,
                  g.magnet_pitch_radius_mm, g.magnet_pocket_diameter_mm, g.magnet_pocket_depth_mm,
                  g.coupon_diameter_step_mm, g.coil_former_diameter_mm, g.coil_former_height_mm,
                  g.upper_air_gap_mm, g.lower_air_gap_mm, g.spacer_outer_diameter_mm,
                  g.clamp_nut_across_flats_mm, g.clamp_washer_thickness_mm,
                  p.closure.shaft_bottom_projection_mm)
    if any(not isfinite(value) or value <= 0 for value in dimensions):
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
            or g.carrier_hub_diameter_mm/2-m.nut_pocket_across_flats_mm/sqrt(3) < wall):
        raise ValueError('Carrier hub must support the captive nut ceiling and torque load')
    if not s.clearance_hole_diameter_mm < g.clamp_nut_across_flats_mm < m.nut_pocket_across_flats_mm:
        raise ValueError('Nominal M8 nut must surround the bore and fit its coupon-gated pocket')
    if not s.clearance_hole_diameter_mm < g.spacer_outer_diameter_mm < g.clamp_nut_across_flats_mm:
        raise ValueError('Central spacer must clear the shaft and fit the upper nut access')
    d = HousingDimensions()
    if g.carrier_diameter_mm >= 2*d.cavity_radius_mm:
        raise ValueError('Housing cavity must clear both rotating carriers')
    if g.upper_air_gap_mm <= d.cover_clearance_mm+d.diaphragm_mm or g.lower_air_gap_mm <= 1:
        raise ValueError('Magnetic gaps must also clear the cover diaphragm and cassette floor')
    bottom_clearance = (d.cassette_bottom_mm+1-g.lower_air_gap_mm-g.carrier_height_mm
                        -p.closure.shaft_bottom_projection_mm-d.floor_mm)
    if bottom_clearance <= 0:
        raise ValueError('Lower rotor, clamp and rod must remain above the closed housing floor')
    b = p.bearings
    if not (s.clearance_hole_diameter_mm < b.thrust_rotating_pilot_diameter_mm < b.thrust_bore_diameter_mm
            < b.thrust_outer_diameter_mm < b.thrust_housing_seat_diameter_mm):
        raise ValueError('51105 pilot, bore, outer envelope and housing seat must nest')
    if b.thrust_rotating_pilot_diameter_mm/2-m.nut_pocket_across_flats_mm/sqrt(3) < wall:
        raise ValueError('51105 pilot must retain a loaded wall around the M8 hex access')
    if b.thrust_housing_seat_depth_mm < b.thrust_height_mm:
        raise ValueError('51105 seat must contain the complete bearing height')
    if not 0 < g.coupon_diameter_step_mm < g.magnet_pocket_diameter_mm:
        raise ValueError('Coupon variation must leave a positive smallest pocket')


def _carrier(p: DesignParameters, radial_ribs: bool = True) -> cq.Workplane:
    """Local pocket face Z=0; ribs and axial clamping face point toward +Z."""
    _validate(p)
    g, m = p.generator,p.manufacturing
    bore = p.shaft.clearance_hole_diameter_mm/2
    body = _ring(g.carrier_diameter_mm/2,bore,0,g.carrier_disc_thickness_mm)
    body = body.union(_ring(g.carrier_hub_diameter_mm/2,bore,0,g.carrier_height_mm))
    rib_start = g.carrier_hub_diameter_mm/2-1
    rib_end = g.carrier_diameter_mm/2-m.minimum_loaded_wall_mm
    if radial_ribs:
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
    body = body.clean()
    if not body.val().isValid() or len(body.val().Solids()) != 1:
        raise ValueError('Magnet carrier must be one valid connected solid')
    return body


def upper_magnet_face_z_mm(p: DesignParameters) -> float:
    _validate(p)
    return -p.modules.base_shaft_flange_depth_mm-p.generator.carrier_height_mm


def lower_magnet_face_z_mm(p: DesignParameters) -> float:
    g = p.generator
    return upper_magnet_face_z_mm(p)-g.upper_air_gap_mm-(g.coil_former_height_mm-1)-g.lower_air_gap_mm


def base_bearing_interface(p: DesignParameters) -> dict[str, float]:
    """51105 elevations and boss clearance in the Base blade's local frame.

    HousingDimensions owns the diaphragm stack. The shoulder bears on the
    shaft washer while its outside clears the cover's taller retaining rim.
    """
    d, b = HousingDimensions(), p.bearings
    face = upper_magnet_face_z_mm(p)
    floor = face-p.generator.upper_air_gap_mm+d.cover_clearance_mm+d.diaphragm_mm
    shoulder = floor+b.thrust_height_mm
    shoulder_top = max(0, shoulder+p.manufacturing.minimum_loaded_wall_mm)
    return {'bearing_floor_z_mm': floor, 'shoulder_z_mm': shoulder,
            'shoulder_top_z_mm': shoulder_top,
            'nut_bottom_z_mm': shoulder_top-p.manufacturing.minimum_loaded_wall_mm-p.manufacturing.nut_pocket_depth_mm,
            'boss_clearance_radius_mm': b.thrust_housing_seat_diameter_mm/2+3+d.radial_clearance_mm,
            'boss_clearance_top_z_mm': floor+b.thrust_housing_seat_depth_mm+p.manufacturing.axial_clearance_mm,
            'pilot_bottom_z_mm': face}


def build_upper_magnet_carrier(parameters: DesignParameters) -> cq.Workplane:
    """Down-facing annular carrier; Base blade walls connect it around the boss."""
    p = parameters
    face = upper_magnet_face_z_mm(p)
    clearance = _ring(base_bearing_interface(p)['boss_clearance_radius_mm'],
                      p.shaft.clearance_hole_diameter_mm/2, face, p.generator.carrier_height_mm+1)
    return _carrier(p,radial_ribs=False).translate((0,0,face)).cut(clearance).clean()


def build_lower_magnet_rotor(parameters: DesignParameters) -> cq.Workplane:
    """Separate up-facing rotor with a rear-open captive M8 torque-nut pocket."""
    p = parameters
    face = lower_magnet_face_z_mm(p)
    body = _carrier(p).mirror('XY').translate((0,0,face))
    rear = face-p.generator.carrier_height_mm
    return body.cut(_hex(p.manufacturing.nut_pocket_across_flats_mm,
                         rear,p.manufacturing.nut_pocket_depth_mm)).clean()


@dataclass(frozen=True)
class GeneratorAssembly:
    """Placed solids with explicit motion ownership; housing_parts stays cup-local."""

    base_module: 'RotorModuleModel'
    upper_carrier: cq.Workplane
    lower_rotor: cq.Workplane
    housing_parts: GeneratorHousingParts
    housing_offset_z_mm: float
    stationary_parts: dict[str,cq.Workplane]
    bearings: dict[str,BearingReference]
    magnets: dict[str,cq.Workplane]
    shaft: cq.Workplane
    spacer: cq.Workplane
    clamp_hardware: dict[str,cq.Workplane]
    rotating_axis_diameter_mm: float
    lower_rotor_nut_pocket_across_flats_mm: float

    @property
    def housing(self) -> cq.Workplane:
        return self.stationary_parts['housing']

    @property
    def coil_cassette(self) -> cq.Workplane:
        return self.stationary_parts['coil_cassette']

    @property
    def cover(self) -> cq.Workplane:
        return self.stationary_parts['cover']

    @property
    def winding_volume(self) -> cq.Workplane:
        return self.stationary_parts['winding_volume']

    @property
    def rotating_parts(self) -> dict[str,cq.Workplane]:
        return {'base': self.base_module.shape, 'lower_magnet_rotor': self.lower_rotor,
                'shaft': self.shaft, 'spacer': self.spacer, **self.clamp_hardware,
                'upper_magnets': self.magnets['upper'], 'lower_magnets': self.magnets['lower'],
                '51105_shaft_washer': self.bearings['51105'].parts['shaft_washer']}

    @property
    def bearing_parts(self) -> dict[str,cq.Workplane]:
        """Rolling envelope has its own kinematics; neither shaft-fixed nor housing-fixed."""
        return {'51105_rolling_envelope': self.bearings['51105'].parts['rolling_envelope']}

    @property
    def magnet_rotor_count(self) -> int:
        return len(self.upper_carrier.val().Solids())+len(self.lower_rotor.val().Solids())

    @property
    def upper_rotor_integrated_with_base(self) -> bool:
        retained = self.upper_carrier.intersect(self.base_module.shape).val().Volume()
        return len(self.base_module.shape.val().Solids()) == 1 and retained > self.upper_carrier.val().Volume()*0.65

    def upper_air_gap_mm(self) -> float:
        return self.air_gap_report()['upper_air_gap_mm']

    def lower_air_gap_mm(self) -> float:
        return self.air_gap_report()['lower_air_gap_mm']

    def air_gap_report(self) -> dict:
        upper = self.magnets['upper'].val().BoundingBox().zmin
        lower = self.magnets['lower'].val().BoundingBox().zmax
        coil = self.winding_volume.val().BoundingBox()
        return {'upper_air_gap_mm': upper-coil.zmax, 'lower_air_gap_mm': coil.zmin-lower,
                'upper_magnet_face_z_mm': upper, 'lower_magnet_face_z_mm': lower,
                'coil_active_bottom_z_mm': coil.zmin, 'coil_active_top_z_mm': coil.zmax,
                'basis': 'Flush nominal magnet-envelope faces to active winding-envelope faces',
                'physical_magnet_dimensions_verified': False}

    def collision_report(self, rotating_parts: dict[str,cq.Workplane] | None = None) -> dict:
        """Every moving/stationary pair, without blanket bearing exclusions.

        Intended bearing support contacts are measured separately at zero
        distance; their penetration volumes still count as collisions.
        """
        moving = self.rotating_parts if rotating_parts is None else rotating_parts
        pairs = {f'{name}/{other}': intersection_volume(shape, stationary)
                 for name, shape in moving.items()
                 for other, stationary in self.stationary_parts.items()}
        bearing = self.bearings['51105'].parts
        contacts = {}
        for name, first, second in (
                ('cover/51105_housing_washer', self.cover, bearing['housing_washer']),
                ('base/51105_shaft_washer', moving['base'], bearing['shaft_washer']),
                ('51105_housing_washer/51105_rolling_envelope', bearing['housing_washer'], bearing['rolling_envelope']),
                ('51105_rolling_envelope/51105_shaft_washer', bearing['rolling_envelope'], bearing['shaft_washer'])):
            contacts[name] = {'distance_mm': first.val().distance(second.val()),
                              'intersection_mm3': intersection_volume(first, second)}
        rolling = bearing['rolling_envelope']
        rolling_pairs = {f'{name}/51105_rolling_envelope': intersection_volume(shape, rolling)
                         for name, shape in {**moving, **self.stationary_parts}.items()}
        # These supports share motion ownership, so neither belongs to the
        # moving/stationary or rolling-envelope pair collections above.
        support_penetration = sum(contacts[name]['intersection_mm3'] for name in
                                  ('cover/51105_housing_washer', 'base/51105_shaft_washer'))
        return {'rotating_stationary_pairs_mm3': pairs, 'rolling_envelope_pairs_mm3': rolling_pairs,
                'rotating_part_count': len(moving), 'stationary_part_count': len(self.stationary_parts),
                'unintended_intersection_mm3': sum(pairs.values())+sum(rolling_pairs.values())+support_penetration,
                'intended_bearing_contacts': contacts, 'numerical_tolerance_mm3': 0.01}

    def rotor_stator_intersection_volume_mm3(self) -> float:
        return self.collision_report()['unintended_intersection_mm3']


def intersection_volume(first: cq.Workplane, second: cq.Workplane) -> float:
    """Skip disjoint or merely touching bounding boxes before the solid boolean."""
    a, b = first.val().BoundingBox(), second.val().BoundingBox()
    if any(min(getattr(a, f'{axis}max'), getattr(b, f'{axis}max')) -
           max(getattr(a, f'{axis}min'), getattr(b, f'{axis}min')) <= 1e-7 for axis in 'xyz'):
        return 0.0
    return first.intersect(second).val().Volume()


def _magnet_envelope(p: DesignParameters, face: float, upper: bool) -> cq.Workplane:
    """Flush 2 mm-deep nominal discs; a 0.1 mm radial gap avoids pocket overlap."""
    g = p.generator
    centers = [(g.magnet_pitch_radius_mm*cos(2*pi*i/g.magnet_pocket_count),
                g.magnet_pitch_radius_mm*sin(2*pi*i/g.magnet_pocket_count))
               for i in range(g.magnet_pocket_count)]
    bottom = face if upper else face-g.magnet_pocket_depth_mm
    return (cq.Workplane('XY').pushPoints(centers).circle(g.magnet_pocket_diameter_mm/2-0.1)
            .extrude(g.magnet_pocket_depth_mm).translate((0, 0, bottom)))


def build_generator_assembly(parameters: DesignParameters) -> GeneratorAssembly:
    """Place the cup from the winding face, then seat the 51105 beneath Base.

    The rod terminates above the closed floor. Its complete seven-stage length
    belongs to assembly.py. M4 cover screws and captive nuts remain stationary.
    """
    from windwall.rotor_modules import build_base_module

    p,g,m = parameters,parameters.generator,parameters.manufacturing
    _validate(p)
    upper_face,lower_face = upper_magnet_face_z_mm(p),lower_magnet_face_z_mm(p)
    housing = build_generator_housing(p)
    offset = upper_face-g.upper_air_gap_mm-housing.winding_volume.val().BoundingBox().zmax
    stationary = {name: getattr(housing, name).translate((0, 0, offset))
                  for name in ('housing', 'coil_cassette', 'cover', 'winding_volume')}
    floor = housing.metadata['bearing_seat_floor_z_mm']+offset
    reference = build_51105_reference(p)
    bearing = BearingReference(reference.designation, reference.nominal_dimensions_mm,
                               {name: shape.translate((0, 0, floor)) for name, shape in reference.parts.items()})
    stationary['51105_housing_washer'] = bearing.parts['housing_washer']
    for index, fastener in enumerate(housing.cover_fasteners, 1):
        stationary[f'cover_screw_{index}'] = fastener.screw.translate((0, 0, offset))
        stationary[f'cover_nut_{index}'] = fastener.nut.translate((0, 0, offset))
    rear = lower_face-g.carrier_height_mm
    bottom = rear-p.closure.shaft_bottom_projection_mm
    shaft = cq.Workplane('XY').circle(p.shaft.nominal_diameter_mm/2).extrude(p.rotor.stage_height_mm+15-bottom).translate((0,0,bottom))
    upper_nut_bottom = base_bearing_interface(p)['nut_bottom_z_mm']
    spacer = _ring(g.spacer_outer_diameter_mm/2,p.shaft.clearance_hole_diameter_mm/2,
                   lower_face,upper_nut_bottom-lower_face)
    hardware = {'upper_nut':_hex(g.clamp_nut_across_flats_mm,upper_nut_bottom,m.nut_pocket_depth_mm),
                'lower_nut':_hex(g.clamp_nut_across_flats_mm,rear,m.nut_pocket_depth_mm)}
    for name in ('upper_nut','lower_nut'):
        hardware[name] = hardware[name].cut(shaft)
    magnets = {'upper': _magnet_envelope(p, upper_face, True),
               'lower': _magnet_envelope(p, lower_face, False)}
    return GeneratorAssembly(build_base_module(p),build_upper_magnet_carrier(p),build_lower_magnet_rotor(p),
                             housing,offset,stationary,{'51105': bearing},magnets,shaft,spacer,hardware,
                             p.shaft.nominal_diameter_mm,m.nut_pocket_across_flats_mm)


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
