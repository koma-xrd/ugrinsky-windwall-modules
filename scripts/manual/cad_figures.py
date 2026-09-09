"""Render print-readable assembly figures from the actual CadQuery solids.

The figures are explanatory CAD views, not manufacturing approval.  Printable
parts come directly from the assembly, module and generator builders; nominal
hardware is shown only as a clearly identified reference envelope.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, radians, sin
import os
from pathlib import Path
from typing import Iterable, Sequence

import cadquery as cq
import numpy as np

from scripts.manual.manual_data import load_manual_data
from windwall.assembly import (
    RotorAssembly,
    build_exploded_rotor_assembly,
    build_locked_rotor_assembly,
)
from windwall.drivers import build_drivers, build_joint_interface
from windwall.generator import lower_magnet_face_z_mm, upper_magnet_face_z_mm
from windwall.parameters import DEFAULT_PARAMETERS


@dataclass(frozen=True)
class FigureRecord:
    """Stable hand-off record used by the manual document builder."""

    drawing_id: str
    path: Path
    caption: str
    callouts: tuple[str, ...]


@dataclass(frozen=True)
class _RenderPart:
    shape: cq.Workplane
    color: str
    alpha: float = 1.0


@dataclass(frozen=True)
class _Leader:
    bom_id: str
    target: tuple[float, float, float]
    detail: str | None = None


_PRINTED = '#5f91b3'
_PRINTED_ALT = '#7babc5'
_ROTATING = '#cf8738'
_STATIONARY = '#6d9e94'
_HARDWARE = '#777d84'
_REFERENCE = '#8876a4'
_MAGNET = '#bd5b4d'
_SECTION = '#91b8cd'

_CLASSIFICATION_LEGENDS = {
    'E01': (
        (_PRINTED, 'DRUCKTEILE: P01–P05'),
        (_HARDWARE, 'AUSGEWÄHLTE HARDWARE: H01–H05 (Nennhüllen)'),
        (_REFERENCE, 'PROVISORISCHE REFERENZHÜLLEN: Stator, Lager, Distanzstück'),
    ),
    'E02': (
        (_PRINTED, 'DRUCKTEILE: P01, P05'),
        (_HARDWARE, 'AUSGEWÄHLTE HARDWARE: H01–H03 (Nennhüllen)'),
        (_REFERENCE, 'PROVISORISCH/REFERENZ: H06, H07, H10 und stationäre Generatorhüllen'),
    ),
    'E03': (
        (_PRINTED, 'DRUCKTEILE: P01, P05'),
        (_REFERENCE, 'PROVISORISCH/REFERENZ: H10; H11 Rückhaltung noch offen'),
    ),
    'E04': (
        (_PRINTED, 'DRUCKTEILE: P01, P02 einschließlich der zwei Treiber'),
        (_HARDWARE, 'AUSGEWÄHLTE HARDWARE: H04 (Nennhüllen)'),
    ),
    'E05': (
        (_PRINTED, 'DRUCKTEILE: P03, P04'),
        (_HARDWARE, 'AUSGEWÄHLTE HARDWARE: H01–H05 (Nennhüllen)'),
    ),
    'E06': (
        (_PRINTED, 'DRUCKTEILE: P01, P02, P03, P05'),
        (_HARDWARE, 'AUSGEWÄHLTE HARDWARE: H01–H03 (Nennhüllen)'),
        (_REFERENCE, 'PROVISORISCH/REFERENZ: H06, H07, H10 und stationäre Generatorhüllen'),
    ),
}

_SHORT_NAMES = {
    'P01': 'Basis-Modul / oberer Träger',
    'P02': 'Standard-Rotormodul',
    'P03': 'Top-Rotormodul',
    'P04': 'abnehmbare Abdeckung',
    'P05': 'unterer Magnetrotor',
    'H01': 'M8-Gewindestange',
    'H02': 'M8-Mutter',
    'H03': 'M8-Unterlegscheibe',
    'H04': '2 × radialer M3-Rückhalter',
    'H05': '2 × M3-Verschlussschraube',
    'H06': 'Lagerhülle (Referenz)',
    'H07': 'Distanzhülse (Referenz)',
    'H10': 'Magnete 10 × 2 mm (Referenz)',
    'H11': 'Kleber/Rückhaltung: offen',
}


def _center(shape: cq.Workplane) -> tuple[float, float, float]:
    box = shape.val().BoundingBox()
    return (
        (box.xmin + box.xmax) / 2,
        (box.ymin + box.ymax) / 2,
        (box.zmin + box.zmax) / 2,
    )


def _radial_target(shape: cq.Workplane, radius: float) -> tuple[float, float, float]:
    center = _center(shape)
    return center[0] + radius, center[1], center[2]


def _translate(shape: cq.Workplane, x: float = 0, y: float = 0, z: float = 0) -> cq.Workplane:
    return shape.translate((x, y, z))


def _compound(shapes: Iterable[cq.Workplane]) -> cq.Workplane:
    solids = [solid for shape in shapes for solid in shape.val().Solids()]
    return cq.Workplane(obj=cq.Compound.makeCompound(solids))


def _magnet_references(*, upper: bool, z_shift: float = 0) -> cq.Workplane:
    """Return nominal 10 x 2 mm magnets at the real carrier pocket centers."""

    p = DEFAULT_PARAMETERS
    g = p.generator
    face_z = upper_magnet_face_z_mm(p) if upper else lower_magnet_face_z_mm(p)
    bottom = face_z if upper else face_z - 2.0
    magnets = []
    for index in range(g.magnet_pocket_count):
        angle = 2 * pi * index / g.magnet_pocket_count
        center = (
            g.magnet_pitch_radius_mm * cos(angle),
            g.magnet_pitch_radius_mm * sin(angle),
            bottom + z_shift,
        )
        solid = cq.Solid.makeCylinder(5.0, 2.0, cq.Vector(*center), cq.Vector(0, 0, 1))
        magnets.append(cq.Workplane(obj=solid))
    return _compound(magnets)


def _projection_basis() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One orthographic isometric camera shared by all six drawings."""

    view = np.array([1.0, -1.7, 0.82], dtype=float)
    view /= np.linalg.norm(view)
    right = np.array([1.7, 1.0, 0.0], dtype=float)
    right /= np.linalg.norm(right)
    up = np.cross(view, right)
    up /= np.linalg.norm(up)
    return view, right, up


def _project(point: tuple[float, float, float]) -> tuple[float, float]:
    _, right, up = _projection_basis()
    vector = np.asarray(point, dtype=float)
    return float(vector @ right), float(vector @ up)


def _draw_geometry(
    ax,
    parts: Sequence[_RenderPart],
    *,
    horizontal_margin: float = 0.62,
) -> tuple[float, float, float, float]:
    """Tessellate real solids, globally depth-sort triangles, and draw them."""

    from matplotlib.collections import PolyCollection
    from matplotlib.colors import to_rgb

    view, right, up = _projection_basis()
    polygons: list[np.ndarray] = []
    depths: list[np.ndarray] = []
    colors: list[np.ndarray] = []
    for part in parts:
        for solid in part.shape.val().Solids():
            vertices, triangles = solid.tessellate(0.45, 0.32)
            if not triangles:
                continue
            points = np.asarray([vertex.toTuple() for vertex in vertices], dtype=float)
            xyz = points[np.asarray(triangles, dtype=int)]
            normals = np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0])
            normal_lengths = np.linalg.norm(normals, axis=1)
            normals /= np.maximum(normal_lengths[:, None], 1e-12)
            illumination = 0.50 + 0.50 * np.abs(normals @ view)
            rgb = np.asarray(to_rgb(part.color), dtype=float)
            rgba = np.column_stack((illumination[:, None] * rgb, np.full(len(xyz), part.alpha)))
            polygons.append(np.stack((xyz @ right, xyz @ up), axis=2))
            depths.append((xyz @ view).mean(axis=1))
            colors.append(rgba)
    if not polygons:
        raise ValueError('Figure scene contains no tessellated CAD triangles')
    flat_polygons = np.concatenate(polygons)
    flat_depths = np.concatenate(depths)
    flat_colors = np.concatenate(colors)
    order = np.argsort(flat_depths)
    ax.add_collection(PolyCollection(
        flat_polygons[order],
        facecolors=flat_colors[order],
        edgecolors=(0.14, 0.17, 0.19, 0.20),
        linewidths=0.10,
    ))
    xmin = float(flat_polygons[:, :, 0].min())
    xmax = float(flat_polygons[:, :, 0].max())
    ymin = float(flat_polygons[:, :, 1].min())
    ymax = float(flat_polygons[:, :, 1].max())
    width = max(xmax - xmin, 1.0)
    height = max(ymax - ymin, 1.0)
    ax.set_xlim(xmin - width * horizontal_margin, xmax + width * horizontal_margin)
    ax.set_ylim(ymin - height * 0.09, ymax + height * 0.09)
    ax.set_aspect('equal')
    ax.axis('off')
    return xmin, xmax, ymin, ymax


def _draw_leaders(
    ax,
    leaders: Sequence[_Leader],
    bounds: tuple[float, float, float, float],
    *,
    horizontal_offset: float = 0.44,
    start_number: int = 1,
    grow_inward: bool = False,
) -> None:
    xmin, xmax, ymin, ymax = bounds
    width = xmax - xmin
    height = ymax - ymin
    projected = [
        (index, leader, _project(leader.target))
        for index, leader in enumerate(leaders)
    ]
    projected.sort(key=lambda entry: (entry[2][0], entry[2][1]))
    split = (len(projected) + 1) // 2
    left = sorted(projected[:split], key=lambda entry: entry[2][1], reverse=True)
    right = sorted(projected[split:], key=lambda entry: entry[2][1], reverse=True)
    alignments = ('left', 'right') if grow_inward else ('right', 'left')
    for entries, x, alignment in (
        (left, xmin - width * horizontal_offset, alignments[0]),
        (right, xmax + width * horizontal_offset, alignments[1]),
    ):
        slots = np.linspace(ymax - height * 0.02, ymin + height * 0.02, max(len(entries), 2))
        for slot, (index, leader, target) in zip(slots, entries):
            detail = leader.detail or _SHORT_NAMES.get(leader.bom_id, leader.bom_id)
            ax.annotate(
                f'{start_number + index:02d}  {leader.bom_id}\n{detail}',
                xy=target,
                xytext=(x, float(slot)),
                ha=alignment,
                va='center',
                fontsize=7.2,
                color='#1f2930',
                linespacing=1.15,
                arrowprops={
                    'arrowstyle': '-|>',
                    'color': '#37434a',
                    'lw': 0.75,
                    'mutation_scale': 7,
                    'shrinkA': 3,
                    'shrinkB': 0,
                    'connectionstyle': 'angle3',
                },
                bbox={
                    'boxstyle': 'round,pad=0.26',
                    'facecolor': '#ffffff',
                    'edgecolor': '#aeb8be',
                    'linewidth': 0.55,
                    'alpha': 0.96,
                },
                annotation_clip=False,
            )
            ax.plot(
                target[0],
                target[1],
                marker='o',
                markersize=2.8,
                markerfacecolor='#ffffff',
                markeredgecolor='#26343b',
                markeredgewidth=0.75,
                zorder=5,
            )


def _validated_callout_ids(
    drawing_id: str,
    expected_ids: Sequence[str],
    leaders: Sequence[_Leader],
) -> tuple[str, ...]:
    """Return IDs from rendered leaders, rejecting omissions or extras."""

    expected = tuple(expected_ids)
    rendered = tuple(leader.bom_id for leader in leaders)
    if rendered == expected:
        return rendered
    missing = [bom_id for bom_id in expected if bom_id not in rendered]
    unexpected = [bom_id for bom_id in rendered if bom_id not in expected]
    details = []
    if missing:
        details.append(f"missing: {', '.join(missing)}")
    if unexpected:
        details.append(f"unexpected: {', '.join(unexpected)}")
    if not missing and not unexpected:
        details.append('leader order differs from manual data')
    raise ValueError(f"{drawing_id} rendered callouts differ from manual data; {'; '.join(details)}")


def _style_for_assembly_part(name: str) -> tuple[str, float]:
    if name.startswith('standard_') or name in {'base', 'top'}:
        return (_PRINTED_ALT if name.startswith('standard_') else _PRINTED, 1.0)
    if name == 'top_closure':
        return _ROTATING, 1.0
    if name == 'lower_magnet_rotor':
        return _ROTATING, 1.0
    if name.startswith('generator_') and name not in {'generator_upper_nut', 'generator_lower_nut'}:
        return _STATIONARY, 0.88
    if name == 'spacer':
        return _REFERENCE, 0.9
    return _HARDWARE, 1.0


def _scene_e01(exploded: RotorAssembly) -> tuple[list[_RenderPart], list[_Leader], list[str]]:
    display_shapes = dict(exploded.parts)
    generator_offsets = {
        'generator_stator_cover': -10.0,
        'generator_coil_former': -20.0,
        'lower_magnet_rotor': -32.0,
        'generator_lower_washer': -32.0,
        'generator_lower_nut': -32.0,
        'generator_base': -65.0,
        'generator_bearing': -65.0,
    }
    for name, offset in generator_offsets.items():
        display_shapes[name] = _translate(display_shapes[name], z=offset)
    display_shapes['spacer'] = _translate(display_shapes['spacer'], x=18)
    parts = [
        _RenderPart(shape, *_style_for_assembly_part(name))
        for name, shape in display_shapes.items()
    ]
    leaders = [
        _Leader('P01', _center(display_shapes['base'])),
        _Leader('P02', _center(display_shapes['standard_3'])),
        _Leader('P03', _center(display_shapes['top'])),
        _Leader('P04', _center(display_shapes['top_closure'])),
        _Leader('P05', _radial_target(display_shapes['lower_magnet_rotor'], 30)),
        _Leader('H01', _center(display_shapes['shaft'])),
        _Leader('H02', _center(display_shapes['top_nut'])),
        _Leader('H03', _center(display_shapes['top_washer'])),
        _Leader('H04', _center(display_shapes['standard_1_retainer_1'])),
        _Leader('H05', _center(display_shapes['closure_retainer_1'])),
    ]
    notes = [
        '1 Basis + 5 Standardstufen + 1 Top',
        'Stufen kumulativ abgehoben; Generatorgruppen axial geordnet; Einsetzlage -18°',
    ]
    return parts, leaders, notes


def _scene_e02(locked: RotorAssembly) -> tuple[list[_RenderPart], list[_Leader], list[str]]:
    generator = locked.generator
    shifts = {'upper': 48.0, 'cover': 23.0, 'coil': 8.0, 'base': -30.0, 'bearing': -48.0, 'lower': -70.0}
    base = _translate(generator.base_module.shape, z=shifts['upper'])
    upper_magnets = _magnet_references(upper=True, z_shift=shifts['upper'])
    cover = _translate(generator.stationary.stator_cover, z=shifts['cover'])
    coil = _translate(generator.stationary.coil_former, z=shifts['coil'])
    stationary_base = _translate(generator.stationary.base, z=shifts['base'])
    bearing = _translate(generator.stationary.bearing, z=shifts['bearing'])
    lower = _translate(generator.lower_rotor, z=shifts['lower'])
    lower_magnets = _magnet_references(upper=False, z_shift=shifts['lower'])
    spacer = _translate(generator.spacer, x=18)
    lower_washer = _translate(generator.clamp_hardware['lower_washer'], z=shifts['lower'])
    lower_nut = _translate(generator.clamp_hardware['lower_nut'], z=shifts['lower'] - 4)
    parts = [
        _RenderPart(base, _PRINTED),
        _RenderPart(upper_magnets, _MAGNET, 0.88),
        _RenderPart(cover, _STATIONARY, 0.72),
        _RenderPart(coil, _STATIONARY, 0.72),
        _RenderPart(stationary_base, _STATIONARY, 0.86),
        _RenderPart(bearing, _REFERENCE),
        _RenderPart(lower, _ROTATING),
        _RenderPart(lower_magnets, _MAGNET, 0.88),
        _RenderPart(generator.shaft, _HARDWARE),
        _RenderPart(spacer, _REFERENCE),
        _RenderPart(lower_washer, _HARDWARE),
        _RenderPart(lower_nut, _HARDWARE),
    ]
    leaders = [
        _Leader('P01', _center(base)),
        _Leader('P05', _radial_target(lower, 30)),
        _Leader('H01', _center(generator.shaft)),
        _Leader('H02', _radial_target(lower_nut, 5)),
        _Leader('H03', _radial_target(lower_washer, 10)),
        _Leader('H06', _radial_target(bearing, 5)),
        _Leader('H07', _radial_target(spacer, 5)),
        _Leader('H10', _radial_target(lower_magnets, 44.5)),
    ]
    notes = [
        'Rotierend: Orange/Blau · Stationär: Grün · Referenzhüllen: Violett',
        'Der obere Magnetträger bleibt untrennbar in P01 integriert.',
    ]
    return parts, leaders, notes


def _scene_e03(locked: RotorAssembly) -> tuple[list[_RenderPart], list[_Leader], list[str]]:
    generator = locked.generator
    base = _translate(generator.base_module.shape, z=23)
    upper_magnets = _magnet_references(upper=True, z_shift=23)
    lower = _translate(generator.lower_rotor, z=-34)
    lower_magnets = _magnet_references(upper=False, z_shift=-34)
    parts = [
        _RenderPart(base, _PRINTED),
        _RenderPart(upper_magnets, _MAGNET, 0.9),
        _RenderPart(lower, _ROTATING),
        _RenderPart(lower_magnets, _MAGNET, 0.9),
    ]
    pocket_target = _center(upper_magnets)
    leaders = [
        _Leader('P01', _center(base)),
        _Leader('P05', _radial_target(lower, 30)),
        _Leader('H10', _radial_target(lower_magnets, 44.5)),
        _Leader('H11', (pocket_target[0] + 44.5, pocket_target[1], pocket_target[2]), 'Rückhaltung vor Betrieb entwickeln'),
    ]
    notes = [
        '18 Taschen je Rotor; Magnetkörper nur als nominale Referenzhülle',
        'Kleber allein ist keine nachgewiesene Fliehkraftsicherung.',
    ]
    return parts, leaders, notes


def _joint_screws() -> tuple[cq.Workplane, cq.Workplane]:
    p = DEFAULT_PARAMETERS
    joint = build_joint_interface(p)
    result = []
    for axis in joint.screw_axes:
        angle = radians(axis.angle_deg)
        direction = (cos(angle), sin(angle), 0)
        start_radius = axis.head_radius_mm - p.manufacturing.screw_length_mm
        start = (start_radius * direction[0], start_radius * direction[1], axis.center_z_mm)
        head_start = (axis.head_radius_mm * direction[0], axis.head_radius_mm * direction[1], axis.center_z_mm)
        shank = cq.Workplane(obj=cq.Solid.makeCylinder(
            p.manufacturing.screw_nominal_diameter_mm / 2,
            p.manufacturing.screw_length_mm,
            cq.Vector(*start),
            cq.Vector(*direction),
        ))
        head = cq.Workplane(obj=cq.Solid.makeCylinder(
            p.manufacturing.screw_head_diameter_mm / 2,
            p.manufacturing.screw_head_height_mm,
            cq.Vector(*head_start),
            cq.Vector(*direction),
        ))
        result.append(shank.union(head))
    return result[0], result[1]


def _scene_e04() -> tuple[list[_RenderPart], list[_Leader], list[str]]:
    p = DEFAULT_PARAMETERS
    joint = build_joint_interface(p)
    drivers = build_drivers(p)
    screw_1, screw_2 = _joint_screws()
    left_x, right_x = -43.0, 43.0
    insertion_male = joint.male_at_travel(0).translate((left_x, 0, 16))
    insertion_drivers = drivers.rotate((0, 0, 0), (0, 0, 1), -p.bayonet.insertion_offset_deg).translate((left_x, 0, 16 - p.bayonet.ramp_rise_mm))
    locked_male = _translate(joint.male, x=right_x)
    locked_drivers = _translate(drivers, x=right_x)
    female_left = _translate(joint.female, x=left_x)
    female_right = _translate(joint.female, x=right_x)
    screw_1 = _translate(screw_1, x=right_x)
    screw_2 = _translate(screw_2, x=right_x)
    parts = [
        _RenderPart(female_left, _PRINTED, 0.82),
        _RenderPart(insertion_male, _ROTATING),
        _RenderPart(insertion_drivers, _MAGNET),
        _RenderPart(female_right, _PRINTED, 0.62),
        _RenderPart(locked_male, _ROTATING),
        _RenderPart(locked_drivers, _MAGNET),
        _RenderPart(screw_1, _HARDWARE),
        _RenderPart(screw_2, _HARDWARE),
    ]
    leaders = [
        _Leader('P01', _center(female_left), 'unteres Empfangsteil'),
        _Leader('P02', _center(insertion_male), 'oberes Teil: 3 Bajonettnasen'),
        _Leader('H04', _center(screw_1)),
    ]
    notes = [
        'LINKS: Einsetzen bei -18° (18° im Uhrzeigersinn von fluchtend)',
        'RECHTS: gegen Uhrzeigersinn bis 0° verriegeln · 3 Nasen · 2 Treiber · 2 Rückhalter',
    ]
    return parts, leaders, notes


def _scene_e05(locked: RotorAssembly) -> tuple[list[_RenderPart], list[_Leader], list[str]]:
    top_stage_z = locked.stages[-1].z_mm
    top = locked.local_modules['top']
    closure = _translate(locked.parts['top_closure'], z=-top_stage_z + 28)
    washer = _translate(locked.parts['top_washer'], z=-top_stage_z + 9)
    nut = _translate(locked.parts['top_nut'], z=-top_stage_z + 16)
    shaft = cq.Workplane('XY').circle(DEFAULT_PARAMETERS.shaft.nominal_diameter_mm / 2).extrude(112).translate((0, 0, -16))
    closure_screws = [
        _translate(locked.parts[f'closure_retainer_{index}'], z=-top_stage_z + 40)
        for index in (1, 2)
    ]
    radial_screws = [
        _translate(locked.parts[f'top_retainer_{index}'], z=-top_stage_z)
        for index in (1, 2)
    ]
    parts = [
        _RenderPart(top, _PRINTED),
        _RenderPart(closure, _ROTATING),
        _RenderPart(washer, _HARDWARE),
        _RenderPart(nut, _HARDWARE),
        _RenderPart(shaft, _HARDWARE),
        *[_RenderPart(shape, _HARDWARE) for shape in radial_screws + closure_screws],
    ]
    leaders = [
        _Leader('P03', _center(top)),
        _Leader('P04', _center(closure)),
        _Leader('H01', _center(shaft)),
        _Leader('H02', _radial_target(nut, 5)),
        _Leader('H03', _radial_target(washer, 10)),
        _Leader('H04', _center(radial_screws[0])),
        _Leader('H05', _center(closure_screws[0])),
    ]
    notes = [
        'M8-Scheibe und -Mutter klemmen P03; P04 bleibt lastfrei abnehmbar.',
        'Die zwei M3-Schrauben befestigen nur die Abdeckung.',
    ]
    return parts, leaders, notes


def _section_half(shape: cq.Workplane, zmin: float, zmax: float) -> cq.Workplane:
    cutter = (
        cq.Workplane('XY')
        .box(360, 180, zmax - zmin + 20, centered=(True, False, False))
        .translate((0, 0, zmin - 10))
    )
    return shape.intersect(cutter)


def _add_classification_legend(fig, drawing_id: str) -> None:
    """Identify the status of every displayed non-printed solid on the sheet."""

    from matplotlib.patches import Rectangle

    entries = _CLASSIFICATION_LEGENDS[drawing_id]
    positions = {
        2: ((0.055, 0.089), (0.47, 0.089)),
        3: ((0.055, 0.089), (0.47, 0.089), (0.055, 0.068)),
    }[len(entries)]
    for (x, y), (color, label) in zip(positions, entries):
        fig.add_artist(Rectangle(
            (x, y - 0.006),
            0.009,
            0.012,
            transform=fig.transFigure,
            facecolor=color,
            edgecolor='#49545a',
            linewidth=0.45,
        ))
        fig.text(x + 0.012, y, label, ha='left', va='center', fontsize=6.4, color='#29353c')


def _add_sheet_text(fig, drawing_id: str, drawing: dict, notes: Sequence[str]) -> None:
    fig.suptitle(
        f"{drawing_id}  {drawing['title']}",
        x=0.055,
        y=0.965,
        ha='left',
        fontsize=15,
        fontweight='bold',
        color='#17232a',
    )
    fig.text(0.055, 0.925, drawing['description'], ha='left', va='top', fontsize=8.4, color='#3b474e')
    _add_classification_legend(fig, drawing_id)
    fig.text(0.055, 0.027, '\n'.join(notes), ha='left', va='bottom', fontsize=7.3, color='#344149')
    fig.text(
        0.945,
        0.010,
        'CAD-REFERENZ · KEINE PHYSISCHE PASSUNGS-, FESTIGKEITS- ODER RÜCKHALTEFREIGABE',
        ha='right',
        va='bottom',
        fontsize=7.2,
        fontweight='bold',
        color='#9c3f34',
    )


def _save_standard_figure(path: Path, drawing_id: str, drawing: dict, parts, leaders, notes) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 8.4))
    fig.patch.set_facecolor('#f7f7f4')
    ax.set_facecolor('#f7f7f4')
    margin = 0.85 if drawing_id == 'E04' else 0.62
    offset = 0.55 if drawing_id == 'E04' else 0.44
    bounds = _draw_geometry(ax, parts, horizontal_margin=margin)
    _draw_leaders(
        ax,
        leaders,
        bounds,
        horizontal_offset=offset,
        grow_inward=drawing_id in {'E04', 'E05'},
    )
    _add_sheet_text(fig, drawing_id, drawing, notes)
    fig.subplots_adjust(left=0.035, right=0.965, top=0.895, bottom=0.11)
    fig.savefig(path, dpi=200, facecolor=fig.get_facecolor(), metadata={'Software': 'Windwall CAD manual renderer'})
    plt.close(fig)


def _save_section_figure(
    path: Path,
    drawing_id: str,
    drawing: dict,
    locked: RotorAssembly,
) -> list[_Leader]:
    import matplotlib.pyplot as plt

    generator = locked.generator
    full_names = [stage.name for stage in locked.stages] + ['top_closure', 'shaft']
    full_parts = []
    for name in full_names:
        shape = _section_half(locked.parts[name], -80, 570)
        color, alpha = _style_for_assembly_part(name)
        full_parts.append(_RenderPart(shape, color if name != 'shaft' else _HARDWARE, alpha))

    upper_magnets = _magnet_references(upper=True)
    lower_magnets = _magnet_references(upper=False)
    detail_shapes = [
        (generator.base_module.shape, _SECTION, 0.92),
        (generator.lower_rotor, _ROTATING, 0.95),
        (generator.stationary.coil_former, _STATIONARY, 0.82),
        (generator.stationary.stator_cover, _STATIONARY, 0.82),
        (generator.stationary.base, _STATIONARY, 0.88),
        (generator.stationary.bearing, _REFERENCE, 1.0),
        (generator.shaft, _HARDWARE, 1.0),
        (generator.spacer, _REFERENCE, 0.92),
        (generator.clamp_hardware['lower_washer'], _HARDWARE, 1.0),
        (generator.clamp_hardware['lower_nut'], _HARDWARE, 1.0),
        (upper_magnets, _MAGNET, 0.92),
        (lower_magnets, _MAGNET, 0.92),
    ]
    detail_parts = [
        _RenderPart(_section_half(shape, -85, 15), color, alpha)
        for shape, color, alpha in detail_shapes
    ]

    fig, (overview_ax, detail_ax) = plt.subplots(1, 2, figsize=(12, 8.4), gridspec_kw={'width_ratios': (0.72, 1.28)})
    fig.patch.set_facecolor('#f7f7f4')
    for ax in (overview_ax, detail_ax):
        ax.set_facecolor('#f7f7f4')
    overview_bounds = _draw_geometry(overview_ax, full_parts, horizontal_margin=0.95)
    overview_ax.set_title('A  Gesamter Wellenverlauf', fontsize=9, loc='left', pad=8)
    detail_bounds = _draw_geometry(detail_ax, detail_parts, horizontal_margin=0.95)
    detail_ax.set_title('B  Generator-Schnitt (vergrößert)', fontsize=9, loc='left', pad=8)

    overview_leaders = [
        _Leader('P01', _center(locked.parts['base']), 'Basis-Modul'),
        _Leader('P02', _center(locked.parts['standard_3']), 'Standard-Modul'),
        _Leader('P03', _center(locked.parts['top'])),
    ]
    detail_leaders = [
        _Leader('P05', _radial_target(generator.lower_rotor, 30)),
        _Leader('H01', _center(generator.shaft)),
        _Leader('H02', _radial_target(generator.clamp_hardware['lower_nut'], 5)),
        _Leader('H03', _radial_target(generator.clamp_hardware['lower_washer'], 10)),
        _Leader('H06', _radial_target(generator.stationary.bearing, 5), 'Lagerhülle (Ref.)'),
        _Leader('H07', _radial_target(generator.spacer, 5), 'Distanzhülse (Ref.)'),
        _Leader('H10', _radial_target(lower_magnets, 44.5), '10 × 2 mm (Ref.)'),
    ]
    _draw_leaders(
        overview_ax,
        overview_leaders,
        overview_bounds,
        horizontal_offset=0.58,
        grow_inward=True,
    )
    _draw_leaders(
        detail_ax,
        detail_leaders,
        detail_bounds,
        horizontal_offset=0.58,
        start_number=4,
        grow_inward=True,
    )

    upper_face = upper_magnet_face_z_mm(DEFAULT_PARAMETERS)
    upper_stator = generator.stationary.stator_cover.val().BoundingBox().zmax
    lower_face = lower_magnet_face_z_mm(DEFAULT_PARAMETERS)
    lower_stator = generator.stationary.coil_former.val().BoundingBox().zmin
    x = DEFAULT_PARAMETERS.generator.coil_former_diameter_mm / 2 + 4
    for label, z1, z2 in (
        ('oben 1,5 mm', upper_stator, upper_face),
        ('unten 1,5 mm', lower_face, lower_stator),
    ):
        start = _project((x, 0, z1))
        end = _project((x, 0, z2))
        detail_ax.plot([start[0], end[0]], [start[1], end[1]], color='#a3473c', lw=1.4)
        detail_ax.annotate(
            label,
            xy=((start[0] + end[0]) / 2, (start[1] + end[1]) / 2),
            xytext=(14, 0),
            textcoords='offset points',
            fontsize=7.5,
            color='#8d382f',
            va='center',
            bbox={'facecolor': '#fff9f6', 'edgecolor': '#c88980', 'boxstyle': 'round,pad=0.2'},
        )

    notes = [
        'Nennluftspalt je Seite: 1,5 mm – nur bei bündig oder versenkt sitzenden Magneten.',
        'Magnettaschenboden, Lager und Distanzhülse sind sichtbar; Passung und axiale Sicherung bleiben offen.',
    ]
    _add_sheet_text(fig, drawing_id, drawing, notes)
    fig.subplots_adjust(left=0.035, right=0.965, top=0.87, bottom=0.12, wspace=0.12)
    fig.savefig(path, dpi=200, facecolor=fig.get_facecolor(), metadata={'Software': 'Windwall CAD manual renderer'})
    plt.close(fig)
    return overview_leaders + detail_leaders


def render_cad_figures(project_root: Path, output_dir: Path) -> list[FigureRecord]:
    """Render E01-E06 into ``output_dir`` and return stable figure records."""

    project_root = Path(project_root).resolve()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache = project_root / 'build' / 'matplotlib'
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR', str(cache))
    import matplotlib

    matplotlib.use('Agg')
    data = load_manual_data(project_root)
    locked = build_locked_rotor_assembly(DEFAULT_PARAMETERS)
    exploded = build_exploded_rotor_assembly(DEFAULT_PARAMETERS, locked=locked)
    scene_builders = {
        'E01': lambda: _scene_e01(exploded),
        'E02': lambda: _scene_e02(locked),
        'E03': lambda: _scene_e03(locked),
        'E04': _scene_e04,
        'E05': lambda: _scene_e05(locked),
    }
    records = []
    for drawing_id in ('E01', 'E02', 'E03', 'E04', 'E05', 'E06'):
        drawing = data['drawings'][drawing_id]
        path = output_dir / Path(drawing['figure_file']).name
        if drawing_id == 'E06':
            leaders = _save_section_figure(path, drawing_id, drawing, locked)
            callouts = _validated_callout_ids(drawing_id, drawing['items'], leaders)
        else:
            parts, leaders, notes = scene_builders[drawing_id]()
            callouts = _validated_callout_ids(drawing_id, drawing['items'], leaders)
            _save_standard_figure(path, drawing_id, drawing, parts, leaders, notes)
        records.append(FigureRecord(
            drawing_id=drawing_id,
            path=path,
            caption=f"{drawing['title']}. {drawing['description']}",
            callouts=callouts,
        ))
    return records


__all__ = ['FigureRecord', 'render_cad_figures']
