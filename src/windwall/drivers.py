"""Permanent bayonet interface and the compact open-spoke calibration coupon.

The historical module name is retained for existing imports. V4.3 replaced the
radial drivers and screws with the three-lug permanent lock. Module builders
phase the interface by the blade twist; the coupon preserves that same joint
and adds a shallow hex calibration recess, not a load-bearing nut socket.
"""

from dataclasses import dataclass, replace
from math import cos, isfinite, radians

import cadquery as cq

from windwall.bayonet import BayonetCoupon, build_bayonet_coupon
from windwall.blade_profile import build_blade_section_faces
from windwall.parameters import DesignParameters


def joint_interface_height_mm(parameters: DesignParameters) -> float:
    """Height of the compact bayonet male used to recess the module interface."""
    return build_bayonet_coupon(parameters).male.val().BoundingBox().zmax


@dataclass(frozen=True)
class JointCoupon(BayonetCoupon):
    driver_centers: tuple = ()
    screw_axes: tuple = ()
    registration: dict | None = None
    nut_calibration_recess_depth_mm: float | None = None
    blade_sample_count: int = 0

    def unplanned_intersection_volume_mm3(self) -> float:
        return self.locked_intersection_volume_mm3()


def build_joint_interface(parameters: DesignParameters) -> JointCoupon:
    """The shared permanent bayonet in its zero-degree locked coupon frame."""
    p = parameters
    base = build_bayonet_coupon(p)
    return JointCoupon(p, base.male, base.female,
        registration={'nominal_module_rotation_deg': 0, 'blade_bottom_phase_deg': 0,
                      'blade_top_phase_deg': p.blade.twist_deg,
                      'joint_locked_phase_deg': p.blade.twist_deg,
                      'module_end_registration_verified': True})


def build_joint_coupon(parameters: DesignParameters) -> JointCoupon:
    """Short plain blade-wall samples share the module's bayonet assembly path.

    Spokes below/above the nominal plane join both blade samples to their respective
    bayonet halves. The historical shallow open-spoke hex calibration remains.
    """
    joint = build_joint_interface(parameters)
    m = parameters.manufacturing
    if any(not isfinite(value) or value <= 0
           for value in (m.nut_pocket_across_flats_mm, m.nut_pocket_depth_mm)):
        raise ValueError('Nut calibration dimensions must be positive and finite')
    recess_depth = min(4.2, m.nut_pocket_depth_mm)
    top = joint.male.val().BoundingBox().zmax
    nut = (cq.Workplane('XY').polygon(6, m.nut_pocket_across_flats_mm/cos(radians(30)))
           .extrude(m.nut_pocket_depth_mm+1).translate((0,0,top-recess_depth)))
    male, female = joint.male.cut(nut), joint.female
    phase = parameters.blade.twist_deg-parameters.modules.joint_phase_deg
    keepout = parameters.bayonet.hub_outer_diameter_mm/2+parameters.bayonet.lug_radial_depth_mm+2*m.minimum_loaded_wall_mm
    annulus = cq.Face.makeFromWires(cq.Workplane('XY').circle(parameters.blade.rotor_radius_mm).val(),
                                  [cq.Workplane('XY').circle(keepout).val()])
    for index, face in enumerate(build_blade_section_faces(parameters)):
        section = max(face.intersect(annulus).Faces(), key=lambda item: item.Area())
        section = section.rotate((0,0,0),(0,0,1),phase)
        lower_wall = cq.Workplane(obj=cq.Solid.extrudeLinear(
            section.outerWire(),[],cq.Vector(0,0,6))).translate((0,0,top-6))
        upper_wall = cq.Workplane(obj=cq.Solid.extrudeLinear(
            section.outerWire(),[],cq.Vector(0,0,4))).translate((0,0,top))
        # Tip-directed spokes stay clear of the three axial lug entry windows.
        tip_radius = parameters.blade.small_arc_center_xy_mm[0]+parameters.blade.small_arc_radius_mm
        male_radius = parameters.bayonet.hub_outer_diameter_mm/2-1
        # Bury the spoke root in the ring wall. A root tangent to the bore
        # creates split cylindrical edges that do not tessellate consistently.
        female_radius = parameters.bayonet.hub_outer_diameter_mm/2+m.radial_clearance_mm+m.minimum_loaded_wall_mm/2
        angle = 180*index+phase
        spoke = (cq.Workplane('XY').box(tip_radius-male_radius,3,3,centered=(False,True,False))
                 .translate((male_radius,0,0)).rotate((0,0,0),(0,0,1),angle))
        lower_spoke = (cq.Workplane('XY').box(tip_radius-female_radius,3,3,centered=(False,True,False))
                       .translate((female_radius,0,top-6))
                       .rotate((0,0,0),(0,0,1),angle))
        female = female.union(lower_spoke).union(lower_wall)
        male = male.union(spoke.translate((0,0,top))).union(upper_wall)
    if any(not part.val().isValid() or len(part.val().Solids()) != 1 for part in (male, female)):
        raise ValueError('Each joint coupon half must be one valid connected solid')
    return replace(joint, male=male, female=female,
                   nut_calibration_recess_depth_mm=recess_depth, blade_sample_count=2)
