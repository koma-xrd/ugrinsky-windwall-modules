"""CAD-derived manual figures must cover the released mechanical BOM."""

import unittest
from pathlib import Path

from PIL import Image

from scripts.manual.cad_figures import render_cad_figures
from tests.support import temporary_build_directory


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ManualCadFigureTests(unittest.TestCase):
    def test_cad_figures_cover_the_mechanical_bom(self):
        with temporary_build_directory() as destination:
            records = render_cad_figures(PROJECT_ROOT, destination)

            self.assertEqual(
                [record.drawing_id for record in records],
                ['E01', 'E02', 'E03', 'E04', 'E05', 'E06'],
            )
            self.assertTrue(all(record.path.stat().st_size > 50_000 for record in records))
            self.assertTrue(
                {'P01', 'P02', 'P03', 'P04', 'P05', 'H01', 'H10'}
                <= {item for record in records for item in record.callouts}
            )
            for record in records:
                with Image.open(record.path) as image:
                    self.assertGreaterEqual(max(image.size), 2200)


if __name__ == '__main__':
    unittest.main()
