"""Bind the finished V5 geometry, drawings and manual in one portable inventory.

The geometry manifest remains the CAD API. This final index verifies its file
hashes, PNG dimensions and a separately produced DOCX audit bound to the exact
reviewed inputs. It does not author documents, certify physical operation or
claim rendered-page review.
"""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PREFIX = PurePosixPath('release/v5')
MANUAL = 'release/v5/docs/Ugrinsky-Wind-Wall-V5-Bauanleitung.docx'


def build_release_index(project_root: Path) -> dict:
    root = Path(project_root).resolve()
    release = root / PREFIX
    output = release / 'release-index.json'
    output.unlink(missing_ok=True)
    records = {}

    def asset(relative, kind, *, expected_hash=None, **metadata):
        path = PurePosixPath(relative)
        if (path.is_absolute() or '..' in path.parts or '\\' in relative
                or ':' in relative or not path.is_relative_to(PREFIX)):
            raise ValueError('Artifact paths must be relative and contained in release/v5')
        local = (root / path).resolve()
        if not local.is_relative_to(release.resolve()):
            raise ValueError('Artifact path escapes release/v5')
        digest = hashlib.sha256(local.read_bytes()).hexdigest()
        if expected_hash is not None and digest != expected_hash:
            raise ValueError(f'Artifact hash differs from its reviewed source: {relative}')
        record = {'path': relative, 'kind': kind, 'sha256': digest,
                  'size_bytes': local.stat().st_size, **metadata}
        records[relative] = record
        return local, record

    geometry_path, geometry_record = asset('release/v5/manifest.json', 'geometry-manifest', role='inventory')
    geometry = json.loads(geometry_path.read_bytes())
    figures_path, figures_record = asset('release/v5/drawings/figures.json', 'drawing-manifest', role='inventory')
    figures = json.loads(figures_path.read_bytes())
    if geometry['release'] != 'v5' or figures['release'] != 'v5':
        raise ValueError('The final index requires V5 inputs')
    if figures['source_manifest_sha256'] != geometry_record['sha256']:
        raise ValueError('Drawing source manifest hash is stale')
    for item in geometry['production_parts'] + geometry['coupons'] + geometry['assemblies']:
        for suffix in ('stl', 'step'):
            if f'{suffix}_path' not in item:
                continue
            asset(item[f'{suffix}_path'], 'geometry', expected_hash=item[f'{suffix}_sha256'],
                  name=item['name'], role=item['role'], quantity=item['quantity'],
                  dimensions_mm=item['dimensions_mm'], validation=item['topology_result'],
                  physical_validation_verified=item['physical_validation_verified'])
    if [item['drawing_id'] for item in figures['figures']] != [f'E{i:02d}' for i in range(1, 16)]:
        raise ValueError('The release requires E01 through E15 exactly once')
    drawing_hashes = {}
    for drawing in figures['figures']:
        local, record = asset('release/v5/drawings/' + drawing['filename'], 'drawing',
                              name=drawing['drawing_id'], role='documentation', quantity=1,
                              language=drawing['language'], caption=drawing['caption'])
        with Image.open(local) as picture:
            picture.verify()
        with Image.open(local) as picture:
            size = list(picture.size)
        if size != [drawing['pixel_width'], drawing['pixel_height']] or size[0] < 2400 or size[1] < 1680:
            raise ValueError(f'Invalid drawing dimensions: {drawing["drawing_id"]}')
        record.update(dimensions_px=size, validation={'png_decodes': True, 'inventory_dimensions_match': True})
        drawing_hashes[drawing['filename']] = record['sha256']
    asset('release/v5/drawings/README.md', 'drawing-notes', role='documentation')
    audit_path, _ = asset('release/v5/audits/manual.json', 'manual-audit', role='validation-evidence')
    audit = json.loads(audit_path.read_bytes())
    if audit.get('geometry_manifest_sha256') != geometry_record['sha256']:
        raise ValueError('Manual audit no longer matches the reviewed geometry manifest')
    if audit.get('figures_manifest_sha256') != figures_record['sha256']:
        raise ValueError('Manual audit no longer matches the reviewed figures manifest')
    if len(drawing_hashes) != 15 or audit.get('drawing_sha256_by_filename') != drawing_hashes:
        raise ValueError('Manual audit no longer matches the exact reviewed drawing hashes')
    if (audit['artifact_path'] != MANUAL or not audit['structural_checks_passed']
            or not audit['canonical_zip_verified'] or any(audit['accessibility_findings'].values())):
        raise ValueError('Manual structural and accessibility evidence has not passed')
    asset(MANUAL, 'document', expected_hash=audit['artifact_sha256'], role='documentation', quantity=1,
          language='de-DE', validation=audit, physical_validation_verified=False)
    actual = {p.relative_to(root).as_posix() for p in release.rglob('*') if p.is_file()}
    if actual != set(records):
        raise ValueError(f'Unlisted release artifacts require review: {sorted(actual - set(records))}')
    result = {'release': 'v5', 'schema_version': 1, 'geometry_manifest': 'release/v5/manifest.json',
              'known_limitations': [
                  'The user reported that the printed V4.3 bayonet coupon fits and closes; no measured assembly-force or durability approval follows.',
                  'Lifted module motion has nonzero rigid-body overlap at pawls and lug roofs; elastic assembly remains unverified.',
                  'Magnet retention, winding performance, strength, outdoor operation and printed bearing fits require physical validation.',
                  'DOCX rendered-page review and PDF output remain blocked by the absent bundled LibreOffice executable.',
              ],
              'physical_validation_verified': False, 'artifacts': [records[key] for key in sorted(records)]}
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + '\n',
                      encoding='utf-8', newline='\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=ROOT)
    args = parser.parse_args()
    result = build_release_index(args.project_root)
    print(f'Indexed {len(result["artifacts"])} verified V5 artifacts; physical validation remains false.')


if __name__ == '__main__':
    main()
