"""Deterministic release exports from analytic builders, with geometry gates.

STEP preserves assembly frames; STL translates each candidate to print Z=0.
Only five unique bodies are production candidates. Coupons are separate, and
stationary generator/hardware envelopes remain explicitly named in assemblies.
The manifest certifies CAD checks only, never print fit, strength or operation.
"""

from dataclasses import asdict, dataclass
from hashlib import sha256
from importlib.metadata import version
import json
from math import isfinite
from pathlib import Path
from platform import python_version
import re

import cadquery as cq

from windwall.assembly import RotorAssembly, build_exploded_rotor_assembly, build_locked_rotor_assembly
from windwall.assembly_validation import audit_rotor_assembly, require_valid_assembly_audit
from windwall.bayonet import build_bayonet_coupon
from windwall.drivers import build_joint_coupon
from windwall.generator import build_magnet_pocket_coupon
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters
from windwall.reference_mesh import MeshReport, analyze_binary_stl


@dataclass(frozen=True)
class PartExport:
    name: str
    quantity: int
    step_path: Path
    stl_path: Path
    step_sha256: str
    stl_sha256: str
    cad_volume_mm3: float
    cad_bounds: dict
    mesh: MeshReport

    @property
    def boundary_edge_count(self) -> int:
        return self.mesh.boundary_edge_count

    @property
    def nonmanifold_edge_count(self) -> int:
        return self.mesh.nonmanifold_edge_count

    @property
    def degenerate_face_count(self) -> int:
        return self.mesh.degenerate_face_count

    def as_dict(self, root: Path) -> dict:
        return {
            'name': self.name, 'quantity': self.quantity,
            'step_path': self.step_path.relative_to(root).as_posix(),
            'stl_path': self.stl_path.relative_to(root).as_posix(),
            'step_sha256': self.step_sha256, 'stl_sha256': self.stl_sha256,
            'cad_volume_mm3': self.cad_volume_mm3, 'cad_bounds_mm': self.cad_bounds,
            'cad_valid': True, 'cad_solid_count': 1, 'step_round_trip_valid': True,
            'expected_component_count': 1, 'mesh': self.mesh.as_dict(),
            'stl_translation_z_mm': -self.cad_bounds['minimum_xyz'][2],
        }


@dataclass(frozen=True)
class ExportManifest:
    production_parts: tuple[PartExport, ...]
    coupons: tuple[PartExport, ...]
    assemblies: tuple[dict, ...]
    path: Path

    def part_names(self) -> set[str]:
        return {part.name for part in self.production_parts}


def _bounds(shape: cq.Shape) -> dict:
    box = shape.BoundingBox()
    return {'minimum_xyz': [box.xmin, box.ymin, box.zmin],
            'maximum_xyz': [box.xmax, box.ymax, box.zmax],
            'size_xyz': [box.xlen, box.ylen, box.zlen]}


def _valid_solid(shape: cq.Shape, name: str) -> None:
    if (not shape.isValid() or len(shape.Solids()) != 1
            or not isfinite(shape.Volume()) or shape.Volume() <= 0):
        raise ValueError(f'{name} must be one valid solid with positive finite volume')


def _volume_mm3(shape: cq.Shape) -> float:
    # OCCT's default quadrature changes with STEP surface representation.
    # Explicit adaptive integration gives consistent pre/post-export volumes.
    return shape.Volume(1e-6)


def _validate_tolerances(parameters: DesignParameters) -> None:
    m = parameters.manufacturing
    for value in (m.export_linear_tolerance_mm, m.export_angular_tolerance_rad):
        if not isfinite(value) or value <= 0:
            raise ValueError('Export linear and angular tolerances must be positive and finite')


def validate_mesh(path: Path, expected_components: int = 1) -> MeshReport:
    """Reject actual malformed, open, nonmanifold, degenerate or empty meshes."""
    mesh = analyze_binary_stl(path)
    if (mesh.boundary_edge_count or mesh.nonmanifold_edge_count
            or mesh.degenerate_face_count or mesh.triangle_count == 0):
        raise ValueError(f'{path.name} failed STL topology validation: {mesh.as_dict()}')
    if mesh.component_count != expected_components:
        raise ValueError(f'{path.name} has {mesh.component_count} components; expected {expected_components}')
    if (not isfinite(mesh.signed_volume) or mesh.signed_volume <= 0
            or not all(isfinite(value) for value in (*mesh.minimum_xyz, *mesh.maximum_xyz))):
        raise ValueError(f'{path.name} must have finite bounds and positive signed volume')
    return mesh


def _canonicalize_step_header(path: Path) -> None:
    # Named assemblies avoid OCCT's process-global unnamed-product counter.
    # Normalize the timestamp and occurrence IDs, never geometry or entity refs.
    content = path.read_text(encoding='utf-8')
    content, count = re.subn(
        r"(FILE_NAME\('[^']*',)'[^']*'",
        r"\1'1970-01-01T00:00:00'", content, count=1,
    )
    if count != 1:
        raise ValueError(f'{path.name} is missing the expected STEP FILE_NAME header')
    occurrence_ids = iter(range(1, content.count('NEXT_ASSEMBLY_USAGE_OCCURRENCE') + 1))
    content = re.sub(r"(NEXT_ASSEMBLY_USAGE_OCCURRENCE\()'\d+'",
                     lambda match: f"{match[1]}'{next(occurrence_ids)}'", content)
    # Counter digit widths also change OCCT's wrapping before normalization.
    # Join only occurrence-record continuation lines; preserve every token.
    content = re.sub(r'NEXT_ASSEMBLY_USAGE_OCCURRENCE\([\s\S]*?\);',
                     lambda match: re.sub(r'\n[ \t]*', '', match[0]), content)
    path.write_text(content, encoding='utf-8', newline='\n')


def _file_hash(path: Path) -> str:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f'Missing or empty export: {path}')
    return sha256(path.read_bytes()).hexdigest()


def _export_step(assembly: cq.Assembly, path: Path, expected_count: int,
                 volume: float) -> str:
    assembly.export(str(path))
    _canonicalize_step_header(path)
    imported = cq.importers.importStep(str(path)).val()
    if (not imported.isValid() or len(imported.Solids()) != expected_count
            or any(not solid.isValid() for solid in imported.Solids())
            # Apply the same 0.01 mm3 round-trip budget to each solid; seven
            # STEP-healed blade surfaces accumulate about 0.022 mm3 in a stack.
            or abs(_volume_mm3(imported) - volume) > max(0.01 * expected_count, volume * 1e-8)):
        raise ValueError(f'{path.name} STEP round trip changed valid solids or volume')
    return _file_hash(path)


def export_part(name: str, shape: cq.Workplane, destination: Path,
                parameters: DesignParameters = DEFAULT_PARAMETERS, *,
                coupon: bool = False, quantity: int = 1) -> PartExport:
    """Validate and export one candidate; return paths and independently measured mesh."""
    _validate_tolerances(parameters)
    solid = shape.val()
    _valid_solid(solid, name)
    bounds = _bounds(solid)
    step_dir, stl_dir = destination / 'step', destination / ('coupons' if coupon else 'stl')
    step_dir.mkdir(parents=True, exist_ok=True)
    stl_dir.mkdir(parents=True, exist_ok=True)
    step_path, stl_path = step_dir / f'{name}.step', stl_dir / f'{name}.stl'
    assembly = cq.Assembly(name=name).add(shape, name=f'{name}_body')
    volume = _volume_mm3(solid)
    step_hash = _export_step(assembly, step_path, 1, volume)
    printable = shape.translate((0, 0, -bounds['minimum_xyz'][2]))
    m = parameters.manufacturing
    cq.exporters.export(printable, str(stl_path), tolerance=m.export_linear_tolerance_mm,
                        angularTolerance=m.export_angular_tolerance_rad)
    mesh = validate_mesh(stl_path)
    if (abs(mesh.signed_volume - volume) > max(0.05, volume * 0.005)
            or max(abs(a - b) for a, b in zip(mesh.size_xyz, bounds['size_xyz']))
            > 2 * m.export_linear_tolerance_mm
            or abs(mesh.minimum_xyz[2]) > 1e-5):
        raise ValueError(f'{name} STL changed CAD envelope, volume or print origin')
    return PartExport(name, quantity, step_path, stl_path, step_hash, _file_hash(stl_path),
                      volume, bounds, mesh)


def _export_assembly(model: RotorAssembly, destination: Path, parameters: DesignParameters) -> dict:
    if len(model.parts) != 34:
        raise ValueError('Complete rotor STEP must contain exactly 34 component solids')
    name = 'rotor_exploded' if model.exploded else 'rotor_locked'
    path = destination / 'assembly' / f'{name}.step'
    path.parent.mkdir(parents=True, exist_ok=True)
    # OCCT serializes color presentation records in pointer-dependent order.
    # Keep release geometry/names deterministic; previews supply visual colors.
    assembly = cq.Assembly(name=name)
    components = []
    production_names = {stage.name for stage in model.stages} | {'top_closure', 'lower_magnet_rotor'}
    m = parameters.manufacturing
    for component_name, workplane in model.parts.items():
        assembly.add(workplane, name=component_name)
        solid = workplane.val()
        _valid_solid(solid, component_name)
        _, triangles = solid.tessellate(m.export_linear_tolerance_mm, m.export_angular_tolerance_rad)
        components.append({'name': component_name, 'cad_valid': True, 'cad_solid_count': 1,
                           'role': 'production_candidate' if component_name in production_names else 'reference_envelope',
                           'cad_bounds_mm': _bounds(solid), 'cad_volume_mm3': _volume_mm3(solid),
                           'triangle_count': len(triangles)})
    volume = sum(component['cad_volume_mm3'] for component in components)
    step_hash = _export_step(assembly, path, len(components), volume)
    compound = cq.Compound.makeCompound([part.val() for part in model.parts.values()])
    return {'name': name, 'step_path': path.relative_to(destination).as_posix(),
            'step_sha256': step_hash, 'cad_bounds_mm': _bounds(compound),
            'summed_component_volume_mm3': volume,
            'triangle_count': sum(component['triangle_count'] for component in components),
            'component_count': len(components), 'expected_component_count': 34,
            'step_round_trip_valid': True, 'components': components,
            'stages': [asdict(stage) for stage in model.stages]}


def export_all(destination: Path, parameters: DesignParameters = DEFAULT_PARAMETERS) -> ExportManifest:
    """Build every candidate, audit the assembly and publish a manifest only on success.

    Fixed paths are overwritten on rebuild; unrelated files are never removed.
    A failed rebuild removes its previous manifest so partial files cannot be
    mistaken for a current validated release. No physical process is initiated.
    """
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / 'manifest.json'
    manifest_path.unlink(missing_ok=True)
    _validate_tolerances(parameters)
    coupons = [export_part('magnet_pocket_coupon', build_magnet_pocket_coupon(parameters),
                           destination, parameters, coupon=True)]
    for prefix, builder in (('bayonet', build_bayonet_coupon), ('joint', build_joint_coupon)):
        pair = builder(parameters)
        for member in ('male', 'female'):
            coupons.append(export_part(f'{prefix}_{member}', getattr(pair, member),
                                       destination, parameters, coupon=True))
    locked = build_locked_rotor_assembly(parameters)
    audit = audit_rotor_assembly(locked)
    require_valid_assembly_audit(audit)
    production = [export_part(f'{kind}_rotor_module', locked.local_modules[kind],
                             destination, parameters, quantity=5 if kind == 'standard' else 1)
                  for kind in ('base', 'standard', 'top')]
    production.extend((
        export_part('top_closure', locked.parts['top_closure'].translate((0, 0, -locked.stages[-1].z_mm)),
                    destination, parameters),
        export_part('lower_magnet_rotor', locked.parts['lower_magnet_rotor'], destination, parameters),
    ))
    assemblies = tuple(_export_assembly(model, destination, parameters) for model in (
        locked, build_exploded_rotor_assembly(parameters, locked=locked)))
    data = {
        'schema_version': 1, 'units': 'mm', 'parameters': asdict(parameters),
        'runtime': {'python': python_version(), **{name: version(name) for name in
                    ('cadquery', 'cadquery-ocp', 'numpy', 'vtk', 'casadi', 'nlopt')}},
        'production_quantity': sum(part.quantity for part in production),
        'production_parts': [part.as_dict(destination) for part in production],
        'coupons': [part.as_dict(destination) for part in coupons],
        'assemblies': assemblies, 'assembly_audit': audit,
        'physical_fit_verified': False, 'print_ready': False,
        'outdoor_operation_validated': False, 'overspeed_validated': False,
        'storm_operation_validated': False, 'electrical_operation_validated': False,
        'determinism': 'Same parameters and pinned runtime; uncolored named STEP assemblies, normalized timestamp and occurrence counters. Geometry unchanged.',
        'runtime_exit_status': 'Reported by the caller after process termination; not certified by this manifest.',
    }
    pending = destination / 'manifest.pending.json'
    pending.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    pending.replace(manifest_path)
    return ExportManifest(tuple(production), tuple(coupons), assemblies, manifest_path)
