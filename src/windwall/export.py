"""Deterministic release exports from analytic builders, with geometry gates.

STEP preserves assembly frames; STL translates each candidate to print Z=0.
Eight unique bodies are production candidates. Coupons are separate, and
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

from windwall.assembly import RotorAssembly, build_locked_rotor_assembly
from windwall.assembly_validation import audit_rotor_assembly, require_valid_assembly_audit
from windwall.bayonet import build_bayonet_coupon
from windwall.bearings import build_51105_fit_coupon, build_608_fit_coupon
from windwall.drivers import build_joint_coupon
from windwall.generator import build_magnet_pocket_coupon, intersection_volume
from windwall.generator_housing import build_coil_fit_coupon
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters
from windwall.reference_mesh import MeshReport, analyze_binary_stl
from windwall.top_support import build_top_support


PRINT_SOURCES = {
    'base_rotor_module': ('rotating', 'windwall.rotor_modules.build_base_module'),
    'standard_rotor_module': ('rotating', 'windwall.rotor_modules.build_standard_module'),
    'top_rotor_module': ('rotating', 'windwall.rotor_modules.build_top_module'),
    'lower_magnet_rotor': ('rotating', 'windwall.generator.build_lower_magnet_rotor'),
    'generator_housing': ('stationary', 'windwall.generator_housing.build_generator_housing'),
    'coil_cassette': ('stationary', 'windwall.generator_housing.build_coil_cassette'),
    'generator_cover': ('stationary', 'windwall.generator_housing.build_generator_cover'),
    'top_support': ('stationary', 'windwall.top_support.build_top_support'),
}
PROTOTYPE_LIMITS = (
    'Printed fits, material strength and physical assembly remain unverified.',
    'Permanent bayonet elastic insertion and inherited joint axial float require coupon tests.',
    'Magnet retention, electrical output, load capacity and outdoor operation remain unvalidated.',
)


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
    role: str = 'hardware-reference'
    source_builder: str = 'windwall.export.export_part'
    fit_dimensions_mm: dict | None = None

    @property
    def boundary_edge_count(self) -> int:
        return self.mesh.boundary_edge_count

    @property
    def nonmanifold_edge_count(self) -> int:
        return self.mesh.nonmanifold_edge_count

    @property
    def degenerate_face_count(self) -> int:
        return self.mesh.degenerate_face_count

    def as_dict(self, root: Path, prefix: Path = Path()) -> dict:
        record = {
            'name': self.name, 'quantity': self.quantity,
            'step_path': (prefix / self.step_path.relative_to(root)).as_posix(),
            'stl_path': (prefix / self.stl_path.relative_to(root)).as_posix(),
            'step_sha256': self.step_sha256, 'stl_sha256': self.stl_sha256,
            'cad_volume_mm3': self.cad_volume_mm3, 'cad_bounds_mm': self.cad_bounds,
            'cad_valid': True, 'cad_solid_count': 1, 'step_round_trip_valid': True,
            'expected_component_count': 1, 'mesh': self.mesh.as_dict(),
            'stl_translation_z_mm': -self.cad_bounds['minimum_xyz'][2],
            'role': self.role, 'printable': True, 'source_builder': self.source_builder,
            'dimensions_mm': self.cad_bounds, 'physical_validation_verified': False,
            'known_limitations': list(PROTOTYPE_LIMITS),
            'topology_result': {'cad_valid': True, 'cad_solid_count': 1,
                                'step_round_trip_valid': True, 'stl_binary': True,
                                'stl_closed_manifold': True, 'stl_component_count': 1},
        }
        if self.fit_dimensions_mm is not None:
            record['fit_dimensions_mm'] = self.fit_dimensions_mm
        return record


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
                coupon: bool = False, quantity: int = 1,
                role: str | None = None, source_builder: str = 'windwall.export.export_part',
                fit_dimensions_mm: dict | None = None) -> PartExport:
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
    # The Workplane exporter uses edge-relative deflection. Our parameter is
    # millimetres; use absolute deflection and a serial mesh for reproducibility.
    if not printable.val().exportStl(str(stl_path), tolerance=m.export_linear_tolerance_mm,
                                     angularTolerance=m.export_angular_tolerance_rad,
                                     ascii=False, relative=False, parallel=False):
        raise ValueError(f'{name} binary STL export failed')
    mesh = validate_mesh(stl_path)
    if (abs(mesh.signed_volume - volume) > max(0.05, volume * 0.005)
            or max(abs(a - b) for a, b in zip(mesh.size_xyz, bounds['size_xyz']))
            > 2 * m.export_linear_tolerance_mm
            or abs(mesh.minimum_xyz[2]) > 1e-5):
        raise ValueError(f'{name} STL changed CAD envelope, volume or print origin')
    return PartExport(name, quantity, step_path, stl_path, step_hash, _file_hash(stl_path),
                      volume, bounds, mesh, role or ('coupon' if coupon else 'hardware-reference'),
                      source_builder, fit_dimensions_mm)


def _component_record(name: str, shape: cq.Workplane, rotating: set[str],
                      stationary: set[str], source: str) -> dict:
    print_name = {'base': 'base_rotor_module', 'top': 'top_rotor_module',
                  'housing': 'generator_housing', 'cover': 'generator_cover'}.get(name, name)
    if name.startswith('standard_'):
        print_name = 'standard_rotor_module'
    printable = print_name in PRINT_SOURCES
    role, builder = PRINT_SOURCES.get(print_name, ('hardware-reference', source))
    solid = shape.val()
    solids = solid.Solids()
    if not solids or not solid.isValid():
        raise ValueError(f'{name} must contain valid component solids')
    for member in solids:
        _valid_solid(member, name)
    return {
        'name': name, 'role': role, 'printable': printable,
        'quantity': len(solids), 'named_group_count': 1, 'cad_solid_count': len(solids),
        'motion': ('rotating' if name in rotating else 'stationary' if name in stationary
                   else 'bearing-internal'),
        'source_builder': builder, 'dimensions_mm': _bounds(solid),
        'cad_bounds_mm': _bounds(solid), 'cad_volume_mm3': _volume_mm3(solid),
        'cad_valid': True, 'physical_validation_verified': False,
        'known_limitations': list(PROTOTYPE_LIMITS) if printable else
            ['Nominal occupied-volume reference; procurement dimensions, material and physical fit are unverified.'],
        'topology_result': {'cad_valid': True, 'cad_solid_count': len(solids),
                            'step_round_trip_valid': True, 'stl_required': False},
        **({'print_part': print_name} if printable else {}),
    }


def _export_named_assembly(name: str, parts: dict[str, cq.Workplane], destination: Path,
                           *, rotating: set[str], stationary: set[str], source: str,
                           prefix: Path = Path(), source_overrides: dict | None = None) -> dict:
    """Export named groups while counting every solid in compound references."""
    path = destination / 'assembly' / f'{name}.step'
    path.parent.mkdir(parents=True, exist_ok=True)
    # OCCT serializes color presentation records in pointer-dependent order.
    # Keep release geometry/names deterministic; previews supply visual colors.
    assembly = cq.Assembly(name=name)
    components = []
    for component_name, workplane in parts.items():
        assembly.add(workplane, name=component_name)
        builder = (source_overrides or {}).get(component_name, source)
        components.append(_component_record(component_name, workplane, rotating, stationary, builder))
    volume = sum(component['cad_volume_mm3'] for component in components)
    count = sum(component['cad_solid_count'] for component in components)
    step_hash = _export_step(assembly, path, count, volume)
    compound = cq.Compound.makeCompound([part.val() for part in parts.values()])
    return {'name': name, 'step_path': (prefix / path.relative_to(destination)).as_posix(),
            'step_sha256': step_hash, 'cad_bounds_mm': _bounds(compound),
            'summed_component_volume_mm3': volume,
            'component_count': len(components), 'expected_component_count': len(parts),
            'cad_solid_count': count, 'role': 'hardware-reference', 'motion': 'mixed',
            'quantity': 1, 'printable': False, 'dimensions_mm': _bounds(compound),
            'source_builder': source, 'physical_validation_verified': False,
            'known_limitations': list(PROTOTYPE_LIMITS),
            'topology_result': {'cad_valid': True, 'cad_solid_count': count,
                                'step_round_trip_valid': True, 'stl_required': False},
            'step_round_trip_valid': True, 'components': components}


def _export_assembly(model: RotorAssembly, destination: Path, parameters: DesignParameters,
                     prefix: Path = Path()) -> dict:
    """Export the rotor with explicit ownership and no fixed hardware count."""
    record = _export_named_assembly('rotor_exploded' if model.exploded else 'rotor_locked',
        model.parts, destination, rotating=set(model.rotating_parts),
        stationary=set(model.stationary_parts),
        source='windwall.assembly.build_locked_rotor_assembly', prefix=prefix)
    record.update(stages=[asdict(stage) for stage in model.stages], stage_count=len(model.stages))
    return record


def _export_coupons(destination: Path, p: DesignParameters) -> tuple[PartExport, ...]:
    """Split the Task-1 combined gauge at its empty midline into print choices.

    The negative-Y half retains all three outer seats; the positive-Y half
    retains all three pilot gauges. The cut preserves sampled fit surfaces.
    """
    result = [export_part('magnet_pocket_coupon', build_magnet_pocket_coupon(p), destination, p,
                          coupon=True, source_builder='windwall.generator.build_magnet_pocket_coupon',
                          fit_dimensions_mm={'pocket_diameters': [
                              p.generator.magnet_pocket_diameter_mm + offset*p.generator.coupon_diameter_step_mm
                              for offset in (-1, 0, 1)], 'pocket_depth': p.generator.magnet_pocket_depth_mm})]
    thrust = build_51105_fit_coupon(p)
    box = thrust.shape.val().BoundingBox()
    for name, center_y, dimensions in (
            ('51105_outer_seat_coupon', box.ymin/2,
             {'seat_diameters': list(thrust.seat_diameters_mm), 'seat_depth': thrust.seat_depth_mm}),
            ('25mm_pilot_coupon', box.ymax/2,
             {'pilot_diameters': list(thrust.pilot_diameters_mm), 'bearing_bore': p.bearings.thrust_bore_diameter_mm})):
        half = (cq.Workplane('XY').box(box.xlen+2, abs(center_y)*2, box.zlen+2,
                                      centered=(True, True, False))
                .translate((0, center_y, box.zmin-1)))
        shape = thrust.shape.intersect(half).clean()
        result.append(export_part(name, shape, destination, p, coupon=True,
            source_builder='windwall.bearings.build_51105_fit_coupon', fit_dimensions_mm=dimensions))
    radial = build_608_fit_coupon(p)
    result.append(export_part('608_seat_coupon', radial.shape, destination, p, coupon=True,
        source_builder='windwall.bearings.build_608_fit_coupon',
        fit_dimensions_mm={'seat_diameters': list(radial.seat_diameters_mm), 'seat_depth': radial.seat_depth_mm}))
    coil = build_coil_fit_coupon(p)
    result.append(export_part('coil_cassette_segment_coupon', coil.shape, destination, p, coupon=True,
        source_builder='windwall.generator_housing.build_coil_fit_coupon',
        fit_dimensions_mm={'radial_clearances': list(coil.radial_clearances_mm),
                           'cassette_diameter': coil.cassette_diameter_mm,
                           'release_instruction': coil.release_instruction}))
    for name, builder in (('bayonet', build_bayonet_coupon), ('joint', build_joint_coupon)):
        pair = builder(p)
        for member in ('male', 'female'):
            result.append(export_part(f'{name}_{member}', getattr(pair, member), destination, p,
                coupon=True, source_builder=f'{builder.__module__}.{builder.__name__}'))
    return tuple(result)


def _integrate_top_support(locked: RotorAssembly, support) -> tuple[dict, dict, set[str]]:
    """Replace the rod once and audit the full rotating collection against the support.

    The wood block and screws describe engagement, not a complete fence or
    structural validation. The top clamp must be fitted before installing the
    support; the rotor-only service-access audit does not include that plate.
    """
    extra = {'top_support': support.shape, 'bearing_608': support.bearing,
             'upper_wood_frame_reference': support.wood_frame_reference,
             **{f'wood_screw_{i}_reference': shape for i, shape in enumerate(support.wood_screws, 1)}}
    parts = {**locked.parts, 'shaft': support.required_shaft_reference, **extra}
    rotating = {name: parts[name] for name in locked.rotating_parts}
    pairs = {f'{moving}/{fixed}/axial_shift_{shift:g}': intersection_volume(
                 shape.translate((0, 0, shift)), stationary)
             for moving, shape in rotating.items() for fixed, stationary in extra.items()
             for shift in (-support.axial_float_mm, 0, support.axial_float_mm)}
    shaft_pairs = {name: intersection_volume(parts['shaft'], shape)
                   for name, shape in parts.items() if name != 'shaft'}
    original = locked.parts['shaft'].val().BoundingBox()
    shaft = parts['shaft'].val().BoundingBox()
    bearing = support.bearing.val().BoundingBox()
    frame_bottom = support.wood_frame_reference.val().BoundingBox().zmin
    engaged = (shaft.zmin+support.axial_float_mm <= bearing.zmin
               and shaft.zmax-support.axial_float_mm >= frame_bottom-1e-6)
    if (sum(pairs.values()) >= 0.01 or sum(shaft_pairs.values()) >= 0.01
            or abs(shaft.zmin-original.zmin) > 1e-6 or not engaged):
        raise ValueError('Integrated upper support requires a clear, fully engaged replacement shaft')
    audit = {
        'extended_shaft_integrated': True, 'shaft_bounds_z_mm': [shaft.zmin, shaft.zmax],
        'shaft_extension_mm': shaft.zmax-original.zmax,
        'shaft_engages_full_bearing_at_axial_float': engaged,
        'axial_float_each_direction_mm': support.axial_float_mm,
        'bearing_seat_play_mm': frame_bottom-bearing.zmax,
        'upper_support_rotating_intersection_mm3': sum(pairs.values()),
        'upper_support_pair_intersections_mm3': pairs,
        'shaft_pair_intersections_mm3': shaft_pairs,
        'physical_validation_verified': False,
        'known_limitations': ['Fit and tighten the top clamp before installing the support.',
            'Wood and screw overlap denotes unvalidated nominal engagement.',
            '608 envelope does not resolve individual race or rolling-element kinematics.',
            'Existing wood frame is a local closure reference; lower frame and mounting screws are not modeled.'],
    }
    return parts, audit, set(extra)


def export_all(destination: Path, parameters: DesignParameters = DEFAULT_PARAMETERS, *,
               repository_prefix: Path = Path()) -> ExportManifest:
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
    coupons = _export_coupons(destination, parameters)
    locked = build_locked_rotor_assembly(parameters)
    audit = audit_rotor_assembly(locked)
    require_valid_assembly_audit(audit)
    support = build_top_support(parameters)
    generator = locked.generator
    shapes = {f'{kind}_rotor_module': locked.local_modules[kind] for kind in ('base', 'standard', 'top')}
    shapes.update(lower_magnet_rotor=generator.lower_rotor,
                  generator_housing=generator.housing_parts.housing,
                  coil_cassette=generator.housing_parts.coil_cassette,
                  generator_cover=generator.housing_parts.cover,
                  top_support=support.shape.translate((0, 0, -support.plate_bottom_z_mm)))
    production = tuple(export_part(name, shape, destination, parameters,
        quantity=5 if name == 'standard_rotor_module' else 1,
        role=PRINT_SOURCES[name][0], source_builder=PRINT_SOURCES[name][1])
        for name, shape in shapes.items())
    total_parts, support_audit, extra_names = _integrate_top_support(locked, support)
    assemblies = (
        _export_assembly(locked, destination, parameters, repository_prefix),
        _export_named_assembly('generator', {**generator.rotating_parts, **generator.stationary_parts,
                              **generator.bearing_parts}, destination,
            rotating=set(generator.rotating_parts), stationary=set(generator.stationary_parts),
            source='windwall.generator.build_generator_assembly', prefix=repository_prefix),
        _export_named_assembly('fence_assembly', total_parts, destination,
            rotating=set(locked.rotating_parts), stationary=set(locked.stationary_parts) | extra_names,
            source='windwall.assembly.build_locked_rotor_assembly', prefix=repository_prefix,
            source_overrides={name: 'windwall.top_support.build_top_support'
                              for name in extra_names | {'shaft'}}))
    # Legacy builders read rod projections from ClosureParameters; V5 exposes
    # only those active shaft dimensions instead of obsolete cover dimensions.
    parameter_record = asdict(parameters)
    parameter_record.pop('closure')
    parameter_record['modules'].pop('closure_pilot_depth_mm')
    parameter_record['modules'].pop('closure_screw_radius_mm')
    parameter_record['shaft_end'] = {
        'rod_projection_mm': parameters.closure.rod_projection_mm,
        'shaft_bottom_projection_mm': parameters.closure.shaft_bottom_projection_mm,
    }
    data = {
        'schema_version': 2, 'release': 'v5', 'units': 'mm', 'parameters': parameter_record,
        'runtime': {'python': python_version(), **{name: version(name) for name in
                    ('cadquery', 'cadquery-ocp', 'numpy', 'vtk', 'casadi', 'nlopt')}},
        'production_quantity': sum(part.quantity for part in production),
        'production_parts': [part.as_dict(destination, repository_prefix) for part in production],
        'coupons': [part.as_dict(destination, repository_prefix) for part in coupons],
        'assemblies': assemblies, 'assembly_audit': audit, 'fence_assembly_audit': support_audit,
        'coordinate_frames': {'print_step': 'Builder-local coordinates; support bottom at Z=0.',
                              'print_stl': 'Each STEP body translated vertically to bottom Z=0.',
                              'assembly_step': 'Base nominal blade bottom Z=0; shaft axis X=Y=0.'},
        'manifest_path_base': 'repository' if repository_prefix.parts else 'output directory',
        'physical_validation_verified': False, 'known_limitations': list(PROTOTYPE_LIMITS),
        'physical_fit_verified': False, 'print_ready': False,
        'outdoor_operation_validated': False, 'overspeed_validated': False,
        'storm_operation_validated': False, 'electrical_operation_validated': False,
        'determinism': 'Same parameters and pinned runtime; absolute serial STL meshing, uncolored named STEP assemblies, normalized timestamp and occurrence counters.',
        'runtime_exit_status': 'Reported by the caller after process termination; not certified by this manifest.',
    }
    pending = destination / 'manifest.pending.json'
    pending.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    pending.replace(manifest_path)
    return ExportManifest(tuple(production), tuple(coupons), assemblies, manifest_path)
