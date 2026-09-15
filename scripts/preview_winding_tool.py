"""Deterministic workshop drawings from the actual winding-tool CAD bodies.

Orthographic triangle projections use fixed cameras, canvas, font and palette.
Exploded translations are presentation data, never an operating configuration.
No V5 geometry or rendering inventory is consumed. Run via run_geometry.py.
"""

import argparse
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
import cadquery as cq

from windwall.winding_head import build_winding_head, tape_station_angles
from windwall.winding_tool_service import brake_access_key, coil_removal_stages


COLORS = {'structure': '#3b8d91', 'rib': '#d89932', 'cam': '#5972b9',
          'hardware': '#8d98a5', 'bearing': '#9363a4', 'clamp': '#c46845'}
INK = '#25384b'
DRAWING_NAMES = ('winding-jig-reference.png', 'winding-jig-range.png',
                 'winding-tool-exploded.png')


def _color(name):
    if name == 'coil':
        return '#bc6540'
    if 'bearing' in name or name in ('shaft_washer', 'housing_washer', 'rolling_envelope'):
        return COLORS['bearing']
    if name.rsplit('_', 1)[0] in ('rib', 'slider'):
        return COLORS['rib'] if name.startswith('rib_') else COLORS['cam']
    if name == 'cam':
        return COLORS['cam']
    if name in ('clamp', 'adjuster'):
        return COLORS['clamp']
    if name in ('platter', 'crank', 'head_hub', 'head_retaining_collar'):
        return COLORS['rib']
    if name in ('base', 'backplate', 'left_upright', 'right_upright'):
        return COLORS['structure']
    return COLORS['hardware']


def _page(title, subtitle):
    fig = plt.figure(figsize=(20, 14), dpi=100, facecolor='white')
    fig.text(.04, .947, title, fontsize=27, weight='bold', color=INK)
    fig.text(.04, .908, subtitle, fontsize=15, color=INK)
    fig.text(.04, .055, 'Werkstatthilfe / Prototyp · CAD-Nennmaße in mm · nicht maßstäblich · physisch ungeprüft',
             fontsize=12, color=INK)
    fig.text(.04, .030, 'Akkuschrauberbetrieb ist nicht freigegeben', fontsize=13, weight='bold', color='#a54432')
    return fig


def _project(fig, rectangle, parts, direction):
    """Draw copied meshes, so prior export tessellation cannot affect pixels."""
    ax = fig.add_axes(rectangle)
    view = np.asarray(direction, dtype=float)
    view /= np.linalg.norm(view)
    right = np.cross((0, 0, 1), view)
    if np.linalg.norm(right) < 1e-8:
        right = np.array((1., 0., 0.))
    right /= np.linalg.norm(right)
    up = np.cross(view, right)
    polygons, depths, shades, points_by_name = [], [], [], {}
    for name, body in sorted(parts.items()):
        vertices, faces = body.val().copy(mesh=False).tessellate(.25, .2)
        triangles = np.asarray([v.toTuple() for v in vertices])[np.asarray(faces)]
        # Bound planar triangle size to keep a far centroid from painting over
        # a nearer bearing or tape opening. This changes no CAD geometry.
        finished = []
        while len(triangles):
            large = np.linalg.norm(triangles - np.roll(triangles, 1, axis=1), axis=2).max(axis=1) > 10
            finished.append(triangles[~large])
            a, b, c = triangles[large].transpose(1, 0, 2)
            ab, bc, ca = (a+b)/2, (b+c)/2, (c+a)/2
            triangles = np.concatenate([np.stack(group, axis=1) for group in
                                        ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca))])
        xyz = np.concatenate(finished)
        normals = np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0])
        normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
        illumination = .6 + .4*np.abs(normals @ view)
        projected = np.stack((xyz @ right, xyz @ up), axis=2)
        polygons.append(projected)
        depths.append((xyz @ view).mean(axis=1))
        shades.append(illumination[:, None]*np.asarray(to_rgb(_color(name))))
        points_by_name[name] = projected.reshape(-1, 2)
    flat = np.concatenate(polygons)
    order = np.argsort(np.concatenate(depths), kind='stable')
    ax.add_collection(PolyCollection(flat[order], facecolors=np.concatenate(shades)[order],
                                    edgecolors='none', linewidths=0, antialiaseds=False))
    points = flat.reshape(-1, 2)
    lower, upper = points.min(axis=0), points.max(axis=0)
    span = np.maximum(upper-lower, 1)
    ax.set_xlim(lower[0]-.12*span[0], upper[0]+.12*span[0])
    ax.set_ylim(lower[1]-.14*span[1], upper[1]+.14*span[1])
    ax.set_aspect('equal')
    ax.axis('off')
    return ax, points_by_name


def _number(ax, points, name, number, offset=(0, 0)):
    outline = points[name]
    target = outline[np.argmax(outline[:, 0])]
    ax.annotate(str(number), target, xytext=offset, textcoords='offset points',
                ha='center', va='center', fontsize=12, weight='bold', color=INK,
                bbox=dict(boxstyle='circle,pad=.22', fc='white', ec=INK, lw=.8),
                arrowprops=dict(arrowstyle='-', lw=.7, color=INK))


def _labels(fig, x, y, rows, spacing=.031, size=13):
    for index, row in enumerate(rows):
        fig.text(x, y-index*spacing, row, fontsize=size, color=INK, va='top')


def _reference(model):
    p = model.parameters
    fig = _page('01  ·  Wickeln von Hand',
                f'Ø{p.reference_diameter_mm:g} mm Referenz · zwei unabhängige Module · Drahtzufuhr frei ausrichten')
    fig.text(.06, .84, 'A  WICKELVORRICHTUNG', fontsize=17, weight='bold', color=INK)
    fig.text(.64, .84, 'B  DRAHTABROLLER', fontsize=17, weight='bold', color=INK)
    ax, points = _project(fig, (.02, .31, .59, .51), model.winding_jig, (1.8, -2.5, 1.35))
    for number, name, offset in ((1, 'rib_2', (12, 15)), (2, 'cam', (-15, 20)),
                                  (3, 'bearing_608_2', (10, 18)), (4, 'crank_grip', (12, 10))):
        _number(ax, points, name, number, offset)
    payoff_view = {**model.wire_payoff, 'hex_key': brake_access_key(),
                   'bench_surface': cq.Workplane('XY').box(205, 205, 2)
                   .translate((0, 0, -25))}
    ax, points = _project(fig, (.61, .34, .36, .43), payoff_view, (1.6, -2, 1.2))
    _number(ax, points, 'platter', 5, (8, 10))
    _number(ax, points, 'base', 6, (10, -5))
    _labels(fig, .05, .28, (
        f'1  {p.rib_count} Rippen · Kontaktkreis Ø{p.reference_diameter_mm:g} mm',
        f'2  Zentraler Kurvenring · {p.tape_station_count} Bandstellen, je {360/p.tape_station_count:g}°',
        '3  2 × 608 · Außenring im Ständer, Innenring auf der Welle',
        f'4  Handkurbel mit frei drehendem Griff · Welle Ø{p.shaft_diameter_mm:g} mm',
        'Links: zwei verstiftete Stahlbundringe; beide Lager mit Kappen.'))
    _labels(fig, .64, .28, (
        f'5  Teller Ø{p.platter_diameter_mm:g} mm · Dorn Ø{p.spool_pilot_diameter_mm:g} × {p.spool_pilot_height_mm:g} mm',
        '6  51105; verdrehgesicherter Bremseinsteller',
        '24-mm-Füße: kurzer Inbusschlüssel von rechts.',
        'Werkbank und Werkzeug nur als Zugangsnachweis.'))
    feed = fig.add_axes((.34, .32, .43, .035))
    feed.annotate('', (.04, .5), (.96, .5), arrowprops=dict(arrowstyle='->', color='#a54432', lw=2.5))
    feed.text(.5, 1.1, 'Drahtzufuhr  B → A  (schematisch)', ha='center', fontsize=12, color=INK)
    feed.axis('off')
    fig.text(.05, .115, 'Wickeldrehsinn: in Ansicht 02 gegen den Uhrzeigersinn; Start A / Ende B markieren.', fontsize=13, color=INK)
    return fig


def _range(model):
    p = model.parameters
    diameters = (p.minimum_diameter_mm, p.reference_diameter_mm, p.maximum_diameter_mm)
    fig = _page('02  ·  Durchmesser, Bandzugang und Freigabe',
                f'{p.rib_count} radial geführte Rippen · {p.tape_station_count} Bandstellen im {360/p.tape_station_count:g}°-Raster · Frontansicht des Kopfes')
    for index, diameter in enumerate(diameters):
        head = build_winding_head(p, diameter)
        ax, _ = _project(fig, (.025+index*.325, .51, .30, .30), head.printable_parts, (0, 0, 1))
        for circle_diameter, color, style in zip(diameters, ('#a44944', '#25384b', '#416aaf'), (':', '-', '--')):
            ax.add_patch(Circle((0, 0), circle_diameter/2, fill=False, edgecolor=color, lw=1.2, linestyle=style))
        for station, angle in enumerate(tape_station_angles(p), 1):
            theta = np.deg2rad(angle)
            ax.text(88*np.cos(theta), 88*np.sin(theta), str(station), fontsize=10,
                    color=INK, ha='center', va='center')
        ax.set_xlim(-103, 103)
        ax.set_ylim(-103, 103)
        fig.text(.175+index*.325, .825, f'Ø{diameter:g} mm', ha='center', fontsize=22, weight='bold', color=INK)
    fig.text(.05, .495, f'Kontaktkreise Ø{diameters[0]:g} / Ø{diameters[1]:g} / Ø{diameters[2]:g} · Wickeln: gegen Uhrzeigersinn in dieser Frontansicht.',
             fontsize=13, color=INK)
    fig.text(.05, .462, f'18 Streifen {p.tape_width_mm:g}-mm-Band; Passage ≥{p.tape_passage_width_mm:g} mm. Anhalten, tapen, Vorspannung lösen, Rippen {p.release_travel_mm:g} mm einziehen.',
             fontsize=13, color=INK)
    stages = coil_removal_stages(model)
    captions = ('1  Helfer stützt Kopf / lose Teile; 5 Stifte heraus.\n    Welle 220 mm nach links herausziehen.',
                '2  Kopf und getapte Spule gemeinsam\n    200 mm zwischen Ständern anheben.',
                '3  Kopf auf weicher Unterlage zusammenhalten.\n    Spule 50 mm axial zur Rippenseite abziehen.')
    visible = set(model.frame.printable_parts) | set(model.head.printable_parts) | {'shaft', 'coil'}
    for index, stage in enumerate(stages[2:]):
        view = {**stage['fixed'], **{name: shape.translate(stage['translation_mm'])
                                    for name, shape in stage['moving'].items()}}
        view = {name: shape for name, shape in view.items() if name in visible}
        _project(fig, (.02+index*.325, .16, .30, .255), view, (1.0, -3, .9))
        fig.text(.035+index*.325, .425, captions[index], fontsize=11, color=INK, va='top')
    fig.text(.05, .122, 'Braun = Spulen-Hüllkörper: 10 mm axial, 3 mm radial, 0,5 mm Band nach innen. Ständer und Lagerkappen bleiben montiert.',
             fontsize=12, color=INK)
    fig.text(.05, .094, 'Nach Montage alle fünf Stifte sichern und axialen Freigang prüfen. Größere Wicklungen benötigen eine eigene Entnahmeprüfung.',
             fontsize=12, color=INK)
    return fig


def _exploded(model, jig):
    fig = _page('03  ·  Montagegruppen und Lagerzuordnung',
                'Zwei getrennte Explosionsansichten · Abstände nur zur Darstellung · vollständige Stückliste in der Anleitung')
    fig.text(.04, .852, 'A  WICKELVORRICHTUNG', fontsize=16, weight='bold', color=INK)
    ax, points = _project(fig, (.015, .49, .62, .35), jig, (-1, -3.5, 1.5))
    calls = ((1, 'base', (0, -14)), (2, 'right_upright', (10, 12)),
             (3, 'bearing_608_1', (0, 15)), (4, 'head_hub', (6, -15)),
             (5, 'backplate', (-8, 10)), (6, 'rib_2', (8, 12)),
             (7, 'cam', (-5, -12)), (8, 'clamp', (-8, -15)), (9, 'crank', (0, 15)))
    for number, name, offset in calls:
        _number(ax, points, name, number, offset)
    _labels(fig, .66, .83, (
        '1  Grundplatte + Tischbefestigung', '2  Zwei Ständer + vier M4-Schrauben',
        '3  Zwei 608 + Lagerkappen; links zwei Stahlbundringe', '4  Welle, Nabe, Haltering + fünf Sicherungsstifte',
        '5  Rückplatte + sechs abnehmbare Anschläge', '6  Sechs Rippen / Schieber + M3-Verbindungen',
        '7  Kurvenring + sechs Metall-Kurvenfolger', '8  Klemmring; drei Vorspannschrauben am Haltering',
        '9  Kurbel + Griff, Achse, Scheiben, Sicherungen'), spacing=.030, size=12)
    fig.text(.04, .475, 'B  DRAHTABROLLER', fontsize=16, weight='bold', color=INK)
    translations = {'platter': (0, 0, 115), 'shaft_washer': (0, 0, 85),
                    'rolling_envelope': (0, 0, 60), 'housing_washer': (0, 0, 35)}
    for name in model.payoff.brake_parts:
        translations[name] = (45, 0, 35)
    payoff = {name: body.translate(translations.get(name, (0, 0, 0)))
              for name, body in model.wire_payoff.items()}
    ax, points = _project(fig, (.04, .09, .56, .37), payoff, (1.6, -2.5, 1.1))
    for number, name, offset in ((10, 'base', (15, -7)), (11, 'housing_washer', (-20, 0)),
                                  (12, 'rolling_envelope', (-20, 5)), (13, 'shaft_washer', (-20, 8)),
                                  (14, 'platter', (12, 10)), (15, 'adjuster', (15, 10))):
        _number(ax, points, name, number, offset)
    _labels(fig, .66, .44, (
        '10  Grundplatte mit 24-mm-Füßen + Tischbefestigung',
        '11  51105-Gehäusescheibe: bleibt in der Basis',
        '12  51105-Wälzkranz: lagerinterne Bewegung',
        '13  51105-Wellenscheibe: dreht mit Teller',
        '14  Abnehmbarer Teller + angefaster Spulendorn',
        '15  Filz, geführter Einsteller/Mutter, Feder, Schraube',
        '11–13 = EIN komplettes 51105, kein Lagertrio.',
        '608: Außenring fest; Innenring dreht mit Welle.',
        'Bremse leicht schleifend; kein starrer Tellerstopp.'), spacing=.030, size=12)
    return fig, translations


def render_winding_tool_drawings(model, exploded_jig, destination: Path) -> tuple[dict, ...]:
    """Render all required drawings; report metadata for the release manifest."""
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    with plt.rc_context({'font.family': 'DejaVu Sans', 'font.size': 13,
                         'path.simplify': False, 'savefig.facecolor': 'white'}):
        exploded, payoff_translations = _exploded(model, exploded_jig)
        figures = (_reference(model), _range(model), exploded)
        try:
            for filename, fig in zip(DRAWING_NAMES, figures):
                fig.savefig(destination / filename, dpi=100, metadata={'Software': 'windwall winding-tool renderer'})
                records.append({'path': f'drawings/{filename}', 'width_px': 2000, 'height_px': 1400,
                                'source_builder': 'scripts.preview_winding_tool.render_winding_tool_drawings',
                                'presentation_only': True})
        finally:
            for fig in figures:
                plt.close(fig)
    records[-1]['payoff_component_translations_mm'] = {
        name: list(payoff_translations.get(name, (0, 0, 0))) for name in sorted(model.wire_payoff)}
    return tuple(records)


def main():
    from windwall.winding_tool_assembly import build_winding_tool_assemblies
    from windwall.winding_tool_export import _exploded_jig

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=PROJECT_ROOT / 'build/winding-tool-drawings')
    args = parser.parse_args()
    model = build_winding_tool_assemblies()
    render_winding_tool_drawings(model, _exploded_jig(model)[0], args.output_dir)
    print(f'Three winding-tool drawings: {args.output_dir}', flush=True)


if __name__ == '__main__':
    main()
