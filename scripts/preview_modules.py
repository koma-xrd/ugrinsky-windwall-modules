"""Export the three mechanical stage bodies or inspect them in CQ-editor.

Run CLI through scripts/run_geometry.py. This is local CAD evidence only;
the base includes its coupon-gated generator carrier and no print job is sent.
"""

import argparse
import json
from math import ceil
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for import_root in (PROJECT_ROOT, PROJECT_ROOT / 'src'):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import cadquery as cq

from scripts.preview_generator import export_magnet_pocket_coupon
from windwall.blade_profile import build_blade_stage
from windwall.drivers import build_joint_interface
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters
from windwall.reference_mesh import analyze_binary_stl
from windwall.rotor_modules import (build_base_module, build_standard_module,
                                    build_top_module, module_joint_depth_mm)


def export_modules(parameters: DesignParameters, output_dir: Path) -> dict:
    p, m = parameters, parameters.manufacturing
    export_magnet_pocket_coupon(p,output_dir)
    models = {name: builder(p) for name, builder in (
        ('base',build_base_module), ('standard',build_standard_module), ('top',build_top_module))}
    output_dir.mkdir(parents=True, exist_ok=True)
    parts = {}
    for name, model in models.items():
        shape = model.shape
        box = shape.val().BoundingBox()
        cq.exporters.export(shape, str(output_dir / f'{name}_module.step'))
        printable = shape.translate((0,0,-box.zmin))
        path = output_dir / f'{name}_module.stl'
        cq.exporters.export(printable, str(path), tolerance=m.export_linear_tolerance_mm,
                            angularTolerance=m.export_angular_tolerance_rad)
        mesh = analyze_binary_stl(path)
        if (mesh.component_count != 1 or mesh.boundary_edge_count or mesh.nonmanifold_edge_count
                or mesh.degenerate_face_count or mesh.signed_volume <= 0):
            raise ValueError(f'{name} module STL failed topology validation: {mesh.as_dict()}')
        cq.exporters.export(shape, str(output_dir / f'{name}_module.svg'), opt={
            'projectionDir': (1,-2,1.5), 'showHidden': False, 'width': 900, 'height': 800})
        parts[name] = {'mesh': mesh.as_dict(), 'cad_volume_mm3': shape.val().Volume(),
                       'assembly_z_bounds_mm': [box.zmin,box.zmax],
                       'shaft_clearance_radial_mm': model.shaft_clearance_radial_mm,
                       'nut_pocket_across_flats_mm': model.nut_pocket_across_flats_mm,
                       'washer_seat_diameter_mm': model.washer_seat_diameter_mm}
    height, depth = p.rotor.stage_height_mm, module_joint_depth_mm(p)
    phase = p.modules.joint_phase_deg
    joint = build_joint_interface(p)
    locked, access = [], []
    for lower_name, upper_name in (('base','standard'), ('standard','standard'), ('standard','top')):
        lower = models[lower_name].shape
        upper = models[upper_name].shape.translate((0,0,height))
        locked.append(lower.intersect(upper).val().Volume())
        for axis in joint.screw_axes:
            tool = axis.access.rotate((0,0,0), (0,0,1), phase).translate((0,0,height-depth))
            access.extend(part.intersect(tool).val().Volume() for part in (lower,upper))
    lower, upper = models['standard'].shape, models['top'].shape
    travel = p.bayonet.insertion_offset_deg
    motion = []
    for index in range(ceil(travel*2)+1):
        angle = min(index/2,travel)
        moved = upper.rotate((0,0,0), (0,0,1), angle-travel).translate(
            (0,0,height+p.bayonet.ramp_rise_mm*(angle/travel-1)))
        motion.append({'travel_deg': angle, 'intersection_mm3': lower.intersect(moved).val().Volume()})
    insertion = []
    for lift in range(ceil(depth)+2):
        moved = upper.rotate((0,0,0), (0,0,1), -travel).translate((0,0,height-p.bayonet.ramp_rise_mm+lift))
        insertion.append(lower.intersect(moved).val().Volume())
    source = build_blade_stage(p)
    relief_height = p.bayonet.ramp_rise_mm+m.axial_clearance_mm
    edge = (cq.Workplane('XY').circle(p.blade.rotor_radius_mm+1)
            .circle(p.modules.end_support_radius_mm).extrude(relief_height))
    removed = source.intersect(edge).val().Volume()
    receiver_region = (cq.Workplane('XY').circle(p.modules.end_support_radius_mm)
                       .circle(20).extrude(depth).translate((0,0,height-depth)))
    report = {'modules': parts, 'nominal_module_rotation_deg': 0,
              'blade_twist_deg': p.blade.twist_deg, 'joint_phase_deg': phase,
              'aerodynamic_seam_continuous': False, 'upper_magnet_carrier_integrated': True,
              'physical_fit_verified': False, 'interactive_qa_verified': False,
              'physical_magnet_fit_verified': False, 'print_ready': False,
              'magnet_coupon': 'magnet_pocket_coupon.stl',
              'joint_depth_mm': depth, 'female_bottom_z_mm': height-depth,
              'bottom_edge_relief_height_mm': relief_height,
              'bottom_edge_removed_source_volume_mm3': removed,
              'bottom_edge_removed_source_volume_percent': 100*removed/source.val().Volume(),
              'receiver_region_source_displaced_outside_20mm_radius_mm3': source.intersect(receiver_region).val().Volume(),
              'end_support_radius_mm': p.modules.end_support_radius_mm,
              'upper_support_bottom_z_mm': height-depth-p.modules.end_support_thickness_mm,
              'retainer_angles_deg': [(axis.angle_deg+phase) % 360 for axis in joint.screw_axes],
              'maximum_locked_intersection_mm3': max(locked),
              'maximum_tool_intersection_mm3': max(access),
              'maximum_motion_intersection_mm3': max(sample['intersection_mm3'] for sample in motion),
              'maximum_insertion_intersection_mm3': max(insertion), 'motion_samples': motion}
    if max(report[key] for key in ('maximum_locked_intersection_mm3', 'maximum_tool_intersection_mm3',
            'maximum_motion_intersection_mm3', 'maximum_insertion_intersection_mm3')) >= 0.01:
        raise ValueError('Assembled module collision, lock path or tool access check failed')
    cq.exporters.export(cq.Compound.makeCompound([lower.val(),upper.translate((0,0,height)).val()]),
                        str(output_dir / 'two_modules_locked.step'))
    (output_dir / 'module_fit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=PROJECT_ROOT / 'build/modules')
    args = parser.parse_args()
    print(json.dumps(export_modules(DEFAULT_PARAMETERS,args.output_dir), indent=2), flush=True)
    return 0


if 'show_object' in globals():
    for name, builder, x in (('Base',build_base_module,-140), ('Standard',build_standard_module,0),
                             ('Top',build_top_module,140)):
        show_object(builder(DEFAULT_PARAMETERS).shape.translate((x,0,0)), name=name,
                    options={'color': (80,140,190)})
elif __name__ == '__main__':
    raise SystemExit(main())
