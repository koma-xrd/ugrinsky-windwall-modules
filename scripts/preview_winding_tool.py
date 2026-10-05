"""Deterministic drawings and guide tables for the two manual PLA tools.

Every solid is an actual current CAD occurrence. Fixed orthographic cameras,
fresh serial tessellation, palette and bundled DejaVu font make repeat renders
byte-identical. Exploded groups and operating poses have explicit ownership;
presentation offsets never change the assembly or its audits. No V5 inventory
or geometry is imported. Run CAD entry points through run_geometry.py.
"""

import argparse
from math import cos, radians, sin
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for import_root in (PROJECT_ROOT, PROJECT_ROOT / 'src'):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / 'build' / 'matplotlib'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgb
from matplotlib.patches import Circle
import numpy as np

from windwall.winding_head import build_winding_head
from windwall.winding_tool_parameters import diameter_settings_mm
from windwall.winding_tool_service import coil_removal_stages, _winding_fixture, installed_shape


INK = '#213649'
MUTED = '#536573'
ACCENT = '#ad4830'
COLORS = {'structure': '#397f8b', 'wheel': '#4e74a2', 'shoe': '#e6a338',
          'journal': '#65737b', 'bearing': '#946ca6',
          'coil': '#b36131', 'tape': '#7c994a'}
DRAWING_NAMES = ('winding-jig-reference.png', 'winding-jig-range.png',
                 'winding-tool-exploded.png')
CAMERA = (1.5, -3.5, 1.7)
CRADLE_PROFILE_VIEW_DIRECTION = (-2.5, -0.7, -1.4)


def _color(name):
    if name.startswith('tape_'):
        return COLORS['tape']
    if name == 'coil':
        return COLORS['coil']
    if name.startswith('bearing') or name.endswith('_washer'):
        return COLORS['bearing']
    if name.startswith('shoe') or name in ('platter', 'crank', 'grip'):
        return COLORS['shoe']
    if name == 'wheel':
        return COLORS['wheel']
    if name in ('hub', 'spindle'):
        return COLORS['journal']
    return COLORS['structure']


def _page(title, subtitle):
    fig = plt.figure(figsize=(20, 14), dpi=100, facecolor='white')
    fig.text(.035, .951, title, fontsize=26, weight='bold', color=INK)
    fig.text(.035, .916, subtitle, fontsize=14, color=MUTED)
    fig.text(.035, .047,
             'PLA-Werkstattprototyp · CAD-Nennmaße in mm · Ansichten nicht maßstäblich · physisch ungeprüft',
             fontsize=11, color=MUTED)
    fig.text(.035, .021, 'Akkuschrauberbetrieb ist nicht freigegeben',
             fontsize=12, weight='bold', color=ACCENT)
    return fig


def _basis(direction):
    view = np.asarray(direction, dtype=float)
    view /= np.linalg.norm(view)
    right = np.cross((0, 0, 1), view)
    if np.linalg.norm(right) < 1e-8:
        right = np.array((1., 0., 0.))
    right /= np.linalg.norm(right)
    return view, right, np.cross(view, right)


def _cradle_profile_projection_contract():
    """Describe the unrotated shoe axes in drawing 02's screen projection."""
    _, _, screen_up = _basis(CRADLE_PROFILE_VIEW_DIRECTION)
    positive_z_screen_y = float(np.dot((0., 0., 1.), screen_up))
    if positive_z_screen_y <= 0:
        raise ValueError('Drawing 02 must project the shoe free-front +Z side above the wheel side')
    return {
        'view_direction': list(CRADLE_PROFILE_VIEW_DIRECTION),
        'local_positive_z_feature': 'free_front',
        'local_positive_z_screen_direction': 'above',
        'local_negative_z_feature': 'wheel_side',
        'local_negative_z_screen_direction': 'below',
    }


def _project(fig, rectangle, parts, direction=CAMERA, padding=.09):
    """Project copied CAD meshes; fine planar triangles keep openings visible."""
    ax = fig.add_axes(rectangle)
    view, right, up = _basis(direction)
    polygons, depths, shades, points_by_name = [], [], [], {}
    for name, body in sorted(parts.items()):
        vertices, faces = body.val().copy(mesh=False).tessellate(.20, .15)
        triangles = np.asarray([v.toTuple() for v in vertices])[np.asarray(faces)]
        finished = []
        while len(triangles):
            large = np.linalg.norm(triangles - np.roll(triangles, 1, axis=1), axis=2).max(axis=1) > 8
            finished.append(triangles[~large])
            a, b, c = triangles[large].transpose(1, 0, 2)
            ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
            triangles = np.concatenate([np.stack(group, axis=1) for group in
                                        ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca))])
        xyz = np.concatenate(finished)
        normals = np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0])
        normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
        illumination = .63 + .37 * np.abs(normals @ view)
        projected = np.stack((xyz @ right, xyz @ up), axis=2)
        polygons.append(projected)
        depths.append((xyz @ view).mean(axis=1))
        shades.append(illumination[:, None] * np.asarray(to_rgb(_color(name))))
        points_by_name[name] = projected.reshape(-1, 2)
    flat = np.concatenate(polygons)
    order = np.argsort(np.concatenate(depths), kind='stable')
    ax.add_collection(PolyCollection(flat[order], facecolors=np.concatenate(shades)[order],
                                    edgecolors='none', linewidths=0, antialiaseds=False))
    points = flat.reshape(-1, 2)
    lower, upper = points.min(axis=0), points.max(axis=0)
    span = np.maximum(upper - lower, 1)
    ax.set_xlim(lower[0] - padding * span[0], upper[0] + padding * span[0])
    ax.set_ylim(lower[1] - padding * span[1], upper[1] + padding * span[1])
    ax.set_aspect('equal')
    ax.axis('off')
    return ax, points_by_name


def _labels(fig, x, y, rows, spacing=.026, size=12):
    for index, row in enumerate(rows):
        fig.text(x, y - index * spacing, row, fontsize=size, color=INK, va='top')


def _callout(ax, points, name, text, position, target=None):
    target = points[name].mean(axis=0) if target is None else target
    ax.annotate(text, target, xytext=position, textcoords='axes fraction',
                fontsize=11, color=INK, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=.25', fc='white', ec='#ccd4db'),
                arrowprops=dict(arrowstyle='-', lw=.8, color=INK))


def _rotation_arrow(ax, center, radius):
    angles = np.linspace(radians(20), radians(105), 50)
    points = np.column_stack((np.cos(angles), np.sin(angles))) * radius + center
    ax.plot(points[:, 0], points[:, 1], color=ACCENT, lw=2)
    ax.annotate('', points[-1], points[-4],
                arrowprops=dict(arrowstyle='-|>', color=ACCENT, lw=2))


def _reference(model):
    fig = _page('01  ·  Waagerechtes Wickelrad und freier Drahtabroller',
                'Gemeinsame Basis: 190 × 190 mm · je ein 51105 · steckbare Handkurbel · Referenz Ø150 mm')
    height = model.ownership['winding_jig']['wheel']['axis_height_mm']
    winding = {name: installed_shape(shape, height)
               for name, shape in _winding_fixture(model.parameters, 150).items()}
    ax, points = _project(fig, (.02, .37, .49, .51), {**model.winding_jig, **winding})
    _callout(ax, points, 'wheel', 'Waagerechtes Wickelrad', (.25, .16))
    _callout(ax, points, 'crank', '6,35-mm-Sechskant: abziehbare Kurbel', (.58, .96))
    _callout(ax, points, 'shoe_2', '6 oben offene Kontaktschuhe', (.76, .68))
    _, right, up = _basis(CAMERA)
    start, end = (np.array((60, -45, z)) for z in (8, 33))
    start, end = np.array((start @ right, start @ up)), np.array((end @ right, end @ up))
    ax.annotate('', end, start, arrowprops=dict(arrowstyle='<->', color=ACCENT, lw=1.5))
    ax.text(*(start + end) / 2, ' 25 mm', color=ACCENT, fontsize=11, weight='bold')
    ax, points = _project(fig, (.53, .37, .44, .51), model.wire_payoff)
    _callout(ax, points, 'platter', 'Ø150-mm-Teller', (.67, .65))
    _callout(ax, points, 'base', 'Identische Basis: zweimal drucken', (.40, .12))
    _labels(fig, .035, .34, (
        'Wickler: Lastweg Rad → Nabe → obere Scheibe → Wälzkranz → untere Scheibe → Basis.',
        '25 mm freier Arbeitsraum unter dem Rad außerhalb des mittigen Lagersitzes.',
        '18 Bandstellen: im Stillstand umwickeln; danach Kurbel entfernen und Spule nach oben abheben.',
        'Drahtabroller bleibt unverändert: Kupferrolle aufrecht, Zentrierung Ø15 × 20 mm.',
        'Kein automatischer Vorschub und keine Bremse: Draht führen, Rolle von Hand stoppen.',
        'Passungen, Lagerlauf und PLA-Festigkeit vor der ersten Probespule prüfen.',
    ), spacing=.043, size=14)
    return fig


def _range(model):
    p = model.parameters
    diameters = (p.minimum_diameter_mm, 150., p.maximum_diameter_mm)
    fig = _page('02  ·  Gleiche Schuhpositionen, ehrliche Bandwinkel',
                '100–200 mm in 10-mm-Schritten · alle sechs Schuhe auf dieselbe Markierung · zwei Reibzungen je Schuh')
    for index, diameter in enumerate(diameters):
        head = build_winding_head(p, diameter)
        parts = {'wheel': head.wheel, **{f'shoe_{i}': shoe for i, shoe in enumerate(head.shoes, 1)}}
        ax, _ = _project(fig, (.025 + index * .326, .485, .30, .37), parts, (0, 0, 1))
        for envelope, color, style in zip(diameters, ('#a64d40', '#213649', '#387c85'), (':', '-', '--')):
            ax.add_patch(Circle((0, 0), envelope / 2, fill=False, edgecolor=color, lw=1.1, linestyle=style))
        actual = head.metadata['actual_tape_angles_deg']
        for station, angle in enumerate(actual, 1):
            theta = radians(angle)
            radius = diameter / 2 + 10
            ax.text(radius * cos(theta), radius * sin(theta), str(station), fontsize=9.5,
                    color=INK, ha='center', va='center',
                    bbox=dict(boxstyle='circle,pad=.10', fc='white', ec='none'))
        ax.set_xlim(-119, 119)
        ax.set_ylim(-119, 119)
        _rotation_arrow(ax, (0, 0), 33)
        fig.text(.175 + index * .326, .864, f'Ø{diameter:g} mm', ha='center', fontsize=21, weight='bold', color=INK)
        alpha = (actual[2] - actual[1]) % 360
        fig.text(.175 + index * .326, .478, f'Je Schuh: Mitte ±{alpha:.2f}°', ha='center', fontsize=12, color=INK)
    fig.text(.035, .440, 'Hüllkreise 100 / 150 / 200 mm; tatsächliche Wicklung: gerundete Sechseckform.', fontsize=12, color=INK)
    fig.text(.035, .414, 'Zahlen 1–18 = nominale Stationsidentitäten. Keine gleichmäßige physische 20°-Teilung, auch bei 150 mm.', fontsize=12, color=ACCENT)

    setting_text = '   '.join(f'{diameter:g}' for diameter in diameter_settings_mm(p))
    fig.text(.035, .370, 'ELF MARKIERTE EINSTELLUNGEN (mm)', fontsize=13, weight='bold', color=INK)
    fig.text(.035, .337, setting_text, fontsize=16, weight='bold', color=INK)
    _labels(fig, .035, .293, ('Ein Schritt = 10 mm Durchmesser / 5 mm radial.',
                           'Beide Öffnungsreihen nutzen; zwölf Reibzungen prüfen.',
                           'Die sechs Schuhmitten liegen jeweils 60° auseinander.',
                           'Drei getrennte Bandöffnungen pro Schuh = 18 insgesamt.',
                           f'Je ≥{p.tape_clearance_mm:g} mm tangential und axial; 10-mm-Band.',
                           'Rad liegt waagerecht; Spule hebt nach oben ab.'), spacing=.030, size=12)

    head = build_winding_head(p, 150)
    projection = _cradle_profile_projection_contract()
    _project(fig, (.65, .145, .31, .19), {'shoe_1': head.shoe_master},
             CRADLE_PROFILE_VIEW_DIRECTION)
    annotations = {
        'wheel_side': ('Radseite unten: gerundete Auflage '
                       f'+{head.metadata["rear_shoulder_height_mm"]:.1f} mm').replace('.', ','),
        'free_front': ('Oben offen: Überstand '
                       f'+{head.metadata["free_shoulder_height_mm"]:.1f} mm').replace('.', ','),
    }
    fig.text(.65, .370, 'EIN SCHUH · SPULE NACH OBEN ABZIEHEN',
             fontsize=12, weight='bold', color=INK)
    fig.text(.65, .130, 'Drei offene Passagen · zwei massive Schienen-Reibzungen',
             fontsize=10.5, color=INK)
    _labels(fig, .65, .108, annotations.values(), spacing=.019, size=10.5)
    return fig, annotations, projection


def _exploded_groups(model):
    """Partition every installed solid exactly once; preserve its ownership."""
    definitions = {
        'winding_jig': (
            ('A1  Gemeinsame Basis', ('base',)),
            ('A2  51105: unten / Wälzkranz / oben', ('lower_washer', 'bearing', 'upper_washer')),
            ('A3  Gedruckte horizontale Nabe', ('hub',)),
            ('A4  Einstellbares Wickelrad', ('wheel',)),
            ('A5  6 gleiche offene Schuhe', tuple(f'shoe_{i}' for i in range(1, 7))),
            ('A6  Steckkurbel + drehbarer Griff', ('crank', 'grip')),
        ),
        'wire_payoff': (
            ('B1  Gleiche Basis', ('base',)),
            ('B2  Gedruckte Steckachse', ('spindle',)),
            ('B3  Zweites komplettes 51105', ('lower_washer', 'bearing', 'upper_washer')),
            ('B4  Teller + Zentriernippel', ('platter',)),
        ),
    }
    result = {}
    for tool, entries in definitions.items():
        names = [name for _, members in entries for name in members]
        if len(names) != len(set(names)) or set(names) != set(getattr(model, tool)):
            raise ValueError(f'Exploded groups must cover each {tool} occurrence exactly once')
        result[tool] = [{'label': label, 'members': list(members),
                        'ownership': {name: model.ownership[tool][name] for name in members}}
                       for label, members in entries]
    return result


def _spread_group(parts, members):
    """Separate the three actual bearing members only for presentation."""
    result = {name: parts[name] for name in members}
    if set(members) == {'lower_washer', 'bearing', 'upper_washer'}:
        result['bearing'] = result['bearing'].translate((0, 0, 12))
        result['upper_washer'] = result['upper_washer'].translate((0, 0, 24))
    return result


def _exploded(model):
    fig = _page('03  ·  Zwei Module, gemeinsame Basis und Abzug nach oben',
                'Kaufteile violett: zwei komplette 51105 · keine Lagerteile drucken · keine Schuhe beim Abzug entfernen')
    groups = _exploded_groups(model)
    for index, group in enumerate(groups['winding_jig']):
        x = .025 + index * .163
        _project(fig, (x, .64, .145, .20), _spread_group(model.winding_jig, group['members']))
        fig.text(x, .855, group['label'], fontsize=10.5, color=INK, weight='bold')
    for index, group in enumerate(groups['wire_payoff']):
        x = .035 + index * .242
        _project(fig, (x, .385, .22, .18), _spread_group(model.wire_payoff, group['members']))
        fig.text(x, .59, group['label'], fontsize=11, color=INK, weight='bold')
    fig.text(.035, .355, 'SPULENABZUG: alle sechs Schuhe bleiben eingesteckt; Lagerung und Rad bleiben montiert.',
             fontsize=14, color=ACCENT, weight='bold')
    labels = ('1  Wicklung im Stillstand tapen', '2  Kurbel und Griff nach oben abnehmen',
              '3  Getapte Spule senkrecht nach oben abheben')
    for index, (stage, label) in enumerate(zip(coil_removal_stages(model), labels)):
        x = .03 + index * .326
        parts = {**stage['fixed'], **stage['moving']}
        # Show the end pose of each authorized motion, with every solid retained.
        for name, shape in stage['moving'].items():
            parts[name] = shape.translate(stage['translation_mm'])
        _project(fig, (x, .09, .30, .22), parts, (1.5, -3.5, 1.2))
        fig.text(x, .315, label, fontsize=11, color=INK)
    return fig, groups


def render_winding_tool_drawings(model, destination: Path) -> tuple[dict, ...]:
    """Render all three required PNGs and return their portable support records."""
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    with plt.rc_context({'font.family': 'DejaVu Sans', 'font.size': 12,
                         'path.simplify': False, 'savefig.facecolor': 'white'}):
        figures = []
        try:
            figures.append(_reference(model))
            range_figure, cradle_annotations, cradle_projection = _range(model)
            figures.append(range_figure)
            exploded, groups = _exploded(model)
            figures.append(exploded)
            for filename, fig in zip(DRAWING_NAMES, figures):
                fig.savefig(destination / filename, dpi=100,
                            metadata={'Software': 'windwall simple winding-tool renderer'})
                records.append({'path': f'drawings/{filename}', 'width_px': 2000, 'height_px': 1400,
                                'source_builder': 'scripts.preview_winding_tool.render_winding_tool_drawings',
                                'presentation_only': True})
        finally:
            for fig in figures:
                plt.close(fig)
    records[1]['cradle_profile_annotations'] = cradle_annotations
    records[1]['cradle_profile_projection'] = cradle_projection
    records[-1]['exploded_groups'] = groups
    return tuple(records)


def _table_block(source, name, lines):
    start, end = f'<!-- BEGIN {name} -->', f'<!-- END {name} -->'
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError(f'German guide must contain one {name} block')
    before, remainder = source.split(start)
    _, after = remainder.split(end)
    return before + start + '\n' + '\n'.join(lines) + '\n' + end + after


def winding_tool_guide(model, bom):
    """Synchronize the author-maintained guide's canonical BOM and angle tables."""
    source = (PROJECT_ROOT / 'docs/serpentine-coil-winding-tool-de.md').read_text('utf-8')
    print_lines = ['| Menge | Master | STL-Stamm | Material |', '| ---: | --- | --- | --- |']
    hardware_lines = ['| Menge | Kaufteil | Nennmaße und Umfang |', '| ---: | --- | --- |']
    for row in bom['items']:
        if row['source'] == 'printed':
            print_lines.append(f"| {row['quantity']} | `{row['master']}` | `{row['master'].replace('/', '_')}` | {row['material']} |")
        else:
            hardware_lines.append(f"| {row['quantity']} | `{row['name']}` | {row['specification']} |")
    angle_lines = ['| Markierung / Nennhülle (mm) | Physische Winkel je Schuhmitte |', '| ---: | --- |']
    for diameter in diameter_settings_mm(model.parameters):
        actual = build_winding_head(model.parameters, diameter).metadata['actual_tape_angles_deg']
        alpha = (actual[2] - actual[1]) % 360
        angle_lines.append(f'| {diameter:g} | −{alpha:.2f}° / 0° / +{alpha:.2f}° |')
    for name, lines in (('print-bom', print_lines), ('hardware-bom', hardware_lines), ('tape-angles', angle_lines)):
        source = _table_block(source, name, lines)
    return source


def main():
    from windwall.winding_tool_assembly import build_winding_tool_assemblies

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=PROJECT_ROOT / 'build/winding-tool-drawings')
    args = parser.parse_args()
    render_winding_tool_drawings(build_winding_tool_assemblies(), args.output_dir)
    print(f'Three winding-tool drawings: {args.output_dir}', flush=True)


if __name__ == '__main__':
    main()
