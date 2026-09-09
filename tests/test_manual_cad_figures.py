"""CAD-derived manual figures must cover the released mechanical BOM."""

import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from scripts.manual import cad_figures
from scripts.manual.cad_figures import render_cad_figures
from tests.support import temporary_build_directory


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ManualCadFigureTests(unittest.TestCase):
    def test_missing_rendered_leader_is_rejected(self):
        def scene(*bom_ids):
            leaders = [cad_figures._Leader(bom_id, (0.0, 0.0, 0.0)) for bom_id in bom_ids]
            return [], leaders, []

        with (
            temporary_build_directory() as destination,
            patch.object(cad_figures, 'build_locked_rotor_assembly', return_value=object()),
            patch.object(cad_figures, 'build_exploded_rotor_assembly', return_value=object()),
            patch.object(cad_figures, '_scene_e01', return_value=scene(
                'P01', 'P02', 'P03', 'P04', 'P05', 'H01', 'H02', 'H03', 'H04'
            )),
            patch.object(cad_figures, '_scene_e02', return_value=scene(
                'P01', 'P05', 'H01', 'H02', 'H03', 'H06', 'H07', 'H10'
            )),
            patch.object(cad_figures, '_scene_e03', return_value=scene('P01', 'P05', 'H10', 'H11')),
            patch.object(cad_figures, '_scene_e04', return_value=scene('P01', 'P02', 'H04')),
            patch.object(cad_figures, '_scene_e05', return_value=scene(
                'P03', 'P04', 'H01', 'H02', 'H03', 'H04', 'H05'
            )),
            patch.object(cad_figures, '_save_standard_figure'),
            patch.object(cad_figures, '_save_section_figure', return_value=[
                cad_figures._Leader(bom_id, (0.0, 0.0, 0.0))
                for bom_id in ('P01', 'P02', 'P03', 'P05', 'H01', 'H02', 'H03', 'H06', 'H07', 'H10')
            ]),
        ):
            with self.assertRaisesRegex(ValueError, 'E01.*missing.*H05'):
                render_cad_figures(PROJECT_ROOT, destination)

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
