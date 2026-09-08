"""Two transition-adjacent drivers and radial retainers for the shared bayonet.

All builders use its locked joint frame: insertion is -18 degrees, locking is
positive CCW to zero with the bayonet ramp rise. The nearby small-arc stations
replace impossible tabs at the true transitions inside the central receiver.
Short shoulders connect the fittings, without altering the blade source. This
isolated coupon does not resolve the +60-degree twisted module end registration.
"""

from dataclasses import dataclass, replace
from math import atan2, ceil, cos, degrees, hypot, isfinite, radians, sin

import cadquery as cq

from windwall.bayonet import (BayonetCoupon, _insertion_height, _lug_outer_radius,
                             _receiver_height, build_bayonet_coupon, locked_angle_deg)
from windwall.parameters import DesignParameters


def _validate(p: DesignParameters) -> None:
    locked_angle_deg(p)
    d, m = p.drivers, p.manufacturing
    values = (d.radial_length_mm, d.inner_width_mm, d.outer_width_mm,
              d.corner_radius_mm, d.root_thickness_mm, d.engagement_depth_mm,
              d.sweep_step_deg, d.screw_clearance_diameter_mm,
              d.screwdriver_diameter_mm, m.screw_pilot_diameter_mm, m.screw_length_mm)
    if any(not isfinite(v) or v <= 0 for v in values):
        raise ValueError('Driver and screw dimensions must be positive and finite')
    if d.root_thickness_mm < max(3, m.minimum_loaded_wall_mm):
        raise ValueError('Driver root thickness must retain at least the loaded wall')
    if d.corner_radius_mm*2 >= min(d.radial_length_mm, d.outer_width_mm):
        raise ValueError('Driver corners consume the footprint')
    if not 0 < d.sweep_step_deg <= 1 or not 110 <= d.small_arc_station_deg <= 130:
        raise ValueError('Use a nearby small-arc station and sweep steps at most one degree')
    if any(not isfinite(angle) for angle in d.screw_angles_deg):
        raise ValueError('Screw angles must be finite')
    if len(d.screw_angles_deg) != 2 or len({angle % 360 for angle in d.screw_angles_deg}) != 2:
        raise ValueError('Exactly two distinct radial screws are required')
    if not m.screw_pilot_diameter_mm < m.screw_nominal_diameter_mm < d.screw_clearance_diameter_mm:
        raise ValueError('Screw pilot, nominal and clearance diameters must increase')


def _station(p):
    b, d = p.blade, p.drivers
    angle = radians(d.small_arc_station_deg)
    x = b.small_arc_center_xy_mm[0] + b.small_arc_radius_mm*cos(angle)
    y = b.small_arc_center_xy_mm[1] + b.small_arc_radius_mm*sin(angle)
    return hypot(x,y), degrees(atan2(y,x))


def _outer(p):
    return _lug_outer_radius(p) + p.manufacturing.radial_clearance_mm + p.manufacturing.minimum_loaded_wall_mm


def _arm_bottom(p):
    m, d = p.manufacturing, p.drivers
    wall = max(3, m.minimum_loaded_wall_mm)
    screw_z = _insertion_height(p)+p.bayonet.ramp_rise_mm+wall+m.screw_pilot_diameter_mm/2
    boss_top = screw_z+d.screw_clearance_diameter_mm/2+wall
    return max(_receiver_height(p), boss_top) + m.axial_clearance_mm + p.bayonet.ramp_rise_mm


def joint_interface_height_mm(parameters: DesignParameters) -> float:
    """Validated height from receiver bottom to the upper male shoulder face."""
    _validate(parameters)
    return _arm_bottom(parameters)+parameters.drivers.root_thickness_mm


def _footprint(p, clearance=0):
    radius, _ = _station(p)
    d = p.drivers
    inner, outer = radius-d.radial_length_mm/2, radius+d.radial_length_mm/2
    wire = (cq.Workplane('XY').polyline([(inner,-d.inner_width_mm/2),
            (outer,-d.outer_width_mm/2), (outer,d.outer_width_mm/2),
            (inner,d.inner_width_mm/2)]).close().val())
    face = cq.Face.makeFromWires(wire)
    wire = face.fillet2D(d.corner_radius_mm, face.Vertices()).outerWire()
    return wire.offset2D(clearance)[0] if clearance else wire


def _extrude(wire, bottom, height):
    return cq.Workplane(obj=cq.Solid.extrudeLinear(wire, [], cq.Vector(0,0,height))).translate((0,0,bottom))


def _pair(shape, angle):
    return cq.Workplane(obj=cq.Compound.makeCompound([
        shape.val().rotate((0,0,0), (0,0,1), angle+phase) for phase in (0,180)]))


def build_drivers(parameters: DesignParameters) -> cq.Workplane:
    """Two rounded trapezoidal keys, including a full >=3 mm shoulder root."""
    _validate(parameters)
    p = parameters
    bottom = _receiver_height(p)-p.drivers.engagement_depth_mm
    top = _arm_bottom(p)+p.drivers.root_thickness_mm
    return _pair(_extrude(_footprint(p), bottom, top-bottom), _station(p)[1])


def _single_pocket(p, extra=0):
    d, m, b = p.drivers, p.manufacturing, p.bayonet
    radius, _ = _station(p)
    count = ceil(b.insertion_offset_deg/d.sweep_step_deg)
    step = b.insertion_offset_deg/count
    # Lipschitz displacement bound covers every intermediate rotation, not only
    # the sampled positions. Axial clearance includes the full ramp rise.
    extent = hypot(radius+d.radial_length_mm/2, d.inner_width_mm/2)
    clearance = m.radial_clearance_mm + extent*radians(step)/2 + extra
    bottom = _receiver_height(p)-d.engagement_depth_mm-b.ramp_rise_mm-m.axial_clearance_mm
    key = _extrude(_footprint(p, clearance), bottom,
                   _arm_bottom(p)+d.root_thickness_mm+1-bottom)
    pocket = key
    for index in range(1,count+1):
        pocket = pocket.union(key.rotate((0,0,0), (0,0,1), -index*step))
    if extra == 0:
        # The leading trapezoid flat is the load face. Preserve its exact plane
        # at the terminal stop, while retaining running clearance elsewhere.
        inner, outer = radius-d.radial_length_mm/2, radius+d.radial_length_mm/2
        slope = (d.outer_width_mm-d.inner_width_mm)/(2*d.radial_length_mm)
        def leading(x):
            return d.inner_width_mm/2 + slope*(x-inner)
        stop = (cq.Workplane('XY').polyline([(inner-2,leading(inner-2)),
                (outer+2,leading(outer+2)), (outer+2,30), (inner-2,30)])
                .close().extrude(40))
        pocket = pocket.cut(stop)
    return pocket


def build_driver_pockets(parameters: DesignParameters) -> cq.Workplane:
    """Open-top pocket cutters enclosing the entire lock path and ramp motion."""
    _validate(parameters)
    return _pair(_single_pocket(parameters), _station(parameters)[1])


@dataclass(frozen=True)
class ScrewAxis:
    angle_deg: float
    center_z_mm: float
    head_radius_mm: float
    minimum_pilot_edge_margin_mm: float
    pilot: cq.Workplane
    clearance: cq.Workplane
    access: cq.Workplane


def _radial_cylinder(radius, start, length, z, angle):
    solid = cq.Solid.makeCylinder(radius, length, cq.Vector(start,0,z), cq.Vector(1,0,0))
    return cq.Workplane(obj=solid.rotate((0,0,0), (0,0,1), angle))


def _screw_axes(p):
    m, d, b = p.manufacturing, p.drivers, p.bayonet
    wall = max(3, m.minimum_loaded_wall_mm)
    z = _insertion_height(p)+b.ramp_rise_mm+wall+m.screw_pilot_diameter_mm/2
    start = _outer(p)-m.screw_length_mm
    margin = min(wall, start-p.shaft.clearance_hole_diameter_mm/2,
                 _arm_bottom(p)+d.root_thickness_mm-z-m.screw_pilot_diameter_mm/2)
    if margin < wall-1e-8 or start >= b.hub_outer_diameter_mm/2-wall:
        raise ValueError('Screw length must retain loaded material at blind pilot end and sufficient engagement')
    axes = []
    for configured_angle in d.screw_angles_deg:
        angle = configured_angle % 360
        axes.append(ScrewAxis(angle, z, _outer(p), margin,
            _radial_cylinder(m.screw_pilot_diameter_mm/2, start,
                             b.hub_outer_diameter_mm/2+m.radial_clearance_mm-start, z, angle),
            _radial_cylinder(d.screw_clearance_diameter_mm/2, b.hub_outer_diameter_mm/2,
                             _outer(p)-b.hub_outer_diameter_mm/2+1, z, angle),
            _radial_cylinder(d.screwdriver_diameter_mm/2, _outer(p)+0.01,
                             p.blade.rotor_radius_mm, z, angle)))
    return tuple(axes)


def build_screw_pilots(parameters: DesignParameters) -> cq.Workplane:
    """Two blind radial pilot cutters in the inner male member (PLA default 2.3)."""
    _validate(parameters)
    return cq.Workplane(obj=cq.Compound.makeCompound([axis.pilot.val() for axis in _screw_axes(parameters)]))


@dataclass(frozen=True)
class JointCoupon(BayonetCoupon):
    driver_centers: tuple = ()
    screw_axes: tuple = ()
    registration: dict = None

    def unplanned_intersection_volume_mm3(self) -> float:
        return self.locked_intersection_volume_mm3()


def build_joint_interface(parameters: DesignParameters) -> JointCoupon:
    """Complete reusable joint members, without the coupon-only nut pocket."""
    _validate(parameters)
    p, d, m = parameters, parameters.drivers, parameters.manufacturing
    base = build_bayonet_coupon(p)
    male, female = base.male, base.female
    radius, angle = _station(p)
    arm_z = _arm_bottom(p)
    top = arm_z+d.root_thickness_mm
    # Top annulus connects two local shoulder arms; it does not enlarge the hub.
    male = male.union(cq.Workplane('XY').circle(p.bayonet.hub_outer_diameter_mm/2)
                      .circle(p.shaft.clearance_hole_diameter_mm/2).extrude(top-arm_z).translate((0,0,arm_z)))
    arm = (cq.Workplane('XY').box(radius-p.bayonet.hub_outer_diameter_mm/2+4,
            d.inner_width_mm, d.root_thickness_mm, centered=(False,True,False))
           .translate((p.bayonet.hub_outer_diameter_mm/2-2,0,arm_z)).edges('|Z').fillet(d.corner_radius_mm))
    for phase in (angle,angle+180):
        male = male.union(arm.rotate((0,0,0), (0,0,1), phase))
    male = male.union(build_drivers(p))
    # Swept local pads preserve >=3 mm outside the pocket perimeter.
    pad_outline = _single_pocket(p, max(3,m.minimum_loaded_wall_mm))
    pad_section = pad_outline.section(_receiver_height(p)).val().Wires()[0].translate((0,0,-_receiver_height(p)))
    pad = _extrude(pad_section, 0, _receiver_height(p))
    # Only overlap the receiver's outer loaded wall; filling deeper would close
    # the existing bayonet track near the second transition-adjacent driver.
    pad = pad.cut(cq.Workplane('XY').circle(_outer(p)-1).extrude(_receiver_height(p)+1))
    for phase in (angle,angle+180):
        female = female.union(pad.rotate((0,0,0), (0,0,1), phase))
    female = female.cut(build_driver_pockets(p))
    axes = _screw_axes(p)
    for axis in axes:
        boss_top = axis.center_z_mm + d.screw_clearance_diameter_mm/2 + max(3,m.minimum_loaded_wall_mm)
        boss = (cq.Workplane('XY').box(_outer(p)-p.bayonet.hub_outer_diameter_mm/2,
                d.screw_clearance_diameter_mm+2*max(3,m.minimum_loaded_wall_mm), boss_top,
                centered=(False,True,False)).translate((p.bayonet.hub_outer_diameter_mm/2,0,0))
                .rotate((0,0,0), (0,0,1), axis.angle_deg))
        # Clip the head face to the circular ring so the screwdriver corridor
        # begins outside every solid, including the rectangular boss corners.
        boss = boss.intersect(cq.Workplane('XY').circle(_outer(p)).extrude(boss_top))
        female = female.union(boss).cut(axis.clearance)
        male = male.cut(axis.pilot)
    female = female.cut(cq.Workplane('XY').circle(p.bayonet.hub_outer_diameter_mm/2+m.radial_clearance_mm).extrude(top+1))
    centers = tuple((radius*cos(radians(a)),radius*sin(radians(a))) for a in (angle,angle+180))
    return JointCoupon(p, male, female, driver_centers=centers, screw_axes=axes,
        registration={'nominal_module_rotation_deg': 0, 'blade_bottom_phase_deg': 0,
                      'blade_top_phase_deg': p.blade.twist_deg,
                      'joint_locked_phase_deg': 0, 'module_end_registration_verified': False})


def build_joint_coupon(parameters: DesignParameters) -> JointCoupon:
    """Add the top-accessible M8 fit sample to the reusable joint pair."""
    joint = build_joint_interface(parameters)
    m = parameters.manufacturing
    top = _arm_bottom(parameters) + parameters.drivers.root_thickness_mm
    nut = (cq.Workplane('XY').polygon(6, m.nut_pocket_across_flats_mm/cos(radians(30)))
           .extrude(m.nut_pocket_depth_mm+1).translate((0,0,top-m.nut_pocket_depth_mm)))
    return replace(joint, male=joint.male.cut(nut))
