"""Single source of truth for the assembly manual's parts and dimensions.

This module deliberately has no CadQuery dependency.  Mechanical dimensions
that describe the released stack are read from ``build/manifest.json`` while
the design parameters provide the remaining provisional generator envelopes.
The returned records are copies, so document and figure builders can annotate
them without changing the source model for later consumers.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from windwall.parameters import DEFAULT_PARAMETERS


SELECTION_AFTER_MEASUREMENT = 'Nach Messung auswählen'


def _part(
    description: str,
    quantity: int | str,
    specification: str,
    drawings: tuple[str, ...],
    *,
    source_file: str | None = None,
    selection_status: str = 'Erforderlich',
    size: str | None = None,
) -> dict[str, Any]:
    """Create a consistent BOM record for a printed or purchased item."""

    record: dict[str, Any] = {
        'description': description,
        'quantity': quantity,
        'specification': specification,
        'selection_status': selection_status,
        'source_file': source_file,
        'drawings': list(drawings),
    }
    if size is not None:
        record['size'] = size
    return record


PRINTED_PARTS: dict[str, dict[str, Any]] = {
    'P01': _part(
        'Basis-Rotormodul mit integriertem oberem Magnetträger',
        1,
        'Ein Basis-Modul; der obere Magnetträger ist in diesem Druckteil integriert.',
        ('E01', 'E02', 'E03', 'E04', 'E06'),
        source_file='src/windwall/rotor_modules.py',
    ),
    'P02': _part(
        'Standard-Rotormodul',
        5,
        'Fünf identische Standardstufen für den Sieben-Stufen-Rotor.',
        ('E01', 'E04', 'E06'),
        source_file='src/windwall/rotor_modules.py',
    ),
    'P03': _part(
        'Top-Rotormodul',
        1,
        'Oberes Rotormodul mit zugänglichem M8-Klemmplatz.',
        ('E01', 'E05', 'E06'),
        source_file='src/windwall/rotor_modules.py',
    ),
    'P04': _part(
        'Abnehmbare obere Abdeckung',
        1,
        'Abdeckung mit zwei M3-Pilotbohrungen; sie übernimmt nicht die M8-Klemmkraft.',
        ('E01', 'E05'),
        source_file='src/windwall/top_closure.py',
    ),
    'P05': _part(
        'Unterer separater Magnetrotor',
        1,
        'Separater, nach oben gerichteter Magnetträger unter dem Stator.',
        ('E01', 'E02', 'E03', 'E06', 'E07'),
        source_file='src/windwall/generator.py',
    ),
}


HARDWARE: dict[str, dict[str, Any]] = {
    'H01': _part(
        'M8 Gewindestange',
        1,
        'Durchgehende nominale Achse; modellierte Hülllänge 559,64 mm. Zuschnitt erst nach Messung des realen Stacks.',
        ('E01', 'E02', 'E05', 'E06'),
        source_file='build/manifest.json',
        size='M8',
    ),
    'H02': _part(
        'M8 Mutter',
        3,
        'Drei Klemmstellen: Basis, unterer Rotor und obere Klemme; nominal 13 mm Schlüsselweite.',
        ('E01', 'E02', 'E05', 'E06'),
        source_file='build/manifest.json',
        size='M8; 13 mm SW',
    ),
    'H03': _part(
        'M8 Unterlegscheibe',
        2,
        'Klemmflächen unter der oberen Mutter und über der unteren Mutter; nominal 24 mm außen × 2 mm.',
        ('E01', 'E02', 'E05', 'E06'),
        source_file='build/manifest.json',
        size='24 mm außen × 2 mm',
    ),
    'H04': _part(
        'Radialer M3-Rückhaltebolzen',
        12,
        'Zwei je Naht an sechs Nähten; nominal M3 × 12 mm, selbstschneidend, nur gegen Rückdrehen.',
        ('E01', 'E04', 'E05'),
        source_file='build/manifest.json',
        size='M3 × 12 mm',
    ),
    'H05': _part(
        'Verschlussschraube M3',
        2,
        'Zwei Schrauben zur lösbaren oberen Abdeckung; nicht Teil der M8-Klemmung.',
        ('E01', 'E05'),
        source_file='build/manifest.json',
        size='M3 × 12 mm',
    ),
    'H06': _part(
        'Lagerhülle (provisorische Referenz)',
        1,
        'Nominale Hüllgeometrie 12 × 8 × 6 mm in einem gemessenen Sitz; kein freigegebenes Lagerprodukt.',
        ('E02', 'E06'),
        source_file='src/windwall/generator.py',
        selection_status='Provisorische Referenzgeometrie; Sitz und axiale Halterung messen',
        size='12 mm außen × 8 mm innen × 6 mm',
    ),
    'H07': _part(
        'Distanzhülse (provisorisch)',
        1,
        'Nominal 12 mm außen, 8,8 mm Bohrung, bei den Standardlücken etwa 17 mm lang; Werkstoff und Drucklast offen.',
        ('E02', 'E06'),
        source_file='src/windwall/generator.py',
        selection_status='Provisorische Referenzgeometrie; Länge und Drucklast messen',
        size='12 mm außen × 8,8 mm Bohrung',
    ),
    'H08': _part(
        'Emaillierter Kupferdraht',
        1,
        'Mit vorhandenem nominalem 0,18-mm-Draht starten; jede Spule über der Emaille mit Mikrometer messen.',
        ('E08', 'E09', 'E10'),
        selection_status='Durch Messung charakterisieren; kein finaler Drahtdurchmesser festgelegt',
        size='nominal 0,18 mm, gemessener Durchmesser maßgeblich',
    ),
    'H09': _part(
        'Isolierung und temporäres Bindematerial',
        'nach Bedarf',
        'Isolierpapier oder geeignete Folie sowie weiches Band/Faden für die Testwicklung; keine scharfen Werkzeuge an der Emaille.',
        ('E08', 'E09', 'E10'),
        selection_status='Nach Material- und Isolationsprüfung auswählen',
    ),
    'H10': _part(
        'Neodym-Scheibenmagnet',
        36,
        'Zwei Rotoren mit je 18 Magneten; auf jedem Rotor abwechselnde N-S-Polung und gegenüberliegende Anziehung.',
        ('E02', 'E03', 'E06', 'E07'),
        source_file='build/manifest.json',
        selection_status='Magnetmaß, Polung, Überstand und Rückhalteverfahren vor Betrieb messen',
        size='10 x 2 mm',
    ),
    'H11': _part(
        'Magnetkleber und mechanische Rückhaltung',
        'nach Bedarf',
        'Klebstoff plus separat zu entwickelnde Rückhaltung gegen Fliehkraft; Kleben erst nach Trockenlayout und Coupon.',
        ('E03', 'E06', 'E07'),
        selection_status='Vor Retentionstest nicht freigegeben',
    ),
    'H12': _part(
        'Geeigneter Brückengleichrichter',
        1,
        SELECTION_AFTER_MEASUREMENT,
        ('E10', 'E11'),
        selection_status=SELECTION_AFTER_MEASUREMENT,
    ),
    'H13': _part(
        'Überstromschutz auf Generatorseite',
        1,
        SELECTION_AFTER_MEASUREMENT,
        ('E10', 'E11'),
        selection_status=SELECTION_AFTER_MEASUREMENT,
    ),
    'H14': _part(
        'Windgenerator-Laderegler mit Diversion/Dump-Load-Funktion',
        1,
        SELECTION_AFTER_MEASUREMENT,
        ('E10', 'E11'),
        selection_status=SELECTION_AFTER_MEASUREMENT,
    ),
    'H15': _part(
        'Dump Load / Überschusslast',
        1,
        SELECTION_AFTER_MEASUREMENT,
        ('E11',),
        selection_status=SELECTION_AFTER_MEASUREMENT,
    ),
    'H16': _part(
        'Batterieseitige Sicherung',
        1,
        SELECTION_AFTER_MEASUREMENT,
        ('E11',),
        selection_status=SELECTION_AFTER_MEASUREMENT,
    ),
    'H17': _part(
        '48-V-Bleiakku-Bank',
        1,
        'Vorhandene oder separat spezifizierte Bleiakku-Bank; Generator niemals direkt anschließen.',
        ('E11',),
        selection_status='Systemkonfiguration und Ladegrenzen vor Auswahl prüfen',
        size='48 V nominal',
    ),
}


DRAWINGS: dict[str, dict[str, Any]] = {
    'E01': {
        'title': 'Gesamtexplosion des Sieben-Stufen-Rotors',
        'description': 'Explosionsansicht mit Basis, fünf Standardstufen, Top, Abdeckung, Welle und Klemmteilen.',
        'items': ['P01', 'P02', 'P03', 'P04', 'P05', 'H01', 'H02', 'H03', 'H04', 'H05'],
        'figure_file': 'output/manual-figures/E01-gesamt-explosion.png',
    },
    'E02': {
        'title': 'Generator-Explosion',
        'description': 'Getrennte rotierende und stehende Generatorgruppen mit Lager- und Distanzreferenzen.',
        'items': ['P01', 'P05', 'H01', 'H02', 'H03', 'H06', 'H07', 'H10'],
        'figure_file': 'output/manual-figures/E02-generator-explosion.png',
    },
    'E03': {
        'title': 'Basisrotor und Magnetträger',
        'description': 'Basis mit integriertem oberem Träger und separatem unteren Magnetrotor; Magnetrückhaltung bleibt offen.',
        'items': ['P01', 'P05', 'H10', 'H11'],
        'figure_file': 'output/manual-figures/E03-basisrotor.png',
    },
    'E04': {
        'title': 'Standardverbindung und CCW-Bajonett',
        'description': 'Einsetzen 18 Grad im Uhrzeigersinn, Verriegeln gegen den Uhrzeigersinn; drei Nasen, zwei Treiber und zwei Rückhalter.',
        'items': ['P01', 'P02', 'H04'],
        'figure_file': 'output/manual-figures/E04-standardverbindung.png',
    },
    'E05': {
        'title': 'Top-Abschluss und Klemmung',
        'description': 'Obere Abdeckung mit zwei lösbaren M3-Schrauben, Scheibe und zugänglicher M8-Mutter.',
        'items': ['P03', 'P04', 'H01', 'H02', 'H03', 'H04', 'H05'],
        'figure_file': 'output/manual-figures/E05-topabschluss.png',
    },
    'E06': {
        'title': 'Schnitt durch Welle und Luftspalte',
        'description': 'Schnittansicht mit nominal 1,5 mm Luftspalt je Seite, bündigen oder versenkten Magneten und provisorischen Lagerhüllen.',
        'items': ['P01', 'P02', 'P03', 'P05', 'H01', 'H02', 'H03', 'H06', 'H07', 'H10'],
        'figure_file': 'output/manual-figures/E06-schnitt-luftspalt.png',
    },
    'E07': {
        'title': 'Magnetpolung beider Rotoren',
        'description': 'Je 18 Taschen mit alternierender N-S-Polung; gegenüberliegende Flächen zeigen entgegengesetzte Pole und ziehen sich an.',
        'items': ['P05', 'H10', 'H11'],
        'figure_file': 'output/manual-figures/E07-magnetpolung.png',
    },
    'E08': {
        'title': 'Serpentinenpfad der Testwicklung',
        'description': 'Ein durchgehender Pfad zwischen Innen- und Außenradius mit markiertem Start A1 und Ende A2.',
        'items': ['H08', 'H09'],
        'figure_file': 'output/manual-figures/E08-serpentinenpfad.png',
    },
    'E09': {
        'title': 'Wickelschablone',
        'description': 'Board- und isolierte-Pin-Schablone für 20-, 40- und 80-Windungen, ohne erzwungenes Packen.',
        'items': ['H08', 'H09'],
        'figure_file': 'output/manual-figures/E09-wickelschablone.png',
    },
    'E10': {
        'title': 'Messaufbau der Testspulen',
        'description': 'Drehzahlmesser, Multimeter, definierte Last und Messfelder für Spannung, Strom, Widerstand und Temperatur.',
        'items': ['H08', 'H09', 'H12', 'H13', 'H14'],
        'figure_file': 'output/manual-figures/E10-messaufbau.png',
    },
    'E11': {
        'title': 'Sichere Ladekette',
        'description': 'Generator → Gleichrichter → Schutz → Wind-Laderegler/Dump Load → Sicherung → 48-V-Bleiakku; direkte Verbindung ist durchgestrichen.',
        'items': ['H12', 'H13', 'H14', 'H15', 'H16', 'H17'],
        'figure_file': 'output/manual-figures/E11-ladekette.png',
    },
}


VALIDATION_STATUS: dict[str, Any] = {
    'physical_fit': False,
    'pla_strength': False,
    'magnet_retention': False,
    'bearing_retention': False,
    'outdoor_service': False,
    'electrical_design_finalized': False,
    'electrical_ratings': SELECTION_AFTER_MEASUREMENT,
    'direct_generator_to_battery': 'Verboten',
}


def _read_manifest(project_root: Path) -> dict[str, Any]:
    manifest_path = project_root / 'build' / 'manifest.json'
    try:
        return json.loads(manifest_path.read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f'Release manifest not found: {manifest_path}') from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f'Release manifest is not valid JSON: {manifest_path}') from exc


def _dimensions(manifest: dict[str, Any]) -> dict[str, Any]:
    """Read released stack dimensions from the manifest audit."""

    audit = manifest.get('assembly_audit')
    if not isinstance(audit, dict):
        raise ValueError("Release manifest has no 'assembly_audit' mapping")
    required = ('aerodynamic_height_mm', 'shaft_z_bounds_mm', 'upper_generator_air_gap_mm')
    missing = [field for field in required if field not in audit]
    if missing:
        raise ValueError(f"Release manifest audit missing: {', '.join(missing)}")
    shaft_bounds = audit['shaft_z_bounds_mm']
    if not isinstance(shaft_bounds, list) or len(shaft_bounds) != 2:
        raise ValueError("Release manifest audit 'shaft_z_bounds_mm' must have two values")
    stage_z = audit.get('nominal_stage_z_mm', [])
    loaded_pitch = round(stage_z[1] - stage_z[0], 2) if len(stage_z) >= 2 else None
    result: dict[str, Any] = {
        'loaded_height_mm': round(audit['aerodynamic_height_mm'], 2),
        'rod_length_mm': round(shaft_bounds[1] - shaft_bounds[0], 2),
        'air_gap_mm': audit['upper_generator_air_gap_mm'],
        'upper_air_gap_mm': audit['upper_generator_air_gap_mm'],
        'lower_air_gap_mm': audit.get('lower_generator_air_gap_mm'),
        'loaded_stage_pitch_mm': loaded_pitch,
        'stage_count': audit.get('stage_count'),
        'standard_stage_count': audit.get('standard_count'),
        'base_count': audit.get('base_count'),
        'top_count': audit.get('top_count'),
        'source': 'build/manifest.json:assembly_audit',
    }
    # Keep descriptive aliases for downstream builders without introducing a
    # second source of values.
    result['aerodynamic_height_mm'] = result['loaded_height_mm']
    result['rod_envelope_mm'] = result['rod_length_mm']
    result['generator_air_gap_mm'] = result['air_gap_mm']
    return result


def load_manual_data(project_root: Path) -> dict[str, Any]:
    """Return the complete manual data model for ``project_root``.

    ``dimensions`` comes from the release audit.  Generator-specific
    provisional values come from :data:`DEFAULT_PARAMETERS`; they are clearly
    marked as provisional in the relevant BOM records and validation status.
    """

    manifest = _read_manifest(project_root)
    dimensions = _dimensions(manifest)
    p = DEFAULT_PARAMETERS
    dimensions.update({
        'rotor_diameter_mm': p.rotor.rotor_diameter_mm,
        'insertion_offset_deg': p.bayonet.insertion_offset_deg,
        'rotation_direction': p.rotor.rotation_direction,
        'magnet_count_total': 2 * p.generator.magnet_pocket_count,
        'magnet_pocket_count_per_rotor': p.generator.magnet_pocket_count,
        'magnet_pitch_radius_mm': p.generator.magnet_pitch_radius_mm,
        'magnet_pocket_diameter_mm': p.generator.magnet_pocket_diameter_mm,
        'magnet_pocket_depth_mm': p.generator.magnet_pocket_depth_mm,
        'coil_former_diameter_mm': p.generator.coil_former_diameter_mm,
        'coil_former_height_mm': p.generator.coil_former_height_mm,
        'coil_former_bore_mm': p.generator.coil_former_bore_diameter_mm,
    })

    validation = deepcopy(VALIDATION_STATUS)
    validation.update({
        'manifest_physical_fit': bool(manifest.get('physical_fit_verified', False)),
        'manifest_magnet_fit': bool(manifest.get('assembly_audit', {}).get('physical_magnet_fit_verified', False)),
        'manifest_bearing_fit': bool(manifest.get('assembly_audit', {}).get('physical_bearing_fit_verified', False)),
        'manifest_outdoor_operation': bool(manifest.get('outdoor_operation_validated', False)),
    })
    return {
        'dimensions': dimensions,
        'printed_parts': deepcopy(PRINTED_PARTS),
        'hardware': deepcopy(HARDWARE),
        'drawings': deepcopy(DRAWINGS),
        'validation_status': validation,
    }
