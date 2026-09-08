"""Export the complete joint calibration pair, or preview it in CQ-editor.

Use scripts/run_geometry.py for CLI execution. This exports local geometry and
does not send a print job or certify fit/load capacity. Keeping the full ring
preserves its stiffness; the pair includes three lugs, two drivers, two screws,
and one top-accessible M8 nut calibration pocket.
"""

import argparse
import json
from math import ceil
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / 'src'))

import cadquery as cq

from windwall.drivers import build_drivers, build_joint_coupon
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters
from windwall.reference_mesh import analyze_binary_stl


def export_coupon(parameters: DesignParameters, output_dir: Path) -> dict:
    coupon = build_joint_coupon(parameters)
    m = parameters.manufacturing
    output_dir.mkdir(parents=True, exist_ok=True)
    meshes = {}
    for name, part in (('male', coupon.male), ('female', coupon.female)):
        if not part.val().isValid() or len(part.val().Solids()) != 1:
            raise ValueError(f'Joint {name} must be one valid solid')
        path = output_dir / f'joint_{name}.stl'
        printable = part.translate((0,0,-part.val().BoundingBox().zmin))
        cq.exporters.export(printable, str(path), tolerance=m.export_linear_tolerance_mm,
                            angularTolerance=m.export_angular_tolerance_rad)
        mesh = analyze_binary_stl(path)
        if (mesh.component_count != 1 or mesh.boundary_edge_count or mesh.nonmanifold_edge_count
                or mesh.degenerate_face_count or mesh.signed_volume <= 0):
            raise ValueError(f'Joint {name} mesh failed topology validation: {mesh.as_dict()}')
        meshes[name] = mesh.as_dict()
    assembly = cq.Compound.makeCompound([coupon.male.val(), coupon.female.val()])
    cq.exporters.export(assembly, str(output_dir / 'joint_locked.step'))
    for name, direction in (('top', (0,0,1)), ('isometric', (1,-2,2))):
        cq.exporters.export(assembly, str(output_dir / f'joint_{name}.svg'), opt={
            'projectionDir': direction, 'showHidden': False, 'width': 1000, 'height': 800})
    travel = parameters.bayonet.insertion_offset_deg
    motion = [{'travel_deg': min(angle/2,travel), 'intersection_mm3': coupon.male_at_travel(min(angle/2,travel))
               .intersect(coupon.female).val().Volume()}
              for angle in range(ceil(travel*2)+1)]
    insertion = [coupon.male_at_travel(0).translate((0,0,lift)).intersect(coupon.female).val().Volume()
                 for lift in range(25)]
    drivers = build_drivers(parameters)
    ccw = drivers.rotate((0,0,0), (0,0,1), 0.5).intersect(coupon.female).val().Volume()
    cw = drivers.rotate((0,0,0), (0,0,1), -0.5).intersect(coupon.female).val().Volume()
    access = [coupon.male.union(coupon.female).intersect(axis.access).val().Volume()
              for axis in coupon.screw_axes]
    report = {'physically_calibrated': False, 'interactive_qa_verified': False,
              'view': 'from +Z looking down', 'insertion_orientation_deg': -parameters.bayonet.insertion_offset_deg,
              'locked_orientation_deg': 0, 'driver_centers_xy_mm': coupon.driver_centers,
              'screw_angles_deg': [axis.angle_deg for axis in coupon.screw_axes],
              'screw_pilot_diameter_mm': m.screw_pilot_diameter_mm,
              'screw_clearance_diameter_mm': parameters.drivers.screw_clearance_diameter_mm,
              'minimum_pilot_edge_margin_mm': min(axis.minimum_pilot_edge_margin_mm for axis in coupon.screw_axes),
              'maximum_tool_corridor_intersection_mm3': max(access),
              'maximum_motion_intersection_mm3': max(sample['intersection_mm3'] for sample in motion),
              'maximum_insertion_intersection_mm3': max(insertion),
              'ccw_driver_stop_intersection_mm3': ccw, 'cw_driver_release_intersection_mm3': cw,
              'registration': coupon.registration, 'motion_samples': motion, 'meshes': meshes}
    if (report['maximum_motion_intersection_mm3'] >= 0.01 or max(insertion) >= 0.01
            or max(access) >= 0.01 or ccw <= 0.05 or cw >= 0.01):
        raise ValueError('Joint motion, driver stops or radial access validation failed')
    (output_dir / 'joint_fit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=PROJECT_ROOT / 'build/coupons')
    args = parser.parse_args()
    print(json.dumps(export_coupon(DEFAULT_PARAMETERS, args.output_dir), indent=2), flush=True)
    return 0


if 'show_object' in globals():
    coupon = build_joint_coupon(DEFAULT_PARAMETERS)
    show_object(coupon.female, name='Receiver and radial clearance holes', options={'color': (170,180,195), 'alpha': 0.5})
    show_object(coupon.male, name='Locked drivers and blind pilots', options={'color': (35,120,220)})
    show_object(coupon.male_at_travel(0).translate((0,0,24)), name='Insertion at -18 degrees', options={'color': (230,155,40), 'alpha': 0.5})
elif __name__ == '__main__':
    raise SystemExit(main())
