from dataclasses import dataclass, field
from math import acos, degrees


@dataclass(frozen=True)
class ManufacturingParameters:
    radial_clearance_mm: float = 0.30
    axial_clearance_mm: float = 0.25
    minimum_loaded_wall_mm: float = 3.0
    nut_pocket_across_flats_mm: float = 13.30
    nut_pocket_depth_mm: float = 6.8
    washer_outer_diameter_mm: float = 24.0
    screw_nominal_diameter_mm: float = 3.0
    screw_pilot_diameter_mm: float = 2.3
    screw_length_mm: float = 12.0
    screw_head_diameter_mm: float = 5.5
    screw_head_height_mm: float = 3.0
    export_linear_tolerance_mm: float = 0.08
    export_angular_tolerance_rad: float = 0.12


@dataclass(frozen=True)
class ShaftParameters:
    nominal_diameter_mm: float = 8.0
    clearance_hole_diameter_mm: float = 8.8


@dataclass(frozen=True)
class RotorParameters:
    stage_height_mm: float = 70.0
    stage_count: int = 7
    standard_stage_count: int = 5
    rotor_diameter_mm: float = 121.5
    rotation_direction: str = "counterclockwise_from_top"

    @property
    def nominal_stack_height_mm(self) -> float:
        return self.stage_height_mm * self.stage_count


@dataclass(frozen=True)
class BayonetParameters:
    lug_count: int = 3
    insertion_offset_deg: float = 18.0
    hub_outer_diameter_mm: float = 34.0
    lug_radial_depth_mm: float = 4.0
    lug_tangential_width_mm: float = 8.0
    lug_axial_thickness_mm: float = 3.2
    ramp_rise_mm: float = 0.45
    root_fillet_mm: float = 1.5


@dataclass(frozen=True)
class BladeParameters:
    """Measured circular centerlines in the bottom-section shaft frame, in mm.

    The small upper semicircle meets the descending large arc at (12, 0).
    The second blade is its 180-degree rotation. Stage height remains in
    RotorParameters; twist is positive counterclockwise when viewed from above.
    """

    rotor_radius_mm: float = 60.75
    wall_thickness_mm: float = 1.5
    small_arc_center_xy_mm: tuple[float, float] = (36.0, 0.0)
    large_arc_center_xy_mm: tuple[float, float] = (-48.0, 0.0)
    small_arc_radius_mm: float = 24.0
    large_arc_radius_mm: float = 60.0
    tangent_transition_xy_mm: tuple[float, float] = (12.0, 0.0)
    large_arc_sweep_deg: float = degrees(acos(0.4))
    hub_blend_radius_mm: float = 13.0
    twist_deg: float = 60.0
    loft_section_count: int = 9


@dataclass(frozen=True)
class DriverParameters:
    """Local joint fittings; small-arc station is measured from its +X radius."""

    small_arc_station_deg: float = 125.0
    radial_length_mm: float = 6.0
    inner_width_mm: float = 8.0
    outer_width_mm: float = 6.0
    corner_radius_mm: float = 0.8
    root_thickness_mm: float = 3.0
    engagement_depth_mm: float = 4.0
    sweep_step_deg: float = 1.0
    screw_angles_deg: tuple[float, float] = (70.0, 180.0)
    screw_clearance_diameter_mm: float = 3.3
    screwdriver_diameter_mm: float = 6.0


@dataclass(frozen=True)
class ModuleParameters:
    """Local structural end fittings and the generator carrier fusion offset."""

    end_support_radius_mm: float = 36.0
    end_support_thickness_mm: float = 3.0
    base_shaft_flange_depth_mm: float = 3.0
    washer_seat_depth_mm: float = 0.5
    closure_screw_radius_mm: float = 24.0
    closure_pilot_depth_mm: float = 8.0
    joint_phase_deg: float = 100.0
    locked_seating_travel_mm: float = 0.35


@dataclass(frozen=True)
class GeneratorParameters:
    """Mechanical reference reconstruction, never an electrical or print approval.

    Hole count/pitch/diameter come from the mesh, not measured magnets. Carrier
    OD grows from 104 to 106 mm to retain a 3 mm rim. The 12 x 8 x 6 bearing
    envelope is a provisional sleeve inside the measured ~12.3 mm opening;
    it does not identify a bearing product, fit, or axial retention system.
    """

    carrier_diameter_mm: float = 106.0
    carrier_height_mm: float = 10.0
    carrier_disc_thickness_mm: float = 5.0
    carrier_hub_diameter_mm: float = 34.0
    rib_count: int = 6
    rib_width_mm: float = 3.0
    magnet_pocket_count: int = 18
    magnet_pitch_radius_mm: float = 44.5
    magnet_pocket_diameter_mm: float = 11.0
    magnet_pocket_depth_mm: float = 2.0
    coupon_diameter_step_mm: float = 0.2
    coil_former_diameter_mm: float = 118.0
    coil_former_height_mm: float = 12.0
    coil_former_bore_diameter_mm: float = 12.4
    stator_cover_diameter_mm: float = 112.0
    stator_cover_bore_diameter_mm: float = 62.0
    stator_cover_height_mm: float = 2.0
    base_diameter_mm: float = 120.0
    base_cavity_diameter_mm: float = 114.0
    base_height_mm: float = 27.0
    base_floor_mm: float = 3.0
    bearing_seat_diameter_mm: float = 12.3
    bearing_outer_diameter_mm: float = 12.0
    bearing_bore_diameter_mm: float = 8.0
    bearing_length_mm: float = 6.0
    bearing_support_diameter_mm: float = 20.0
    upper_air_gap_mm: float = 1.5
    lower_air_gap_mm: float = 1.5
    spacer_outer_diameter_mm: float = 12.0
    clamp_nut_across_flats_mm: float = 13.0
    clamp_washer_thickness_mm: float = 2.0


@dataclass(frozen=True)
class ClosureParameters:
    """Removable cover and nominal M8 rod end, pending actual hardware fitting."""

    plate_thickness_mm: float = 5.0
    roof_thickness_mm: float = 3.0
    rod_projection_mm: float = 3.0
    shaft_bottom_projection_mm: float = 5.0
    exploded_joint_lift_mm: float = 15.0


@dataclass(frozen=True)
class DesignParameters:
    manufacturing: ManufacturingParameters = field(default_factory=ManufacturingParameters)
    shaft: ShaftParameters = field(default_factory=ShaftParameters)
    rotor: RotorParameters = field(default_factory=RotorParameters)
    bayonet: BayonetParameters = field(default_factory=BayonetParameters)
    blade: BladeParameters = field(default_factory=BladeParameters)
    drivers: DriverParameters = field(default_factory=DriverParameters)
    modules: ModuleParameters = field(default_factory=ModuleParameters)
    generator: GeneratorParameters = field(default_factory=GeneratorParameters)
    closure: ClosureParameters = field(default_factory=ClosureParameters)


DEFAULT_PARAMETERS = DesignParameters()
