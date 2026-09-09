"""Exercise the DOCX/PDF release verifier at its real file boundaries."""

from __future__ import annotations

from pathlib import Path
import shutil
import sys
import unittest
from uuid import uuid4

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

from scripts.manual.verify_manual import verify_manual_release


CHAPTERS = (
    '1 Umfang und Prototypstatus',
    '2 Druckteile und STL Dateien',
    '3 Kaufteile für Aufbau und Versuche',
    '4 Druckempfehlungen für PLA und ASA',
    '5 Vorbereitung und Coupon Tests',
    '6 Generator mechanisch montieren',
    '7 Magnete montieren und Polung prüfen',
    '8 Durchgehende Testwicklung herstellen',
    '9 Testspulen vergleichbar messen',
    '10 Sieben Stufen montieren',
    '11 Top Klemmung und Abschluss',
    '12 Inbetriebnahme Wartung und Sicherheit',
    '13 Formeln Messblätter und Quellen',
)

DRAWING_TITLES = (
    'E01 Gesamtexplosion des Sieben-Stufen-Rotors',
    'E02 Generator-Explosion',
    'E03 Basisrotor und Magnetträger',
    'E04 Standardverbindung und CCW-Bajonett',
    'E05 Top-Abschluss und Klemmung',
    'E06 Schnitt durch Welle und Luftspalte',
    'E07 Magnetpolung beider Rotoren',
    'E08 Serpentinenpfad der Testwicklung',
    'E09 Wickelschablone',
    'E10 Messaufbau der Testspulen',
    'E11 Sichere Ladekette',
)

RELEASE_LINES = (
    *CHAPTERS,
    'Generator nicht direkt mit dem Akku verbinden.',
    'N_final = N_test * V_ac_target / V_ac_test',
    ' '.join(f'P{number:02}' for number in range(1, 6)),
    ' '.join(f'H{number:02}' for number in range(1, 18)),
    *DRAWING_TITLES,
)


def _write_docx(path: Path, lines=RELEASE_LINES) -> None:
    document = Document()
    document.core_properties.title = 'Ugrinsky Wind Wall Bauanleitung'
    for line in lines:
        document.add_paragraph(line)
    document.save(path)


def _write_pdf(path: Path, *, lines=RELEASE_LINES, pages: int = 16, blank_last=False) -> None:
    canvas = Canvas(str(path), pagesize=A4)
    canvas.setTitle('Ugrinsky Wind Wall Bauanleitung')
    for page_number in range(1, pages + 1):
        if not (blank_last and page_number == pages):
            canvas.setFont('Helvetica', 9)
            canvas.drawString(42, 805, f'Ugrinsky release page {page_number} of {pages}')
            y = 785
            for line in lines if page_number == 1 else (f'Pruefseite {page_number}',):
                canvas.drawString(42, y, line)
                y -= 13
        canvas.showPage()
    canvas.save()


class ManualReleaseTests(unittest.TestCase):
    """Release verification must catch omissions, stale renders and blank pages."""

    @classmethod
    def setUpClass(cls):
        # A project-local location avoids Windows sandbox ACL failures in tempfile.
        cls.workspace = ROOT / 'build' / f'manual-release-{uuid4().hex}'
        cls.workspace.mkdir(parents=True)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'workspace'):
            if cls.workspace.resolve().parent != (ROOT / 'build').resolve():
                raise AssertionError('Refusing to remove a release fixture outside build/')
            shutil.rmtree(cls.workspace)

    def test_matching_release_has_complete_structure_and_rendered_pages(self):
        docx_path = self.workspace / 'complete.docx'
        pdf_path = self.workspace / 'complete.pdf'
        render_dir = self.workspace / 'complete-render'
        _write_docx(docx_path)
        _write_pdf(pdf_path)

        report = verify_manual_release(docx_path, pdf_path, render_dir)

        self.assertEqual(report['pdf_pages'], 16)
        self.assertEqual(report['rendered_pages'], 16)
        self.assertEqual(report['missing_required_phrases'], [])
        self.assertEqual(report['missing_docx_bom_ids'], [])
        self.assertEqual(report['missing_pdf_bom_ids'], [])
        self.assertEqual(report['missing_docx_drawing_captions'], [])
        self.assertEqual(report['missing_pdf_drawing_captions'], [])
        self.assertEqual(report['blank_or_tiny_pages'], [])
        self.assertEqual(len(report['render_dimensions']), 16)
        self.assertEqual(report['pdf_metadata']['title'], 'Ugrinsky Wind Wall Bauanleitung')

    def test_missing_content_and_blank_page_are_reported(self):
        docx_path = self.workspace / 'incomplete.docx'
        pdf_path = self.workspace / 'incomplete.pdf'
        render_dir = self.workspace / 'incomplete-render'
        _write_docx(docx_path, lines=('Generator nicht direkt mit dem Akku verbinden.',))
        _write_pdf(
            pdf_path,
            lines=('Generator nicht direkt mit dem Akku verbinden.',),
            pages=2,
            blank_last=True,
        )

        report = verify_manual_release(docx_path, pdf_path, render_dir)

        self.assertIn('DOCX: N_final = N_test * V_ac_target / V_ac_test',
                      report['missing_required_phrases'])
        self.assertIn('PDF: N_final = N_test * V_ac_target / V_ac_test',
                      report['missing_required_phrases'])
        self.assertIn('page-2.png', report['blank_or_tiny_pages'])
        self.assertIn('P01', report['missing_docx_bom_ids'])
        self.assertIn('E01 Gesamtexplosion des Sieben-Stufen-Rotors',
                      report['missing_pdf_drawing_captions'])

    def test_missing_release_artifact_has_a_clear_error(self):
        docx_path = self.workspace / 'source.docx'
        _write_docx(docx_path)

        with self.assertRaisesRegex(FileNotFoundError, 'Released PDF not found'):
            verify_manual_release(docx_path, self.workspace / 'missing.pdf',
                                  self.workspace / 'missing-render')


if __name__ == '__main__':
    unittest.main()
