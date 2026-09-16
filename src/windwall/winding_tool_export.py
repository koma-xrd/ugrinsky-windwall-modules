"""Deterministic core release publisher for the two manual winding tools.

Task 5 occurrence ownership is the only print-inventory and BOM authority. This
module orients one representative of each audited printed master, exports the
two independent assemblies, and publishes a success manifest only after every
CAD, mesh, STEP, hash, BOM, audit, drawing and guide gate passes. Supporting
drawings consume current CAD occurrences; the guide tables consume the same BOM.
"""

from collections import Counter
from dataclasses import asdict, dataclass
from importlib.metadata import version
import json
from math import isfinite
from pathlib import Path, PurePosixPath
from platform import python_version

import cadquery as cq

from windwall.export import (
    PartExport, _bounds, _export_step, _file_hash, _valid_solid,
    _validate_tolerances, _volume_mm3, export_part,
)
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters
from windwall.winding_head import build_winding_head, tape_station_angles
from windwall.winding_tool_assembly import (
    WindingToolAssemblies, audit_winding_tool_assemblies,
    build_winding_tool_assemblies, winding_tool_bom,
)
from windwall.winding_tool_parameters import (
    DEFAULT_WINDING_TOOL_PARAMETERS, WindingToolParameters, diameter_settings_mm,
)
from windwall.winding_tool_service import local_shape


PROTOTYPE_LIMITS = (
    'Printed shaft strength and fatigue require physical prototype testing.',
    'PLA snap fit, retention, wear life and bearing fits require physical prototype testing.',
    'Actual winding diameter, repeatability and enamel protection remain unvalidated.',
    'Payoff stability and manual stopping remain unvalidated.',
    'Coil-release force and suitability for continuous or production use remain unvalidated.',
    'Hand-crank operation only; powered operation is not approved.',
)
_ASSEMBLY_SOURCE = 'windwall.winding_tool_assembly.build_winding_tool_assemblies'
_ASSEMBLY_NAMES = {
    'winding_jig': 'simplified_winding_jig',
    'wire_payoff': 'free_running_wire_payoff',
}
_PUBLISHER_MANIFEST_NAMES = frozenset(('manifest.json', 'manifest.pending.json'))
# The Task 5 shaft orientation puts its axis parallel to the bed. This equivalent
# Euler representation adds a 30 degree phase around that axis so an actual
# planar drive face, rather than an inward-tessellated cylinder tangent, defines
# the bed datum. It rotates the unchanged solid; no facet or mesh is rewritten.
_RELEASE_ROTATION_OVERRIDES = {
    'winding_jig/printed_shaft': (90, -30, 0),
}
_FORBIDDEN_BOM_TERMS = (
    'cam', 'slider', 'follower', 'rib', 'clamp', 'upright', 'brake', 'felt',
    'spring', 'adjuster', 'fastener', 'bolt', 'screw', 'threaded', 'metal shaft',
)


@dataclass(frozen=True)
class WindingToolManifest:
    printable_parts: tuple[PartExport, ...]
    assemblies: tuple[dict, ...]
    path: Path
    data: dict


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n',
                    encoding='utf-8', newline='\n')


def _oriented_print_shape(model: WindingToolAssemblies, tool: str, member: str,
                          rotations: tuple[float, float, float]):
    shape = getattr(model, tool)[member]
    if tool == 'winding_jig':
        try:
            height = model.ownership[tool]['wheel']['axis_height_mm']
        except KeyError as error:
            raise ValueError('Winding-jig ownership is missing the assembly datum') from error
        shape = local_shape(shape, height)
    bounds = shape.val().BoundingBox()
    shape = shape.translate((-(bounds.xmin + bounds.xmax) / 2,
                             -(bounds.ymin + bounds.ymax) / 2,
                             -(bounds.zmin + bounds.zmax) / 2))
    for axis, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), rotations):
        shape = shape.rotate((0, 0, 0), axis, angle)
    return shape


def _validated_bom(model: WindingToolAssemblies, bom_rows) -> tuple[dict, ...]:
    """Require the canonical Task 5 rows and exact occurrence-derived quantities."""
    rows = tuple(dict(row) for row in bom_rows)
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError('BOM must contain canonical Task 5 rows')
    expected = Counter(
        f'{tool}/{owner["master"]}'
        for tool, records in model.ownership.items()
        for owner in records.values()
        if owner.get('source') == 'printed'
    )
    printed = {}
    purchased = {}
    for row in rows:
        source = row.get('source')
        if source == 'printed':
            master = row.get('master')
            if master in printed or not isinstance(master, str):
                raise ValueError('BOM contains a duplicate or unnamed printed master')
            if row.get('material') != 'PLA':
                raise ValueError(f'BOM printed master {master} must use PLA')
            printed[master] = row.get('quantity')
        elif source == 'purchased':
            name = row.get('name')
            if name in purchased or not isinstance(name, str):
                raise ValueError('BOM contains a duplicate or unnamed purchase')
            purchased[name] = row.get('quantity')
        else:
            raise ValueError('BOM rows must identify printed or purchased source')
    if printed != dict(sorted(expected.items())):
        raise ValueError('BOM printed-master quantity does not match occurrence ownership')
    if purchased != {'608 bearing': 2, '51105 thrust bearing': 1}:
        raise ValueError('BOM purchases must be exactly two 608 and one 51105 assembly')
    searchable = json.dumps(rows, sort_keys=True).lower()
    stale = [term for term in _FORBIDDEN_BOM_TERMS if term in searchable]
    if stale:
        raise ValueError(f'BOM contains superseded mechanics: {", ".join(stale)}')
    return rows


def _print_inventory(model: WindingToolAssemblies, bom_rows=None) -> tuple[dict, ...]:
    """Collapse audited occurrences solely by their tool-qualified master identity."""
    if bom_rows is None:
        bom_rows = winding_tool_bom(model)
    rows = _validated_bom(model, bom_rows)
    bom_quantities = {row['master']: row['quantity'] for row in rows
                      if row['source'] == 'printed'}
    inventory = []
    for tool in sorted(_ASSEMBLY_NAMES):
        try:
            parts = getattr(model, tool)
            owners = model.ownership[tool]
        except (AttributeError, KeyError) as error:
            raise ValueError(f'Missing {tool} occurrence ownership') from error
        if set(parts) != set(owners):
            raise ValueError(f'{tool} occurrences and ownership do not match')
        grouped = {}
        for member, owner in owners.items():
            if owner.get('source') == 'printed':
                master = owner.get('master')
                if not isinstance(master, str) or not master:
                    raise ValueError(f'{tool}/{member} has no printed master identity')
                grouped.setdefault(f'{tool}/{master}', []).append(member)
            elif owner.get('source') != 'purchased':
                raise ValueError(f'{tool}/{member} has an invalid ownership source')
        for master, members in sorted(grouped.items()):
            records = [owners[member] for member in members]
            rotations = {tuple(record.get('print_rotations_deg', ())) for record in records}
            groups = {record.get('group') for record in records}
            if len(rotations) != 1 or len(next(iter(rotations))) != 3:
                raise ValueError(f'{master} lacks one documented print orientation')
            if len(groups) != 1 or None in groups:
                raise ValueError(f'{master} occurrences disagree on their role')
            ownership_rotation = next(iter(rotations))
            if any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not isfinite(value) for value in ownership_rotation):
                raise ValueError(f'{master} print rotation must be finite numeric degrees')
            rotation = _RELEASE_ROTATION_OVERRIDES.get(master, ownership_rotation)
            quantity = len(members)
            if bom_quantities.get(master) != quantity:
                raise ValueError(f'{master} quantity does not match the canonical BOM')
            representative = sorted(members)[0]
            shape = _oriented_print_shape(model, tool, representative, rotation)
            _valid_solid(shape.val(), master)
            size = _bounds(shape.val())['size_xyz']
            footprint = [size[0], size[1]]
            limit = min(model.parameters.print_bed_mm, 220.0)
            if max(footprint) > limit + 1e-6:
                raise ValueError(f'{master} exceeds the documented {limit:g} mm print bed')
            inventory.append({
                'name': master.replace('/', '_'),
                'master': master,
                'tool': tool,
                'members': tuple(sorted(members)),
                'quantity': quantity,
                'shape': shape,
                'role': next(iter(groups)),
                'source_builder': _ASSEMBLY_SOURCE,
                'ownership_print_rotations_deg': ownership_rotation,
                'print_rotations_deg': rotation,
                'print_bed_footprint_mm': footprint,
            })
    if {row['master'] for row in inventory} != set(bom_quantities):
        raise ValueError('Print inventory does not cover every canonical BOM master')
    return tuple(inventory)


def _export_tool_assembly(release_name: str, tool: str, model: WindingToolAssemblies,
                          destination: Path, inventory: tuple[dict, ...]) -> dict:
    parts = getattr(model, tool)
    owners = model.ownership[tool]
    by_member = {member: row for row in inventory if row['tool'] == tool
                 for member in row['members']}
    assembly = cq.Assembly(name=release_name)
    components = []
    for member, body in sorted(parts.items()):
        solid = body.val()
        _valid_solid(solid, f'{tool}/{member}')
        assembly.add(body, name=member)
        bounds = _bounds(solid)
        center = solid.Center()
        component = {
            'name': member,
            'quantity': 1,
            'cad_valid': True,
            'cad_solid_count': 1,
            'cad_bounds_mm': bounds,
            'cad_center_mm': [center.x, center.y, center.z],
            'placement': 'prepositioned geometry in the assembly coordinate frame',
            'ownership': dict(owners[member]),
            'printable': member in by_member,
            'physical_validation_verified': False,
        }
        if member in by_member:
            component['print_part'] = by_member[member]['name']
        components.append(component)
    path = destination / 'assembly' / f'{release_name}.step'
    path.parent.mkdir(parents=True, exist_ok=True)
    volume = sum(_volume_mm3(body.val()) for body in parts.values())
    digest = _export_step(assembly, path, len(parts), volume)
    compound = cq.Compound.makeCompound([body.val() for _, body in sorted(parts.items())])
    return {
        'name': release_name,
        'tool': tool,
        'step_path': path.relative_to(destination).as_posix(),
        'step_sha256': digest,
        'components': components,
        'component_count': len(components),
        'cad_solid_count': len(components),
        'cad_bounds_mm': _bounds(compound),
        'summed_component_volume_mm3': volume,
        'source_builder': _ASSEMBLY_SOURCE,
        'step_round_trip_valid': True,
        'topology_result': {
            'cad_valid': True,
            'cad_solid_count': len(components),
            'step_round_trip_valid': True,
            'stl_required': False,
        },
        'physical_validation_verified': False,
        'known_limitations': list(PROTOTYPE_LIMITS),
    }


def _export_supporting_artifacts(model, destination, bom):
    """Publish current drawings and a BOM-synchronized German operating guide."""
    from scripts.preview_winding_tool import render_winding_tool_drawings, winding_tool_guide

    drawings = render_winding_tool_drawings(model, destination / 'drawings')
    guide_path = destination / 'docs' / 'serpentine-coil-winding-tool-de.md'
    guide_path.parent.mkdir(parents=True, exist_ok=True)
    guide_path.write_text(winding_tool_guide(model, bom), encoding='utf-8', newline='\n')
    return (*drawings, {'path': 'docs/serpentine-coil-winding-tool-de.md',
                        'source': 'docs/serpentine-coil-winding-tool-de.md',
                        'tables_synchronized_with': 'bom.json and current CAD tape angles'})


def _supporting_artifact_records(destination: Path, artifacts) -> list[dict]:
    if artifacts is None:
        raise ValueError('Supporting-artifact exporter must return an inventory')
    records = []
    release_root = destination.resolve()
    seen_aliases = set()
    seen_targets = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or not isinstance(artifact.get('path'), str):
            raise ValueError('Supporting artifacts require portable relative paths')
        raw_path = artifact['path']
        if ('\\' in raw_path or any(ord(character) < 32 for character in raw_path)):
            raise ValueError(f'Invalid supporting-artifact path: {raw_path!r}')
        relative = PurePosixPath(raw_path)
        if (relative.is_absolute() or '..' in relative.parts
                or str(relative) in ('', '.') or any(':' in part for part in relative.parts)):
            raise ValueError(f'Invalid supporting-artifact path: {raw_path!r}')
        alias_parts = tuple(part.rstrip(' .').casefold() for part in relative.parts)
        if len(alias_parts) == 1 and alias_parts[0] in _PUBLISHER_MANIFEST_NAMES:
            raise ValueError(f'Supporting artifact cannot replace publisher manifest: {raw_path!r}')
        if any(not alias or alias != part.casefold()
               for alias, part in zip(alias_parts, relative.parts)):
            raise ValueError(f'Invalid Windows-portable supporting-artifact path: {raw_path!r}')
        portable = relative.as_posix()
        target = (release_root / Path(*relative.parts)).resolve()
        try:
            target.relative_to(release_root)
        except ValueError as error:
            raise ValueError(f'Supporting-artifact path leaves the release: {raw_path!r}') from error
        for name in _PUBLISHER_MANIFEST_NAMES:
            publisher = release_root / name
            if target.exists() and publisher.exists() and target.samefile(publisher):
                raise ValueError(f'Supporting artifact aliases publisher manifest: {raw_path!r}')
        if alias_parts in seen_aliases or target in seen_targets:
            raise ValueError(f'Duplicate supporting-artifact path: {portable}')
        seen_aliases.add(alias_parts)
        seen_targets.add(target)
        digest = _file_hash(target)
        if artifact.get('sha256') not in (None, digest):
            raise ValueError(f'Supporting-artifact hash mismatch: {portable}')
        records.append({**artifact, 'path': portable, 'sha256': digest})
    return sorted(records, key=lambda row: row['path'])


def _verify_artifact_hashes(destination: Path, data: dict) -> None:
    expected = [(data['bom_path'], data['bom_sha256'])]
    for record in data['printable_parts']:
        expected.extend((record[f'{kind}_path'], record[f'{kind}_sha256'])
                        for kind in ('step', 'stl'))
    expected.extend((record['step_path'], record['step_sha256'])
                    for record in data['assemblies'])
    expected.extend((record['path'], record['sha256'])
                    for record in data['supporting_artifacts'])
    paths = [relative for relative, _ in expected]
    if len(paths) != len(set(paths)):
        raise ValueError('Release artifact inventory contains duplicate paths')
    for relative, digest in expected:
        if _file_hash(destination / relative) != digest:
            raise ValueError(f'Release artifact hash mismatch: {relative}')


def _wheel_settings(parameters: WindingToolParameters) -> list[dict]:
    rows = []
    for diameter in diameter_settings_mm(parameters):
        head = build_winding_head(parameters, diameter)
        rows.append({
            'nominal_diameter_mm': diameter,
            'actual_tape_angles_deg': list(head.metadata['actual_tape_angles_deg']),
        })
    return rows


def _publish_winding_tool(
        destination: Path,
        parameters: WindingToolParameters,
        design_parameters: DesignParameters,
        supporting_artifact_exporter,
        manifest_path: Path,
        pending_path: Path,
) -> WindingToolManifest:
    _validate_tolerances(design_parameters)
    model = build_winding_tool_assemblies(parameters, design_parameters)
    audit = audit_winding_tool_assemblies(model)
    if not audit or not all(isinstance(value, bool) and value for value in audit.values()):
        failed = [name for name, passed in audit.items() if passed is not True]
        raise ValueError(f'Winding-tool export audit failed: {failed or "empty audit"}')

    bom_rows = _validated_bom(model, winding_tool_bom(model))
    inventory = _print_inventory(model, bom_rows)
    prints = tuple(
        export_part(row['name'], row['shape'], destination, design_parameters,
                    quantity=row['quantity'], role=row['role'],
                    source_builder=row['source_builder'])
        for row in inventory
    )
    print_records = []
    for part, row in zip(prints, inventory):
        record = part.as_dict(destination)
        record.update({
            'master': row['master'],
            'material': 'PLA',
            'tool': row['tool'],
            'assembly_members': list(row['members']),
            'print_orientation': {
                'rotations_deg': list(row['print_rotations_deg']),
                'ownership_rotations_deg': list(row['ownership_print_rotations_deg']),
                'axis_order': ['X', 'Y', 'Z'],
                'bed_origin': 'STL minimum Z translated to 0 mm',
                'geometry_policy': ('Rigid orientation only; source CAD and STL facets are not '
                                    'altered by the winding-tool exporter.'),
            },
            'print_bed_footprint_mm': row['print_bed_footprint_mm'],
            'physical_validation_verified': False,
            'known_limitations': list(PROTOTYPE_LIMITS),
        })
        print_records.append(record)

    assemblies = tuple(sorted((
        _export_tool_assembly(release_name, tool, model, destination, inventory)
        for tool, release_name in _ASSEMBLY_NAMES.items()
    ), key=lambda row: row['name']))

    bom = _json_safe({'items': bom_rows})
    bom_path = destination / 'bom.json'
    _write_json(bom_path, bom)
    exporter = supporting_artifact_exporter or _export_supporting_artifacts
    support = _supporting_artifact_records(destination,
        exporter(model, destination, bom))

    nominal_angles = list(tape_station_angles(parameters))
    data = _json_safe({
        'schema_version': 2,
        'release': 'simple-pin-adjustable-coil-winder',
        'units': 'mm',
        'parameters': asdict(parameters),
        'manufacturing_parameters': asdict(design_parameters.manufacturing),
        'bearing_parameters': asdict(design_parameters.bearings),
        'runtime': {
            'python': python_version(),
            'cadquery': version('cadquery'),
            'cadquery-ocp': version('cadquery-ocp'),
        },
        'wheel_settings': _wheel_settings(parameters),
        'tape_angle_semantics': {
            'nominal_angles_deg': nominal_angles,
            'nominal_pitch_deg': 360 / parameters.tape_station_count,
            'nominal_use': 'sequence labels only',
            'actual_values': 'actual_tape_angles_deg are diameter-dependent physical passage centers',
        },
        'printable_parts': print_records,
        'printable_quantity': sum(part.quantity for part in prints),
        'assemblies': assemblies,
        'assembly_audit': audit,
        'ownership': model.ownership,
        'bom_path': bom_path.relative_to(destination).as_posix(),
        'bom_sha256': _file_hash(bom_path),
        'supporting_artifacts': support,
        'physical_validation_verified': False,
        'powered_operation': False,
        'print_ready': False,
        'known_limitations': list(PROTOTYPE_LIMITS),
        'coordinate_frames': {
            'print_step': ('Task 5 master geometry bounding-box-centered at the origin, then '
                           'given the recorded release X/Y/Z rotations; the shaft uses an '
                           'equivalent axis-parallel phase that places a planar face on the bed.'),
            'print_stl': 'The print STEP master translated vertically to minimum Z = 0 mm.',
            'assembly_step': 'Two independent origins; winding-jig axis Y (forward -Y) and payoff axis Z.',
        },
        'manifest_path_base': 'output directory',
        'determinism': ('Sorted ownership-derived inventory, sorted named assemblies, canonical STEP headers, '
                        'absolute serial STL meshing, and sorted JSON keys.'),
    })
    _verify_artifact_hashes(destination, data)
    _write_json(pending_path, data)
    pending_path.replace(manifest_path)
    return WindingToolManifest(prints, assemblies, manifest_path, data)


def export_winding_tool(
        destination: Path,
        parameters: WindingToolParameters = DEFAULT_WINDING_TOOL_PARAMETERS,
        design_parameters: DesignParameters = DEFAULT_PARAMETERS,
        *,
        supporting_artifact_exporter=None,
) -> WindingToolManifest:
    """Publish successfully or remove both publisher-owned manifest files."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / 'manifest.json'
    pending_path = destination / 'manifest.pending.json'
    manifest_path.unlink(missing_ok=True)
    pending_path.unlink(missing_ok=True)
    published = False
    try:
        result = _publish_winding_tool(
            destination, parameters, design_parameters, supporting_artifact_exporter,
            manifest_path, pending_path,
        )
        published = True
        return result
    finally:
        if not published:
            manifest_path.unlink(missing_ok=True)
            pending_path.unlink(missing_ok=True)
