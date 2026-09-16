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
from windwall.winding_tool_service import coil_removal_stages


INK = '#213649'
MUTED = '#536573'
ACCENT = '#ad4830'
COLORS = {'structure': '#397f8b', 'wheel': '#4e74a2', 'shoe': '#e6a338',
          'shaft': '#65737b', 'snap': '#bf6655', 'bearing': '#946ca6',
          'coil': '#b36131', 'tape': '#7c994a'}
DRAWING_NAMES = ('winding-jig-reference.png', 'winding-jig-range.png',
                 'winding-tool-exploded.png')
CAMERA = (1.5, -3.5, 1.7)


def _color(name):
    if name.startswith('tape_'):
        return COLORS['tape']
    if name == 'coil':
        return COLORS['coil']
    if name.startswith('snap_collar') or name.startswith('bearing_retainer'):
        return COLORS['snap']
    if name.startswith('bearing') or name.endswith('_washer'):
        return COLORS['bearing']
    if name.startswith('shoe') or name in ('platter', 'crank', 'grip'):
        return COLORS['shoe']
    if name == 'wheel':
        return COLORS['wheel']
    if name in ('shaft', 'spindle'):
        return COLORS['shaft']
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
    p = model.parameters
    fig = _page('01  ·  Zwei einfache Module zum Wickeln von Hand',
                'Vertikales Wickelrad bei 150 mm · separater freilaufender Abroller · schraubenlos gestecktes PLA')
    fig.text(.04, .864, 'A  WICKELRAD + HANDKURBEL', fontsize=16, weight='bold', color=INK)
    fig.text(.675, .864, 'B  FREIER DRAHTABROLLER', fontsize=16, weight='bold', color=INK)
    ax, points = _project(fig, (.025, .36, .61, .49), model.winding_jig)
    height = model.ownership['winding_jig']['wheel']['axis_height_mm']
    _, right, up = _basis(CAMERA)
    hole = np.array((88, -5, height + 5))
    _callout(ax, points, 'shoe_2', '6 steckbare Schuhe', (.20, .93))
    _callout(ax, points, 'wheel', '2 Lochreihen je Speiche', (.70, .90),
             target=(hole @ right, hole @ up))
    _callout(ax, points, 'tower', 'Einseitiger Ständer', (.78, .10))
    angles = np.linspace(radians(20), radians(105), 50)
    xyz = np.column_stack((34 * np.cos(angles), np.full_like(angles, -35), height + 34 * np.sin(angles)))
    arc = np.column_stack((xyz @ right, xyz @ up))
    ax.plot(arc[:, 0], arc[:, 1], color=ACCENT, lw=2)
    ax.annotate('', arc[-1], arc[-4], arrowprops=dict(arrowstyle='-|>', color=ACCENT, lw=2))
    ax.text(.36, .58, 'nur von Hand', transform=ax.transAxes, color=ACCENT, fontsize=11)
    payoff_ax, _ = _project(fig, (.66, .45, .31, .36), model.wire_payoff, (1.6, -2.6, 1.8))
    # Dashed roll outline is a loading example, not an additional product part.
    _, right, up = _basis((1.6, -2.6, 1.8))
    top = model.wire_payoff['platter'].val().BoundingBox().zmax - p.spool_pilot_height_mm
    theta = np.linspace(0, 2 * np.pi, 100)
    for height in (top + 1, top + 48):
        xyz = np.column_stack((45 * np.cos(theta), 45 * np.sin(theta), np.full_like(theta, height)))
        payoff_ax.plot(xyz @ right, xyz @ up, '--', color=ACCENT, lw=1.2)
    for x, y in ((45, 0), (-45, 0)):
        xyz = np.array(((x, y, top + 1), (x, y, top + 48)))
        payoff_ax.plot(xyz @ right, xyz @ up, '--', color=ACCENT, lw=1.2)
    payoff_ax.set_ylim(payoff_ax.get_ylim()[0], max(payoff_ax.get_ylim()[1], top + 60))
    _labels(fig, .675, .805, ('Vorratsrolle aufrecht', '(gestrichelte Beispielkontur)'), size=11, spacing=.020)
    _labels(fig, .675, .43, (f'Teller Ø{p.platter_diameter_mm:g} mm',
                           f'Integraler Dorn Ø{p.spool_pilot_diameter_mm:g} × {p.spool_pilot_height_mm:g} mm',
                           '1 × 51105 unter dem Teller',
                           'Freier Lauf; von Hand stoppen.'), spacing=.025)
    feed = fig.add_axes((.29, .32, .44, .035))
    feed.annotate('', (.04, .5), (.96, .5), arrowprops=dict(arrowstyle='->', color=ACCENT, lw=2.5))
    feed.text(.5, 1.15, 'Drahtzufuhr B → A · 0,18-mm-Kupferlackdraht', ha='center', fontsize=12, color=INK)
    feed.axis('off')

    drive_names = ('shaft', 'snap_collar_1', 'snap_collar_2', 'bearing_608_1',
                   'bearing_608_2', 'bearing_retainer_1', 'bearing_retainer_2', 'crank', 'grip')
    drive = {name: model.winding_jig[name] for name in drive_names}
    ax, points = _project(fig, (.025, .115, .43, .17), drive, (3, -.6, 1.2), padding=.14)
    _callout(ax, points, 'shaft', 'PLA-Welle', (.28, .12))
    _callout(ax, points, 'bearing_608_1', '2 × 608', (.48, .95))
    _callout(ax, points, 'snap_collar_2', '2 Schnappringe', (.84, .85))
    fig.text(.04, .292, 'Antriebsdetail · dieselben Teile; Rad und Ständer ausgeblendet', fontsize=11, color=MUTED)
    _labels(fig, .49, .269, ('608: Außenringe im Ständer; Innenringe folgen der Welle.',
                           'Zwei Schnappringe halten die Welle am vorderen 608.',
                           'Handkurbel und Griff sind einzeln abnehmbar.',
                           'Beide Module separat gegen Rutschen/Kippen sichern.',
                           'Schutzbrille · vor jedem Versuch Risse und Drahtflächen prüfen.'),
            spacing=.029, size=12)
    return fig


def _range(model):
    p = model.parameters
    diameters = (p.minimum_diameter_mm, 150., p.maximum_diameter_mm)
    fig = _page('02  ·  Gleiche Schuhpositionen, ehrliche Bandwinkel',
                '100–200 mm in 10-mm-Schritten · alle sechs Schuhe auf dieselbe Markierung · zwei Stifte je Schuh')
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
                           'Beide Lochreihen nutzen; zwölf Rastzungen prüfen.',
                           'Die sechs Schuhmitten liegen jeweils 60° auseinander.',
                           'Drei getrennte Bandöffnungen pro Schuh = 18 insgesamt.',
                           f'Je Öffnung ≥{p.tape_clearance_mm:g} mm axial für 10-mm-Band.',
                           'Drehsinn der Frontansicht markieren; nur Handkurbel.'), spacing=.030, size=12)

    head = build_winding_head(p, 150)
    _project(fig, (.65, .145, .31, .19), {'shoe_1': head.shoe_master}, (-2.5, -.7, -1.4))
    fig.text(.65, .370, 'EIN SCHUH · RÜCKSEITE / BANDZUGANG', fontsize=12, weight='bold', color=INK)
    fig.text(.65, .120, 'Drei offene Passagen · zwei Schlüsselstifte mit Rastzungen', fontsize=11, color=INK)
    return fig


def _exploded_groups(model):
    """Partition real occurrences exactly once into readable assembly groups."""
    definitions = {
        'winding_jig': (
            ('A1  Basis', ('base',)),
            ('A2  Lagerturm', ('tower',)),
            ('A3  2 × 608 + 2 Außenclips', ('bearing_608_1', 'bearing_608_2', 'bearing_retainer_1', 'bearing_retainer_2')),
            ('A4  Welle + 2 Schnappringe', ('shaft', 'snap_collar_1', 'snap_collar_2')),
            ('A5  Kurbel + Drehgriff', ('crank', 'grip')),
            ('A6  Wickelrad', ('wheel',)),
            ('A7  6 gleiche Kontaktschuhe', tuple(f'shoe_{i}' for i in range(1, model.parameters.spoke_count + 1))),
        ),
        'wire_payoff': (
            ('B1  Basis', ('base',)),
            ('B2  1 × 51105: unten / innen / oben', ('lower_washer', 'bearing', 'upper_washer')),
            ('B3  Druckspindel', ('spindle',)),
            ('B4  Teller + integraler Dorn', ('platter',)),
        ),
    }
    groups = {}
    for tool, entries in definitions.items():
        flattened = [name for _, members in entries for name in members]
        if len(flattened) != len(set(flattened)) or set(flattened) != set(getattr(model, tool)):
            raise ValueError(f'Exploded groups must cover each {tool} occurrence exactly once')
        groups[tool] = [{'label': label, 'members': list(members),
                         'ownership': {name: model.ownership[tool][name] for name in members}}
                        for label, members in entries]
    return groups


def _spread_group(parts, members):
    """Separate parts with rigid translations; retain their real size within a group."""
    shapes, cursor = {}, 0.
    for name in members:
        body = parts[name]
        bounds = body.val().BoundingBox()
        shapes[name] = body.translate((cursor - bounds.xmin,
                                      -(bounds.ymin + bounds.ymax) / 2,
                                      -(bounds.zmin + bounds.zmax) / 2))
        cursor += bounds.xlen + 12
    return shapes


def _exploded(model):
    fig = _page('03  ·  Steckmontage und vollständige Spulenentnahme',
                'Zwei unabhängige Module · alle Bauteile in getrennten Montagegruppen · Darstellungsabstände ohne Montagefunktion')
    groups = _exploded_groups(model)
    fig.text(.035, .865, f'A  WICKELMODUL · {len(model.winding_jig)} BAUGLIEDER', fontsize=14, weight='bold', color=INK)
    fig.text(.695, .865, f'B  ABROLLER · {len(model.wire_payoff)} BAUGLIEDER', fontsize=14, weight='bold', color=INK)
    for index, group in enumerate(groups['winding_jig']):
        column, row = index % 4, index // 4
        x, y = .025 + column * .163, .685 - row * .177
        width = .153 if index != 6 else .315
        fig.text(x + .005, y + .137, group['label'], fontsize=10.5, color=INK, weight='bold')
        _project(fig, (x, y, width, .126),
                 _spread_group(model.winding_jig, group['members']), (1, -3.5, 1.4))
    for index, group in enumerate(groups['wire_payoff']):
        column, row = index % 2, index // 2
        x, y = .685 + column * .155, .685 - row * .177
        label = group['label'].replace(': unten / innen / oben', '\nunten / innen / oben')
        fig.text(x + .004, y + .137, label, fontsize=10.5, color=INK, weight='bold')
        _project(fig, (x, y, .15, .126), _spread_group(model.wire_payoff, group['members']), (1, -3, 1.8))
    _labels(fig, .035, .488, ('Steckfolge A: Basis → Turm → 608/Außenclips → Welle/2 Ringe → Kurbel/Griff → Rad → 6 Schuhe.',
                           '608: Außenringe stehen; Innenringe drehen. Zwei Ringe orten die Welle am vorderen 608.'),
            spacing=.024, size=11)
    _labels(fig, .695, .488, ('B: unten Gehäusescheibe (steht),',
                           'Wälzkranz (lagerintern), oben',
                           'Wellenscheibe (dreht mit Teller).'), spacing=.020, size=10.5)

    stages = coil_removal_stages(model)
    selected = (stages[0], stages[-2], stages[-1])
    captions = ('1  Anhalten; alle 18 Bandstellen schließen.',
                '2  Alle sechs Schuhe vollständig abnehmen.',
                '3  Getapte Spule zusammen nach vorn abziehen.')
    notes = ('Helfer hält die Spule; Leitungen A/B markieren.',
             'Je zwei Zungen lösen; vorziehen und beiseitelegen.',
             'Rad, Welle, Kurbel und Ständer bleiben montiert.')
    for index, (stage, caption, note) in enumerate(zip(selected, captions, notes)):
        parts = {**stage['fixed'], **{name: shape.translate(stage['translation_mm'])
                                    for name, shape in stage['moving'].items()}}
        direction = (2.3, -3.5, 1.6)
        ax, _ = _project(fig, (.02 + index * .326, .132, .31, .254), parts, direction)
        if stage['name'] == 'remove_taped_coil':
            height = model.ownership['winding_jig']['wheel']['axis_height_mm']
            _, right, up = _basis(direction)
            path = np.array(((30, -45, height + 52), (30, -130, height + 52)))
            projected = np.column_stack((path @ right, path @ up))
            ax.annotate('', projected[1], projected[0],
                        arrowprops=dict(arrowstyle='-|>', color=ACCENT, lw=2))
        fig.text(.035 + index * .326, .402, caption, fontsize=11, weight='bold', color=INK)
        fig.text(.035 + index * .326, .378, note, fontsize=10.5, color=INK)
    fig.text(.035, .103,
             'Service: Rastflächen lösen, Steckfolge umkehren. Abroller von oben zerlegen; beide Lagerscheiben getrennt erhalten.',
             fontsize=11, color=INK)
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
            figures.append(_range(model))
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
