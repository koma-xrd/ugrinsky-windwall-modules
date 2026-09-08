from dataclasses import dataclass, field


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
    lug_axial_thickness_mm: float = 3.2
    ramp_rise_mm: float = 0.45
    root_fillet_mm: float = 1.5


@dataclass(frozen=True)
class DesignParameters:
    manufacturing: ManufacturingParameters = field(default_factory=ManufacturingParameters)
    shaft: ShaftParameters = field(default_factory=ShaftParameters)
    rotor: RotorParameters = field(default_factory=RotorParameters)
    bayonet: BayonetParameters = field(default_factory=BayonetParameters)


DEFAULT_PARAMETERS = DesignParameters()
