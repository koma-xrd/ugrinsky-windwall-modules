"""Final inventory must bind every distributed artifact to its review evidence."""

import hashlib
import importlib
import json
from pathlib import Path
import unittest

from PIL import Image

from tests.support import temporary_build_directory


class ReleaseIndexTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.index_v5'),
                             'The complete release index builder is missing')
        self.build = importlib.import_module('scripts.index_v5').build_release_index
        self.root = self.enterContext(temporary_build_directory())
        self.release = self.root / 'release/v5'
        self.release.mkdir(parents=True)
        self.part = {'name': 'sample', 'role': 'rotating', 'quantity': 5,
                     'dimensions_mm': {'size_xyz': [12, 20, 30]},
                     'topology_result': {'cad_valid': True, 'stl_closed_manifold': True},
                     'physical_validation_verified': False}
        for suffix in ('stl', 'step'):
            relative = f'release/v5/{suffix}/sample.{suffix}'
            payload = f'verified {suffix} fixture'.encode()
            self.write(relative, payload)
            self.part[f'{suffix}_path'] = relative
            self.part[f'{suffix}_sha256'] = hashlib.sha256(payload).hexdigest()
        self.manifest = {'release': 'v5', 'production_parts': [self.part], 'coupons': [], 'assemblies': []}
        self.save('release/v5/manifest.json', self.manifest)
        drawings = []
        for i in range(1, 16):
            filename = f'E{i:02d}.png'
            path = self.release / 'drawings' / filename
            path.parent.mkdir(exist_ok=True)
            Image.new('RGB', (2400, 1680), (i, 0, 0)).save(path)
            drawings.append({'drawing_id': f'E{i:02d}', 'filename': filename,
                             'pixel_width': 2400, 'pixel_height': 1680,
                             'caption': 'Geprüfte Zeichnung', 'language': 'de'})
        self.figures = {'release': 'v5', 'source_manifest_sha256': self.digest('release/v5/manifest.json'),
                        'figures': drawings}
        self.save('release/v5/drawings/figures.json', self.figures)
        self.write('release/v5/drawings/README.md', b'Drawing inventory')
        self.write('release/v5/docs/Ugrinsky-Wind-Wall-V5-Bauanleitung.docx', b'reviewed document fixture')
        self.audit = {'artifact_path': 'release/v5/docs/Ugrinsky-Wind-Wall-V5-Bauanleitung.docx',
                      'artifact_sha256': self.digest('release/v5/docs/Ugrinsky-Wind-Wall-V5-Bauanleitung.docx'),
                      'structural_checks_passed': True, 'accessibility_findings': {'high': 0, 'medium': 0, 'low': 0},
                      'canonical_zip_verified': True, 'page_review': 'blocked_missing_bundled_soffice',
                      'geometry_manifest_sha256': self.digest('release/v5/manifest.json'),
                      'figures_manifest_sha256': self.digest('release/v5/drawings/figures.json'),
                      'drawing_sha256_by_filename': {item['filename']: self.digest('release/v5/drawings/' + item['filename'])
                                                     for item in drawings},
                      'physical_validation_verified': False}
        self.save('release/v5/audits/manual.json', self.audit)

    def write(self, relative, payload):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    def save(self, relative, data):
        self.write(relative, json.dumps(data).encode())

    def digest(self, relative):
        return hashlib.sha256((self.root / relative).read_bytes()).hexdigest()

    def test_complete_index_records_every_file_hash_dimensions_quantity_and_limits(self):
        result = self.build(self.root)
        records = {item['path']: item for item in result['artifacts']}
        self.assertEqual(set(records), {p.relative_to(self.root).as_posix()
                                      for p in self.release.rglob('*') if p.is_file()
                                      and p.name != 'release-index.json'})
        self.assertEqual(len([r for r in records.values() if r['kind'] == 'drawing']), 15)
        part = records['release/v5/stl/sample.stl']
        self.assertEqual((part['role'], part['quantity'], part['dimensions_mm']['size_xyz']),
                         ('rotating', 5, [12, 20, 30]))
        self.assertEqual(records['release/v5/drawings/E01.png']['dimensions_px'], [2400, 1680])
        for path, record in records.items():
            self.assertEqual(record['sha256'], self.digest(path))
            self.assertEqual(record['size_bytes'], (self.root / path).stat().st_size)
        manual = records[self.audit['artifact_path']]
        self.assertEqual(manual['validation']['page_review'], 'blocked_missing_bundled_soffice')
        self.assertFalse(result['physical_validation_verified'])
        first = (self.release / 'release-index.json').read_bytes()
        self.assertNotIn(b'\r\n', first, 'Canonical inventory bytes must not depend on the host OS')
        self.build(self.root)
        self.assertEqual((self.release / 'release-index.json').read_bytes(), first)

    def test_changed_geometry_is_rejected_and_stale_index_removed(self):
        self.build(self.root)
        self.write('release/v5/stl/sample.stl', b'tampered')
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.build(self.root)
        self.assertFalse((self.release / 'release-index.json').exists())

    def test_changed_manual_cannot_inherit_previous_review(self):
        self.write(self.audit['artifact_path'], b'changed document')
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.build(self.root)

    def test_same_dimension_drawing_replacement_cannot_inherit_manual_review(self):
        self.build(self.root)
        replacement = (self.release / 'drawings/E02.png').read_bytes()
        self.assertNotEqual(replacement, (self.release / 'drawings/E01.png').read_bytes())
        self.write('release/v5/drawings/E01.png', replacement)
        with self.assertRaisesRegex(ValueError, 'reviewed drawing'):
            self.build(self.root)
        self.assertFalse((self.release / 'release-index.json').exists())

    def test_updated_geometry_and_drawing_source_cannot_reuse_stale_manual_review(self):
        self.manifest['production_parts'][0]['quantity'] = 6
        self.save('release/v5/manifest.json', self.manifest)
        self.figures['source_manifest_sha256'] = self.digest('release/v5/manifest.json')
        self.save('release/v5/drawings/figures.json', self.figures)
        with self.assertRaisesRegex(ValueError, 'reviewed geometry manifest'):
            self.build(self.root)

    def test_updated_figure_metadata_cannot_reuse_stale_manual_review(self):
        self.figures['figures'][0]['caption'] = 'Changed source caption'
        self.save('release/v5/drawings/figures.json', self.figures)
        with self.assertRaisesRegex(ValueError, 'reviewed figures manifest'):
            self.build(self.root)

    def test_manual_review_requires_exact_drawing_filename_hash_mapping(self):
        for change in ('missing', 'extra', 'wrong_hash'):
            with self.subTest(change=change):
                audit = json.loads(json.dumps(self.audit))
                mapping = audit['drawing_sha256_by_filename']
                if change == 'missing':
                    mapping.pop('E01.png')
                elif change == 'extra':
                    mapping['E16.png'] = '0' * 64
                else:
                    mapping['E01.png'] = '0' * 64
                self.save('release/v5/audits/manual.json', audit)
                with self.assertRaisesRegex(ValueError, 'reviewed drawing'):
                    self.build(self.root)

    def test_missing_figure_stale_source_and_escape_paths_are_rejected(self):
        for change in ('missing', 'stale', 'escape'):
            with self.subTest(change=change):
                figures = json.loads(json.dumps(self.figures))
                if change == 'missing':
                    figures['figures'].pop()
                elif change == 'stale':
                    figures['source_manifest_sha256'] = '0' * 64
                else:
                    figures['figures'][0]['filename'] = '../../outside.png'
                self.save('release/v5/drawings/figures.json', figures)
                with self.assertRaises((ValueError, FileNotFoundError)):
                    self.build(self.root)

    def test_unlisted_release_file_requires_review(self):
        self.write('release/v5/stl/obsolete.stl', b'obsolete')
        with self.assertRaisesRegex(ValueError, 'Unlisted'):
            self.build(self.root)


if __name__ == '__main__':
    unittest.main()
