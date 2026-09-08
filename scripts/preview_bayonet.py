"""Export the isolated bayonet coupon, or show its locked fit in CQ-editor.

CLI exports are local evidence, not a print command. Both STL bottoms are placed
at Z=0; STEP preserves the locked assembly frame. No blade or reference STL is
needed. Fit clearances remain uncalibrated until the physical PLA test.
"""

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

import cadquery as cq

from windwall.bayonet import build_bayonet_coupon
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters
from windwall.reference_mesh import analyze_binary_stl


def preview_objects(parameters: DesignParameters) -> list[tuple[cq.Workplane, str, dict]]:
    coupon = build_bayonet_coupon(parameters)
    radius = coupon.female.val().BoundingBox().xlen/2 + 5
    z = coupon.female.val().BoundingBox().zmax + 1
    arc = cq.Edge.makeCircle(radius, cq.Vector(0,0,z), angle1=0, angle2=90)
    head = cq.Wire.makePolygon([(3,radius+2,z), (0,radius,z), (3,radius-2,z)])
    marker = cq.Workplane(obj=cq.Compound.makeCompound([arc, head]))
    return [(coupon.female, "Female: entry at -18 deg, solid CCW stops", {"color": (170,180,195), "alpha": 0.55}),
            (coupon.male, "Male: locked at zero", {"color": (35,120,220)}),
            (coupon.male_at_travel(0).translate((0,0,16)), "Insertion ghost: -18 deg", {"color": (230,155,40), "alpha": 0.65}),
            (marker, "Positive CCW viewed from +Z", {"color": (25,180,75)})]


def export_coupon(parameters: DesignParameters, output_dir: Path) -> dict:
    coupon = build_bayonet_coupon(parameters)
    m = parameters.manufacturing
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = {}
    for name, part in (("male", coupon.male), ("female", coupon.female)):
        if not part.val().isValid() or len(part.val().Solids()) != 1:
            raise ValueError(f"Bayonet {name} must be one valid solid before export")
        printable = part.translate((0,0,-part.val().BoundingBox().zmin))
        path = output_dir / f"bayonet_{name}.stl"
        cq.exporters.export(printable, str(path), tolerance=m.export_linear_tolerance_mm,
                            angularTolerance=m.export_angular_tolerance_rad)
        mesh = analyze_binary_stl(path)
        if (mesh.component_count != 1 or mesh.boundary_edge_count
                or mesh.nonmanifold_edge_count or mesh.degenerate_face_count
                or mesh.signed_volume <= 0):
            raise ValueError(f"Bayonet {name} STL failed topology validation: {mesh.as_dict()}")
        reports[name] = mesh.as_dict()
    assembly = cq.Compound.makeCompound([coupon.male.val(), coupon.female.val()])
    cq.exporters.export(assembly, str(output_dir / "bayonet_locked.step"))
    cq.exporters.export(assembly, str(output_dir / "bayonet_top.svg"), opt={
        "projectionDir": (0,0,1), "showHidden": True, "width": 900, "height": 900})
    cq.exporters.export(assembly, str(output_dir / "bayonet_isometric.svg"), opt={
        "projectionDir": (1,-2,2), "showHidden": True, "width": 1000, "height": 800})
    motion = [{"travel_deg": angle,
               "intersection_mm3": coupon.male_at_travel(angle).intersect(coupon.female).val().Volume()}
              for angle in range(int(parameters.bayonet.insertion_offset_deg)+1)]
    insertion = [coupon.male_at_travel(0).translate((0,0,lift)).intersect(coupon.female).val().Volume()
                 for lift in range(int(coupon.female.val().BoundingBox().zmax)+2)]
    ccw = coupon.male.rotate((0,0,0), (0,0,1), 0.5).intersect(coupon.female).val().Volume()
    cw = coupon.male.rotate((0,0,0), (0,0,1), -0.5).intersect(coupon.female).val().Volume()
    report = {"physically_calibrated": False, "view": "from +Z looking down",
              "insertion_orientation_deg": -parameters.bayonet.insertion_offset_deg,
              "locked_orientation_deg": 0, "lug_count": 3,
              "radial_clearance_parameter_mm": m.radial_clearance_mm,
              "axial_clearance_parameter_mm": m.axial_clearance_mm,
              "minimum_measured_running_clearance_mm": coupon.minimum_locked_clearance_mm(),
              "intentional_stop_contact_clearance_mm": coupon.male.val().distance(coupon.female.val()),
              "maximum_motion_intersection_mm3": max(item["intersection_mm3"] for item in motion),
              "maximum_insertion_intersection_mm3": max(insertion),
              "ccw_stop_intersection_mm3": ccw, "cw_release_intersection_mm3": cw,
              "motion_samples": motion, "meshes": reports}
    if (report["maximum_motion_intersection_mm3"] >= 0.01 or max(insertion) >= 0.01
            or ccw <= 0.05 or cw >= 0.01):
        raise ValueError("Coupon motion or directional stop validation failed")
    (output_dir / "bayonet_fit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "build/coupons")
    args = parser.parse_args()
    print(json.dumps(export_coupon(DEFAULT_PARAMETERS, args.output_dir), indent=2), flush=True)
    return 0


if "show_object" in globals():
    for shape, name, options in preview_objects(DEFAULT_PARAMETERS):
        show_object(shape, name=name, options=options)
elif __name__ == "__main__":
    raise SystemExit(main())
