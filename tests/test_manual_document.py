"""Check the generated maker document at its OOXML delivery boundary.

Run with bundled document Python via ``python -m unittest discover -s tests
-p test_manual_document.py``. Committed drawing assets need no CAD runtime.
"""

from importlib import import_module
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from uuid import uuid4

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Mm


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))


class ManualDocumentTests(unittest.TestCase):
    """Missing content, drawings, layout or accessibility must fail delivery."""

    document = None
    target = None

    def setUp(self):
        self.assertTrue(
            (ROOT / 'scripts/manual/build_manual.py').is_file(),
            'The German manual builder has not been implemented',
        )
        if self.__class__.document is None:
            (ROOT / 'build').mkdir(exist_ok=True)
            # Windows sandbox ACLs reject tempfile's mode-0700 directories.
            # Use a unique artifact in the existing writable build directory.
            target = ROOT / 'build' / f'manual-test-{uuid4().hex}.docx'
            self.__class__.target = target
            builder = import_module('scripts.manual.build_manual').build_manual
            self.assertEqual(builder(ROOT, target), target)
            self.__class__.document = Document(target)
        self.doc = self.document
        self.text = '\n'.join(self.doc.element.body.xpath('.//w:t/text()'))

    @classmethod
    def tearDownClass(cls):
        if cls.target:
            cls.target.unlink(missing_ok=True)

    def test_required_instructions_and_safety_are_present(self):
        required = (
            'Prototyp', 'Sicherheit', 'Hauptmaße', 'Druckteile', 'Kaufteile',
            'Bambu Lab P2S', '0,4 mm', 'PLA', 'ASA', 'Coupon',
            'Generator mechanisch montieren', 'Magnete', 'Trockenlayout',
            'Testwicklung', 'Serpentinen', 'A1', 'A2', 'Emaille',
            '20', '40', '80', '0,18 mm', 'Leerlauf', 'definierte Last',
            'Widerstand', 'Temperatur', 'gleicher Drehzahl',
            'N_final = N_test * V_ac_target / V_ac_test', 'aufrunden',
            'Sieben Stufen', '-18°', 'CCW', 'M8', 'Rundlauf', 'Balance',
            'Inbetriebnahme', 'Wartung', 'Fehlersuche', 'Messblatt',
            'Zeichnungsindex', 'Quellen', '69,64', '487,84', '559,64',
            '+60°', '-60°', '10,8', '11,0', '11,2', '1,5 mm',
            'Generator nicht direkt mit dem Akku verbinden.',
            'Wasserstoff', 'Überdrehzahl', 'Feuchtigkeit', 'unbeaufsichtigt',
            'Nach Messung auswählen',
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)

    def test_boms_include_all_ids_and_printable_stl_references(self):
        table_text = '\n'.join(cell.text for t in self.doc.tables
                               for row in t.rows for cell in row.cells)
        for prefix, count in (('P', 5), ('H', 17)):
            for number in range(1, count + 1):
                self.assertIn(f'{prefix}{number:02}', table_text)
        for filename in ('base_rotor_module.stl', 'standard_rotor_module.stl',
                         'top_rotor_module.stl', 'top_closure.stl',
                         'lower_magnet_rotor.stl'):
            self.assertIn(filename, table_text)

    def test_all_drawings_are_inline_accessible_and_captioned(self):
        self.assertEqual(len(self.doc.inline_shapes), 11)
        self.assertFalse(self.doc.element.body.xpath('.//wp:anchor'))
        image_ids = []
        paragraphs = self.doc.paragraphs
        for index, paragraph in enumerate(paragraphs):
            properties = paragraph._p.xpath('.//wp:inline/wp:docPr')
            if not properties:
                continue
            self.assertEqual(len(properties), 1)
            description = properties[0].get('descr', '')
            drawing_id = description.split(':', 1)[0]
            image_ids.append(drawing_id)
            caption = paragraphs[index + 1]
            self.assertEqual(caption.style.name, 'Caption')
            self.assertTrue(caption.text.startswith(drawing_id + '  '))
            self.assertGreater(len(description), 25)
            relationship_id = paragraph._p.xpath('.//a:blip')[0].get(qn('r:embed'))
            actual_bytes = self.doc.part.related_parts[relationship_id].blob
            expected_asset = next((ROOT / 'assets/manual/release/output/manual-figures').glob(
                drawing_id + '-*.png',
            ))
            self.assertEqual(actual_bytes, expected_asset.read_bytes(),
                             f'{drawing_id} must embed its own drawing asset')
        self.assertCountEqual(image_ids, [f'E{i:02}' for i in range(1, 12)])

    def test_a4_portrait_and_eighteen_mm_side_margins(self):
        for section in self.doc.sections:
            for actual, expected in ((section.page_width, Mm(210)),
                                     (section.page_height, Mm(297)),
                                     (section.left_margin, Mm(18)),
                                     (section.right_margin, Mm(18))):
                self.assertAlmostEqual(actual, expected, delta=700)

    def test_headings_use_continuous_black_word_styles(self):
        levels = [int(p.style.name[-1]) for p in self.doc.paragraphs
                  if p.style.name.startswith('Heading ')]
        self.assertIn(1, levels)
        self.assertIn(2, levels)
        previous = 0
        for level in levels:
            self.assertLessEqual(level, previous + 1)
            previous = level
        self.assertTrue(any(p.style.name == 'Title' for p in self.doc.paragraphs))
        for name in ('Title', 'Heading 1', 'Heading 2'):
            self.assertEqual(str(self.doc.styles[name].font.color.rgb), '000000')

    def test_thirteen_chapter_outline_keeps_page_topics_subordinate(self):
        self.assertEqual(
            [p.text for p in self.doc.paragraphs if p.style.name == 'Heading 1'],
            ['1 Umfang und Prototypstatus', '2 Druckteile und STL Dateien',
             '3 Kaufteile für Aufbau und Versuche', '4 Druckempfehlungen für PLA und ASA',
             '5 Vorbereitung und Coupon Tests', '6 Generator mechanisch montieren',
             '7 Magnete montieren und Polung prüfen', '8 Durchgehende Testwicklung herstellen',
             '9 Testspulen vergleichbar messen', '10 Sieben Stufen montieren',
             '11 Top Klemmung und Abschluss', '12 Inbetriebnahme Wartung und Sicherheit',
             '13 Formeln Messblätter und Quellen'],
        )

    def test_each_wire_diameter_has_a_fit_gated_turn_matrix_and_records(self):
        matrices = [table for table in self.doc.tables
                    if table.cell(0, 0).text == 'Drahtcharge und gemessenes d']
        self.assertEqual(len(matrices), 1)
        matrix = matrices[0]
        self.assertEqual([cell.text for cell in matrix.rows[0].cells[1:]],
                         ['20 Windungen', '40 Windungen', '80 Windungen'])
        self.assertGreaterEqual(len(matrix.rows), 4)
        for row in matrix.rows[1:]:
            self.assertIn('d = ____ mm', row.cells[0].text)
            for cell in row.cells[1:]:
                self.assertIn('passt / passt nicht', cell.text)
        headers = [cell.text for table in self.doc.tables for cell in table.rows[0].cells]
        for label in ('Drahtlänge m', 'f leer Hz', 'R pro m Ω/m', 'ΔV intern V'):
            self.assertIn(label, headers)
        for phrase in ('Für jeden verfügbaren gemessenen Drahtdurchmesser',
                       'R_pro_m = R_spule / l_draht',
                       'Delta_V_intern = V_leer - V_last'):
            self.assertIn(phrase, self.text)

    def test_first_loaded_measurements_require_current_limit(self):
        for phrase in ('Erste Lasttests ausdrücklich strombegrenzen',
                       'mit hohem Lastwiderstand beginnen',
                       'Stromgrenze vor dem Drehen dokumentieren'):
            self.assertTrue(phrase in self.text, f'Missing current-limit instruction: {phrase}')

    def test_coil_placement_and_later_potting_have_separate_validation_gates(self):
        for phrase in ('Testspule in den realen Wicklungsträger einsetzen',
                       'gebundene Spule trocken und ohne Kraft',
                       'A1 und A2 zugentlasten',
                       'vor und nach dem Einsetzen',
                       'eine volle Umdrehung von Hand',
                       'Erste elektrische Versuche bleiben unvergossen',
                       'Vergussversuch erst nach der Spulenauswahl',
                       'geringer Reaktionswärme', 'kleinen ausgehärteten Coupon',
                       'vollständig nach Herstellerangaben aushärten',
                       'Maße, Isolation und Lasttemperatur erneut prüfen',
                       'keine nachgewiesene Magnet- oder Wicklungsrückhaltung'):
            self.assertTrue(phrase in self.text, f'Missing winding workflow gate: {phrase}')

    def test_every_drawing_is_referenced_in_instructional_prose(self):
        prose = '\n'.join(p.text for p in self.doc.paragraphs if p.style.name == 'Normal')
        for number in range(1, 12):
            self.assertIn(f'E{number:02}', prose)

    def test_tables_have_borders_repeating_headers_and_no_fixed_height(self):
        self.assertGreaterEqual(len(self.doc.tables), 4)
        for table in self.doc.tables:
            self.assertIsNotNone(table.rows[0]._tr.find('w:trPr/w:tblHeader', table._element.nsmap))
            self.assertTrue(table._tbl.xpath('./w:tblPr/w:tblBorders'))
            for height in table._tbl.xpath('.//w:trHeight'):
                self.assertNotEqual(height.get(qn('w:hRule')), 'exact')


class CleanManualProjectTests(unittest.TestCase):
    """The document-only build must work without ignored outputs or CAD."""

    def setUp(self):
        self.snapshot = ROOT / 'assets/manual/release'
        self.assertTrue(self.snapshot.is_dir(), 'A committed manual asset snapshot is required')
        (ROOT / 'build').mkdir(exist_ok=True)
        self.project = ROOT / 'build' / f'manual-clean-{uuid4().hex}'
        self.project.mkdir()
        shutil.copytree(self.snapshot, self.project / 'assets/manual/release')

    def tearDown(self):
        if hasattr(self, 'project'):
            self.assertEqual(self.project.resolve().parent, (ROOT / 'build').resolve())
            shutil.rmtree(self.project)

    def test_clean_project_builds_without_ignored_outputs_or_cad(self):
        self.assertFalse((self.project / 'build').exists())
        self.assertFalse((self.project / 'output').exists())
        target = self.project / 'manual.docx'
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts/manual/build_manual.py'),
             '--project-root', str(self.project), '--output', str(target)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(Document(target).inline_shapes), 11)

    def test_missing_drawing_names_the_asset_without_importing_cad(self):
        drawing = self.project / 'assets/manual/release/output/manual-figures/E01-gesamt-explosion.png'
        drawing.unlink()
        builder = import_module('scripts.manual.build_manual').build_manual
        with self.assertRaisesRegex(FileNotFoundError, 'Manual drawing asset missing: E01'):
            builder(self.project, self.project / 'manual.docx')

if __name__ == '__main__':
    unittest.main()
