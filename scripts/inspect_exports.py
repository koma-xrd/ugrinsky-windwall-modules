"""Render STEP/STL and sections for visual QA, without opening a native GUI.

Run through scripts/run_geometry.py, or use build_all.py --inspect. Views read
the current manifest's artifacts and verify their hashes before rendering.
This visual evidence complements the solid/mesh audits, not physical fitting.
"""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for import_root in (PROJECT_ROOT, PROJECT_ROOT / 'src'):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import cadquery as cq
import numpy as np


def _projection(ax, triangles, view, color):
    from matplotlib.colors import to_rgb

    direction = np.array(view, dtype=float)
    direction /= np.linalg.norm(direction)
    right = np.cross([0, 0, 1], direction)
    right /= np.linalg.norm(right)
    up = np.cross(direction, right)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
    brightness = .35 + .65 * np.abs(normals @ direction)
    projected = np.stack((triangles @ right, triangles @ up, triangles @ direction), axis=2)
    lower, upper = projected[:, :, :2].min(axis=(0, 1)), projected[:, :, :2].max(axis=(0, 1))
    scale = 650 / max(upper - lower)
    width, height = np.ceil((upper - lower) * scale).astype(int) + 3
    pixels = np.ones((height, width, 3))
    depths = np.full((height, width), -np.inf)
    # Per-pixel depth avoids centroid-sorting artifacts: a hidden pocket wall
    # must never paint over the large flat underside of its enclosing solid.
    for triangle, shade in zip(projected, brightness):
        screen = (triangle[:, :2] - lower) * scale + 1
        x0, y0 = np.maximum(np.floor(screen.min(axis=0)).astype(int), 0)
        x1, y1 = np.minimum(np.ceil(screen.max(axis=0)).astype(int) + 1, (width, height))
        a, b, c = screen
        denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(denominator) < 1e-12:
            continue
        x, y = np.meshgrid(np.arange(x0, x1) + .5, np.arange(y0, y1) + .5)
        first = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / denominator
        second = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / denominator
        third = 1 - first - second
        inside = (first >= -1e-10) & (second >= -1e-10) & (third >= -1e-10)
        depth = first * triangle[0, 2] + second * triangle[1, 2] + third * triangle[2, 2]
        visible = inside & (depth > depths[y0:y1, x0:x1])
        depths[y0:y1, x0:x1][visible] = depth[visible]
        pixels[y0:y1, x0:x1][visible] = shade * np.array(to_rgb(color))
    ax.imshow(pixels, origin='lower', extent=(lower[0] - 1 / scale,
              lower[0] + (width - 1) / scale, lower[1] - 1 / scale,
              lower[1] + (height - 1) / scale))
    ax.set_aspect('equal')
    ax.margins(.07)


def _section(ax, shape, z=None):
    workplane = cq.Workplane(obj=shape)
    if z is None:
        section = workplane.rotate((0, 0, 0), (1, 0, 0), 90).section(0)
    else:
        section = workplane.section(z)
    for edge in section.val().Edges():
        points = edge.positions(np.linspace(0, 1, max(2, int(edge.Length() / .2))))
        ax.plot([p.x for p in points], [-p.y if z is None else p.y for p in points],
                color='#236486', linewidth=1)
    ax.set_aspect('equal')
    ax.grid(alpha=.2)


def inspect_exports(manifest_path: Path) -> None:
    root = manifest_path.resolve().parent
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    cache = root / 'matplotlib'
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR', str(cache))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from scripts.preview_assembly import _static_inspection

    destination = root / 'inspection'
    destination.mkdir(parents=True, exist_ok=True)
    for record in manifest['production_parts'] + manifest['coupons'] + manifest['assemblies']:
        for suffix in ('step', 'stl'):
            if f'{suffix}_path' not in record:
                continue
            path = root / record[f'{suffix}_path']
            if sha256(path.read_bytes()).hexdigest() != record[f'{suffix}_sha256']:
                raise ValueError(f'Artifact changed since validation: {path}')
    triangle_dtype = np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')])
    manufacturing = manifest['parameters']['manufacturing']
    for part in manifest['production_parts'] + manifest['coupons']:
        solid = cq.importers.importStep(str(root / part['step_path'])).val()
        vertices, indices = solid.tessellate(manufacturing['export_linear_tolerance_mm'],
                                            manufacturing['export_angular_tolerance_rad'])
        step_triangles = np.array([vertex.toTuple() for vertex in vertices])[np.array(indices)]
        payload = (root / part['stl_path']).read_bytes()
        stl_triangles = np.frombuffer(payload, dtype=triangle_dtype, offset=84)['vertices'].astype(float)
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        for ax, triangles, view, title, color in (
            (axes[0, 0], step_triangles, (1, -2, 1.5), 'STEP | from above', '#5b99b7'),
            (axes[0, 1], stl_triangles, (1, -2, 1.5), 'STL | from above, print Z=0', '#c0903e'),
            (axes[0, 2], step_triangles, (1, -2, -1.5), 'STEP | underside', '#5b99b7'),
        ):
            _projection(ax, triangles, view, color)
            ax.set_title(title)
        box = solid.BoundingBox()
        for ax, plane, title in (
            (axes[1, 0], None, 'STEP XZ section | shaft and pocket floors'),
            (axes[1, 1], box.zmin + box.zlen / 2, 'STEP XY section | mid-height'),
            (axes[1, 2], box.zmax - min(1, box.zlen / 4), 'STEP XY section | 1 mm below top'),
        ):
            _section(ax, solid, plane)
            ax.set_title(title, fontsize=9)
            ax.set_xlabel('X / mm')
            ax.set_ylabel('Z / mm' if plane is None else 'Y / mm')
        dimensions = ' × '.join(f'{value:.2f}' for value in part['cad_bounds_mm']['size_xyz'])
        fig.suptitle(f"{part['name']} | {dimensions} mm | {part['cad_volume_mm3']:.2f} mm³\n"
                     'Actual exported geometry; supports, hardware and physical fit unverified', fontsize=14)
        fig.tight_layout(rect=(0, 0, 1, .94))
        fig.savefig(destination / f"{part['name']}.png", dpi=140)
        plt.close(fig)
    _static_inspection(root / 'assembly', manifest['assembly_audit'])
    print(f'Inspected artifact hashes and rendered 10 part sheets plus locked/exploded assembly sections in {root}', flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path, nargs='?', default=PROJECT_ROOT / 'build/manifest.json')
    inspect_exports(parser.parse_args().manifest)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
