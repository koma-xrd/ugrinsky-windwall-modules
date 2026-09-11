"""Load-bearing base, standard and top stages in a common nominal blade frame.

The source blade frame spans z=0 to stage_height_mm with its +60-degree twist;
two inset outer blade-wall seams retain the exterior skin. The upper
receiver is recessed into a local end-support region;
the next stage's male extends below zero into it. The support plate bridges
the phase difference structurally. Successive modules rotate by the blade twist
to continue the aerodynamic surface. Base fuses the upper generator carrier and
51105 pilot. Its blade-root extension reaches the original carrier top surface
without changing the carrier disc thickness or entering the cover envelope.
Top retains only the compact washer force plate and exposed nut.
"""

from dataclasses import dataclass
from math import cos, hypot, isfinite, pi, sin

import cadquery as cq
from windwall.blade_profile import build_blade_stage
from windwall.blade_seam import BladeSeamInterface, build_blade_seam
from windwall.drivers import build_joint_interface, joint_interface_height_mm
from windwall.generator import base_bearing_interface, build_upper_magnet_carrier
from windwall.parameters import DesignParameters


@dataclass(frozen=True)
class RotorModuleModel:
    """One printable solid and its mating dimensions in the blade-local frame.

    Base's bearing seat diameter/floor describe the mating stationary cover;
    its own rotating surfaces are the pilot and the washer load shoulder.
    """

    shape: cq.Workplane
    shaft_clearance_radial_mm: float
    nut_pocket_across_flats_mm: float | None = None
    washer_seat_diameter_mm: float | None = None
    bearing_seat_diameter_mm: float | None = None
    bearing_seat_bottom_z_mm: float | None = None
    nut_pocket_bottom_z_mm: float | None = None
    retainer_screw_count: int | None = None
    bearing_pilot_diameter_mm: float | None = None
    bearing_load_shoulder_z_mm: float | None = None


def module_joint_depth_mm(parameters: DesignParameters) -> float:
    """Distance from the nominal seam to the receiver bottom in the lower stage."""
    return joint_interface_height_mm(parameters)


def _validate(p: DesignParameters) -> None:
    s, m, end = p.shaft, p.manufacturing, p.modules
    values = (s.nominal_diameter_mm, s.clearance_hole_diameter_mm,
              end.end_support_radius_mm, end.end_support_thickness_mm,
              end.base_shaft_flange_depth_mm, end.washer_seat_depth_mm,
              m.washer_outer_diameter_mm)
    if any(not isfinite(value) or value <= 0 for value in values):
        raise ValueError('Module, shaft and clamping dimensions must be positive and finite')
    if not isfinite(end.joint_phase_deg):
        raise ValueError('Common joint phase must be finite')
    if not (end.locked_seating_travel_mm == 0 and p.bayonet.ramp_rise_mm == 0):
        raise ValueError('Flush prototype requires zero axial bayonet rise and seating travel')
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


def _disc(radius: float, bottom: float, depth: float) -> cq.Workplane:
    return cq.Workplane('XY').circle(radius).extrude(depth).translate((0,0,bottom))


def _end_guide(p: DesignParameters, bottom: float, angle_deg: float) -> cq.Workplane:
    guide = (cq.Workplane('XY').circle(6).circle(p.shaft.clearance_hole_diameter_mm/2)
             .extrude(3).translate((0,0,bottom)))
    bridge = (cq.Workplane('XY').box(10,3,3,centered=(False,True,False))
              .translate((4,0,bottom)))
    for phase in (angle_deg,angle_deg+180):
        guide = guide.union(bridge.rotate((0,0,0),(0,0,1),phase))
    return guide


def _base_blade_extension(source: cq.Workplane, depth: float,
                          inner_radius: float) -> cq.Workplane:
    """Join the blade root to the unchanged top face of the carrier disc."""
    faces = [face for face in source.val().Faces()
             if abs(face.Center().z) < 0.01 and abs(face.normalAt().z) > 0.9]
    solids = [cq.Solid.extrudeLinear(face.outerWire(),face.innerWires(),cq.Vector(0,0,-depth))
              for face in faces]
    extension = cq.Workplane(obj=cq.Compound.makeCompound(solids))
    blade_zone = (cq.Workplane('XY').circle(62).circle(inner_radius)
                  .extrude(depth).translate((0,0,-depth)))
    return extension.intersect(blade_zone)


def _base_magnet_pocket_volume(p: DesignParameters, plate_bottom_z: float) -> cq.Workplane:
    """Nominal upper-carrier pocket voids retained after blade-support fusion."""
    g = p.generator
    centers = [(g.magnet_pitch_radius_mm*cos(2*pi*index/g.magnet_pocket_count),
                g.magnet_pitch_radius_mm*sin(2*pi*index/g.magnet_pocket_count))
               for index in range(g.magnet_pocket_count)]
    return (cq.Workplane('XY').pushPoints(centers).circle(g.magnet_pocket_diameter_mm/2)
            .extrude(g.magnet_pocket_depth_mm).translate((0,0,plate_bottom_z)))


def _build(parameters: DesignParameters, kind: str) -> RotorModuleModel:
    _validate(parameters)
    p, end, m = parameters, parameters.modules, parameters.manufacturing
    height = p.rotor.stage_height_mm
    depth = module_joint_depth_mm(p)
    joint_z = height-depth
    joint = build_joint_interface(p)
    seam = build_blade_seam(p)
    body = build_blade_stage(p)
    # Rotate the upper stage with tongues clear, then seat axially at +60 degrees.
    if kind == 'base':
        plate_bottom = -end.base_shaft_flange_depth_mm-p.generator.carrier_height_mm
        carrier_disc_top_depth = (end.base_shaft_flange_depth_mm+p.generator.carrier_height_mm
                                  -p.generator.carrier_disc_thickness_mm)
        carrier_ring_radius = base_bearing_interface(p)['boss_clearance_radius_mm']
        support = _base_blade_extension(
            body,carrier_disc_top_depth+0.1,carrier_ring_radius-0.1)
        carrier = build_upper_magnet_carrier(p).union(support)
        body = body.union(carrier)
        body = body.union(_disc(p.bayonet.hub_outer_diameter_mm/2,
                                -end.base_shaft_flange_depth_mm, end.base_shaft_flange_depth_mm))
    else:
        body = body.union(joint.male.rotate((0,0,0), (0,0,1), end.joint_phase_deg-p.blade.twist_deg).translate((0,0,-depth)))
    if kind != 'top':
        # Remove the source hub/skin only inside the localized receiver envelope.
        # The floor connects the explicitly phased pads to the twisted blade.
        receiver_radius = max(hypot(vertex.X,vertex.Y)
                              for vertex in joint.female.val().Vertices())+0.05
        body = body.cut(_disc(receiver_radius, joint_z, depth+1))
        body = body.union(joint.female.rotate((0,0,0), (0,0,1), end.joint_phase_deg).translate((0,0,joint_z)))
        guide_angle = p.blade.twist_deg*(joint_z-1.5)/height
        body = body.union(_end_guide(p,joint_z-3,guide_angle))
    else:
        washer_floor = height-end.washer_seat_depth_mm
        hub_radius = max(p.bayonet.hub_outer_diameter_mm/2,
                         m.washer_outer_diameter_mm/2+m.radial_clearance_mm+m.minimum_loaded_wall_mm)
        # Carry reinforcement through the bridge root to avoid enclosed slivers
        # where the twisted skin meets the otherwise narrower source hub.
        hub_bottom = washer_floor-m.minimum_loaded_wall_mm
        body = body.union(_disc(hub_radius, hub_bottom, height-hub_bottom))
        # The nut stays exposed above the washer. A buried hex would put the
        # washer above the nut and defeat its intended load-spreading function.
        body = body.cut(_disc(m.washer_outer_diameter_mm/2+m.radial_clearance_mm,
                         height-end.washer_seat_depth_mm, end.washer_seat_depth_mm+1))
    bottom = -max(depth,end.base_shaft_flange_depth_mm)-1
    body = body.cut(_disc(p.shaft.clearance_hole_diameter_mm/2, bottom, height-bottom+1)).clean()
    bearing_bottom = nut_bottom = None
    if kind == 'base':
        interface = base_bearing_interface(p)
        body = body.cut(_base_magnet_pocket_volume(p,plate_bottom))
        bearing_bottom = interface['bearing_floor_z_mm']
        nut_bottom = interface['nut_bottom_z_mm']
        pilot_bottom = interface['pilot_bottom_z_mm']
        shoulder = interface['shoulder_z_mm']
        # Leave a full annular clearance around the stationary cover boss.
        # The blade-form walls reach the carrier outside this central relief.
        body = body.cut(_disc(interface['boss_clearance_radius_mm'], pilot_bottom-1,
                              interface['boss_clearance_top_z_mm']-pilot_bottom+1))
        body = body.union(_disc(p.bearings.thrust_rotating_pilot_diameter_mm/2,
                                pilot_bottom, shoulder-pilot_bottom))
        body = body.union(_disc(p.bearings.thrust_outer_diameter_mm/2,
                                shoulder, interface['shoulder_top_z_mm']-shoulder))
        nut = (cq.Workplane('XY').polygon(6,2*m.nut_pocket_across_flats_mm/(3**0.5))
               .extrude(nut_bottom+m.nut_pocket_depth_mm-pilot_bottom+1)
               .translate((0,0,pilot_bottom-1)))
        body = body.cut(nut)
        shaft_bottom = body.val().BoundingBox().zmin-1
        body = body.cut(_disc(p.shaft.clearance_hole_diameter_mm/2,
                              shaft_bottom, height-shaft_bottom+1)).clean()
    if kind != 'top':
        body = body.union(seam.tongues.rotate((0,0,0),(0,0,1),p.blade.twist_deg)
                          .translate((0,0,height)))
    if kind != 'base':
        body = body.cut(seam.groove_clearance)
    if not body.val().isValid() or len(body.val().Solids()) != 1:
        raise ValueError(f'{kind.capitalize()} module must be one valid connected solid')
    return RotorModuleModel(body, (p.shaft.clearance_hole_diameter_mm-p.shaft.nominal_diameter_mm)/2,
                            m.nut_pocket_across_flats_mm if kind == 'base' else None,
                            m.washer_outer_diameter_mm+2*m.radial_clearance_mm if kind == 'top' else None,
                            p.bearings.thrust_housing_seat_diameter_mm if kind == 'base' else None,
                            bearing_bottom, nut_bottom, None,
                            p.bearings.thrust_rotating_pilot_diameter_mm if kind == 'base' else None,
                            interface['shoulder_z_mm'] if kind == 'base' else None)


def build_base_module(parameters: DesignParameters) -> RotorModuleModel:
    """Base blade, upper receiver and fused down-facing magnet carrier/torque nut."""
    return _build(parameters, 'base')


def build_standard_module(parameters: DesignParameters) -> RotorModuleModel:
    """Shared blade, lower permanent male bayonet and upper receiver."""
    return _build(parameters, 'standard')


def build_top_module(parameters: DesignParameters) -> RotorModuleModel:
    """Lower permanent bayonet and compact washer force plate for an exposed nut."""
    return _build(parameters, 'top')
