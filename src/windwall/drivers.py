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
    """Preserve the V4.3 4.2 mm open-spoke hex recess; no full nut floor exists."""
    joint = build_joint_interface(parameters)
    m = parameters.manufacturing
    if any(not isfinite(value) or value <= 0
           for value in (m.nut_pocket_across_flats_mm, m.nut_pocket_depth_mm)):
        raise ValueError('Nut calibration dimensions must be positive and finite')
    recess_depth = min(4.2, m.nut_pocket_depth_mm)
    top = joint.male.val().BoundingBox().zmax
    nut = (cq.Workplane('XY').polygon(6, m.nut_pocket_across_flats_mm/cos(radians(30)))
           .extrude(m.nut_pocket_depth_mm+1).translate((0,0,top-recess_depth)))
    return replace(joint, male=joint.male.cut(nut),
                   nut_calibration_recess_depth_mm=recess_depth)
