"""Export coupon-gated generator CAD and static sections; never submit a print.

Use scripts/run_geometry.py for CLI execution. CQ-editor can display the same
analytic arrangement, with reference solids distinguished from rotating parts.
Physical magnet protrusion, bearing fit/retention and electrical work are open.
"""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / 'src') not in sys.path:
    sys.path.insert(0,str(PROJECT_ROOT / 'src'))

import cadquery as cq

from windwall.generator import build_generator_assembly, build_magnet_pocket_coupon
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters
from windwall.reference_mesh import analyze_binary_stl


def _export_print_candidate(name: str, shape: cq.Workplane, p: DesignParameters, destination: Path) -> dict:
    box = shape.val().BoundingBox()
    cq.exporters.export(shape,str(destination / f'{name}.step'))
    path = destination / f'{name}.stl'
    cq.exporters.export(shape.translate((0,0,-box.zmin)),str(path),
                        tolerance=p.manufacturing.export_linear_tolerance_mm,
                        angularTolerance=p.manufacturing.export_angular_tolerance_rad)
    mesh = analyze_binary_stl(path)
    if (mesh.component_count != 1 or mesh.boundary_edge_count or mesh.nonmanifold_edge_count
            or mesh.degenerate_face_count or mesh.signed_volume <= 0):
        raise ValueError(f'{name} STL failed topology validation: {mesh.as_dict()}')
    return {'mesh':mesh.as_dict(),'cad_volume_mm3':shape.val().Volume(),
            'assembly_z_bounds_mm':[box.zmin,box.zmax]}


def export_magnet_pocket_coupon(parameters: DesignParameters, output_dir: Path) -> dict:
    """Shared export prerequisite for every script that writes full carriers."""
    output_dir.mkdir(parents=True,exist_ok=True)
    return _export_print_candidate('magnet_pocket_coupon',
                                   build_magnet_pocket_coupon(parameters),parameters,output_dir)


def export_generator(parameters: DesignParameters, output_dir: Path) -> dict:
    """Generate and verify the fit coupon before exporting any full carrier."""
    p,g = parameters,parameters.generator
    output_dir.mkdir(parents=True,exist_ok=True)
    parts = {'magnet_pocket_coupon':export_magnet_pocket_coupon(p,output_dir)}
    a = build_generator_assembly(p)
    for name,shape in (('base_with_upper_carrier',a.base_module.shape),('lower_magnet_rotor',a.lower_rotor)):
        parts[name] = _export_print_candidate(name,shape,p,output_dir)
    moving = a.rotating_parts
    all_parts = {**moving, **a.stationary_parts, **a.bearing_parts}
    collision_report = a.collision_report()
    collisions = collision_report['rotating_stationary_pairs_mm3']
    if collision_report['unintended_intersection_mm3'] >= 0.01:
        raise ValueError(f'Generator rotating/stationary collision: {collisions}')
    if min(a.upper_air_gap_mm(),a.lower_air_gap_mm()) <= 0:
        raise ValueError('Generator carrier-to-stator air gaps must be positive')
    assembly = cq.Assembly(name='Generator_clearance_reference')
    for name,shape in all_parts.items():
        color = ((0.25,0.6,0.65) if name in a.stationary_parts else
                 (0.6,0.45,0.7) if name in a.bearing_parts else (0.8,0.55,0.25))
        assembly.add(shape,name=name,color=cq.Color(*color))
    assembly.export(str(output_dir / 'generator_assembly.step'))
    shapes = cq.Compound.makeCompound([shape.val() for shape in all_parts.values()])
    cq.exporters.export(shapes,str(output_dir / 'generator_isometric.svg'),opt={
        'projectionDir':(1,-2,1.5),'showHidden':False,'width':900,'height':1000})
    section_bottom = a.shaft.val().BoundingBox().zmin-1
    section_width = max(shape.val().BoundingBox().xlen for shape in all_parts.values())+10
    section_box = (cq.Workplane('XY').box(section_width,0.2,
                    p.modules.end_support_thickness_mm-section_bottom,centered=(True,True,False))
                   .translate((0,0,section_bottom)))
    sections = [shape.intersect(section_box).val() for shape in all_parts.values()]
    cq.exporters.export(cq.Compound.makeCompound(sections),str(output_dir / 'generator_section.svg'),opt={
        'projectionDir':(0,-1,0),'showHidden':False,'width':1100,'height':650})
    report = {'print_ready':False,'physical_magnet_fit_verified':False,
              'physical_bearing_fit_verified':False,'electrical_design_finalized':False,
              'bearing_axial_retention_verified':False,'magnet_retention_verified':False,
              'air_gap_basis':a.air_gap_report()['basis'],
              'bearing_basis':'51105 with independent shaft washer, housing washer and rolling envelope',
              'stationary_basis':'V5 cup, winding cassette, cover and M4 hardware; winding is a nominal envelope',
              'magnet_pattern_basis':'Nominal magnet envelopes in CAD pockets; electrical pole assignment unverified',
              'rotation_states':{name:'rotating' if name in moving else 'stationary' if name in a.stationary_parts
                                 else 'bearing' for name in all_parts},
              'export_order':list(parts),'parts':parts,'parameters':asdict(g),
              'coupon_pocket_diameters_left_to_right_mm':[g.magnet_pocket_diameter_mm+i*g.coupon_diameter_step_mm for i in (-1,0,1)],
              'upper_air_gap_mm':a.upper_air_gap_mm(),'lower_air_gap_mm':a.lower_air_gap_mm(),
              'upper_rotor_integrated_with_base':a.upper_rotor_integrated_with_base,
              'rotating_stationary_intersections_mm3':collisions,
              'maximum_rotating_stationary_intersection_mm3':max(collisions.values()),
              'assembly_part_z_bounds_mm':{name:[shape.val().BoundingBox().zmin,shape.val().BoundingBox().zmax]
                                           for name,shape in all_parts.items()}}
    (output_dir / 'generator_fit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=Path('build/generator'))
    args = parser.parse_args()
    report = export_generator(DEFAULT_PARAMETERS,args.output_dir)
    print(json.dumps(report,indent=2))
    return 0


if 'show_object' in globals():
    model = build_generator_assembly(DEFAULT_PARAMETERS)
    show_object(model.base_module.shape,name='Base with upper magnet carrier',options={'color':(220,150,55)})
    show_object(model.lower_rotor,name='Lower magnet carrier',options={'color':(220,150,55)})
    for name,part in model.stationary_parts.items():
        show_object(part,name=f'Stationary reference: {name}',options={'color':(70,160,220),'alpha':0.4})
    show_object(model.shaft,name='Nominal M8 rod',options={'color':(170,175,180)})
    show_object(model.spacer,name='Adjustable central spacer envelope',options={'color':(80,180,100)})
    for name,part in model.clamp_hardware.items():
        show_object(part,name=f'Nominal clamp envelope: {name}',options={'color':(170,175,180)})
elif __name__ == '__main__':
    raise SystemExit(main())
