# Ugrinsky Wind Wall Assembly Manual Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a visually verified German DOCX and PDF construction manual with complete bills of materials, CAD-derived exploded drawings, generator assembly guidance, and an empirical serpentine-coil procedure.

**Architecture:** Extract one deterministic manual data model from the existing design parameters and release manifest, render all technical figures from the actual CAD solids plus explicit schematic overlays, then generate DOCX and PDF from that shared content. Automated audits enforce BOM-to-callout coverage, drawing references, electrical uncertainty labels, and artifact presence; page PNG review provides the final layout gate.

**Tech Stack:** Existing CadQuery/OCP environment, bundled Python runtime with python-docx and Pillow, Matplotlib for CAD projections and schematics, bundled LibreOffice renderer, Poppler, unittest.

**Spec:** `docs/superpowers/specs/2026-09-09-ugrinsky-assembly-manual-design.md`

## Global Constraints

- Write the manual in German for a maker without CAD experience.
- Deliver `output/Ugrinsky-Wind-Wall-Bauanleitung.docx` and `output/pdf/Ugrinsky-Wind-Wall-Bauanleitung.pdf` with identical released content.
- Use the current release manifest and CadQuery sources as the mechanical source of truth.
- Show one base, five standard stages, one top stage, one closure and one separate lower magnet rotor.
- Preserve CCW wind rotation and locking; insertion begins 18 degrees clockwise from the aligned locked pose.
- Use 36 nominal 10 x 2 mm magnets in 18 pockets per rotor, with alternating N-S polarity and opposed attraction.
- Specify 0.50 mm enamelled copper wire and 20 turns only as a test winding, never as the final 48 V winding.
- Do not specify a final winding count, controller, fuse, cable, rectifier or dump-load rating without measured electrical data.
- State that the generator must not be connected directly to the 48 V lead-acid battery.
- Mark physical fit, PLA strength, magnet retention, bearing retention, outdoor service and final electrical performance as unverified.
- Generate figures at print-readable resolution and inspect every rendered page before delivery.

---

### Task 1: Manual data model and coverage contract

**Files:**
- Create: `scripts/manual/__init__.py`
- Create: `scripts/manual/manual_data.py`
- Create: `tests/test_manual_data.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `windwall.parameters.DEFAULT_PARAMETERS`, `build/manifest.json`.
- Produces: `load_manual_data(project_root: Path) -> dict`, stable BOM item IDs `P01` through `P05`, `H01` onward, drawing IDs `E01` onward, and validation helpers used by figure and document builders.

- [ ] **Step 1: Write the failing data-contract tests**

```python
def test_manual_data_matches_release_and_selected_hardware():
    data = load_manual_data(PROJECT_ROOT)
    assert data['dimensions']['loaded_height_mm'] == 487.84
    assert data['printed_parts']['P02']['quantity'] == 5
    assert data['hardware']['H01']['description'] == 'M8 Gewindestange'
    assert data['hardware']['H10']['quantity'] == 36
    assert data['hardware']['H10']['size'] == '10 x 2 mm'

def test_every_bom_item_has_a_drawing_callout():
    data = load_manual_data(PROJECT_ROOT)
    called_out = {item for drawing in data['drawings'].values() for item in drawing['items']}
    assert set(data['printed_parts']) | set(data['hardware']) <= called_out
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_manual_data -v`

Expected: import failure because `scripts.manual.manual_data` does not exist.

- [ ] **Step 3: Implement the centralized data model**

```python
def load_manual_data(project_root: Path) -> dict:
    manifest = json.loads((project_root / 'build/manifest.json').read_text(encoding='utf-8'))
    audit = manifest['assembly_audit']
    return {
        'dimensions': {
            'loaded_height_mm': round(audit['aerodynamic_height_mm'], 2),
            'rod_length_mm': round(audit['shaft_z_bounds_mm'][1] - audit['shaft_z_bounds_mm'][0], 2),
            'air_gap_mm': audit['upper_generator_air_gap_mm'],
        },
        'printed_parts': PRINTED_PARTS,
        'hardware': HARDWARE,
        'drawings': DRAWINGS,
        'validation_status': VALIDATION_STATUS,
    }
```

Define explicit German descriptions, quantities, selection status, source file paths and drawing membership. Include required M8 hardware, twelve radial M3 retainers, two closure screws, bearing/spacer placeholders, 36 magnets, copper wire, insulation, adhesive, rectifier, protection, controller and dump load. Label unresolved ratings as `Nach Messung auswählen`.

- [ ] **Step 4: Add output ignores and validate the model**

Add `/output/` and `/tmp/manual/` to `.gitignore`. Run the Task 1 tests and `git diff --check`.

Expected: all tests pass and the tree has no whitespace errors.

- [ ] **Step 5: Commit**

```powershell
git add .gitignore scripts/manual tests/test_manual_data.py
git commit -m "feat: define assembly manual data model"
```

---

### Task 2: CAD-derived exploded drawings

**Files:**
- Create: `scripts/manual/cad_figures.py`
- Create: `tests/test_manual_cad_figures.py`
- Output: `output/manual-figures/E01-gesamt-explosion.png`
- Output: `output/manual-figures/E02-generator-explosion.png`
- Output: `output/manual-figures/E03-basisrotor.png`
- Output: `output/manual-figures/E04-standardverbindung.png`
- Output: `output/manual-figures/E05-topabschluss.png`
- Output: `output/manual-figures/E06-schnitt-luftspalt.png`

**Interfaces:**
- Consumes: `load_manual_data`, `build_locked_rotor_assembly`, `build_exploded_rotor_assembly`, generator and module builders.
- Produces: `render_cad_figures(project_root: Path, output_dir: Path) -> list[FigureRecord]`, where `FigureRecord` contains drawing ID, path, caption and callout IDs.

- [ ] **Step 1: Write failing rendering and callout tests**

```python
def test_cad_figures_cover_the_mechanical_bom(tmp_path):
    records = render_cad_figures(PROJECT_ROOT, tmp_path)
    assert [record.drawing_id for record in records] == ['E01','E02','E03','E04','E05','E06']
    assert all(record.path.stat().st_size > 50_000 for record in records)
    assert {'P01','P02','P03','P04','P05','H01','H10'} <= {
        item for record in records for item in record.callouts
    }
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_manual_cad_figures -v`

Expected: import failure because `cad_figures.py` does not exist.

- [ ] **Step 3: Implement a reusable projection renderer**

```python
@dataclass(frozen=True)
class FigureRecord:
    drawing_id: str
    path: Path
    caption: str
    callouts: tuple[str, ...]

def project_solids(parts: Sequence[RenderedPart], destination: Path, title: str) -> None:
    """Tessellate real solids, depth-sort triangles and add numbered leaders."""
```

Use one fixed isometric camera, consistent colors for rotor, stationary,
hardware and magnetic parts, and leader labels outside the geometry. Render at
minimum 2200 pixels on the long side. Do not alter production geometry.

- [ ] **Step 4: Build the six mechanical views**

Separate the seven stages cumulatively in E01. E02 separates lower rotor,
generator base, bearing references, stator former/cover and integrated upper
rotor. E04 shows insertion at -18 degrees beside the locked CCW stop and labels
the three lugs, two drivers and two retainers. E06 is a sectional drawing with
the nominal 1.5 mm gaps and flush-magnet condition.

- [ ] **Step 5: Run tests and visually inspect all six PNGs**

Run the Task 2 tests, then inspect every generated PNG at original resolution.
Reject clipped labels, hidden components, ambiguous leaders and unreadable
dimensions.

- [ ] **Step 6: Commit**

```powershell
git add scripts/manual/cad_figures.py tests/test_manual_cad_figures.py
git commit -m "feat: render manual exploded CAD drawings"
```

---

### Task 3: Magnet and serpentine-coil schematics

**Files:**
- Create: `scripts/manual/electrical_figures.py`
- Create: `tests/test_manual_electrical_figures.py`
- Output: `output/manual-figures/E07-magnetpolung.png`
- Output: `output/manual-figures/E08-serpentinenpfad.png`
- Output: `output/manual-figures/E09-wickelschablone.png`
- Output: `output/manual-figures/E10-messaufbau.png`
- Output: `output/manual-figures/E11-ladekette.png`

**Interfaces:**
- Consumes: magnet count/pitch and provisional coil-former envelope from `load_manual_data`.
- Produces: `render_electrical_figures(project_root: Path, output_dir: Path) -> list[FigureRecord]` and `estimate_final_turns(test_turns: int, measured_v_rms: float, target_v_rms: float) -> int`.

- [ ] **Step 1: Write failing topology and calculation tests**

```python
def test_polarity_alternates_and_opposed_faces_attract():
    top, bottom = magnet_polarities(18)
    assert all(top[i] != top[(i + 1) % 18] for i in range(18))
    assert all(top[i] != bottom[i] for i in range(18))

def test_turn_estimate_rounds_up_and_rejects_missing_measurement():
    assert estimate_final_turns(20, 8.0, 60.0) == 150
    with self.assertRaises(ValueError):
        estimate_final_turns(20, 0.0, 60.0)
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_manual_electrical_figures -v`

Expected: import failure because `electrical_figures.py` does not exist.

- [ ] **Step 3: Implement polarity and winding-path models**

```python
def magnet_polarities(count: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if count <= 0 or count % 2:
        raise ValueError('Magnet count must be positive and even')
    top = tuple('N' if index % 2 == 0 else 'S' for index in range(count))
    bottom = tuple('S' if pole == 'N' else 'N' for pole in top)
    return top, bottom

def estimate_final_turns(test_turns: int, measured_v_rms: float, target_v_rms: float) -> int:
    if test_turns <= 0 or measured_v_rms <= 0 or target_v_rms <= 0:
        raise ValueError('Turns and voltages must be positive')
    return math.ceil(test_turns * target_v_rms / measured_v_rms)
```

Generate an 18-leg continuous serpentine path alternating between inner and
outer radii. Show start `A1`, finish `A2`, one unambiguous winding direction and
20 overlaid test turns schematically without implying conductor packing.

- [ ] **Step 4: Render the five electrical figures**

E07 shows both facing rotor maps and the attraction rule. E08 shows the active
radial legs relative to alternating poles. E09 shows a safe board-and-insulated-
pin jig. E10 shows tachometer, multimeter, bridge rectifier only where relevant,
and measurement table fields. E11 shows generator to rectifier to wind charge
controller/dump load to fused 48 V battery bank and explicitly crosses out a
direct generator-to-battery connection.

- [ ] **Step 5: Verify images and tests**

Run Task 3 tests and inspect E07-E11 at original resolution. Confirm polarity is
encoded by both letters and color, all leads are labelled, and no final voltage
or component rating is presented as measured.

- [ ] **Step 6: Commit**

```powershell
git add scripts/manual/electrical_figures.py tests/test_manual_electrical_figures.py
git commit -m "feat: illustrate magnets and serpentine winding"
```

---

### Task 4: German DOCX manual

**Files:**
- Create: `scripts/manual/build_manual.py`
- Create: `tests/test_manual_document.py`
- Output: `output/Ugrinsky-Wind-Wall-Bauanleitung.docx`

**Interfaces:**
- Consumes: manual data and all `FigureRecord` lists.
- Produces: `build_manual(project_root: Path, output_path: Path) -> Path`.

- [ ] **Step 1: Load the bundled document runtime and required instructions**

Use `load_workspace_dependencies`. Read the document skill's
`tasks/create_edit.md`, `tasks/images_figures.md`,
`tasks/headings_numbering.md`, `tasks/tables_spreadsheets.md`,
`tasks/accessibility_a11y.md`, and `tasks/verify_render.md` completely. Run the
required artifact-operation marker exactly once immediately before authoring.

- [ ] **Step 2: Write failing structural-document tests**

```python
def test_manual_contains_required_sections_figures_and_warnings():
    document = Document(OUTPUT_DOCX)
    text = '\n'.join(paragraph.text for paragraph in document.paragraphs)
    assert 'Serpentinen Testwicklung' in text
    assert 'nicht direkt mit dem Akku verbinden' in text
    assert 'N_final = N_test' in text
    assert len(document.inline_shapes) >= 11
    assert len(document.tables) >= 4

def test_all_bom_and_figure_ids_appear_in_document():
    text = extract_docx_text(OUTPUT_DOCX)
    data = load_manual_data(PROJECT_ROOT)
    assert all(item_id in text for item_id in (*data['printed_parts'], *data['hardware']))
    assert all(drawing_id in text for drawing_id in data['drawings'])
```

- [ ] **Step 3: Run the tests and verify RED**

Expected: failure because the DOCX and builder do not exist.

- [ ] **Step 4: Implement the document builder**

Use A4 portrait pages, 18 mm side margins, restrained black/blue technical
styling, Word Title and numbered Heading styles, captions below figures,
repeating BOM table headers, page numbers and descriptive alt text. Use
landscape sections only for drawings or BOM tables that cannot remain readable
in portrait orientation.

Write explicit sequential instructions for printing, coupon checks, magnet dry
layout, generator stack, 20-turn 0.50 mm test winding, enamel preparation,
continuity/resistance checks, RPM/voltage measurements, turn calculation,
potting decision, rotor stacking and commissioning. Include blank measurement
tables rather than invented results.

- [ ] **Step 5: Build and run structural tests**

Generate the DOCX with the bundled Python runtime. Run
`tests/test_manual_document.py` and the packaged heading, image and accessibility
audits. Fix missing alt text, nonrepeating table headers, unresolved IDs or
heading-level errors.

- [ ] **Step 6: Commit source and tests**

```powershell
git add scripts/manual/build_manual.py tests/test_manual_document.py
git commit -m "feat: build German Ugrinsky assembly manual"
```

---

### Task 5: PDF release and full visual QA

**Files:**
- Create: `scripts/manual/verify_manual.py`
- Create: `tests/test_manual_release.py`
- Output: `output/pdf/Ugrinsky-Wind-Wall-Bauanleitung.pdf`
- Output: `tmp/manual/rendered/page-*.png`

**Interfaces:**
- Consumes: final DOCX and bundled render/Poppler paths.
- Produces: `verify_manual_release(docx_path: Path, pdf_path: Path, render_dir: Path) -> dict` containing page count, figure/BOM coverage, missing-text checks and render dimensions.

- [ ] **Step 1: Write failing release tests**

```python
def test_released_pdf_matches_docx_structure_and_has_rendered_pages():
    report = verify_manual_release(DOCX, PDF, RENDER_DIR)
    assert report['pdf_pages'] == report['rendered_pages']
    assert report['pdf_pages'] >= 16
    assert report['missing_required_phrases'] == []
    assert report['blank_or_tiny_pages'] == []
```

- [ ] **Step 2: Run the tests and verify RED**

Expected: failure because no PDF release or verifier exists.

- [ ] **Step 3: Render DOCX and emit PDF**

Run the packaged `render_docx.py` using the absolute bundled runtime paths and
`--emit_pdf`. Copy the verified PDF to the stable `output/pdf/` name. Never use
the user's desktop LibreOffice installation.

- [ ] **Step 4: Implement structural PDF verification**

Use `pypdf` to confirm page count and metadata, `pdfplumber` to extract required
headings/warnings, and Poppler page PNGs to reject blank or implausibly small
pages. Confirm the DOCX and PDF contain the same drawing captions and BOM IDs.

- [ ] **Step 5: Inspect every rendered page at 100 percent**

Review all page PNGs in order. Fix and rerender any clipped tables, overlapping
leaders, orphaned headings, split procedural warnings, missing glyphs, poor
figure scale or inconsistent page numbering. Repeat until every page passes.

- [ ] **Step 6: Run all manual and project tests**

Run all `tests/test_manual_*.py`, then the complete existing 93-test suite with
the supplied reference STL. Record the known native OCP shutdown result
separately from the unittest `OK` result.

- [ ] **Step 7: Final artifact audit and documentation update**

Add a short README section linking the manual outputs and stating their
prototype status. Confirm DOCX, PDF and every final figure exist and are
nonempty. Run `git diff --check` and scan source/document text for placeholders,
unresolved file paths and unsupported final electrical ratings.

- [ ] **Step 8: Commit**

```powershell
git add README.md scripts/manual/verify_manual.py tests/test_manual_release.py
git commit -m "docs: release illustrated Ugrinsky construction manual"
```
