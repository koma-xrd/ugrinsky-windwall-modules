"""Deterministic German V5 drawings from current CadQuery builders.

The release manifest supplies component provenance and motion ownership. Solid
triangles are orthographically projected with a global depth sort; sections
are boolean cuts of those same solids. Numbered markers map to a separate
label column without crossing leader lines. No legacy drawing geometry is used.
Hardware and winding solids remain nominal CAD envelopes, not fit approval.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
import textwrap

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for root in (PROJECT_ROOT, PROJECT_ROOT / 'src'):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / 'build' / 'matplotlib'))

import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgb
import numpy as np

from windwall.assembly import build_exploded_rotor_assembly, build_locked_rotor_assembly
from windwall.bearings import build_51105_fit_coupon, build_608_fit_coupon
from windwall.bayonet import build_bayonet_coupon
from windwall.parameters import DEFAULT_PARAMETERS
from windwall.top_support import build_top_support


COLORS = {'rotating': '#d79732', 'stationary': '#258e91',
          'bearing': '#9576b4', 'reference': '#89939e'}
LEGEND = ('ROTIEREND · Rotor, Welle, M8-Klemmung (Ocker)',
          'STATIONÄR · Gehäuse, Kassette, Deckel, Halter (Türkis)',
          'LAGER · Wälzkörper / unaufgelöste 608-Kinematik (Violett)',
          'REFERENZEN · Prüfkörper / Freiraumhüllen (Grau)')


@dataclass(frozen=True)
class PartRecord:
    name: str
    motion: str
    source_builder: str
    source_bounds_mm: tuple[tuple[float, ...], tuple[float, ...]]
    display_bounds_mm: tuple[tuple[float, ...], tuple[float, ...]]
    printable: bool | None = None
    reference_note: str = ''
    installation_direction: tuple[float, float, float] | None = None


@dataclass(frozen=True)
class FigureRecord:
    drawing_id: str
    path: Path
    filename: str
    caption: str
    alt_text: str
    callout_labels: tuple[str, ...]
    rotation_state_legend: tuple[str, ...]
    pixel_width: int
    pixel_height: int
    language: str
    parts: tuple[PartRecord, ...]
    callouts: tuple[Callout, ...] = ()


@dataclass(frozen=True)
class RenderPart:
    record: PartRecord
    shape: cq.Workplane


@dataclass(frozen=True)
class Callout:
    name: str
    label: str
    target: tuple[float, float, float] | None = None
    marker_offset_mm: tuple[float, float] = (0, 0)


@dataclass(frozen=True)
class Panel:
    title: str
    parts: tuple[RenderPart, ...]
    callouts: tuple[Callout, ...]
    view: tuple[float, float, float] = (1, -1.8, .7)


@dataclass(frozen=True)
class Scene:
    drawing_id: str
    slug: str
    title: str
    caption: str
    note: str
    panels: tuple[Panel, ...]


def _bounds(shape):
    box = shape.val().BoundingBox()
    return ((box.xmin, box.ymin, box.zmin), (box.xmax, box.ymax, box.zmax))


class _Model:
    """One build shared by all drawings; manifest metadata never creates solids."""

    def __init__(self, p):
        self.p = p
        self.manifest_path = PROJECT_ROOT / 'release/v5/manifest.json'
        self.manifest = json.loads(self.manifest_path.read_text(encoding='utf-8'))
        if self.manifest['release'] != 'v5':
            raise ValueError('The figure renderer requires a V5 release manifest')
        self.sources = {item['name']: item for assembly in self.manifest['assemblies']
                        for item in assembly['components']}
        self.locked = build_locked_rotor_assembly(p)
        self.exploded = build_exploded_rotor_assembly(p, locked=self.locked)
        self.generator = self.locked.generator
        self.support = build_top_support(p)
        self.shapes = {**self.locked.parts, 'shaft': self.support.required_shaft_reference,
                       'top_support': self.support.shape, 'bearing_608': self.support.bearing,
                       'upper_wood_frame_reference': self.support.wood_frame_reference,
                       **{f'wood_screw_{i}_reference': s for i, s in enumerate(self.support.wood_screws, 1)}}

    def part(self, name, *, shape=None, offset=(0, 0, 0), cut=None, motion=None, source=None,
             reference_note='', installation_direction=None):
        original = self.shapes[name] if shape is None else shape
        metadata = self.sources.get(name, {})
        state = motion or ('bearing' if name in ('51105_rolling_envelope', 'bearing_608')
                           else metadata.get('motion', 'reference'))
        if state not in COLORS:
            raise ValueError(f'Unknown figure motion classification: {name}: {state}')
        provenance = source or metadata.get('source_builder')
        if not provenance:
            raise ValueError(f'Missing source builder for {name}')
        display = original.translate(offset)
        if cut is not None:
            display = display.intersect(cut)
        if not display.val().Solids():
            return None
        return RenderPart(PartRecord(name, state, provenance, _bounds(original), _bounds(display),
                                     metadata.get('printable', False if reference_note else None), reference_note,
                                     installation_direction), display)

    def parts(self, names, **options):
        return tuple(part for name in names if (part := self.part(name, **options)) is not None)


def _cut_box(zmin=-100, zmax=700, *, section=False):
    return (cq.Workplane('XY').box(400, .3 if section else 200, zmax-zmin,
                                 centered=(True, section, False)).translate((0, 0, zmin)))


def _call(name, label, target=None, marker_offset_mm=(0, 0)):
    return Callout(name, label, target, marker_offset_mm)


def _frame_references(model):
    """Illustrative timber and nominal mounting hardware, never product CAD.

    Contact planes and screw axes come from the installed V5 builders. Timber
    sections and lower 4x30 screw envelopes are drawing-only examples, not a
    structural mounting specification. No threads or wood pilot holes are implied.
    """
    source = 'scripts.manual.v5_figures._frame_references'
    bottom = model.generator.housing_offset_z_mm
    upper = model.support.wood_frame_reference.val().BoundingBox().zmin
    records = []
    for name, z, depth in (('lower_wood_frame_reference', bottom-30, 190),
                            ('upper_wood_frame_reference', upper, 70)):
        wood = cq.Workplane('XY').box(260, depth, 30, centered=(True, True, False)).translate((0, 0, z))
        if name.startswith('upper'):
            passage = (cq.Workplane('XY').circle(model.p.shaft.clearance_hole_diameter_mm/2)
                       .extrude(32).translate((0, 0, z-1)))
            wood = wood.cut(passage)
        records.append(model.part(name, shape=wood, motion='stationary', source=source,
                                   reference_note=f'Holzriegel 260 × {depth} × 30 mm; nicht drucken; Beispielquerschnitt, vor Ort auslegen'))
    for index, tab in enumerate(model.generator.housing_parts.bottom_mount_tabs, 1):
        x, y = tab.axis_xy_mm
        seat = bottom+tab.shape.val().BoundingBox().zmax
        shank = cq.Workplane('XY').circle(2).extrude(27).translate((x, y, seat-27))
        head = cq.Workplane('XY').circle(4.5).extrude(3).translate((x, y, seat))
        records.append(model.part(f'lower_wood_screw_{index}_reference', shape=shank.union(head),
                                   motion='stationary', source=source,
                                   reference_note='Holzschraube 4 × 30 mm, flacher Kopf Ø9; nicht drucken; ungeprüfte Nennhülle',
                                   installation_direction=(0, 0, -1)))
    records += [model.part(f'wood_screw_{i}_reference',
                           reference_note='Holzschraube 4 × 40 mm; nicht drucken; V5-Nennhülle',
                           installation_direction=(0, 0, 1)) for i in range(1, 5)]
    return tuple(records)


def build_v5_scenes(p=DEFAULT_PARAMETERS):
    """Return the actual scenes and source manifest for rendering or inspection."""
    m = _Model(p)
    g, s = m.generator, m.support
    C = _call
    scenes = []

    def add(number, slug, title, caption, note, *panels):
        scenes.append(Scene(f'E{number:02d}', slug, title, caption, note, tuple(panels)))

    def panel(title, parts, *callouts, view=(1, -1.8, .7)):
        return Panel(title, tuple(parts), tuple(callouts), view)

    stage_parts = tuple(m.part(stage.name, shape=m.exploded.parts[stage.name]) for stage in m.exploded.stages)
    add(1, 'rotorstapel', 'Sieben Rotorstufen · Vormontage',
        'Ein Base-Modul, fünf gleiche Standard-Module und ein Top-Modul bilden den Rotor.',
        'Einfügepositionen auseinandergezogen; dauerhafte Rastung nach dem Verriegeln.',
        panel('Axial getrennte Stufen', stage_parts + m.parts(('top_washer', 'top_nut'), offset=(0, 0, 6*p.closure.exploded_joint_lift_mm)),
              *[C(stage.name, f'Stufe {i+1}: {"Base" if i == 0 else "Top" if i == 6 else "Standard"}-Modul · rotierend')
                for i, stage in enumerate(m.exploded.stages)],
              C('top_nut', 'M8-Mutter und Scheibe · rotierend'), view=(1, -2, .18)))

    panels = []
    for kind, title, labels in (
            ('base', 'Base · 1 Stück', ('Oberer Magnetträger integriert', 'Zentrierbund für 51105')),
            ('standard', 'Standard · 5 Stück', ('Unterer Bajonettzapfen', 'Obere Aufnahme und Blattnaht')),
            ('top', 'Top · 1 Stück', ('Kompakte Kraftplatte', 'Offener M8-Muttersitz'))):
        part = m.part(kind, shape=m.locked.local_modules[kind], motion='rotating',
                      source=f'windwall.rotor_modules.build_{kind}_module')
        targets = {'base': ((40, -20, -10), (15, -10, -3)),
                   'standard': ((20, -3, -4), (25, -10, p.rotor.stage_height_mm)),
                   'top': ((10, -6, p.rotor.stage_height_mm-2), (0, 0, p.rotor.stage_height_mm))}
        panels.append(panel(title, (part,), C(kind, labels[0], targets[kind][0]),
                            C(kind, labels[1], targets[kind][1])))
    add(2, 'modultypen', 'Drei Druckmodultypen',
        'Die sieben Stufen bestehen aus drei unterschiedlichen, einteiligen CAD-Modultypen.',
        'Alle dargestellten Modulkörper drehen gemeinsam mit der M8-Welle.', *panels)

    joint = build_bayonet_coupon(p)
    seam_z = p.rotor.stage_height_mm
    seam_cut = _cut_box(seam_z-12, seam_z+10)
    seam_parts = m.parts(('base', 'standard_1'), cut=seam_cut)
    male = m.part('bayonet_male', shape=joint.male_at_travel(0).translate((0, 0, 20)),
                  motion='rotating', source='windwall.bayonet.build_bayonet_coupon')
    female = m.part('bayonet_female', shape=joint.female, motion='rotating',
                    source='windwall.bayonet.build_bayonet_coupon')
    add(3, 'bajonett-blattnaht', 'Bajonett und Nut-Feder-Blattnaht',
        'Drei Bajonettklauen verriegeln die Stufen; Nut und Feder führen die Blattnaht.',
        'Vormontage: einführen und verriegeln; elastische Rastung zuerst am Coupon prüfen.',
        panel('Bajonett · getrennte Einfügeposition', (male, female),
              C('bayonet_male', 'Drei Klauen + dauerhafte Rastzähne'),
              C('bayonet_female', 'Aufnahme mit Rampen und Sperrklinken')),
        panel('Reale Naht · Halbschnitt', seam_parts,
              C('standard_1', 'Standard: untere Nut / Bajonett'), C('base', 'Base: obere Feder / Aufnahme')))

    section_names = ('base', 'shaft', 'upper_nut', 'cover', '51105_shaft_washer',
                     '51105_housing_washer', '51105_rolling_envelope')
    add(4, 'base-51105-schnitt', 'Base und Axiallager 51105 · Schnitt',
        'Die Base-Schulter trägt auf der rotierenden Wellenscheibe; die Gehäusescheibe sitzt im Deckel.',
        '51105: 25 × 42 × 11 mm. Wälzbereich als Hülle; tatsächliche Lagerpassung prüfen.',
        panel('Mittelschnitt X–Z · oberer Blattbereich abgeschnitten',
              m.parts(section_names, cut=_cut_box(-25, 8, section=True)),
              C('base', 'Base-Schulter und 25-mm-Pilot · rotierend',
                (-20, 0, g.bearings['51105'].parts['shaft_washer'].val().BoundingBox().zmax+1)),
              C('51105_shaft_washer', '51105 Wellenscheibe · rotierend'),
              C('51105_rolling_envelope', '51105 Wälzbereich · eigene Bewegung'),
              C('51105_housing_washer', '51105 Gehäusescheibe · stationär'),
              C('cover', 'Deckel mit Lagersitz · stationär'),
              C('upper_nut', 'Gefangene M8-Drehmomentmutter'), view=(0, -1, 0)))

    add(5, 'unterer-magnetrotor', 'Unterer Magnetrotor im Gehäuse',
        'Der separate untere Magnetrotor läuft vollständig innerhalb des Gehäuses unter der Spulenkassette.',
        'Gehäuse vorn aufgeschnitten; Kassette und Deckel zur Einsicht ausgeblendet.',
        panel('Montierte Lage · Gehäuse als Halbschnitt',
              m.parts(('housing',), cut=_cut_box()) + m.parts(('lower_magnet_rotor', 'lower_magnets', 'lower_nut', 'spacer')),
              C('housing', 'Geschlossener Gehäuseboden · stationär'),
              C('lower_magnet_rotor', 'Unterer Träger · rotierend'),
              C('lower_magnets', 'Magnete nach oben zur Spule · rotierend'),
              C('lower_nut', 'M8-Drehmomentmutter in Rückentasche (verdeckt)'),
              C('spacer', 'Distanzhülse auf der M8-Welle · rotierend'), view=(1, -1.8, 1.2)))

    explosion = list(m.parts(('housing',), cut=_cut_box()))
    explosion += list(m.parts(('lower_magnet_rotor', 'lower_magnets', 'lower_nut', 'spacer')))
    explosion += list(m.parts(('coil_cassette', 'winding_volume'), offset=(0, 0, 40)))
    explosion += list(m.parts(('cover', '51105_housing_washer', '51105_rolling_envelope', '51105_shaft_washer'), offset=(0, 0, 70)))
    explosion += list(m.parts(('base', 'upper_magnets', 'upper_nut'), offset=(0, 0, 100), cut=_cut_box(-100, 112)))
    explosion += list(m.parts(('cover_screw_1', 'cover_nut_1'), offset=(0, 0, 90)))
    add(6, 'generator-explosion', 'Generator · Explosionsdarstellung',
        'Kassette, Deckel und Base sind angehoben; der untere Magnetrotor bleibt im aufgeschnittenen Gehäuse.',
        'Unterer Rotor unter der stationären Wicklung. Base-Blätter zur Lesbarkeit gekürzt.',
        panel('Montagereihenfolge entlang der gemeinsamen Wellenachse', explosion,
              C('base', 'Base mit oberem Magnetträger · rotierend'),
              C('cover', 'Deckel und 51105-Aufnahme · stationär'),
              C('coil_cassette', 'Spulenkassette · stationär'),
              C('winding_volume', 'Aktiver Wicklungsraum · stationär'),
              C('lower_magnet_rotor', 'Unterer Magnetrotor im Gehäuse · rotierend'),
              C('housing', 'Gehäuse / Bodenlaschen · stationär'),
              C('cover_screw_1', '6 × M4-Deckelschraube (1 gezeigt)'),
              C('cover_nut_1', '6 × gefangene M4-Mutter (1 gezeigt)'), view=(1, -2, .35)))

    all_generator = tuple({**g.rotating_parts, **g.stationary_parts, **g.bearing_parts})
    add(7, 'generator-schnitt', 'Generator · montierter Mittelschnitt',
        'Zwei rotierende Magnetträger umschließen die stationäre Wicklung; der untere Rotor sitzt im Gehäuse.',
        f'Nennabstand Magnet–Wicklung: oben {g.upper_air_gap_mm():.1f} mm / unten {g.lower_air_gap_mm():.1f} mm. Keine Betriebsfreigabe.',
        panel('X–Z · reale Höhen, keine Explosion', m.parts(all_generator, cut=_cut_box(-60, 8, section=True)),
              C('base', 'Base / oberer Magnetträger · rotierend'),
              C('cover', 'Deckel über der Wicklung · stationär'),
              C('winding_volume', 'Wicklungsraum · stationär'),
              C('coil_cassette', 'Spulenkassette / Boden · stationär'),
              C('lower_magnet_rotor', 'Unterer Magnetrotor · rotierend'),
              C('housing', 'Gehäuse mit geschlossenem Boden · stationär'),
              C('lower_nut', 'M8-Mutter im unteren Rotor'), view=(0, -1, 0)))

    retention = m.parts(('housing',), cut=_cut_box()) + m.parts(('coil_cassette',), offset=(0, 0, 25)) + m.parts(('cover',), offset=(0, 0, 50))
    add(8, 'kassettenrueckhaltung', 'Spulenkassette · Führung und Rückhaltung',
        'Die Kassette sitzt auf der Gehäuseschulter; der Deckel begrenzt den Hub nach oben.',
        'Der einzelne Schlüssel bei −X sperrt die Verdrehung. Passung am Segment-Coupon prüfen.',
        panel('Stationäre Teile · axial getrennt', retention,
              C('cover', 'Deckel hält die Kassette axial zurück'),
              C('coil_cassette', 'Kassette mit einzelnem Verdrehsicherungssteg',
                (-59, 0, 58+g.housing_offset_z_mm)),
              C('housing', 'Gehäuseschulter und passende Schlüsselnut',
                (-g.housing_parts.metadata['cassette_radius_mm']-1.35, 0,
                 g.housing_offset_z_mm+g.housing_parts.metadata['cassette_bottom_z_mm']),
                marker_offset_mm=(14, -5)), view=(-1, -1.8, .7)))

    hardware = m.parts(('housing',), cut=_cut_box()) + m.parts(('cover',), offset=(0, 0, 32))
    hardware += tuple(m.part(f'cover_screw_{i}', offset=(0, 0, 55)) for i in range(1, 7))
    hardware += tuple(m.part(f'cover_nut_{i}', offset=(0, 0, -35)) for i in range(1, 7))
    add(9, 'deckelverschraubung', 'Deckel · sechs M4-Verschraubungen',
        'Sechs M4-Schrauben befestigen den stationären Deckel in gefangenen Muttern der Gehäuseaugen.',
        'Schrauben und Muttern sind Nennhüllen. Zugang von oben; reales Werkzeug prüfen.',
        panel('Hardware axial abgesetzt', hardware,
              C('cover_screw_1', '6 × M4-Schraube · stationär'),
              C('cover', 'Deckel mit sechs Durchgangsbohrungen'),
              C('housing', 'Gehäuseaugen mit Sechskanttaschen',
                (*g.housing_parts.cover_fasteners[0].axis_xy_mm, g.housing_offset_z_mm+3.4),
                marker_offset_mm=(13, 5)),
              C('cover_nut_1', '6 × gefangene M4-Mutter · stationär')))

    cable = g.housing_parts.cable_passage.translate((0, 0, g.housing_offset_z_mm))
    cable_part = m.part('cable_passage', shape=cable, motion='reference',
                        source='windwall.generator_housing.build_generator_housing')
    # The passage is a builder-supplied clearance volume, offset for an exploded
    # view so the actual matching holes remain visible on both stationary bodies.
    add(10, 'seitlicher-kabelausgang', 'Seitlicher Kabelausgang · 45°',
        'Die seitlichen Öffnungen von Kassette und Gehäuse fluchten bei korrekt eingesetztem Schlüssel.',
        'Graue Hülle = freier Kabeldurchgang Ø6 mm; kein montiertes Kabel, keine Abdichtung.',
        panel('Gehäuse und angehobene Kassette', m.parts(('housing',)) + m.parts(('coil_cassette',), offset=(0, 0, 38)) + (cable_part,),
              C('housing', 'Gehäuseöffnung bei 45°', (46, 46, 33+g.housing_offset_z_mm)),
              C('coil_cassette', 'Kassettenöffnung bei 45°', (41, 41, 71+g.housing_offset_z_mm),
                marker_offset_mm=(14, 10)),
              C('cable_passage', 'Ø6-mm-Durchgang · Referenzvolumen'), view=(1, 1, .85)))

    thrust = build_51105_fit_coupon(p)
    radial = build_608_fit_coupon(p)
    seat_part = m.part('51105_outer_seat_coupon',
                       shape=thrust.shape.intersect(_cut_box(0, 40).mirror('XZ')),
                       motion='reference', source='windwall.bearings.build_51105_fit_coupon')
    pilot_part = m.part('25mm_pilot_coupon', shape=thrust.shape.intersect(_cut_box(0, 40)),
                        motion='reference', source='windwall.bearings.build_51105_fit_coupon')
    add(11, '51105-passungsprobe', 'Passungsprobe · Axiallager 51105',
        'Drei Gehäusesitze und drei Pilotdurchmesser erlauben die Auswahl mit dem realen 51105-Lager.',
        'Zwei getrennte Druckproben gemäß V5-Release. Prüflager 51105: 25 × 42 × 11 mm.',
        panel('51105-Außensitz-Coupon', (seat_part,),
              *[C('51105_outer_seat_coupon', f'Sitz {i+1}: Ø {value:.1f} mm'.replace('.', ','),
                  (x, -28, thrust.seat_depth_mm))
                for i, (x, value) in enumerate(zip((-55, 0, 55), thrust.seat_diameters_mm))]),
        panel('25-mm-Pilot-Coupon', (pilot_part,),
              *[C('25mm_pilot_coupon', f'Pilot {i+1}: Ø {value:.1f} mm'.replace('.', ','),
                  (x, 28, thrust.seat_depth_mm+10))
                for i, (x, value) in enumerate(zip((-55, 0, 55), thrust.pilot_diameters_mm))]))
    radial_part = m.part('608_seat_coupon', shape=radial.shape, motion='reference',
                         source='windwall.bearings.build_608_fit_coupon')
    add(12, '608-passungsprobe', 'Passungsprobe · Radiallager 608',
        'Drei Sitzdurchmesser prüfen die Passung des realen 608-Lagers für den oberen Halter.',
        '608: 8 × 22 × 7 mm. Passung auf M8-Gewinde und Beweglichkeit bleiben praktisch zu prüfen.',
        panel('Drei abgestufte Sitze', (radial_part,),
              *[C('608_seat_coupon', f'Sitz {i+1}: Ø {value:.1f} mm'.replace('.', ','), (x, 0, radial.seat_depth_mm))
                for i, (x, value) in enumerate(zip((-30, 0, 30), radial.seat_diameters_mm))]))

    upper = m.parts(('top_support',)) + m.parts(('bearing_608',), offset=(0, 0, 14))
    upper += m.parts(('upper_wood_frame_reference',), offset=(0, 0, 30))
    upper += tuple(m.part(f'wood_screw_{i}_reference', offset=(0, 0, -25)) for i in range(1, 5))
    support_section = m.parts(('top_support', 'bearing_608', 'upper_wood_frame_reference', 'shaft'),
                              cut=_cut_box(s.plate_bottom_z_mm-10, s.plate_bottom_z_mm+43, section=True))
    add(13, 'oberer-halter', 'Oberer 608-Halter · Montage von unten',
        'Der stationäre Halter wird von unten an den Holzrahmen geschraubt; das Holz schließt den Lagersitz.',
        'M8-Klemmung zuerst anziehen. Vier Holzschrauben 4 × 40 mm sind ungeprüfte Nennhüllen.',
        panel('Explosion · Ansicht leicht von unten', upper,
              C('upper_wood_frame_reference', 'Vorhandener Holzrahmen · stationär'),
              C('bearing_608', '608-Lager in nach oben offenem Sitz'),
              C('top_support', 'Halter 80 × 50 × 12 mm · stationär'),
              C('wood_screw_1_reference', '4 × Holzschraube von unten nach oben'), view=(1, -2, -.25)),
        panel('Montierter Mittelschnitt', support_section,
              C('upper_wood_frame_reference', 'Holz hält Lager nach oben zurück'),
              C('bearing_608', '608 führt radial; 0,2 mm Sitzspiel'),
              C('top_support', 'Untere Schulter hält Lager nach unten',
                (-8, 0, s.plate_bottom_z_mm+s.bottom_shoulder_mm)),
              C('shaft', 'Durchgehende verlängerte M8-Welle'), view=(0, -1, 0)))

    frame_references = _frame_references(m)
    fence_names = tuple(name for name in m.shapes if name != 'upper_wood_frame_reference'
                        and not name.startswith('wood_screw_'))
    installed_fence = m.parts(fence_names) + frame_references
    frame_by_name = {part.record.name: part for part in frame_references}
    lower_z = g.housing_offset_z_mm
    # The X-Z section passes through the actual +/-X tab holes and lower screws.
    lower_section = list(m.parts(('housing',), cut=_cut_box(-90, -12, section=True)))
    for name in ('lower_wood_frame_reference', 'lower_wood_screw_1_reference', 'lower_wood_screw_3_reference'):
        part = frame_by_name[name]
        lower_section.append(m.part(name, shape=part.shape, cut=_cut_box(-90, -12, section=True),
                                    motion='stationary', source=part.record.source_builder,
                                    reference_note=part.record.reference_note,
                                    installation_direction=part.record.installation_direction))
    add(14, 'zaunmontage', 'Einbau am vorhandenen Holzrahmen',
        'Zwischen zwei Holzriegeln: Gehäuse von oben befestigt, oberer 608-Halter von unten angeschraubt.',
        'Holz und Holzschrauben: Referenzen, nicht drucken. Querschnitte und Befestigung vor Ort auslegen; keine Lastfreigabe.',
        panel('Vollständige Einbaulage zwischen zwei Riegeln', installed_fence,
              C('upper_wood_frame_reference', 'Oberer Holzriegel · Referenz, nicht drucken'),
              C('top_support', '608-Halter · 4 Holzschrauben von unten', (30, -15, s.plate_bottom_z_mm), (30, -22)),
              C('lower_wood_frame_reference', 'Unterer Holzriegel · Referenz, nicht drucken'),
              C('lower_wood_screw_1_reference', 'Bodenlaschen · 4 Holzschrauben von oben', (83, 0, lower_z+6), (24, 24)),
              view=(1, -2, .15)),
        panel('Unterer Anschluss · Schnitt durch zwei Laschen', lower_section,
              C('housing', 'Gehäuseboden und vier Bodenlaschen', (70, 0, lower_z+5)),
              C('lower_wood_screw_1_reference', '4 × 30 mm von oben nach unten; Nennhüllen', (83, 0, lower_z+8), (15, 14)),
              C('lower_wood_frame_reference', 'Laschen-Unterseite liegt auf dem Holz', (73, 0, lower_z), (0, -15)),
              C('lower_wood_frame_reference', 'Holz / Schrauben: nicht drucken', (-100, 0, lower_z-20)),
              view=(0, -1, 0)))
    add(15, 'gesamtbaugruppe', 'Gesamtbaugruppe · Betriebsanordnung im CAD',
        'Sieben Rotorstufen und Generator sind zwischen unterem und oberem Holzriegel montiert.',
        'Holz / Holzschrauben: nicht drucken, vor Ort auslegen. CAD V5; Passung, Elektrik und Betrieb sind unvalidiert.',
        panel('Gesamtansicht mit beiden Rahmenanschlüssen', installed_fence,
              C('upper_wood_frame_reference', 'Oberer Holzriegel · nicht drucken'),
              C('top_support', '608-Halter · 4 Schrauben von unten', (30, -15, s.plate_bottom_z_mm), (30, -22)),
              C('standard_3', 'Rotor · 1 Base + 5 Standard + 1 Top'),
              C('lower_wood_screw_1_reference', 'Bodenlaschen · 4 Schrauben von oben', (83, 0, lower_z+6), (24, 24)),
              C('lower_wood_frame_reference', 'Unterer Holzriegel · nicht drucken'), view=(1, -2, .18)),
        panel('Generator · aufgeschnittenes Einbaudetail', m.parts(all_generator, cut=_cut_box(-60, 8)),
              C('base', 'Oberer Magnetträger · rotierend'), C('winding_volume', 'Wicklung / Kassette · stationär'),
              C('lower_magnet_rotor', 'Unterer Magnetrotor · rotierend',
                (35, 0, g.lower_rotor.val().BoundingBox().zmax-2)),
              C('housing', 'Gehäuse / Deckel · stationär')))
    return tuple(scenes), m.manifest_path


def _basis(direction):
    view = np.asarray(direction, dtype=float)
    view /= np.linalg.norm(view)
    right = np.cross((0, 0, 1), view)
    if np.linalg.norm(right) < 1e-8:
        right = np.array((1., 0., 0.))
    right /= np.linalg.norm(right)
    return view, right, np.cross(view, right)


def _draw_panel(fig, panel, rectangle, *, compact=False):
    """Use numbered in-scene markers; all descriptive text lives outside CAD."""
    x, y, width, height = rectangle
    if compact:
        ax = fig.add_axes((x, y+height*.30, width, height*.64))
        label_ax = fig.add_axes((x+.015, y, width-.03, height*.27))
    else:
        ax = fig.add_axes((x, y, width*.64, height*.94))
        label_ax = fig.add_axes((x+width*.68, y+height*.05, width*.32, height*.82))
    label_ax.axis('off')
    fig.text(x, y+height*.97, panel.title, fontsize=13, fontweight='bold', color='#324353')
    view, right, up = _basis(panel.view)
    polygons, depths, colors = [], [], []
    projected_by_name = {}
    for part in panel.parts:
        part_polygons = []
        for solid in part.shape.val().Solids():
            vertices, triangles = solid.tessellate(.35, .28)
            xyz = np.asarray([v.toTuple() for v in vertices])[np.asarray(triangles)]
            if 'coupon' in part.record.name or ('wood_frame' in part.record.name and part.record.reference_note):
                # Long planar triangles can incorrectly obscure a nearer seat
                # when sorted only by their centroid. Bound their size before
                # the painter sort; subdivision preserves the actual CAD plane.
                finished = []
                while len(xyz):
                    lengths = np.linalg.norm(xyz-np.roll(xyz, 1, axis=1), axis=2)
                    large = lengths.max(axis=1) > 8
                    finished.append(xyz[~large])
                    a, b, c = xyz[large].transpose(1, 0, 2)
                    ab, bc, ca = (a+b)/2, (b+c)/2, (c+a)/2
                    xyz = np.concatenate([np.stack(v, axis=1) for v in
                                          ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca))])
                xyz = np.concatenate(finished)
            normals = np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0])
            normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
            illumination = .55+.45*np.abs(normals@view)
            polygon = np.stack((xyz@right, xyz@up), axis=2)
            polygons.append(polygon)
            part_polygons.append(polygon)
            depths.append((xyz@view).mean(axis=1))
            rgb = np.asarray(to_rgb(COLORS[part.record.motion]))
            if part.record.name in ('upper_magnets', 'lower_magnets'):
                rgb *= .65
            elif part.record.name == 'winding_volume':
                rgb = .65*rgb+.35
            elif 'wood_frame' in part.record.name and part.record.reference_note:
                rgb = .35*rgb+.65
            colors.append(illumination[:, None]*rgb)
        projected_by_name[part.record.name] = np.concatenate(part_polygons).reshape(-1, 2)
    flat = np.concatenate(polygons)
    order = np.argsort(np.concatenate(depths), kind='stable')
    ax.add_collection(PolyCollection(flat[order], facecolors=np.concatenate(colors)[order],
                                    edgecolors='none', linewidths=0, antialiaseds=True))
    if panel.view == (0, -1, 0):
        # Draw actual section edges so touching parts of the same motion color
        # remain distinguishable (cassette/winding, plate/wood, bearing washers).
        for part in panel.parts:
            for edge in part.shape.val().Edges():
                vertices = edge.positions(np.linspace(0, 1, max(2, int(edge.Length()/.6))))
                xyz = np.asarray([vertex.toTuple() for vertex in vertices])
                ax.plot(xyz@right, xyz@up, color='#294955', linewidth=.45)
    points = flat.reshape(-1, 2)
    minimum, maximum = points.min(axis=0), points.max(axis=0)
    span = np.maximum(maximum-minimum, 1)
    ax.set_xlim(minimum[0]-.13*span[0], maximum[0]+.13*span[0])
    ax.set_ylim(minimum[1]-.08*span[1], maximum[1]+.08*span[1])
    ax.set_aspect('equal')
    ax.axis('off')
    used = []
    for index, callout in enumerate(panel.callouts, 1):
        candidates = projected_by_name.get(callout.name)
        if candidates is None:
            raise ValueError(f'Callout target is not visible: {callout.name}')
        if callout.target is not None:
            target = np.array((np.asarray(callout.target)@right, np.asarray(callout.target)@up))
        else:
            # An actual triangle vertex near the visible right outline avoids
            # placing a marker in a ring bore or an empty bounding-box center.
            target = candidates[np.argmax(candidates[:, 0])].copy()
        marker = target + np.asarray(callout.marker_offset_mm)
        while any(np.linalg.norm((marker-other)/span) < .055 for other in used):
            marker[0] -= span[0]*.055
        used.append(marker)
        if not np.allclose(marker, target):
            ax.plot((marker[0], target[0]), (marker[1], target[1]), color='#263745', lw=.7)
        ax.text(*marker, str(index), ha='center', va='center', fontsize=10, fontweight='bold',
                color='#182c3a', bbox={'boxstyle': 'circle,pad=.23', 'fc': 'white', 'ec': '#405362', 'lw': .8})
        text = textwrap.fill(callout.label, width=40 if compact and width > .4 else 32 if compact else 38)
        label_ax.text(0, 1-(index-1)/max(len(panel.callouts), 1), f'{index:02d}  {text}',
                      va='top', fontsize=11 if compact else 13, color='#263745', linespacing=1.35)


def _render_scene(scene, output_dir):
    fig = plt.figure(figsize=(16, 11.2), dpi=150, facecolor='#ffffff')
    fig.text(.045, .946, f'{scene.drawing_id}  |  WINDWALL V5', fontsize=13, fontweight='bold', color='#487080')
    fig.text(.045, .905, scene.title, fontsize=23, fontweight='bold', color='#182c3a')
    fig.text(.045, .865, scene.caption, fontsize=12.5, color='#3d5261')
    count = len(scene.panels)
    if count == 1:
        _draw_panel(fig, scene.panels[0], (.045, .255, .91, .565))
    else:
        width = .91/count
        for index, panel in enumerate(scene.panels):
            _draw_panel(fig, panel, (.045+index*width, .225, width-.024, .59), compact=True)
    fig.text(.045, .176, textwrap.fill(scene.note, 135), fontsize=12, color='#3d5261', linespacing=1.5)
    for index, (state, label) in enumerate(zip(COLORS, LEGEND)):
        x, y = .045+(index % 2)*.49, .110-(index//2)*.032
        fig.text(x, y, '■', fontsize=16, color=COLORS[state])
        fig.text(x+.019, y+.001, label, fontsize=10, color='#3d5261')
    fig.text(.045, .038, 'Quelle: aktuelle V5-CAD-Builder + release/v5/manifest.json · Nennmaße in mm · keine Maßstabszeichnung',
             fontsize=9, color='#61717c')
    filename = f'{scene.drawing_id}-{scene.slug}.png'
    path = output_dir / filename
    labels = tuple(callout.label for panel in scene.panels for callout in panel.callouts)
    alt = f'{scene.drawing_id}. {scene.caption} {scene.note} ' + ' '.join(labels)
    fig.savefig(path, dpi=150, metadata={'Title': f'{scene.drawing_id} {scene.title}', 'Description': alt,
                                        'Software': 'Windwall V5 deterministic CadQuery/Matplotlib renderer'})
    plt.close(fig)
    parts = tuple(part.record for panel in scene.panels for part in panel.parts)
    callouts = tuple(callout for panel in scene.panels for callout in panel.callouts)
    return FigureRecord(scene.drawing_id, path, filename, scene.caption, alt, labels, LEGEND,
                        2400, 1680, 'de', parts, callouts)


def render_v5_figures(output_dir: Path, p=DEFAULT_PARAMETERS) -> tuple[FigureRecord, ...]:
    """Render exactly E01–E15 and a portable, machine-readable figures.json."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    scenes, manifest_path = build_v5_scenes(p)
    records = tuple(_render_scene(scene, output_dir) for scene in scenes)
    parameters = asdict(p)
    projections = parameters.pop('closure')
    parameters['shaft_projections'] = {key: projections[key] for key in
                                      ('rod_projection_mm', 'shaft_bottom_projection_mm', 'exploded_joint_lift_mm')}
    parameters['modules'].pop('closure_pilot_depth_mm')
    parameters['modules'].pop('closure_screw_radius_mm')
    payload = {'release': 'v5', 'source_manifest': 'release/v5/manifest.json',
               'source_manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
               'render_parameters': parameters, 'physical_validation_verified': False,
               'figures': [{key: value for key, value in asdict(record).items() if key != 'path'}
                           for record in records]}
    (output_dir / 'figures.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return records


def render_rotor_preview(assembly, path: Path) -> None:
    """Share the V5 projection and legend with the legacy preview entry point.

    The caller supplies its already audited assembly, avoiding another CAD
    build and keeping the PNG synchronized with that preview's STEP exports.
    """
    parts, section = [], []
    slab = _cut_box(-60, 8, section=True)
    for name, shape in assembly.parts.items():
        motion = ('rotating' if name in assembly.rotating_parts else
                  'stationary' if name in assembly.stationary_parts else 'bearing')
        record = PartRecord(name, motion, 'windwall.assembly.build_locked_rotor_assembly',
                            _bounds(shape), _bounds(shape))
        parts.append(RenderPart(record, shape))
        clipped = shape.intersect(slab)
        if clipped.val().Solids():
            section.append(RenderPart(PartRecord(name, motion, record.source_builder,
                                                 record.source_bounds_mm, _bounds(clipped)), clipped))
    scene = Scene('V5', 'assembly-preview', 'Rotorbaugruppe · aktuelle V5-Vorschau',
                  'Sieben kontinuierlich phasierte Stufen über dem eingeschlossenen Generator.',
                  'Aktuelle CAD-Geometrie; physische Passung und Betrieb sind nicht validiert.',
                  (Panel('Montierter Rotor', tuple(parts),
                         (Callout('top', 'Top-Modul und offene M8-Klemmung'),
                          Callout('housing', 'Stationäres Generatorgehäuse')), (1, -2, .18)),
                   Panel('Generator · Mittelschnitt', tuple(section),
                         (Callout('base', 'Oberer Magnetträger · rotierend'),
                          Callout('winding_volume', 'Wicklung · stationär'),
                          Callout('lower_magnet_rotor', 'Unterer Magnetrotor im Gehäuse')), (0, -1, 0))))
    record = _render_scene(scene, path.parent)
    record.path.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=PROJECT_ROOT / 'release/v5/drawings')
    args = parser.parse_args()
    records = render_v5_figures(args.output_dir)
    print(f'Rendered {len(records)} V5 drawings at 2400 × 1680 pixels: {args.output_dir}', flush=True)


if __name__ == '__main__':
    main()
