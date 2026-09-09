"""Render the experimental magnet, winding and electrical manual figures.

These sheets explain a measurement workflow.  They deliberately do not set a
final wire diameter, turn count, electrical rating or outdoor approval.
"""

from __future__ import annotations

from math import ceil, cos, isfinite, pi, sin
import os
from pathlib import Path
import textwrap
from typing import Callable, Sequence

from scripts.manual.cad_figures import FigureRecord
from scripts.manual.manual_data import load_manual_data


_INK = '#21323b'
_MUTED = '#617079'
_PAPER = '#f7f7f4'
_PANEL = '#ffffff'
_LINE = '#87949b'
_NORTH = '#2d6fa3'
_SOUTH = '#c4683d'
_COPPER = '#b56a32'
_SAFE = '#3e7b62'
_DANGER = '#a33f35'
_PROVISIONAL = '#74658f'


def magnet_polarities(count: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return alternating facing-pole labels for an attracting rotor pair."""

    if not isinstance(count, int) or isinstance(count, bool) or count <= 0 or count % 2:
        raise ValueError('Die Magnetzahl muss eine positive gerade Ganzzahl sein.')
    top = tuple('N' if index % 2 == 0 else 'S' for index in range(count))
    bottom = tuple('S' if pole == 'N' else 'N' for pole in top)
    return top, bottom


def estimate_final_turns(test_turns: int, measured_v_rms: float, target_v_rms: float) -> int:
    """Scale a measured test winding and round upward to a whole turn.

    This is an experiment-planning estimate only; it is not an electrical
    rating and does not override winding-space or temperature checks.
    """

    values = (test_turns, measured_v_rms, target_v_rms)
    if (
        not isinstance(test_turns, int)
        or isinstance(test_turns, bool)
        or any(isinstance(value, bool) for value in values)
        or any(not isfinite(float(value)) or value <= 0 for value in values)
    ):
        raise ValueError('Windungen und Spannungen müssen positiv und endlich sein.')
    return ceil(test_turns * target_v_rms / measured_v_rms)


def build_test_matrix(measured_diameters_mm: Sequence[float]) -> list[tuple[float, int]]:
    """Pair each enamel-inclusive measured diameter with 20/40/80 turns."""

    diameters = list(measured_diameters_mm)
    if not diameters:
        raise ValueError('Mindestens ein gemessener Drahtdurchmesser ist erforderlich.')
    if any(
        isinstance(diameter, bool)
        or not isfinite(float(diameter))
        or diameter <= 0
        for diameter in diameters
    ):
        raise ValueError('Gemessene Drahtdurchmesser müssen positiv und endlich sein.')
    return [(float(diameter), turns) for diameter in diameters for turns in (20, 40, 80)]


def _new_sheet(drawing_id: str, drawing: dict):
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(12, 8.4), facecolor=_PAPER)
    ax = fig.add_axes((0.04, 0.17, 0.92, 0.68))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.text(
        0.055, 0.955, f"{drawing_id}  {drawing['title']}",
        ha='left', va='top', fontsize=16, fontweight='bold', color=_INK,
    )
    fig.text(
        0.055, 0.905, drawing['description'],
        ha='left', va='top', fontsize=8.8, color='#3b474e',
    )
    return fig, ax


def _item_description(data: dict, item_id: str) -> str:
    registry = data['printed_parts'] if item_id.startswith('P') else data['hardware']
    return registry[item_id]['description']


def _finish_sheet(fig, path: Path, drawing: dict, data: dict) -> None:
    references = ' · '.join(
        f"{item_id} {_item_description(data, item_id)}"
        for item_id in drawing['items']
    )
    reference_lines = textwrap.wrap(references, width=155, break_long_words=False)
    fig.text(
        0.055, 0.115, 'BOM-BEZUG  ' + '\n'.join(reference_lines),
        ha='left', va='top', fontsize=6.5, color=_MUTED, linespacing=1.35,
    )
    fig.text(
        0.055, 0.024,
        'PROTOTYP / MESSPLAN · KEINE FINALE DRAHT-, WINDUNGS-, LEISTUNGS- ODER AUSSENFREIGABE',
        ha='left', va='bottom', fontsize=7.4, fontweight='bold', color=_DANGER,
    )
    fig.savefig(
        path,
        dpi=200,
        facecolor=fig.get_facecolor(),
        metadata={'Software': 'Windwall electrical manual renderer'},
    )
    import matplotlib.pyplot as plt

    plt.close(fig)


def _box(ax, x: float, y: float, width: float, height: float, title: str, lines=(), *, color=_INK):
    from matplotlib.patches import FancyBboxPatch

    patch = FancyBboxPatch(
        (x, y), width, height,
        boxstyle='round,pad=0.08,rounding_size=0.08',
        facecolor=_PANEL, edgecolor=color, linewidth=1.35,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height * 0.68, title, ha='center', va='center',
            fontsize=8.5, fontweight='bold', color=color)
    if lines:
        ax.text(x + width / 2, y + height * 0.31, '\n'.join(lines), ha='center', va='center',
                fontsize=6.8, color=_INK, linespacing=1.25)
    return patch


def _arrow(ax, start, end, *, color=_INK, width=1.5, style='-|>', connectionstyle='arc3'):
    from matplotlib.patches import FancyArrowPatch

    arrow = FancyArrowPatch(
        start, end, arrowstyle=style, mutation_scale=10, linewidth=width,
        color=color, connectionstyle=connectionstyle,
    )
    ax.add_patch(arrow)
    return arrow


def _draw_rotor(ax, center, poles: Sequence[str], label: str, part_id: str) -> None:
    from matplotlib.patches import Circle

    cx, cy = center
    ax.add_patch(Circle(center, 2.05, facecolor='#e7ecee', edgecolor=_INK, linewidth=1.5))
    ax.add_patch(Circle(center, 0.42, facecolor=_PAPER, edgecolor=_LINE, linewidth=1.0))
    for index, pole in enumerate(poles):
        angle = pi / 2 - 2 * pi * index / len(poles)
        x = cx + 1.50 * cos(angle)
        y = cy + 1.50 * sin(angle)
        color = _NORTH if pole == 'N' else _SOUTH
        ax.add_patch(Circle((x, y), 0.225, facecolor=color, edgecolor='#ffffff', linewidth=0.8))
        ax.text(x, y, pole, ha='center', va='center', fontsize=6.4,
                fontweight='bold', color='#ffffff')
    ax.text(cx, cy + 0.10, label, ha='center', va='center', fontsize=9.0,
            fontweight='bold', color=_INK)
    ax.text(cx, cy - 0.22, part_id, ha='center', va='center', fontsize=7.2, color=_MUTED)


def _render_e07(path: Path, drawing_id: str, drawing: dict, data: dict) -> None:
    from matplotlib.patches import Rectangle

    fig, ax = _new_sheet(drawing_id, drawing)
    top, bottom = magnet_polarities(data['dimensions']['magnet_pocket_count_per_rotor'])
    _draw_rotor(ax, (3.0, 4.35), top, 'OBERER ROTOR · Sichtfläche', 'H10')
    _draw_rotor(ax, (9.0, 4.35), bottom, 'UNTERER ROTOR · Sichtfläche', 'P05 / H10')

    ax.text(6.0, 6.85, 'AUSGERICHTETE TASCHEN: immer N ↔ S', ha='center', va='center',
            fontsize=10, fontweight='bold', color=_SAFE)
    _arrow(ax, (5.0, 6.55), (7.0, 6.55), color=_SAFE, style='<|-|>')
    ax.text(6.0, 6.27, '✓ ANZIEHUNG vor dem Einkleben an jeder Position prüfen',
            ha='center', va='center', fontsize=8.4, color=_SAFE)

    for x, color, pole in ((3.55, _NORTH, 'N'), (4.00, _SOUTH, 'S')):
        ax.add_patch(Rectangle((x, 0.75), 0.28, 0.28, facecolor=color, edgecolor=_INK, linewidth=0.5))
        ax.text(x + 0.14, 0.89, pole, ha='center', va='center', color='white',
                fontweight='bold', fontsize=6.5)
    ax.text(4.48, 0.89, 'Farbe + Buchstabe', ha='left', va='center', fontsize=7.5, color=_INK)
    ax.text(8.10, 0.89, '18 je Rotor · 36 gesamt · nominal 10 × 2 mm',
            ha='center', va='center', fontsize=7.5, color=_INK)
    ax.text(6.0, 0.40,
            'H11 Rückhaltung erst nach Trockenlayout und Retentionstest festlegen; Kleber allein ist keine Freigabe.',
            ha='center', va='center', fontsize=7.2, color=_DANGER)
    _finish_sheet(fig, path, drawing, data)


def _serpentine_geometry(count: int, inner_radius: float, outer_radius: float):
    """Return a continuous path plus the radial active-leg segments."""

    points: list[tuple[float, float]] = []
    legs: list[tuple[tuple[float, float], tuple[float, float]]] = []
    angles = [pi / 2 - 2 * pi * index / count for index in range(count)]
    for index, angle in enumerate(angles):
        start_radius, end_radius = (
            (outer_radius, inner_radius) if index % 2 == 0 else (inner_radius, outer_radius)
        )
        start = (start_radius * cos(angle), start_radius * sin(angle))
        end = (end_radius * cos(angle), end_radius * sin(angle))
        if not points:
            points.append(start)
        points.append(end)
        legs.append((start, end))
        if index == count - 1:
            continue
        next_angle = angles[index + 1]
        for step in range(1, 7):
            arc_angle = angle + (next_angle - angle) * step / 6
            points.append((end_radius * cos(arc_angle), end_radius * sin(arc_angle)))
    return points, legs


def _render_e08(path: Path, drawing_id: str, drawing: dict, data: dict) -> None:
    from matplotlib.patches import Circle

    fig, ax = _new_sheet(drawing_id, drawing)
    center = (6.0, 4.05)
    count = data['dimensions']['magnet_pocket_count_per_rotor']
    poles, _ = magnet_polarities(count)
    points, legs = _serpentine_geometry(count, 1.35, 2.65)

    for index, pole in enumerate(poles):
        angle = pi / 2 - 2 * pi * index / count
        x = center[0] + 3.12 * cos(angle)
        y = center[1] + 3.12 * sin(angle)
        color = _NORTH if pole == 'N' else _SOUTH
        ax.add_patch(Circle((x, y), 0.18, facecolor=color, edgecolor='white', linewidth=0.6))
        ax.text(x, y, pole, ha='center', va='center', color='white', fontsize=5.8, fontweight='bold')

    shifted = [(center[0] + x, center[1] + y) for x, y in points]
    ax.plot([point[0] for point in shifted], [point[1] for point in shifted],
            color=_COPPER, linewidth=2.7, solid_capstyle='round')
    for number, (start, end) in enumerate(legs, start=1):
        midpoint = ((start[0] + end[0]) / 2 + center[0], (start[1] + end[1]) / 2 + center[1])
        ax.text(*midpoint, str(number), ha='center', va='center', fontsize=5.4, color=_INK,
                bbox={'facecolor': _PAPER, 'edgecolor': 'none', 'pad': 0.25})

    start = shifted[0]
    finish = shifted[-1]
    ax.scatter([start[0], finish[0]], [start[1], finish[1]], s=55,
               c=[_SAFE, _PROVISIONAL], edgecolors='white', linewidths=1.0, zorder=5)
    ax.annotate('A1 · START', xy=start, xytext=(7.25, 7.12), fontsize=8.2,
                fontweight='bold', color=_SAFE, arrowprops={'arrowstyle': '-|>', 'color': _SAFE})
    ax.annotate('A2 · ENDE', xy=finish, xytext=(2.15, 6.95), fontsize=8.2,
                fontweight='bold', color=_PROVISIONAL, arrowprops={'arrowstyle': '-|>', 'color': _PROVISIONAL})
    _arrow(ax, shifted[14], shifted[15], color=_COPPER, width=1.2)
    ax.text(6.0, 7.35, 'WICKELRICHTUNG A1 → A2 · EIN DURCHGEHENDER LEITER',
            ha='center', va='center', fontsize=9.2, fontweight='bold', color=_INK)
    ax.text(6.0, 0.34,
            'Aktive Radialschenkel 1–18 folgen den wechselnden Polen; Draht H08 über Emaille messen, H09 isoliert führen.',
            ha='center', va='center', fontsize=7.3, color=_INK)
    _finish_sheet(fig, path, drawing, data)


def _draw_jig_board(ax) -> None:
    from matplotlib.patches import Circle, FancyBboxPatch

    ax.add_patch(FancyBboxPatch(
        (0.65, 0.75), 8.0, 6.35, boxstyle='round,pad=0.08',
        facecolor='#e7dfcf', edgecolor='#6f675d', linewidth=1.4,
    ))
    top_y, bottom_y = 5.75, 2.15
    pin_x = [1.30 + index * 0.73 for index in range(10)]
    route = []
    for index, x in enumerate(pin_x):
        y1, y2 = (top_y, bottom_y) if index % 2 == 0 else (bottom_y, top_y)
        route.extend([(x, y1), (x, y2)])
        for y in (top_y, bottom_y):
            ax.add_patch(Circle((x, y), 0.16, facecolor='#f3f6f7', edgecolor=_INK, linewidth=1.0))
            ax.add_patch(Circle((x, y), 0.07, facecolor=_PROVISIONAL, edgecolor='none'))
    ax.plot([point[0] for point in route], [point[1] for point in route],
            color=_COPPER, linewidth=2.3, solid_joinstyle='round')
    ax.text(4.65, 6.62, 'Wiederverwendbares Board · glatte, isolierte Pins',
            ha='center', va='center', fontsize=9.0, fontweight='bold', color=_INK)
    ax.text(4.65, 1.72, 'BINDPUNKTE ×', ha='center', va='center', fontsize=7.3,
            fontweight='bold', color=_SAFE)
    for x in (2.0, 4.65, 7.3):
        ax.plot([x - 0.17, x + 0.17], [1.55, 1.25], color=_SAFE, linewidth=2)
        ax.plot([x - 0.17, x + 0.17], [1.25, 1.55], color=_SAFE, linewidth=2)


def _render_e09(path: Path, drawing_id: str, drawing: dict, data: dict) -> None:
    from matplotlib.patches import Arc

    fig, ax = _new_sheet(drawing_id, drawing)
    _draw_jig_board(ax)
    ax.add_patch(Arc((1.3, 5.75), 0.9, 0.9, theta1=90, theta2=270, color=_SAFE, linewidth=1.8))
    ax.annotate('Biegeradius R: groß und glatt;\nnach Drahtdatenblatt festlegen',
                xy=(0.86, 5.75), xytext=(0.25, 7.55), fontsize=7.2, color=_SAFE,
                arrowprops={'arrowstyle': '-|>', 'color': _SAFE})

    for index, turns in enumerate((20, 40, 80)):
        y = 5.65 - index * 1.55
        _box(ax, 9.15, y, 2.35, 1.05, f'{turns} WINDUNGEN',
             ('nur wenn locker passend', '□ gebaut  □ gemessen'), color=_PROVISIONAL)
    ax.text(10.32, 1.10, 'Abbruch: kein erzwungenes Packen', ha='center', va='center',
            fontsize=7.4, fontweight='bold', color=_DANGER)
    ax.text(4.65, 0.42,
            'H08: nominal 0,18 mm beginnen; jeden Draht über Emaille messen.\nH09: weich binden und isolieren.',
            ha='center', va='center', fontsize=6.9, color=_INK, linespacing=1.3)
    ax.text(10.32, 0.38, 'WARNUNG: Emaille nicht schaben,\nkerben oder knicken.',
            ha='center', va='center', fontsize=7.0, fontweight='bold', color=_DANGER,
            linespacing=1.25)
    _finish_sheet(fig, path, drawing, data)


def _wire(ax, points, color) -> None:
    ax.plot(
        [point[0] for point in points],
        [point[1] for point in points],
        color=color,
        linewidth=1.7,
        solid_capstyle='round',
    )


def _meter_symbol(ax, center, symbol: str, color) -> None:
    from matplotlib.patches import Circle

    ax.add_patch(Circle(center, 0.32, facecolor=_PANEL, edgecolor=color, linewidth=1.5, zorder=3))
    ax.text(*center, symbol, ha='center', va='center', fontsize=8.2,
            fontweight='bold', color=color, zorder=4)


def _draw_resistive_load(ax, left: float, right: float, y: float, color) -> None:
    from matplotlib.patches import Rectangle

    ax.add_patch(Rectangle(
        (left, y - 0.30), right - left, 0.60,
        facecolor=_PANEL, edgecolor=color, linewidth=1.5, zorder=3,
    ))
    ax.text((left + right) / 2, y, 'RTEST = ____ Ω\nP = ____ W',
            ha='center', va='center', fontsize=6.8, color=_INK, linespacing=1.25)


def _draw_parallel_meter(
    ax,
    load_left: float,
    load_right: float,
    load_y: float,
    meter_y: float,
    symbol: str,
    label: str,
    color,
) -> None:
    center_x = (load_left + load_right) / 2
    _wire(ax, ((load_left, load_y), (load_left, meter_y), (center_x - 0.32, meter_y)), color)
    _wire(ax, ((center_x + 0.32, meter_y), (load_right, meter_y), (load_right, load_y)), color)
    ax.scatter((load_left, load_right), (load_y, load_y), s=18, color=color, zorder=5)
    _meter_symbol(ax, (center_x, meter_y), symbol, color)
    ax.text(center_x, meter_y - 0.47, label, ha='center', va='center',
            fontsize=6.3, fontweight='bold', color=color)


def _draw_bridge_rectifier(ax, x: float, y: float, width: float, height: float, color):
    """Draw a four-terminal bridge and return its named terminal coordinates."""

    from matplotlib.patches import Rectangle

    terminals = {
        'ac_1': (x, y + height * 0.75),
        'ac_2': (x, y + height * 0.25),
        'dc_positive': (x + width, y + height * 0.75),
        'dc_negative': (x + width, y + height * 0.25),
    }
    ax.add_patch(Rectangle(
        (x, y), width, height,
        facecolor=_PANEL, edgecolor=color, linewidth=1.5, zorder=3,
    ))
    ax.text(x + width / 2, y + height / 2, 'H12\nBRÜCKE',
            ha='center', va='center', fontsize=7.0, fontweight='bold', color=color)
    terminal_labels = (
        ('AC~1', terminals['ac_1'], 'left', 0.09),
        ('AC~2', terminals['ac_2'], 'left', 0.09),
        ('DC +', terminals['dc_positive'], 'right', -0.09),
        ('DC -', terminals['dc_negative'], 'right', -0.09),
    )
    for label, terminal, alignment, offset in terminal_labels:
        ax.scatter(*terminal, s=22, color=color, zorder=5)
        ax.text(terminal[0] + offset, terminal[1], label, ha=alignment, va='center',
                fontsize=5.7, fontweight='bold', color=color, zorder=6)
    return terminals


def _render_e10(path: Path, drawing_id: str, drawing: dict, data: dict) -> None:
    fig, ax = _new_sheet(drawing_id, drawing)
    _box(ax, 0.15, 5.25, 1.35, 0.95, 'TACHOMETER', ('n = ____ min⁻¹',), color=_SAFE)
    _box(ax, 0.15, 2.20, 1.35, 1.05, 'TEMPERATUR', ('T₀ ____ °C', 'T₁ ____ °C'), color=_SAFE)
    ax.text(0.82, 4.13, 'für jeden Lauf\ngleich erfassen', ha='center', va='center',
            fontsize=6.8, color=_SAFE)
    _arrow(ax, (0.82, 5.23), (0.82, 4.58), color=_SAFE)
    _arrow(ax, (0.82, 3.27), (0.82, 3.72), color=_SAFE)

    # AC configuration: current meter sits in the conductor; voltage meter
    # bridges exactly the two load terminals.
    ac_y, ac_return_y = 5.55, 4.12
    ax.text(1.82, 6.90, 'AC-KONFIGURATION · ohne Gleichrichter · separate Messung',
            fontsize=8.0, fontweight='bold', color=_NORTH)
    _box(ax, 1.82, 4.55, 1.30, 1.55, 'TESTSPULE', ('H08', 'Isolation H09'), color=_NORTH)
    _box(ax, 3.40, 5.18, 0.78, 0.72, 'H13', ('Schutz',), color=_PROVISIONAL)
    _wire(ax, ((3.12, ac_y), (3.40, ac_y)), _NORTH)
    _wire(ax, ((4.18, ac_y), (4.72, ac_y)), _NORTH)
    _meter_symbol(ax, (5.05, ac_y), 'A~', _NORTH)
    ax.text(5.05, 6.05, 'A~ IN REIHE', ha='center', va='center', fontsize=6.5,
            fontweight='bold', color=_NORTH)
    _wire(ax, ((5.38, ac_y), (6.12, ac_y)), _NORTH)
    _draw_resistive_load(ax, 6.12, 8.72, ac_y, _NORTH)
    _wire(
        ax,
        ((8.72, ac_y), (9.02, ac_y), (9.02, ac_return_y),
         (3.12, ac_return_y), (3.12, 4.55)),
        _NORTH,
    )
    _draw_parallel_meter(
        ax, 6.12, 8.72, ac_y, 4.82, 'V~', 'V~ PARALLEL ZU RTEST', _NORTH,
    )
    ax.text(5.05, 4.52, 'A~ und V~: TRUE RMS', ha='center', va='center',
            fontsize=6.4, color=_NORTH)

    # DC configuration: rectification exists only in this separately wired
    # branch; series-current and parallel-voltage topology stays explicit.
    dc_y, dc_return_y = 2.45, 0.82
    ax.text(1.82, 3.55, 'DC-KONFIGURATION · optional · separate Messung',
            fontsize=8.0, fontweight='bold', color=_SOUTH)
    _box(ax, 1.82, 1.35, 1.30, 1.55, 'TESTSPULE', ('H08', 'Isolation H09'), color=_SOUTH)
    _box(ax, 3.30, 2.08, 0.68, 0.72, 'H13', ('Schutz',), color=_PROVISIONAL)
    bridge = _draw_bridge_rectifier(ax, 4.18, 1.175, 1.25, 1.70, _SOUTH)
    _wire(ax, ((3.12, dc_y), (3.30, dc_y)), _SOUTH)
    _wire(ax, ((3.98, dc_y), bridge['ac_1']), _SOUTH)
    _wire(ax, ((3.12, 1.60), bridge['ac_2']), _SOUTH)
    _wire(ax, (bridge['dc_positive'], (5.58, dc_y)), _SOUTH)
    _meter_symbol(ax, (5.90, dc_y), 'A DC', _SOUTH)
    ax.text(5.90, 2.96, 'A DC IN REIHE', ha='center', va='center', fontsize=6.5,
            fontweight='bold', color=_SOUTH)
    _wire(ax, ((6.23, dc_y), (6.55, dc_y)), _SOUTH)
    _draw_resistive_load(ax, 6.55, 8.85, dc_y, _SOUTH)
    _wire(
        ax,
        ((8.85, dc_y), (9.08, dc_y), (9.08, dc_return_y),
         (bridge['dc_negative'][0], dc_return_y), bridge['dc_negative']),
        _SOUTH,
    )
    _draw_parallel_meter(
        ax, 6.55, 8.85, dc_y, 1.62, 'V DC', 'V DC PARALLEL ZU RTEST', _SOUTH,
    )

    _box(ax, 9.48, 0.88, 2.25, 6.10, 'VERGLEICHSFELDER', (
        'd über Emaille ____ mm',
        'Windungen 20 / 40 / 80',
        'n ____ min⁻¹',
        'V~ ____ V   I~ ____ A',
        'V DC ____ V   I DC ____ A',
        'RSpule ____ Ω',
        'RTEST ____ Ω',
        'T₀/T₁ ____ / ____ °C',
        'Datum ____  Lauf ____',
        '',
        'H14 Laderegler erst',
        'aus diesen Messdaten',
        'auswählen.',
    ), color=_PROVISIONAL)
    ax.text(1.82, 0.38,
            'Gleiche Drehzahl, Last und Temperatur; Leerlaufspannung ist kein Leistungswert.',
            ha='left', va='center', fontsize=6.7, color=_DANGER)
    _finish_sheet(fig, path, drawing, data)


def _render_e11(path: Path, drawing_id: str, drawing: dict, data: dict) -> None:
    from matplotlib.patches import FancyArrowPatch

    fig, ax = _new_sheet(drawing_id, drawing)
    nodes = [
        (0.15, 4.15, 1.45, 'GENERATOR', ('Messwerte', 'noch offen'), _INK),
        (2.05, 4.15, 1.45, 'H12', ('bemessener', 'Gleichrichter'), _SOUTH),
        (3.95, 4.15, 1.45, 'H13', ('Überstrom-', 'schutz'), _PROVISIONAL),
        (5.85, 4.15, 1.75, 'H14 REGLER', ('Windregler mit', 'Diversion'), _SAFE),
        (8.05, 4.15, 1.45, 'H16', ('batterieseitige', 'Sicherung'), _PROVISIONAL),
        (9.95, 4.15, 1.80, 'H17 AKKU', ('48 V nominal', 'Bleiakku-Bank'), _INK),
    ]
    for x, y, width, title, lines, color in nodes:
        _box(ax, x, y, width, 1.30, title, lines, color=color)
    for left, right in zip(nodes, nodes[1:]):
        _arrow(ax, (left[0] + left[2] + 0.03, 4.80), (right[0] - 0.03, 4.80), color=_INK)

    _box(ax, 5.85, 1.55, 1.75, 1.30, 'H15 DUMP LOAD', ('bemessen, belüftet,', 'berührungsgeschützt'), color=_DANGER)
    _arrow(ax, (6.72, 4.12), (6.72, 2.88), color=_DANGER)
    ax.text(7.00, 3.47, 'DIVERSION / ÜBERSCHUSS', ha='left', va='center', fontsize=7.0,
            fontweight='bold', color=_DANGER)

    direct = FancyArrowPatch(
        (0.90, 5.52), (10.85, 5.52), arrowstyle='-|>', mutation_scale=12,
        linewidth=2.2, linestyle='--', color=_DANGER,
        connectionstyle='arc3,rad=-0.11',
    )
    ax.add_patch(direct)
    ax.text(5.90, 5.80, '✕  DIREKTVERBINDUNG GENERATOR → 48-V-AKKU VERBOTEN',
            ha='center', va='center', fontsize=9.0, fontweight='bold', color=_DANGER,
            bbox={'boxstyle': 'round,pad=0.30', 'facecolor': '#fff5f2', 'edgecolor': _DANGER})

    ax.text(6.0, 7.15,
            'ZULÄSSIGE FUNKTIONSKETTE · alle Spannungs-, Strom-, Wärme- und Fehlerfallwerte erst messen',
            ha='center', va='center', fontsize=8.6, fontweight='bold', color=_INK)
    ax.text(6.0, 0.65,
            'Schutzorgane nahe an ihrer Quelle anordnen; Abschaltvermögen, Leitungen, Erdung und Gehäuse separat auslegen.',
            ha='center', va='center', fontsize=7.2, color=_INK)
    _finish_sheet(fig, path, drawing, data)


_RENDERERS: dict[str, Callable[[Path, str, dict, dict], None]] = {
    'E07': _render_e07,
    'E08': _render_e08,
    'E09': _render_e09,
    'E10': _render_e10,
    'E11': _render_e11,
}


def render_electrical_figures(project_root: Path, output_dir: Path) -> list[FigureRecord]:
    """Render E07-E11 into ``output_dir`` and return stable figure records."""

    project_root = Path(project_root).resolve()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache = project_root / 'build' / 'matplotlib'
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR', str(cache))
    import matplotlib

    matplotlib.use('Agg')
    data = load_manual_data(project_root)
    records = []
    for drawing_id, renderer in _RENDERERS.items():
        drawing = data['drawings'][drawing_id]
        path = output_dir / Path(drawing['figure_file']).name
        renderer(path, drawing_id, drawing, data)
        records.append(FigureRecord(
            drawing_id=drawing_id,
            path=path,
            caption=f"{drawing['title']}. {drawing['description']}",
            callouts=tuple(drawing['items']),
        ))
    return records


__all__ = [
    'build_test_matrix',
    'estimate_final_turns',
    'magnet_polarities',
    'render_electrical_figures',
]
