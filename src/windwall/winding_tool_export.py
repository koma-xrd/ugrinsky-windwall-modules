"""Isolated, deterministic winding-tool artifacts and fail-closed release manifest.

Consumes the assembly module's audited geometry and purchasing BOM. Shared
export primitives validate STEP round trips and closed STL meshes; this module
owns tooling inventory, placements and metadata independently of turbine V5.
Thin winding-axis parts rotate onto their flat face, then STL translates to
bed Z=0. Neither the CAD audit nor this manifest certifies physical manufacture.
"""

from dataclasses import asdict, dataclass
from importlib.metadata import version
import json
from pathlib import Path
from platform import python_version

import cadquery as cq

from windwall.export import (
    PartExport, _bounds, _export_step, _file_hash, _valid_solid,
    _validate_tolerances, _volume_mm3, export_part,
)
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters
from windwall.winding_head import tape_station_angles
from windwall.winding_tool_assembly import (
    WindingToolAssemblies, audit_winding_tool_assemblies,
    build_winding_tool_assemblies, winding_tool_bom,
)
from windwall.winding_tool_parameters import (
    DEFAULT_WINDING_TOOL_PARAMETERS, WindingToolParameters,
)


PROTOTYPE_LIMITS = (
    'Printed fits, strength, tape clearance and coil release require physical prototype tests.',
    'The 127 mm reference is a calculated starting setting; cassette fit and winding quality remain unverified.',
    'Powered operation is not approved: speed, torque limiting and guarding remain unvalidated.',
    'Wire tension, enamel protection, useful brake drag and electrical performance remain unvalidated.',
    'STL orientations place the lowest point at Z=0; supports and print process require review.',
)
_ASSEMBLY_SOURCE = 'windwall.winding_tool_assembly.build_winding_tool_assemblies'
_GUIDE_SOURCE = Path(__file__).resolve().parents[2] / 'docs/serpentine-coil-winding-tool-de.md'


@dataclass(frozen=True)
class WindingToolManifest:
    printable_parts: tuple[PartExport, ...]
    assemblies: tuple[dict, ...]
    path: Path


def _print_inventory(model: WindingToolAssemblies) -> tuple[dict, ...]:
    """Explicit service masters; verify congruence before collapsing copies.

    Sliders/ribs repeat around X; the two uprights repeat by 180 degrees about
    Z. Comparing transformed solids prevents changed copies being omitted.
    The audited assembly dictionaries are the authoritative exported geometry.
    """
    rows = []
    groups = (
        ('winding_head', 'winding_jig', 'windwall.winding_head.build_winding_head',
         (('backplate', ('backplate',)), ('cam', ('cam',)), ('clamp', ('clamp',)),
          ('slider', tuple(f'slider_{i}' for i in range(1, 7))),
          ('rib', tuple(f'rib_{i}' for i in range(1, 7))))),
        ('winding_frame', 'winding_jig', 'windwall.winding_frame.build_winding_frame',
         (('base', ('base',)), ('upright', ('left_upright', 'right_upright')),
          ('head_hub', ('head_hub',)), ('head_retaining_collar', ('head_retaining_collar',)),
          ('crank', ('crank',)))),
        ('wire_payoff', 'wire_payoff', 'windwall.wire_payoff.build_wire_payoff',
         tuple((name, (name,)) for name in ('base', 'platter', 'adjuster'))),
    )
    covered = set()
    for prefix, tool, source, masters in groups:
        parts = getattr(model, tool)
        for master, members in masters:
            representative = parts[members[0]]
            for index, member in enumerate(members):
                path = f'{tool}/{member}'
                covered.add(path)
                _valid_solid(parts[member].val(), path)
                if index:
                    axis = (0, 0, 1) if master == 'upright' else (1, 0, 0)
                    angle = 180 if master == 'upright' else -index * 60
                    aligned = parts[member].rotate((0, 0, 0), axis, angle)
                    offset = representative.val().Center() - aligned.val().Center()
                    aligned = aligned.translate(offset.toTuple())
                    difference = (representative.cut(aligned).val().Volume()
                                  + aligned.cut(representative).val().Volume())
                    if difference > 1e-4:
                        raise ValueError(f'{path} differs from its unique print master')
            # Flat faces on winding-axis parts avoid a curved tessellated
            # extremum floating above the bed and provide a broad contact face.
            rotation = -90 if (prefix == 'winding_head' or master in
                               ('crank', 'head_hub', 'head_retaining_collar')) else 0
            printable = representative.rotate((0, 0, 0), (0, 1, 0), rotation) if rotation else representative
            rows.append({'name': f'{prefix}_{master}', 'tool': tool,
                         'members': members, 'shape': printable,
                         'print_rotation_y_deg': rotation,
                         'source_builder': source, 'quantity': len(members)})
    if covered != set(model.printable_parts):
        raise ValueError('Tooling print inventory does not cover the audited printable parts')
    return tuple(sorted(rows, key=lambda row: row['name']))


def _exploded_jig(model: WindingToolAssemblies) -> tuple[dict, dict]:
    """Separate service groups along the winding axis and ribs radially.

    Hardware remains with its parent group. These presentation translations
    are recorded explicitly and do not describe an operating configuration.
    """
    parts, translations = {}, {}
    shaft_box = model.winding_jig['shaft'].val().BoundingBox()
    axis_height = (shaft_box.zmin + shaft_box.zmax) / 2
    for name, body in sorted(model.winding_jig.items()):
        dx, dy, dz = 0.0, 0.0, 0.0
        if name.startswith(('rib_', 'slider_', 'cam_follower', 'guide_stop_')):
            dx = -180.0
            centre = body.val().Center()
            dy, dz = centre.y * 0.8, (centre.z - axis_height) * 0.8
        elif name in ('cam', 'clamp', 'backplate'):
            dx = {'backplate': -80.0, 'cam': -290.0, 'clamp': -335.0}[name]
        elif name.startswith(('crank', 'grip_')):
            dx = 90.0
        elif name.startswith('bearing_608_'):
            dz = 100.0
        elif name in ('left_upright', 'right_upright') or name.startswith('upright_fastener_'):
            dz = 45.0
        translations[name] = [dx, dy, dz]
        parts[name] = body.translate((dx, dy, dz))
    return parts, translations


def _export_tool_assembly(name, parts, destination, ownership, inventory):
    """Keep every group named with tooling-specific print and bearing ownership."""
    assembly = cq.Assembly(name=name)
    by_member = {member: row for row in inventory for member in row['members']}
    components = []
    for member, body in sorted(parts.items()):
        solid = body.val()
        _valid_solid(solid, member)
        assembly.add(body, name=member)
        master = by_member.get(member)
        motion = next(group for group in ('rotating', 'stationary', 'bearing_internal')
                      if member in ownership[group])
        component = {
            'name': member, 'quantity': 1, 'cad_solid_count': 1,
            'cad_valid': True, 'cad_bounds_mm': _bounds(solid),
            'cad_volume_mm3': _volume_mm3(solid), 'motion': motion,
            'printable': master is not None, 'hardware_reference': member in ownership['hardware_reference'],
            'adjustable': member in ownership['adjustable'],
            'source_builder': master['source_builder'] if master else _ASSEMBLY_SOURCE,
            'physical_fit_verified': False,
        }
        if master:
            component['print_part'] = master['name']
        components.append(component)
    path = destination / 'assembly' / f'{name}.step'
    path.parent.mkdir(parents=True, exist_ok=True)
    volume = sum(row['cad_volume_mm3'] for row in components)
    digest = _export_step(assembly, path, len(components), volume)
    bounds = _bounds(cq.Compound.makeCompound([body.val() for _, body in sorted(parts.items())]))
    return {'name': name, 'step_path': path.relative_to(destination).as_posix(),
            'step_sha256': digest, 'components': components,
            'component_count': len(components), 'cad_solid_count': len(components),
            'cad_bounds_mm': bounds, 'summed_component_volume_mm3': volume,
            'source_builder': _ASSEMBLY_SOURCE, 'step_round_trip_valid': True,
            'topology_result': {'cad_valid': True, 'cad_solid_count': len(components),
                                'step_round_trip_valid': True, 'stl_required': False},
            'printable': False, 'physical_fit_verified': False,
            'known_limitations': list(PROTOTYPE_LIMITS)}


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n',
                    encoding='utf-8', newline='\n')


def _export_supporting_artifacts(model, exploded, destination, bom):
    """Bind workshop instructions and CAD drawings to this exact release BOM.

    The source guide is complete for the default model. Marked numeric tables
    are regenerated for custom exports without changing source documentation.
    Missing source sections or any render/copy error prevents publication.
    """
    from scripts.preview_winding_tool import render_winding_tool_drawings

    p = model.parameters
    config = [
        ('Wickeldurchmesser min. / Referenz / max.',
         f'Ø{p.minimum_diameter_mm:g} / Ø{p.reference_diameter_mm:g} / Ø{p.maximum_diameter_mm:g} mm'),
        ('Rippen / Bandstellen / Winkelraster', f'{p.rib_count} / {p.tape_station_count} / {360/p.tape_station_count:g}°'),
        ('Bandbreite / freie Passage', f'{p.tape_width_mm:g} / {p.tape_passage_width_mm:g} mm'),
        ('Radialer Freigabeweg', f'{p.release_travel_mm:g} mm'),
        ('Teller / Spulendorn', f'Ø{p.platter_diameter_mm:g} / Ø{p.spool_pilot_diameter_mm:g} × {p.spool_pilot_height_mm:g} mm'),
        ('Welle / Sechskant-Schlüsselweite', f'Ø{p.shaft_diameter_mm:g} / {p.hex_socket_across_flats_mm:g} mm'),
        ('Maximales Druckbett', f'{p.print_bed_size_mm:g} × {p.print_bed_size_mm:g} mm'),
    ]
    sections = {
        'configuration': '| Merkmal | CAD-Konfiguration dieses Releases |\n| --- | --- |\n' +
                         '\n'.join(f'| {key} | {value} |' for key, value in config),
        'print-bom': '| Menge | Druckteil / STL-Stamm | Modul |\n| --- | --- | --- |\n' +
                     '\n'.join(f"| {row['quantity']} | `{row['item']}` | {row['tool']} |"
                               for row in bom['printable_parts']),
        'hardware-bom': '| Menge | Stücklisten-ID | Nennauswahl (CAD) |\n| --- | --- | --- |\n' +
                        '\n'.join(f"| {row['quantity']} | `{row['item']}` | {row['specification']} |"
                                  for row in bom['hardware']),
    }
    guide = _GUIDE_SOURCE.read_text(encoding='utf-8')
    for name, table in sections.items():
        start, end = f'<!-- BEGIN {name} -->', f'<!-- END {name} -->'
        if guide.count(start) != 1 or guide.count(end) != 1:
            raise ValueError(f'Guide requires exactly one {name} section')
        before, remaining = guide.split(start)
        _, after = remaining.split(end)
        guide = before + start + '\n' + table + '\n' + end + after
    guide_path = destination / 'docs' / _GUIDE_SOURCE.name
    guide_path.parent.mkdir(parents=True, exist_ok=True)
    guide_path.write_text(guide, encoding='utf-8', newline='\n')
    artifacts = list(render_winding_tool_drawings(model, exploded, destination / 'drawings'))
    artifacts.append({'path': guide_path.relative_to(destination).as_posix(),
                      'source': 'docs/' + _GUIDE_SOURCE.name,
                      'language': 'de-DE', 'bom_tables_regenerated': True})
    for artifact in artifacts:
        artifact['sha256'] = _file_hash(destination / artifact['path'])
    return sorted(artifacts, key=lambda row: row['path'])


def export_winding_tool(
        destination: Path,
        tool_parameters: WindingToolParameters = DEFAULT_WINDING_TOOL_PARAMETERS,
        design_parameters: DesignParameters = DEFAULT_PARAMETERS,
) -> WindingToolManifest:
    """Rebuild at the reference setting; publish success only after all gates.

    Removes the prior success manifest before any validation. Partial artifacts
    can remain after failure but are never accompanied by a success manifest.
    Paths are relative to the output directory, independent of its location.
    """
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / 'manifest.json'
    path.unlink(missing_ok=True)
    _validate_tolerances(design_parameters)
    model = build_winding_tool_assemblies(tool_parameters, design_parameters)
    audit = audit_winding_tool_assemblies(model)
    if not audit['valid']:
        raise ValueError(f"Winding-tool export audit failed: {audit['checks']}")
    inventory = _print_inventory(model)
    prints = tuple(export_part(row['name'], row['shape'], destination, design_parameters,
                               quantity=row['quantity'], role='tooling',
                               source_builder=row['source_builder']) for row in inventory)
    records = []
    for part, row in zip(prints, inventory):
        record = part.as_dict(destination)
        record.update(known_limitations=list(PROTOTYPE_LIMITS), tool=row['tool'],
                      assembly_members=list(row['members']),
                      print_rotation_y_deg=row['print_rotation_y_deg'])
        records.append(record)
    assemblies = []
    for tool in ('winding_jig', 'wire_payoff'):
        assemblies.append(_export_tool_assembly(
            tool, getattr(model, tool), destination, model.ownership[tool],
            [row for row in inventory if row['tool'] == tool]))
    exploded, translations = _exploded_jig(model)
    exploded_record = _export_tool_assembly(
        'winding_jig_exploded', exploded, destination, model.ownership['winding_jig'],
        [row for row in inventory if row['tool'] == 'winding_jig'])
    exploded_record.update(presentation_only=True, component_translations_mm=translations)
    assemblies.append(exploded_record)
    assemblies.sort(key=lambda row: row['name'])
    hardware = sorted(winding_tool_bom(model), key=lambda row: row['item'])
    bom = {'printable_parts': [
        {'item': row['name'], 'quantity': row['quantity'], 'tool': row['tool'],
         'source_builder': row['source_builder'], 'physical_fit_verified': False}
        for row in inventory], 'hardware': hardware}
    bom_path = destination / 'bom.json'
    _write_json(bom_path, bom)
    supporting_artifacts = _export_supporting_artifacts(model, exploded, destination, bom)
    data = {
        'schema_version': 1, 'release': 'winding-tool', 'units': 'mm',
        'parameters': asdict(tool_parameters),
        'manufacturing_parameters': asdict(design_parameters.manufacturing),
        'bearing_parameters': asdict(design_parameters.bearings),
        'shaft_parameters': asdict(design_parameters.shaft),
        'runtime': {'python': python_version(), 'cadquery': version('cadquery'),
                    'cadquery-ocp': version('cadquery-ocp'), 'matplotlib': version('matplotlib')},
        'reference_diameter_mm': tool_parameters.reference_diameter_mm,
        'diameter_range_mm': [tool_parameters.minimum_diameter_mm, tool_parameters.maximum_diameter_mm],
        'reference_setting_status': 'Calculated starting setting; physical calibration required.',
        'tape_layout': {'station_angles_deg': list(tape_station_angles(tool_parameters)),
                        'tape_width_mm': tool_parameters.tape_width_mm,
                        'passage_width_mm': tool_parameters.tape_passage_width_mm},
        'printable_parts': records, 'printable_quantity': sum(part.quantity for part in prints),
        'assemblies': assemblies, 'assembly_audit': audit,
        'ownership': {tool: {group: sorted(members) for group, members in groups.items()}
                      for tool, groups in model.ownership.items()},
        'bom_path': 'bom.json', 'bom_sha256': _file_hash(bom_path),
        'supporting_artifacts': supporting_artifacts,
        'physical_fit_verified': False, 'powered_operation_validated': False,
        'print_ready': False, 'known_limitations': list(PROTOTYPE_LIMITS),
        'mechanically_synchronized': False, 'shared_base': False,
        'coordinate_frames': {'print_step': 'Representative assembly member rotated about global Y as recorded per part.',
                              'print_stl': 'STEP master translated vertically to bottom Z=0.',
                              'assembly_step': 'Separate tool origins; winding axis X, payoff axis Z.',
                              'exploded_step': 'Presentation translations recorded per component.'},
        'manifest_path_base': 'output directory',
        'determinism': 'Same parameters and pinned runtime; sorted named assemblies, canonical STEP headers, absolute serial STL meshing.',
    }
    pending = destination / 'manifest.pending.json'
    _write_json(pending, data)
    pending.replace(path)
    return WindingToolManifest(prints, tuple(assemblies), path)
