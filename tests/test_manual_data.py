import unittest
import json
from pathlib import Path
from unittest.mock import patch

from scripts.manual.manual_data import load_manual_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ManualDataContractTests(unittest.TestCase):
    def test_manual_data_matches_release_and_selected_hardware(self):
        data = load_manual_data(PROJECT_ROOT)

        self.assertEqual(data['dimensions']['loaded_height_mm'], 487.84)
        self.assertEqual(data['printed_parts']['P02']['quantity'], 5)
        self.assertEqual(data['hardware']['H01']['description'], 'M8 Gewindestange')
        self.assertEqual(data['hardware']['H10']['quantity'], 36)
        self.assertEqual(data['hardware']['H10']['size'], '10 x 2 mm')

    def test_every_bom_item_has_a_drawing_callout(self):
        data = load_manual_data(PROJECT_ROOT)
        called_out = {
            item
            for drawing in data['drawings'].values()
            for item in drawing['items']
        }

        self.assertTrue(set(data['printed_parts']) | set(data['hardware']) <= called_out)

    def test_manifest_backed_display_values_follow_a_changed_audit(self):
        manifest = json.loads((PROJECT_ROOT / 'build' / 'manifest.json').read_text(encoding='utf-8'))
        manifest['assembly_audit']['shaft_z_bounds_mm'] = [-61.0, 501.25]
        manifest['assembly_audit']['upper_generator_air_gap_mm'] = 2.25
        with patch('scripts.manual.manual_data._read_manifest', return_value=manifest):
            data = load_manual_data(PROJECT_ROOT)

        self.assertIn('562,25 mm', data['hardware']['H01']['specification'])
        self.assertIn('2,25 mm', data['drawings']['E06']['description'])


if __name__ == '__main__':
    unittest.main()
