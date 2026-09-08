"""Measure the external blade STL and preview the clean reconstruction.

Reference coordinates are translated to the shaft and untwisted for circle
fitting only. Production CAD never reads this mesh. Set WINDWALL_REFERENCE_BLADE
to an external STL path to enable its section overlay in CQ-editor.
"""

import argparse
import csv
import json
import os
from pathlib import Path
import sys

import numpy as np

# CQ-editor executes scripts without installing the repository package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from windwall.reference_mesh import analyze_binary_stl

REFERENCE_AXIS_XY_MM = np.array([6.25, 122.634])
REFERENCE_HEIGHT_MM = 70.0
REFERENCE_TWIST_DEG = 60.0


def slice_triangles(triangles: np.ndarray, z_mm: float) -> np.ndarray:
    """Intersect triangles at Z using a half-open rule at coincident vertices."""
    segments = []
    for triangle in np.asarray(triangles, dtype=float):
        points = []
        for start, end in zip(triangle, np.roll(triangle, -1, axis=0)):
            if (start[2] < z_mm <= end[2]) or (end[2] < z_mm <= start[2]):
                fraction = (z_mm - start[2]) / (end[2] - start[2])
                points.append((start + fraction * (end - start))[:2])
        if len(points) == 2 and np.linalg.norm(points[0] - points[1]) > 1e-8:
            segments.append(points)
    if not segments:
        raise ValueError(f"No section intersects z={z_mm} mm")
    return np.asarray(segments)


def join_segments(segments: np.ndarray, tolerance_mm: float = 0.05) -> list[np.ndarray]:
    """Join unordered section edges into closed contours; reject broken contours."""
    unused = list(np.asarray(segments, dtype=float))
    loops = []
    while unused:
        chain = list(unused.pop())
        while np.linalg.norm(chain[-1] - chain[0]) > tolerance_mm:
            candidates = np.asarray(unused)
            if not len(candidates):
                raise ValueError("Reference section has an open contour")
            distances = np.linalg.norm(candidates - chain[-1], axis=2)
            edge_index, endpoint = np.unravel_index(np.argmin(distances), distances.shape)
            if distances[edge_index, endpoint] > tolerance_mm:
                raise ValueError("Reference section has a gap greater than 0.05 mm")
            edge = unused.pop(edge_index)
            chain.append(edge[1 - endpoint])
        chain[-1] = chain[0]
        if len(chain) >= 4:
            loops.append(np.asarray(chain))
    return loops


def fit_circle(points: np.ndarray, maximum_rms_mm: float = 0.20) -> dict:
    """Least-squares circle fit with an explicit residual acceptance threshold."""
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 3:
        raise ValueError("A circle fit needs at least three XY points")
    matrix = np.column_stack((2 * points, np.ones(len(points))))
    solution, _, rank, _ = np.linalg.lstsq(matrix, np.sum(points**2, axis=1), rcond=None)
    if rank != 3:
        raise ValueError("Circle samples are collinear")
    center = solution[:2]
    radius = float(np.sqrt(solution[2] + center @ center))
    rms = float(np.sqrt(np.mean((np.linalg.norm(points - center, axis=1) - radius) ** 2)))
    if not np.isfinite(rms) or rms > maximum_rms_mm:
        raise ValueError(f"Circle RMS {rms:.4f} mm exceeds {maximum_rms_mm:.2f} mm")
    return {"center_mm": center.tolist(), "radius_mm": radius, "rms_mm": rms,
            "sample_count": len(points)}


def load_reference_triangles(path: Path) -> np.ndarray:
    """Validate a binary STL through the reference audit before reading vertices."""
    analyze_binary_stl(path)
    records = np.frombuffer(path.read_bytes(), offset=84, dtype=np.dtype([
        ("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")]))
    return records["vertices"].astype(float)


def rotate_xy(points: np.ndarray, degrees: float) -> np.ndarray:
    angle = np.radians(degrees)
    return np.asarray(points) @ np.array([[np.cos(angle), np.sin(angle)],
                                          [-np.sin(angle), np.cos(angle)]])


def measure_reference(path: Path, output_dir: Path) -> tuple[list[np.ndarray], dict]:
    triangles = load_reference_triangles(path)
    raw_loops = join_segments(slice_triangles(triangles, 35.0))
    centered = [loop - REFERENCE_AXIS_XY_MM for loop in raw_loops]
    canonical = np.vstack([rotate_xy(loop, -30.0) for loop in centered])
    # Independent nominal search windows identify the two measured arc families,
    # both wall surfaces and their 180-degree partners. Ends/junctions are omitted.
    fits = {}
    for sign in (1, -1):
        for name, center, radii, ymin, ymax in (
            ("small", (36, 0), (23.25, 24.75), 2, 24.0),
            ("large", (-48, 0), (59.25, 60.75), -53, -3),
        ):
            points = canonical * sign
            domain = points[(points[:,1] > ymin) & (points[:,1] < ymax)]
            distance = np.linalg.norm(domain - center, axis=1)
            for surface, radius in zip(("inner", "outer"), radii):
                samples = domain[abs(distance - radius) < 0.45]
                fit = fit_circle(samples * sign)
                fits[f"{name}_{surface}_{sign:+d}"] = fit
    envelope = np.vstack(centered)
    report = {
        "reference_axis_xy_mm": REFERENCE_AXIS_XY_MM.tolist(),
        "section_z_mm": 35.0, "section_angle_deg": 30.0,
        "twist_degrees_over_stage": 60.0,
        "section_size_xy_mm": np.ptp(envelope, axis=0).tolist(),
        "canonical_tangent_points_mm": [[12.0, 0.0], [-12.0, 0.0]],
        "fits": fits,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "blade-midplane.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["contour", "x_mm", "y_mm", "z_mm"])
        for index, loop in enumerate(centered):
            writer.writerows((index, float(x), float(y), 35.0) for x, y in loop)
    (output_dir / "blade-fit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return centered, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("build"))
    args = parser.parse_args()
    _, report = measure_reference(args.reference, args.output_dir)
    print(json.dumps(report, indent=2))
    return 0


if "show_object" in globals():
    import cadquery as cq
    from windwall.blade_profile import build_blade_stage
    from windwall.parameters import DEFAULT_PARAMETERS

    stage = build_blade_stage(DEFAULT_PARAMETERS)
    show_object(stage, name="Clean twisted stage", options={"color": (180, 190, 205), "alpha": 0.35})
    show_object(cq.Workplane(obj=stage.val()).section(35), name="CAD section z=35", options={"color": (220, 40, 40)})
    reference_path = os.environ.get("WINDWALL_REFERENCE_BLADE")
    contours = []
    if reference_path:
        contours, _ = measure_reference(Path(reference_path), PROJECT_ROOT / "build")
    elif (PROJECT_ROOT / "build/blade-midplane.csv").exists():
        saved = np.loadtxt(PROJECT_ROOT / "build/blade-midplane.csv", delimiter=",", skiprows=1)
        contours = [saved[saved[:,0] == index, 1:3] for index in np.unique(saved[:,0])]
    for index, contour in enumerate(contours):
        overlay = cq.Wire.makePolygon([(float(x), float(y), 35) for x, y in contour])
        show_object(overlay, name=f"Reference section {index+1}", options={"color": (20, 190, 80)})
    marker_arc = cq.Edge.makeCircle(75, cq.Vector(0, 0, 75), angle1=0, angle2=90)
    marker_head = cq.Wire.makePolygon([(5, 78, 75), (0, 75, 75), (5, 72, 75)])
    show_object(cq.Compound.makeCompound([marker_arc, marker_head]), name="CCW viewed from +Z", options={"color": (30, 90, 230)})
elif __name__ == "__main__":
    raise SystemExit(main())
