"""Verify that a released manual PDF matches the authored DOCX structure.

The verifier does not convert DOCX files.  It accepts an already released PDF,
extracts text from both artifacts, renders every PDF page with Poppler and
returns a deterministic report suitable for tests and release automation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Iterable

from docx import Document
from PIL import Image, ImageChops
import pdfplumber
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.manual.manual_data import load_manual_data


REQUIRED_RELEASE_PHRASES = (
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
    'Generator nicht direkt mit dem Akku verbinden.',
    'N_final = N_test * V_ac_target / V_ac_test',
)

MINIMUM_RELEASE_PAGES = 16
MINIMUM_RENDER_WIDTH_PX = 1000
MINIMUM_RENDER_HEIGHT_PX = 1000


def _normalise_text(text: str) -> str:
    """Make layout-driven line and spacing changes irrelevant to comparison."""

    return re.sub(r'\s+', ' ', text).strip()


def _docx_text(path: Path) -> str:
    document = Document(path)
    return _normalise_text(' '.join(document.element.body.xpath('.//w:t/text()')))


def _pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as document:
        return _normalise_text(' '.join(page.extract_text() or '' for page in document.pages))


def _poppler_executable() -> Path:
    name = 'pdftoppm.exe' if sys.platform == 'win32' else 'pdftoppm'
    discovered = shutil.which(name) or shutil.which('pdftoppm')
    if discovered:
        return Path(discovered)

    # The Codex bundled Python sits in dependencies/python; Poppler is its
    # sibling.  Deriving this from the active interpreter avoids a user path.
    dependencies = Path(sys.executable).resolve().parents[1]
    bundled = dependencies / 'native' / 'poppler' / 'Library' / 'bin' / name
    if bundled.is_file():
        return bundled
    raise FileNotFoundError(
        'Poppler pdftoppm was not found on PATH or beside the active bundled Python runtime'
    )


def _numeric_suffix(path: Path) -> int:
    match = re.search(r'-(\d+)$', path.stem)
    if not match:
        raise ValueError(f'Rendered page has no numeric suffix: {path.name}')
    return int(match.group(1))


def _render_pages(pdf_path: Path, render_dir: Path) -> list[Path]:
    render_dir.mkdir(parents=True, exist_ok=True)
    for stale in (*render_dir.glob('page-*.png'), *render_dir.glob('_poppler-*.png')):
        stale.unlink()

    prefix = render_dir / '_poppler'
    result = subprocess.run(
        [str(_poppler_executable()), '-png', '-r', '150', str(pdf_path), str(prefix)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f'Poppler page rendering failed ({result.returncode}): {detail}')

    generated = sorted(render_dir.glob('_poppler-*.png'), key=_numeric_suffix)
    if not generated:
        raise RuntimeError('Poppler reported success but produced no page images')
    pages = []
    for number, generated_path in enumerate(generated, 1):
        stable_path = render_dir / f'page-{number}.png'
        generated_path.replace(stable_path)
        pages.append(stable_path)
    return pages


def _drawing_captions(data: dict) -> list[str]:
    return [f"{drawing_id} {record['title']}"
            for drawing_id, record in data['drawings'].items()]


def _missing(text: str, expected: Iterable[str]) -> list[str]:
    normalised = _normalise_text(text)
    return [item for item in expected if _normalise_text(item) not in normalised]


def _inspect_renders(paths: Iterable[Path]) -> tuple[list[dict], list[str]]:
    dimensions = []
    blank_or_tiny = []
    for path in paths:
        with Image.open(path) as image:
            width, height = image.size
            dimensions.append({'file': path.name, 'width_px': width, 'height_px': height})
            white = Image.new('RGB', image.size, 'white')
            content_box = ImageChops.difference(image.convert('RGB'), white).getbbox()
            if (width < MINIMUM_RENDER_WIDTH_PX or
                    height < MINIMUM_RENDER_HEIGHT_PX or content_box is None):
                blank_or_tiny.append(path.name)
    return dimensions, blank_or_tiny


def verify_manual_release(docx_path: Path, pdf_path: Path, render_dir: Path) -> dict:
    """Return structural and rendered-page evidence for one manual release."""

    docx_path = Path(docx_path)
    pdf_path = Path(pdf_path)
    render_dir = Path(render_dir)
    if not docx_path.is_file():
        raise FileNotFoundError(f'Authored DOCX not found: {docx_path}')
    if not pdf_path.is_file():
        raise FileNotFoundError(f'Released PDF not found: {pdf_path}')

    data = load_manual_data(ROOT)
    docx_text = _docx_text(docx_path)
    pdf_text = _pdf_text(pdf_path)
    reader = PdfReader(pdf_path)
    pdf_pages = len(reader.pages)
    metadata = reader.metadata or {}

    bom_ids = [*data['printed_parts'], *data['hardware']]
    captions = _drawing_captions(data)
    missing_required = [
        *(f'DOCX: {phrase}' for phrase in _missing(docx_text, REQUIRED_RELEASE_PHRASES)),
        *(f'PDF: {phrase}' for phrase in _missing(pdf_text, REQUIRED_RELEASE_PHRASES)),
    ]
    pages = _render_pages(pdf_path, render_dir)
    render_dimensions, blank_or_tiny = _inspect_renders(pages)

    return {
        'docx_path': str(docx_path.resolve()),
        'pdf_path': str(pdf_path.resolve()),
        'pdf_pages': pdf_pages,
        'rendered_pages': len(pages),
        'render_dimensions': render_dimensions,
        'blank_or_tiny_pages': blank_or_tiny,
        'missing_required_phrases': missing_required,
        'missing_docx_bom_ids': _missing(docx_text, bom_ids),
        'missing_pdf_bom_ids': _missing(pdf_text, bom_ids),
        'missing_docx_drawing_captions': _missing(docx_text, captions),
        'missing_pdf_drawing_captions': _missing(pdf_text, captions),
        'pdf_metadata': {
            'title': metadata.get('/Title'),
            'author': metadata.get('/Author'),
            'subject': metadata.get('/Subject'),
        },
    }


def _has_release_defect(report: dict) -> bool:
    return any((
        report['pdf_pages'] < MINIMUM_RELEASE_PAGES,
        report['pdf_pages'] != report['rendered_pages'],
        report['blank_or_tiny_pages'],
        report['missing_required_phrases'],
        report['missing_docx_bom_ids'],
        report['missing_pdf_bom_ids'],
        report['missing_docx_drawing_captions'],
        report['missing_pdf_drawing_captions'],
    ))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docx', type=Path, required=True)
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--render-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    report = verify_manual_release(args.docx, args.pdf, args.render_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if _has_release_defect(report) else 0


if __name__ == '__main__':
    raise SystemExit(main())
