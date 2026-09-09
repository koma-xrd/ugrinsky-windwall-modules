# Ugrinsky Wind Wall V5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and release the V5 stationary generator housing, removable coil cassette, 51105 thrust-bearing interface, upper 608 fence support, current exploded drawings, and German DOCX manual around the approved V4.3 rotor.

**Architecture:** Keep the V4.3 rotor and both magnet carriers on the rotating M8 shaft while placing the lower magnet rotor inside a stationary 130 mm housing below a keyed stationary coil cassette. A removable stationary cover retains the cassette and supports the 51105; a separate rectangular overhead plate carries a captured 608 bearing. Geometry, assemblies, exports, drawings, and documentation consume one parameter model and one manifest.

**Tech Stack:** Python 3, CadQuery/OCP, `unittest`, existing binary-STL topology audit, python-docx through the bundled document runtime, Matplotlib CAD projections, STEP/STL/PNG/DOCX artifacts.

**Spec:** `docs/superpowers/specs/2026-09-09-generator-housing-v5-design.md`

## Global Constraints

- Preserve the committed V4.3 rotor behavior from `cdd1c2d`: seven stages, CCW permanent snap bayonet, continuous lower female rail, 2.0 mm helical blades, outer tongue/groove, free middle, and Base blade-form reinforcement to the central carrier ring.
- The upper magnet carrier, lower magnet carrier, M8 shaft, shaft nuts, and rotor modules rotate; housing, coil cassette, cover, 51105 housing washer, and upper 608 support remain stationary.
- Place the complete lower magnet rotor inside the generator housing below the coil cassette.
- Model 51105 as 25 × 42 × 11 mm and 608 as 8 × 22 × 7 mm; all printed fits remain coupon-gated prototype values.
- Use nominal 1.5 mm upper and lower magnetic air gaps only for flush or subflush magnets.
- Use six symmetric M4 cover fasteners with captive nuts and four lower wooden-frame mounting tabs.
- Use a side cable outlet in V5 and state explicitly that it is not waterproof.
- Remove the obsolete large Top-Closure from V5 assembly, exports, drawings, and manual.
- Use TDD for every behavior change and record the known native CadQuery/OCP teardown exit separately from Python test results.
- Publish the complete reproducible release under tracked `release/v5/`; use ignored temporary directories only for intermediate renders and test builds.
- Do not claim physical fit, strength, weather sealing, electrical performance, or final winding validation.

---

### Task 1: Bearing References and Fit Coupons

**Files:**
- Create: `src/windwall/bearings.py`
- Modify: `src/windwall/parameters.py`
- Create: `tests/test_bearings.py`
- Modify: `tests/test_parameters.py`

**Interfaces:**
- Produces: `BearingReference`, `FitCoupon`, `build_51105_reference(p)`, `build_608_reference(p)`, `build_51105_fit_coupon(p)`, `build_608_fit_coupon(p)`, and `bearing_fit_manifest(p) -> dict`.
- Consumes: `DesignParameters`, shaft clearances, and manufacturing export tolerances.

- [ ] **Step 1: Write failing dimension and topology tests**

```python
def test_normative_bearing_envelopes_and_coupon_variants():
    thrust = build_51105_reference(DEFAULT_PARAMETERS)
    radial = build_608_reference(DEFAULT_PARAMETERS)
    assert thrust.nominal_dimensions_mm == (25.0, 42.0, 11.0)
    assert radial.nominal_dimensions_mm == (8.0, 22.0, 7.0)
    assert build_51105_fit_coupon(DEFAULT_PARAMETERS).seat_diameters_mm == (42.0, 42.2, 42.4)
    assert build_608_fit_coupon(DEFAULT_PARAMETERS).seat_diameters_mm == (22.0, 22.2, 22.4)
```

- [ ] **Step 2: Run the bearing tests and verify RED**

Run: `$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_bearings tests.test_parameters -q`

Expected: failures because the bearing interfaces and parameters do not exist.

- [ ] **Step 3: Implement explicit bearing dataclasses, reference solids, and three-size coupons**

Use independent shaft/housing washers for the 51105, a sealed-envelope ring for the 608, positive finite validation, 42.2/22.2 mm nominal printed seats, and a 24.8 mm initial rotating 51105 pilot. Every coupon must be one valid connected solid and expose its literal candidate dimensions.

- [ ] **Step 4: Run tests and topology audit**

Expected: all Task 1 assertions pass before the known native teardown exit; exported coupon meshes have one component, zero boundary/nonmanifold/degenerate edges, and positive volume.

- [ ] **Step 5: Commit**

```powershell
git add src/windwall/bearings.py src/windwall/parameters.py tests/test_bearings.py tests/test_parameters.py
git commit -m "feat: model 51105 and 608 bearing fits"
```

### Task 2: Stationary Housing, Coil Cassette, and Cover

**Files:**
- Create: `src/windwall/generator_housing.py`
- Create: `tests/test_generator_housing.py`

**Interfaces:**
- Produces: `GeneratorHousingParts`, `build_generator_housing(p)`, `build_coil_cassette(p)`, `build_generator_cover(p)`, `build_coil_fit_coupon(p)`, and `audit_coil_retention(parts) -> dict`.
- Consumes: generator parameters and `build_51105_reference` from Task 1.

- [ ] **Step 1: Write failing stationary-part tests**

```python
def test_coil_is_supported_centered_keyed_and_cover_retained():
    parts = build_generator_housing(DEFAULT_PARAMETERS)
    audit = audit_coil_retention(parts)
    assert audit['downward_support_contact_mm3'] > 1
    assert audit['radial_clearance_mm'] >= 0.30
    assert audit['anti_rotation_contact_mm3'] > 1
    assert audit['upward_cover_clearance_mm'] <= 0.20
    assert len(parts.bottom_mount_tabs) == 4
    assert len(parts.cover_fasteners) == 6
```

- [ ] **Step 2: Run the focused test and verify RED**

Expected: import failure for `windwall.generator_housing`.

- [ ] **Step 3: Implement the 130 mm cup and removable cassette**

Use a nominal 130 mm outer shell, at least 120 mm internal rotor/cassette envelope, closed floor, four symmetric external tabs, side cable boss, inner cassette shoulder, radial pilot, and one asymmetric key. Keep the cable passage open and label it non-waterproof in metadata.

- [ ] **Step 4: Implement the stationary cover and M4 hardware envelopes**

Use six equally spaced M4 clearance passages and six captive hex pockets outside the rotating/magnetic envelopes. Add the central 42.2 mm 51105 housing seat and retain the cassette without crushing its winding volume.

- [ ] **Step 5: Run focused tests and inspect section dimensions**

Expected: valid single solids, all retention directions proven, fastener access clear, 51105 seat present, and no housing material inside declared rotating keep-outs.

- [ ] **Step 6: Commit**

```powershell
git add src/windwall/generator_housing.py tests/test_generator_housing.py
git commit -m "feat: add stationary generator housing and coil cassette"
```

### Task 3: Integrated Rotating Generator and 51105 Load Path

**Files:**
- Modify: `src/windwall/generator.py`
- Modify: `src/windwall/rotor_modules.py`
- Modify: `src/windwall/assembly.py`
- Modify: `src/windwall/assembly_validation.py`
- Modify: `tests/test_generator.py`
- Modify: `tests/test_assembly.py`

**Interfaces:**
- Produces: revised `GeneratorAssembly` with `rotating_parts`, `stationary_parts`, `bearings`, `air_gap_report()`, and `collision_report()`.
- Consumes: `GeneratorHousingParts` and bearing references from Tasks 1–2.

- [ ] **Step 1: Write failing assembly ownership and placement tests**

```python
def test_lower_rotor_is_inside_housing_below_stationary_coil():
    assembly = build_generator_assembly(DEFAULT_PARAMETERS)
    assert assembly.lower_rotor.val().BoundingBox().zmax < assembly.coil_cassette.val().BoundingBox().zmin
    assert assembly.housing.val().BoundingBox().zmin < assembly.lower_rotor.val().BoundingBox().zmin
    assert assembly.housing.val().BoundingBox().zmax > assembly.lower_rotor.val().BoundingBox().zmax
    assert set(assembly.rotating_parts).isdisjoint(assembly.stationary_parts)
```

- [ ] **Step 2: Verify RED against the legacy reference-only assembly**

Expected: missing ownership collections and incorrect legacy housing semantics.

- [ ] **Step 3: Replace the provisional Base bearing recess with the 51105 interface**

Add a 24.8 mm rotating pilot, 42.2 mm bearing envelope, and load shoulder without blocking the raised M8 nut pocket, magnet pockets, blade-form torque ribs, or free rotor middle.

- [ ] **Step 4: Integrate the lower magnet rotor inside the housing**

Position it below the cassette with 1.5 mm nominal lower magnetic gap, rear-open M8 hex drive, and adequate bottom/nut clearance. Keep the upper carrier integrated into Base above the cassette with 1.5 mm nominal upper gap.

- [ ] **Step 5: Remove Top-Closure from the V5 assembly**

Delete its assembly part, two closure retainers, removal audits, and release count assumptions. Retain only the Top module's compact rotating M8 force plate.

- [ ] **Step 6: Implement collision and bearing-contact audits**

Check every rotating part against every stationary part, excluding only named 51105 washer contacts and the intended bearing support surfaces. Confirm shaft passage and both magnetic gaps from actual solid bounding faces.

- [ ] **Step 7: Run generator and assembly tests**

Expected: ownership, housing containment, bearing contact, air gaps, shaft passage, and collision tests pass; any legacy test describing rotating housing or Top-Closure is removed rather than weakened.

- [ ] **Step 8: Commit**

```powershell
git add src/windwall/generator.py src/windwall/rotor_modules.py src/windwall/assembly.py src/windwall/assembly_validation.py tests/test_generator.py tests/test_assembly.py
git commit -m "feat: integrate enclosed dual-rotor generator"
```

### Task 4: Upper 608 Fence Support

**Files:**
- Create: `src/windwall/top_support.py`
- Create: `tests/test_top_support.py`

**Interfaces:**
- Produces: `TopSupport`, `build_top_support(p)`, `build_top_support_assembly(p)`, and `audit_top_support(p) -> dict`.
- Consumes: the 608 reference from Task 1 and final Top-module/M8 heights from Task 3.

- [ ] **Step 1: Write failing fit, capture, and mounting tests**

```python
def test_608_is_inserted_from_top_and_captured_against_downward_loss():
    support = build_top_support(DEFAULT_PARAMETERS)
    assert support.plate_size_mm == (80.0, 50.0, 12.0)
    assert support.bearing_seat_diameter_mm == 22.2
    assert support.bearing_seat_depth_mm == 7.2
    assert support.bottom_shoulder_mm >= 3.0
    assert len(support.wood_screw_axes) == 4
```

- [ ] **Step 2: Verify RED**

Expected: module import failure.

- [ ] **Step 3: Implement rectangular support and captured bearing seat**

Create the 80 × 50 × 12 mm plate, top-open 22.2 × 7.2 mm seat, bottom shoulder, M8 passage, four symmetric countersunk passages for nominal 4 × 40 mm wood screws, and a non-rotating wood-frame closure reference.

- [ ] **Step 4: Verify radial guidance and axial float**

Assert that the 608 outer ring is captured by plate/frame, the M8 shaft clears, the rotating Top module cannot touch the stationary plate, and the upper bearing is not modeled as the primary axial support.

- [ ] **Step 5: Commit**

```powershell
git add src/windwall/top_support.py tests/test_top_support.py
git commit -m "feat: add overhead 608 fence support"
```

### Task 5: V5 Release Export and Manifest

**Files:**
- Create: `scripts/build_v5.py`
- Modify: `src/windwall/export.py`
- Create: `tests/test_build_v5.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `build_v5(output_dir: Path, p=DEFAULT_PARAMETERS) -> dict` and stable tracked `release/v5/` STEP/STL/manifest layout.
- Consumes: Tasks 1–4 builders and existing topology inspection.

- [ ] **Step 1: Write a failing clean-output export test**

Assert exact filenames for Base, Standard, Top, lower magnet rotor, housing, cassette, cover, top support, all coupons, locked rotor STEP, generator STEP, total assembly STEP, and `manifest.json`. Assert no Top-Closure release file exists.

- [ ] **Step 2: Verify RED**

Expected: `scripts.build_v5` missing.

- [ ] **Step 3: Implement deterministic export order and manifest records**

Each record must contain role (`rotating`, `stationary`, `hardware-reference`, or `coupon`), quantity, dimensions, source builder, topology result, physical-validation flag, and known limitations. Export binary manifold STL and STEP for every printable part.

- [ ] **Step 4: Run export tests in a fresh temporary output directory**

Expected: all files present, every STL manifold, all assemblies importable, manifest ownership consistent, and obsolete Top-Closure absent.

- [ ] **Step 5: Generate the tracked release geometry**

Run the same builder with `release/v5` as the output root. Confirm that the manifest uses repository-relative paths and that no absolute machine path is embedded.

- [ ] **Step 6: Commit**

```powershell
git add scripts/build_v5.py src/windwall/export.py tests/test_build_v5.py .gitignore
git commit -m "build: export complete V5 windwall release"
```

### Task 6: Current Exploded Drawings

**Files:**
- Create: `scripts/manual/v5_figures.py`
- Create: `tests/test_v5_figures.py`
- Output: `release/v5/drawings/E01-E15-*.png`

**Interfaces:**
- Produces: `render_v5_figures(output_dir: Path, p=DEFAULT_PARAMETERS) -> tuple[FigureRecord, ...]` with exactly 15 records.
- Consumes: actual V5 solids and manifest from Task 5.

- [ ] **Step 1: Write failing figure-record tests**

Require 15 unique IDs, minimum 2400 × 1680 pixels, German captions, part/fastener callouts, rotation-state legends, and explicit stationary/rotating classifications.

- [ ] **Step 2: Verify RED**

Expected: missing renderer.

- [ ] **Step 3: Render CAD-derived exploded and section figures**

Create: seven-stage rotor, three module types, bayonet/tongue-groove seam, Base/51105 section, generator explosion, generator section, lower rotor inside housing, cassette retention, cover hardware, side cable outlet, 51105 coupon, 608 coupon, upper support, fence installation, and full assembly. E06/E07 must visibly place the lower magnet rotor below the coil and label housing/cassette/cover as stationary.

- [ ] **Step 4: Audit every image**

Reject clipping, crossing callouts, missing IDs, unreadable type, wrong ownership colors, missing lower rotor, or any image containing the obsolete Top-Closure.

- [ ] **Step 5: Commit renderer and tests**

```powershell
git add scripts/manual/v5_figures.py tests/test_v5_figures.py
git commit -m "docs: render V5 windwall exploded drawings"
```

### Task 7: Current German DOCX Manual

**Files:**
- Create by porting the deterministic builders from `feature/assembly-manual`: `scripts/manual/__init__.py`
- Create by porting the deterministic builders from `feature/assembly-manual`: `scripts/manual/manual_data.py`
- Create by porting the deterministic builders from `feature/assembly-manual`: `scripts/manual/build_manual.py`
- Create: `tests/test_v5_manual.py`
- Modify: `README.md`
- Output: `release/v5/docs/Ugrinsky-Wind-Wall-V5-Bauanleitung.docx`

**Interfaces:**
- Produces: `build_v5_manual(project_root: Path, output_path: Path) -> Path`.
- Consumes: V5 manifest, E01–E15, bearing-fit data, and the approved specification.

- [ ] **Step 1: Bring the existing manual toolchain onto the current branch**

Reuse the deterministic document builders from `feature/assembly-manual` without importing its obsolete geometry claims or generated release files. Resolve data exclusively from the V5 manifest.

- [ ] **Step 2: Write failing structural/manual-content tests**

Require A4/18 mm margins, German language, 13 logical H1 chapters, E01–E15 captions and alt text, all V5 filenames, 51105 and 608 dimensions, exact rotating/stationary ownership, lower rotor below coil inside housing, cassette retention, top-support installation, non-waterproof warning, coil experiment matrix, and direct-battery warning.

- [ ] **Step 3: Verify RED**

Expected: V5 builder/content absent.

- [ ] **Step 4: Run the DOCX artifact marker exactly once immediately before first V5 DOCX authoring**

Use the relocated bundled marker path documented in the prior manual report and the bundled document Python. Record success or failure; never run a second DOCX marker for this artifact.

- [ ] **Step 5: Build the full manual**

Update BOM, print orientation, bearing insertion, generator assembly order, housing mounting, coil-cassette removal, upper wood-frame support, magnets, air gaps, wiring experiments, commissioning, maintenance, troubleshooting, and validation limits. Remove every operational reference to Top-Closure and radial bayonet screws.

- [ ] **Step 6: Run structural and accessibility audits**

Require all tests green, inline images only, meaningful alt text, repeated table headers, black headings, no placeholder text, no internal citation tokens, and metadata matching the V5 title/subject.

- [ ] **Step 7: Render and inspect every page when LibreOffice is available**

Use packaged `render_docx.py --emit_pdf`, inspect every PNG at original resolution, repair clipping/overlaps/orphans, and rerender. If `soffice.exe` remains unavailable, report the PDF/page-QA gate as blocked and deliver only the structurally verified DOCX.

- [ ] **Step 8: Update README and commit**

```powershell
git add scripts/manual/manual_data.py scripts/manual/build_manual.py tests/test_v5_manual.py README.md
git commit -m "docs: publish V5 generator assembly manual"
```

### Task 8: Final Verification, Release Commit, and GitHub Push

**Files:**
- Modify as findings require: only files changed by Tasks 1–7
- Output: stable tracked `release/v5/` release artifacts

**Interfaces:**
- Consumes: every preceding task.
- Produces: final verification report and pushed `master` state.

- [ ] **Step 1: Run all focused suites**

Run bearing, housing, generator, assembly, support, export, figure, and manual tests independently. Capture Python `OK` separately from the known OCP process teardown code.

- [ ] **Step 2: Run the complete project suite**

Run `scripts/run_geometry.py -m unittest discover -s tests -t . -q` with the external reference blade path. Do not call the suite passed unless the unittest summary is complete and contains zero failures/errors.

- [ ] **Step 3: Inspect generated artifacts and repository hygiene**

Check every STL topology record, import every STEP assembly, inspect all 15 drawings, scan DOCX XML, run `git diff --check`, remove obsolete generated Top-Closure files from `release/v5`, and confirm no secrets or machine-specific paths are tracked.

- [ ] **Step 4: Perform independent final review and one fix wave**

Review against every specification section. Correct all Critical and Important findings, rerun their regression tests, and record deferred Minor findings.

- [ ] **Step 5: Commit final source/documentation corrections**

```powershell
git add src scripts tests docs README.md .gitignore release/v5
git commit -m "release: finalize Ugrinsky Wind Wall V5"
```

- [ ] **Step 6: Push the verified branch**

Run: `git push origin master`

Expected: GitHub accepts the update and `origin/master` resolves to the final local commit. Report every released local artifact as a clickable absolute path and state any PDF/physical-validation blockers.
