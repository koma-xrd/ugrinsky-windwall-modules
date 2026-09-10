"""Load-bearing base, standard and top stages in a common nominal blade frame.

The source blade frame spans z=0 to stage_height_mm with its +60-degree twist;
only its outer bottom edge is relieved for the axial locking motion. The upper
receiver is recessed into a local end-support region;
the next stage's male extends below zero into it. The support plate bridges
the phase difference structurally. Successive modules rotate by the blade twist
to continue the aerodynamic surface. Base fuses the upper generator carrier and
51105 pilot. Its clipped blade silhouette continues vertically below the root
to the carrier print plane; protected generator volumes are cut after fusion.
Top retains only the compact washer force plate and exposed nut.
"""

from dataclasses import dataclass
from math import cos, hypot, isfinite, pi, sin

import cadquery as cq
from OCP.BRepLib import BRepLib
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

from windwall.blade_profile import build_blade_stage
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


def _outer_blade_key(source: cq.Workplane, height: float, depth: float, top: bool) -> cq.Workplane:
    target_z = height if top else 0
    faces = [face for face in source.val().Faces()
             if abs(face.Center().z-target_z) < 0.01 and abs(face.normalAt().z) > 0.9]
    solids = [cq.Solid.extrudeLinear(face.outerWire(),face.innerWires(),cq.Vector(0,0,depth))
              for face in faces]
    key = cq.Workplane(obj=cq.Compound.makeCompound(solids))
    outer = (cq.Workplane('XY').circle(62).circle(24).extrude(depth+0.2)
             .translate((0,0,target_z)))
    return key.intersect(outer)


def _end_guide(p: DesignParameters, bottom: float, angle_deg: float) -> cq.Workplane:
    guide = (cq.Workplane('XY').circle(6).circle(p.shaft.clearance_hole_diameter_mm/2)
             .extrude(3).translate((0,0,bottom)))
    bridge = (cq.Workplane('XY').box(10,3,3,centered=(False,True,False))
              .translate((4,0,bottom)))
    for phase in (angle_deg,angle_deg+180):
        guide = guide.union(bridge.rotate((0,0,0),(0,0,1),phase))
    return guide


def _base_blade_support(source: cq.Workplane, plate_bottom_z: float,
                        plate_radius: float, protected_radius: float) -> cq.Workplane:
    """Continue the full blade silhouette from the print plane to the root.

    The source is the bare blade stage in its nominal XY frame. Exact top-view
    edges partition the carrier annulus; a vertical ray selects cells occupied
    by either blade. The protected radius excludes the small source hub/bridges.
    Only the retained planar faces are extruded, leaving the active blade intact.
    """
    source_shape = source.val()
    # Bounding-box extrema include OCP tolerances, which are not section planes.
    cap_heights = [face.Center().z for face in source_shape.Faces()
                   if face.geomType() == 'PLANE' and abs(face.normalAt().z) > 0.99]
    root_z, top_z = min(cap_heights), max(cap_heights)
    support_height = root_z-plate_bottom_z
    if support_height <= 0:
        raise ValueError('Carrier plate bottom must lie below the blade root')

    projection = HLRBRep_Algo()
    projection.Add(source_shape.wrapped)
    projection.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(), gp_Dir(0,0,1))))
    projection.Update()
    projection.Hide()
    outline = HLRBRep_HLRToShape(projection)
    edges = []
    for projected in (outline.VCompound(), outline.OutLineVCompound()):
        if not projected.IsNull():
            # HLR returns 2D curves; Boolean splitting needs their 3D geometry.
            BRepLib.BuildCurves3d_s(projected, 1e-7)
            edges.extend(cq.Shape.cast(projected).Edges())
    carrier_face = cq.Face.makeFromWires(cq.Workplane('XY').circle(plate_radius).val(),
                                          [cq.Workplane('XY').circle(protected_radius).val()])
    projected_faces = []
    for face in carrier_face.split(*edges).Faces():
        vertices, triangles = face.tessellate(0.1)
        # A triangle centroid lies inside even a concave trimmed face, whereas
        # the face's center of mass can fall outside its boundary.
        triangle = max(triangles, key=lambda indices:
                       (vertices[indices[1]]-vertices[indices[0]]).cross(
                           vertices[indices[2]]-vertices[indices[0]]).Length)
        point = sum((vertices[index] for index in triangle), cq.Vector())/3
        ray = cq.Edge.makeLine((point.x,point.y,root_z-1), (point.x,point.y,top_z+1))
        if ray.intersect(source_shape).Edges():
            projected_faces.append(face)
    if not projected_faces:
        raise ValueError('Blade silhouette must overlap the carrier annulus')
    footprint = projected_faces[0].fuse(*projected_faces[1:]).clean()
    solids = [cq.Solid.extrudeLinear(face.outerWire(),face.innerWires(),cq.Vector(0,0,support_height))
              for face in footprint.Faces()]
    return cq.Workplane(obj=cq.Compound.makeCompound(solids).translate(cq.Vector(0,0,plate_bottom_z)))


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
    body = build_blade_stage(p)
    # The upper stage starts below its locked height and rises during locking.
    # Relieve the outer bottom edge for its lower insertion/early-travel poses.
    if kind == 'base':
        plate_bottom = -end.base_shaft_flange_depth_mm-p.generator.carrier_height_mm
        support = _base_blade_support(
            body,plate_bottom,p.generator.carrier_diameter_mm/2,
            base_bearing_interface(p)['boss_clearance_radius_mm'])
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
        body = body.union(_outer_blade_key(body,height,0.8,True))
    if kind != 'base':
        groove = _outer_blade_key(build_blade_stage(p),height,0.95,False)
        clearance = groove
        for dx,dy in ((0.12,0),(-0.12,0),(0,0.12),(0,-0.12)):
            clearance = clearance.union(groove.translate((dx,dy,0)))
        body = body.cut(clearance)
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
