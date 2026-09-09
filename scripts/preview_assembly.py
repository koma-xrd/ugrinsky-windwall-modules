"""Export the current V5 rotor to an isolated preview directory.

The magnet coupon precedes seven unique print candidates and locked/exploded
STEP assemblies. Current V5 ownership colors and a true generator section use
the shared manual renderer. These artifacts do not approve physical printing.
"""

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for import_root in (PROJECT_ROOT, PROJECT_ROOT / 'src'):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import cadquery as cq

from scripts.preview_generator import _export_print_candidate, export_magnet_pocket_coupon
from windwall.assembly import (audit_rotor_assembly, build_exploded_rotor_assembly,
                               build_locked_rotor_assembly)
from windwall.assembly_validation import require_valid_assembly_audit
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters


def export_assembly(parameters: DesignParameters, output_dir: Path) -> dict:
    """Audit, export and round-trip installed V5 solids without legacy covers."""
    from scripts.manual.v5_figures import render_rotor_preview

    output_dir.mkdir(parents=True, exist_ok=True)
    exports = {'magnet_pocket_coupon': export_magnet_pocket_coupon(parameters, output_dir)}
    locked = build_locked_rotor_assembly(parameters)
    report = audit_rotor_assembly(locked)
    require_valid_assembly_audit(report)
    exploded = build_exploded_rotor_assembly(parameters, locked=locked)
    unique = {f'{name}_module': shape for name, shape in locked.local_modules.items()}
    unique.update(lower_magnet_rotor=locked.generator.lower_rotor,
                  generator_housing=locked.generator.housing,
                  coil_cassette=locked.generator.coil_cassette,
                  generator_cover=locked.generator.cover)
    for name, shape in unique.items():
        exports[name] = _export_print_candidate(name, shape, parameters, output_dir)
    for name, model in (('rotor_locked', locked), ('rotor_exploded', exploded)):
        model.as_cq_assembly().export(str(output_dir / f'{name}.step'))
        imported = cq.importers.importStep(str(output_dir / f'{name}.step')).val()
        expected_solids = sum(len(part.val().Solids()) for part in model.parts.values())
        if not imported.isValid() or len(imported.Solids()) != expected_solids:
            raise ValueError(f'{name} STEP round trip lost valid assembly solids')
    section_bottom = report['top_blade_end_z_mm']-5
    section_height = locked.parts['top_nut'].val().BoundingBox().zmax-section_bottom+1
    slab = (cq.Workplane('XY').box(parameters.blade.rotor_radius_mm*2+5, .2, section_height,
                                 centered=(True, True, False)).translate((0, 0, section_bottom)))
    sections = [solid for shape in locked.parts.values() if shape.val().BoundingBox().zmax >= section_bottom
                for solid in shape.intersect(slab).val().Solids()]
    cq.exporters.export(cq.Compound.makeCompound(sections), str(output_dir / 'top_clamp_section.svg'),
                        opt={'projectionDir': (0, -1, 0), 'showHidden': False, 'width': 1100, 'height': 450})
    render_rotor_preview(locked, output_dir / 'assembly_inspection.png')
    report.update(export_order=list(exports), exports=exports,
                  exploded_stage_poses=[{'name': stage.name, 'z_mm': stage.z_mm, 'angle_deg': stage.angle_deg}
                                        for stage in exploded.stages],
                  static_qa_artifact='assembly_inspection.png')
    (output_dir / 'assembly_fit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=PROJECT_ROOT / 'build/previews/assembly')
    args = parser.parse_args()
    print(json.dumps(export_assembly(DEFAULT_PARAMETERS, args.output_dir), indent=2), flush=True)
    return 0


if 'show_object' in globals():
    model = build_locked_rotor_assembly(DEFAULT_PARAMETERS)
    show_object(model.as_cq_assembly(), name='V5 locked rotor | seven continuous stages')
    exploded = build_exploded_rotor_assembly(DEFAULT_PARAMETERS, locked=model)
    for name, shape in exploded.parts.items():
        show_object(shape.translate((180, 0, 0)), name=f'Preassembly: {name}')
elif __name__ == '__main__':
    raise SystemExit(main())
