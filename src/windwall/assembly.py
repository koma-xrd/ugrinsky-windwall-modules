"""Seven phased rotor stages on one rotating M8 rod above the stationary cup.

The integrated generator owns the bearing and stationary housing components.
Modules retain their blade-local frames; successive 60-degree placements keep
the helical seams continuous. The exposed top nut loads a compact force plate.
The exploded view depicts preassembly, not removal of the permanent bayonets.
"""

from dataclasses import dataclass
from math import isfinite, sqrt

import cadquery as cq

from windwall.generator import GeneratorAssembly, build_generator_assembly
from windwall.parameters import DesignParameters
from windwall.rotor_modules import build_standard_module, build_top_module


def place(shape: cq.Workplane, angle: float = 0, z: float = 0) -> cq.Workplane:
    return shape.rotate((0, 0, 0), (0, 0, 1), angle).translate((0, 0, z))


@dataclass(frozen=True)
class StagePlacement:
    name: str
    kind: str
    z_mm: float
    angle_deg: float = 0


@dataclass(frozen=True)
class RotorAssembly:
    parameters: DesignParameters
    parts: dict[str, cq.Workplane]
    stages: tuple[StagePlacement, ...]
    generator: GeneratorAssembly
    local_modules: dict[str, cq.Workplane]
    exploded: bool = False

    @property
    def base_count(self) -> int:
        return sum(stage.kind == 'base' for stage in self.stages)

    @property
    def standard_count(self) -> int:
        return sum(stage.kind == 'standard' for stage in self.stages)

    @property
    def top_count(self) -> int:
        return sum(stage.kind == 'top' for stage in self.stages)

    @property
    def aerodynamic_stage_count(self) -> int:
        return len(self.stages)

    @property
    def rotating_parts(self) -> dict[str, cq.Workplane]:
        names = set(self.generator.rotating_parts) | {s.name for s in self.stages} | {'top_washer', 'top_nut'}
        return {name: shape for name, shape in self.parts.items() if name in names}

    @property
    def stationary_parts(self) -> dict[str, cq.Workplane]:
        return {name: self.parts[name] for name in self.generator.stationary_parts}

    def maximum_stage_angle_error_deg(self) -> float:
        return max(abs(((stage.angle_deg-index*self.parameters.blade.twist_deg)+180) % 360-180)
                   for index, stage in enumerate(self.stages))

    def aerodynamic_height_mm(self) -> float:
        return self.parts['top'].val().BoundingBox().zmax-self.stages[0].z_mm

    def unplanned_intersection_volume_mm3(self) -> float:
        from windwall.assembly_validation import intersection_report
        return intersection_report(self)[0]

    def as_cq_assembly(self) -> cq.Assembly:
        result = cq.Assembly(name='rotor_exploded' if self.exploded else 'rotor_locked')
        for name, shape in self.parts.items():
            color = (0.38, 0.64, 0.81) if name in self.rotating_parts else (0.50, 0.54, 0.58)
            result.add(shape, name=name, color=cq.Color(*color))
        return result


def build_locked_rotor_assembly(parameters: DesignParameters) -> RotorAssembly:
    """One Base, five identical Standards and one Top, with an enclosed generator."""
    p, m = parameters, parameters.manufacturing
    if (type(p.rotor.stage_count) is not int or type(p.rotor.standard_stage_count) is not int
            or (p.rotor.stage_count, p.rotor.standard_stage_count) != (7, 5)):
        raise ValueError('Full rotor requires one base, five standard stages and one top')
    if any(not isfinite(v) or v <= 0 for v in
           (p.closure.rod_projection_mm, p.closure.shaft_bottom_projection_mm, p.closure.exploded_joint_lift_mm)):
        raise ValueError('Rod projections and preassembly spacing must be positive and finite')
    generator = build_generator_assembly(p)
    modules = {'base': generator.base_module.shape, 'standard': build_standard_module(p).shape,
               'top': build_top_module(p).shape}
    stages = tuple(StagePlacement('base' if i == 0 else 'top' if i == 6 else f'standard_{i}',
                   'base' if i == 0 else 'top' if i == 6 else 'standard',
                   i*p.rotor.stage_height_mm, i*p.blade.twist_deg) for i in range(7))
    parts = {**generator.rotating_parts, **generator.stationary_parts, **generator.bearing_parts}
    parts.update({s.name: place(modules[s.kind], s.angle_deg, s.z_mm) for s in stages})
    washer = stages[-1].z_mm+p.rotor.stage_height_mm-p.modules.washer_seat_depth_mm
    nut = washer+p.generator.clamp_washer_thickness_mm
    tip = nut+m.nut_pocket_depth_mm+p.closure.rod_projection_mm
    shaft_bottom = generator.shaft.val().BoundingBox().zmin
    parts['shaft'] = cq.Workplane('XY').circle(p.shaft.nominal_diameter_mm/2).extrude(
        tip-shaft_bottom).translate((0, 0, shaft_bottom))
    parts['top_washer'] = (cq.Workplane('XY').circle(m.washer_outer_diameter_mm/2)
                          .circle(p.shaft.clearance_hole_diameter_mm/2)
                          .extrude(p.generator.clamp_washer_thickness_mm).translate((0, 0, washer)))
    parts['top_nut'] = (cq.Workplane('XY').polygon(6, 2*p.generator.clamp_nut_across_flats_mm/sqrt(3))
                       .extrude(m.nut_pocket_depth_mm).translate((0, 0, nut)).cut(parts['shaft']))
    return RotorAssembly(p, parts, stages, generator, modules)


def build_exploded_rotor_assembly(parameters: DesignParameters, *, locked: RotorAssembly | None = None) -> RotorAssembly:
    """Preassembly view: entry-angle stages separated by the configured axial lift.

    Permanent teeth/pawls block reversal after locking. This view claims no
    non-destructive disassembly path. The rod retains its installed length.
    """
    a = locked or build_locked_rotor_assembly(parameters)
    if a.parameters != parameters or a.exploded:
        raise ValueError('Explosion must use a matching locked assembly')
    p = parameters
    increment = p.closure.exploded_joint_lift_mm
    if increment <= -min(a.local_modules[k].val().BoundingBox().zmin for k in ('standard', 'top')):
        raise ValueError('Preassembly spacing must fully separate each lower male')
    stages = tuple(StagePlacement(s.name, s.kind, s.z_mm+i*increment,
                                  s.angle_deg-p.bayonet.insertion_offset_deg if i else s.angle_deg)
                   for i, s in enumerate(a.stages))
    parts = dict(a.parts)
    for stage in stages:
        parts[stage.name] = place(a.local_modules[stage.kind], stage.angle_deg, stage.z_mm)
    for name in ('top_washer', 'top_nut'):
        parts[name] = place(a.parts[name], -p.bayonet.insertion_offset_deg, 6*increment)
    return RotorAssembly(p, parts, stages, a.generator, a.local_modules, True)


def audit_rotor_assembly(assembly: RotorAssembly) -> dict:
    """Measure placed solids, permanent-joint contacts and service access."""
    from windwall.assembly_validation import audit_rotor_assembly as audit
    return audit(assembly)
