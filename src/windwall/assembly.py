"""Named seven-stage rotor placements, service hardware and full-length shaft.

Unique printable bodies come from rotor_modules/top_closure; generator supplies
the lower mechanism. Shapes are already placed in millimetres. Every locked
blade frame has zero angular offset, retaining +60-degree internal twist and
a -60-degree skin phase jump at each seam.
Nominal screw envelopes intentionally overlap blind pilots to represent thread
forming, confined by explicit per-fastener masks. Validation owns the fit audit.
"""

from dataclasses import dataclass
from math import cos, radians, sin, sqrt

import cadquery as cq

from windwall.drivers import build_joint_interface
from windwall.generator import GeneratorAssembly, build_generator_assembly
from windwall.parameters import DesignParameters
from windwall.rotor_modules import build_standard_module, build_top_module, module_joint_depth_mm
from windwall.top_closure import build_top_closure, top_clamp_levels_mm


def place(shape: cq.Workplane, angle: float = 0, z: float = 0) -> cq.Workplane:
    return shape.rotate((0,0,0),(0,0,1),angle).translate((0,0,z))


@dataclass(frozen=True)
class StagePlacement:
    name: str
    kind: str
    z_mm: float
    angle_deg: float = 0


@dataclass(frozen=True)
class Retainer:
    name: str
    body_name: str
    thread_envelope: cq.Workplane
    head: cq.Workplane
    tool: cq.Workplane
    angle_deg: float | None = None


@dataclass(frozen=True)
class RotorAssembly:
    parameters: DesignParameters
    parts: dict[str,cq.Workplane]
    stages: tuple[StagePlacement,...]
    generator: GeneratorAssembly
    local_modules: dict[str,cq.Workplane]
    retainers: tuple[Retainer,...]
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

    def maximum_stage_angle_error_deg(self) -> float:
        return max(abs((stage.angle_deg+180)%360-180) for stage in self.stages)

    def aerodynamic_height_mm(self) -> float:
        return self.parts['top'].val().BoundingBox().zmax-self.stages[0].z_mm

    def unplanned_intersection_volume_mm3(self) -> float:
        from windwall.assembly_validation import intersection_report
        return intersection_report(self)[0]

    def as_cq_assembly(self) -> cq.Assembly:
        result = cq.Assembly(name='rotor_exploded' if self.exploded else 'rotor_locked')
        for name, shape in self.parts.items():
            color = ((0.38,0.64,0.81) if name in {s.name for s in self.stages}
                     else (0.88,0.62,0.25) if name == 'top_closure'
                     else (0.50,0.54,0.58))
            result.add(shape,name=name,color=cq.Color(*color))
        return result


def _cylinder(radius, length, point, direction=(0,0,1)):
    return cq.Workplane(obj=cq.Solid.makeCylinder(radius,length,cq.Vector(*point),cq.Vector(*direction)))


def build_locked_rotor_assembly(parameters: DesignParameters) -> RotorAssembly:
    """Exactly one base, five identical standards, one top and separate closure."""
    p,m = parameters,parameters.manufacturing
    if type(p.rotor.stage_count) is not int or type(p.rotor.standard_stage_count) is not int or (p.rotor.stage_count,p.rotor.standard_stage_count) != (7,5):
        raise ValueError('Full rotor requires one base, five standard stages and one top')
    closure = build_top_closure(p)
    generator = build_generator_assembly(p)
    modules = {'base':generator.base_module.shape,'standard':build_standard_module(p).shape,
               'top':build_top_module(p).shape}
    stages = tuple(StagePlacement('base' if i == 0 else 'top' if i == 6 else f'standard_{i}',
                   'base' if i == 0 else 'top' if i == 6 else 'standard',i*p.rotor.stage_height_mm)
                   for i in range(7))
    parts = {s.name:place(modules[s.kind],s.angle_deg,s.z_mm) for s in stages}
    parts.update({f'generator_{name}':shape for name,shape in generator.stationary.parts.items()})
    parts.update({f'generator_{name}':shape for name,shape in generator.clamp_hardware.items()})
    parts.update(lower_magnet_rotor=generator.lower_rotor,spacer=generator.spacer)
    washer,nut,tip = (z+stages[-1].z_mm for z in top_clamp_levels_mm(p))
    shaft_bottom = generator.stationary.base.val().BoundingBox().zmin-p.closure.shaft_bottom_projection_mm
    parts['shaft'] = _cylinder(p.shaft.nominal_diameter_mm/2,tip-shaft_bottom,(0,0,shaft_bottom))
    parts['top_washer'] = (cq.Workplane('XY').circle(m.washer_outer_diameter_mm/2)
                          .circle(p.shaft.clearance_hole_diameter_mm/2)
                          .extrude(p.generator.clamp_washer_thickness_mm).translate((0,0,washer)))
    parts['top_nut'] = (cq.Workplane('XY').polygon(6,2*p.generator.clamp_nut_across_flats_mm/sqrt(3))
                       .extrude(m.nut_pocket_depth_mm).translate((0,0,nut)).cut(parts['shaft']))
    parts['top_closure'] = place(closure,z=stages[-1].z_mm)
    joint,retainers = build_joint_interface(p),[]
    for stage in stages[1:]:
        for index,axis in enumerate(joint.screw_axes):
            angle = (axis.angle_deg+p.modules.joint_phase_deg)%360
            direction = (cos(radians(angle)),sin(radians(angle)),0)
            z = stage.z_mm-module_joint_depth_mm(p)+axis.center_z_mm
            radius = axis.head_radius_mm
            point = lambda r: (r*direction[0],r*direction[1],z)
            shank = _cylinder(m.screw_nominal_diameter_mm/2,m.screw_length_mm,point(radius-m.screw_length_mm),direction)
            head = _cylinder(m.screw_head_diameter_mm/2,m.screw_head_height_mm,point(radius),direction)
            name = f'{stage.name}_retainer_{index+1}'
            parts[name] = shank.union(head)
            # Only the blind pilot segment in the upper male may be displaced.
            envelope = _cylinder(m.screw_nominal_diameter_mm/2,
                p.bayonet.hub_outer_diameter_mm/2-(radius-m.screw_length_mm),
                point(radius-m.screw_length_mm),direction)
            tool = place(axis.access,p.modules.joint_phase_deg,stage.z_mm-module_joint_depth_mm(p))
            retainers.append(Retainer(name,stage.name,envelope,head,tool,angle))
    top_z = stages[-1].z_mm+p.rotor.stage_height_mm
    for index,x in enumerate((-p.modules.closure_screw_radius_mm,p.modules.closure_screw_radius_mm)):
        head_z = top_z+p.closure.plate_thickness_mm
        bottom = head_z-m.screw_length_mm
        shank = _cylinder(m.screw_nominal_diameter_mm/2,m.screw_length_mm,(x,0,bottom))
        head = _cylinder(m.screw_head_diameter_mm/2,m.screw_head_height_mm,(x,0,head_z))
        name = f'closure_retainer_{index+1}'
        parts[name] = shank.union(head)
        envelope = _cylinder(m.screw_nominal_diameter_mm/2,top_z-bottom,(x,0,bottom))
        tool = _cylinder(p.drivers.screwdriver_diameter_mm/2,30,(x,0,head_z+0.01))
        retainers.append(Retainer(name,'top',envelope,head,tool))
    return RotorAssembly(p,parts,stages,generator,modules,tuple(retainers))


def build_exploded_rotor_assembly(parameters: DesignParameters, *, locked: RotorAssembly | None = None) -> RotorAssembly:
    """Withdraw stages at -18 degrees, leaving 15 mm above each entry position.

    Lifts accumulate to keep all stages separated. Each upper stage is shown
    relative to its own locked lower frame; this is not a simultaneous assembly
    motion. The real rod retains its locked length. Radial screws withdraw first.
    """
    a = locked or build_locked_rotor_assembly(parameters)
    if a.parameters != parameters or a.exploded:
        raise ValueError('Explosion must use a matching locked assembly')
    p,b = parameters,parameters.bayonet
    increment = p.closure.exploded_joint_lift_mm-b.ramp_rise_mm
    if increment <= -min(a.local_modules[k].val().BoundingBox().zmin for k in ('standard','top')):
        raise ValueError('Explosion lift must fully withdraw each lower male')
    stages = tuple(StagePlacement(s.name,s.kind,s.z_mm+i*increment,-b.insertion_offset_deg if i else 0)
                   for i,s in enumerate(a.stages))
    parts = dict(a.parts)
    for stage in stages:
        parts[stage.name] = place(a.local_modules[stage.kind],stage.angle_deg,stage.z_mm)
    top_lift = 6*increment
    for name in ('top_washer','top_nut','top_closure','closure_retainer_1','closure_retainer_2'):
        extra = p.closure.exploded_joint_lift_mm if name == 'top_closure' or name.startswith('closure_retainer') else 0
        if name.startswith('closure_retainer'):
            extra += p.manufacturing.screw_length_mm
        parts[name] = place(a.parts[name],-b.insertion_offset_deg,top_lift+extra)
    for retainer in a.retainers:
        if retainer.angle_deg is not None:
            index = next(i for i,s in enumerate(a.stages) if s.name == retainer.body_name)
            direction = (cos(radians(retainer.angle_deg)),sin(radians(retainer.angle_deg)))
            removed = a.parts[retainer.name].translate((18*direction[0],18*direction[1],0))
            parts[retainer.name] = place(removed,-b.insertion_offset_deg,index*increment)
    return RotorAssembly(p,parts,stages,a.generator,a.local_modules,(),True)


def audit_rotor_assembly(assembly: RotorAssembly) -> dict:
    """Measure actual placed solids, motion, contact semantics and service paths."""
    from windwall.assembly_validation import audit_rotor_assembly as audit
    return audit(assembly)
