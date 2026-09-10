# Windwall V5.2 Rotor Seams and Visual Publishing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce support-friendly base geometry, explicit load-sharing blade seams, English technical drawings, a realistic ten-rotor fence hero image, the supplied README animation, and six synchronized manuals.

**Architecture:** Keep the existing CadQuery module and release pipelines, but isolate blade-seam construction in explicit helpers based on aerodynamic section faces. Keep one canonical English raster drawing set shared by every localized DOCX, while captions and alt text remain localized through the existing OOXML catalog pipeline. Treat the generated hero PNG and supplied GIF as indexed presentation assets rather than regenerable engineering drawings.

**Tech Stack:** Python 3, CadQuery/OCP, unittest, Matplotlib, python-docx/lxml, deterministic STL/STEP exporters, built-in image generation, Git.

**Spec:** `docs/superpowers/specs/2026-09-10-rotor-seams-and-visuals-v5-2-design.md`

## Global Constraints

- Preserve seven 70 mm rotor stages, 122 mm nominal diameter, the open centre, the M8 shaft, and counterclockwise locking viewed from above.
- Preserve the generator, 51105 and 608 bearing architecture, magnet layout, and four-M4 enclosure design.
- The permanent three-lug bayonet remains the primary module form lock.
- All 15 tracked technical raster drawings use English annotations and are shared by all six manuals.
- README embeds only English technical drawings, the hero PNG, and the supplied GIF.
- Physical strength, fit, balance, output, weather resistance, and safe speed remain explicitly unvalidated.

---

### Task 1: Support-friendly base blade roots

**Files:**
- Modify: `src/windwall/rotor_modules.py`
- Modify: `tests/test_rotor_modules.py`
- Modify: `tests/test_exports.py`

**Interfaces:**
- Consumes: `build_blade_stage(parameters) -> cq.Workplane`, `build_upper_magnet_carrier(parameters) -> cq.Workplane`, `base_bearing_interface(parameters) -> dict`.
- Produces: `_base_blade_support(source: cq.Workplane, plate_bottom_z: float, plate_radius: float, protected_radius: float) -> cq.Workplane` and unchanged `build_base_module(parameters) -> RotorModuleModel`.

- [ ] **Step 1: Add failing solid tests for the unsupported blade-root regions**

  Add probes derived from the actual blade footprint at several heights and require continuous material down to the carrier plate print plane wherever the XY point lies inside the carrier radius. Also assert zero intersection with the shaft bore, nut pocket, bearing-boss keepout, and magnet pockets.

- [ ] **Step 2: Run the focused base tests and capture the expected failures**

  Run `python -m unittest tests.test_rotor_modules.RotorModuleTests.test_base_blade_roots_are_supported_to_plate_print_plane -v` with the project CadQuery runtime. Expected: at least one unsupported probe fails on the current base.

- [ ] **Step 3: Replace the current bottom-face extrusion with an explicit vertical blade support projection**

  Build the support from the two aerodynamic blade section faces, clip it to the carrier plate radius and outside the protected stationary-boss radius, extrude it from the carrier plate bottom to the nominal blade root, union it before the existing protected-volume cuts, and retain one solid.

- [ ] **Step 4: Run rotor and export tests**

  Run `python -m unittest tests.test_rotor_modules tests.test_exports -v`. Expected: all tests report `OK`; document the known post-OK native OCP exit separately if it occurs.

- [ ] **Step 5: Commit the base geometry**

  Commit `src/windwall/rotor_modules.py` and its focused tests with message `fix: support base blade roots from the print plane`.

### Task 2: Explicit two-blade tongue-and-groove seam

**Files:**
- Modify: `src/windwall/parameters.py`
- Modify: `src/windwall/rotor_modules.py`
- Modify: `src/windwall/drivers.py`
- Modify: `tests/test_rotor_modules.py`
- Modify: `tests/test_drivers.py`

**Interfaces:**
- Consumes: the two aerodynamic section faces from `build_blade_stage` and the existing 60-degree `BladeParameters.twist_deg` phase.
- Produces: `build_blade_seam(parameters: DesignParameters) -> BladeSeamInterface`, where `BladeSeamInterface` contains `tongues`, `groove_clearance`, `tongue_count`, `groove_count`, and nominal transverse clearance metadata.

- [ ] **Step 1: Add failing tests for two explicit seam features and their load path**

  Require exactly two connected tongue regions and two matching groove regions, no locked-pose solid overlap, zero axial aerodynamic gap, and nonzero intersection between a small counterclockwise tangential sweep of each tongue and its loaded groove flank.

- [ ] **Step 2: Add failing insertion and parameter-contract tests**

  Require positive finite tongue height, groove depth greater than tongue height, and transverse clearance suitable for the existing PLA prototype. Sample insertion and counterclockwise locking poses, allowing only the already documented elastic latch interference.

- [ ] **Step 3: Implement the dedicated blade-seam builder**

  Extract only the two blade-wall section wires at the seam plane. Extrude the top tongues by the configured height. Create the bottom groove cutter from the same phased wires, enlarged by the configured transverse clearance. Do not collect unrelated horizontal faces from hubs, guides, or receiver floors.

- [ ] **Step 4: Integrate seams with base, standard, top, and joint coupon**

  Give base and standard modules upper tongues; give standard and top modules lower grooves. Update the coupon so both blade seams and the bayonet interface can be measured in one small print.

- [ ] **Step 5: Run joint, module, assembly, and export tests**

  Run `python -m unittest tests.test_drivers tests.test_rotor_modules tests.test_assembly tests.test_exports -v`. Expected: all tests report `OK`.

- [ ] **Step 6: Commit the seam implementation**

  Commit the parameters, builders, and tests with message `fix: define load-sharing blade seams explicitly`.

### Task 3: Rebuild and inspect CAD release artifacts

**Files:**
- Modify: `release/v5/stl/*.stl` where geometry changed
- Modify: `release/v5/step/*.step` where geometry changed
- Modify: `release/v5/coupons/*`
- Modify: `release/v5/assembly/*.step`
- Modify: `release/v5/manifest.json`

**Interfaces:**
- Consumes: current CAD builders and deterministic export utilities.
- Produces: updated V5 release geometry and manifest hashes.

- [ ] **Step 1: Run the canonical geometry release builder**

  Run `python scripts/run_geometry.py scripts/build_v5.py --output-dir release/v5` with `PYTHONPATH=src;.` and the project CadQuery Python.

- [ ] **Step 2: Validate all generated bodies and assemblies**

  Run `python -m unittest tests.test_build_v5 tests.test_exports tests.test_preview_modules tests.test_preview_assembly -v`. Expected: all tests report `OK`.

- [ ] **Step 3: Inspect base and seam geometry visually**

  Render or export focused base and two-stage joint previews. Inspect support continuity, both seam pairs, open centre, protected volumes, and locked blade continuity.

- [ ] **Step 4: Commit the generated geometry**

  Commit release geometry and manifest with message `build: regenerate V5.2 rotor artifacts`.

### Task 4: Create presentation media

**Files:**
- Create: `release/v5/media/windwall-fence-hero.png`
- Create: `release/v5/media/ugrinsky_windwall_10_rotors.gif`
- Modify: `tests/test_release_index.py`

**Interfaces:**
- Consumes: the user-supplied GIF at `C:/Users/fi87roy/Downloads/ugrinsky_windwall_10_rotors.gif` and the approved visual brief.
- Produces: a realistic, landscape-oriented hero PNG and byte-identical tracked GIF.

- [ ] **Step 1: Add failing media inventory tests**

  Require both files, a landscape hero image large enough for README and A4 use, byte identity between the supplied and tracked GIF, and release-index coverage.

- [ ] **Step 2: Generate the realistic hero image**

  Use the built-in image generator with a modern house, planted garden, broad landscape, and one plausible fence run containing ten slim vertical helical Ugrinsky rotors. Avoid labels, logos, impossible mechanics, unsafe close-up people, or claims of certified performance.

- [ ] **Step 3: Copy the supplied GIF unchanged**

  Copy the binary into `release/v5/media/ugrinsky_windwall_10_rotors.gif` and verify identical SHA-256 hashes.

- [ ] **Step 4: Inspect the hero image at original resolution**

  Confirm ten visible rotor positions, a credible fence context, uncluttered composition, no text artifacts, and sufficient negative space for cropping.

- [ ] **Step 5: Commit presentation media**

  Commit both assets and inventory tests with message `docs: add ten-rotor windwall presentation media`.

### Task 5: Convert E01-E15 to canonical English drawings

**Files:**
- Modify: `scripts/manual/v5_figures.py`
- Modify: `tests/test_v5_figures.py`
- Modify: `release/v5/drawings/E01-*.png` through `E15-*.png`
- Modify: `release/v5/drawings/figures.json`

**Interfaces:**
- Consumes: current CAD assemblies, manifest values, and drawing scenes.
- Produces: exactly 15 English raster drawings and a manifest field `raster_language: "en-GB"`.

- [ ] **Step 1: Add failing tests rejecting German raster annotations**

  Inspect the generated Matplotlib text objects and require English titles, notes, legend labels, and callouts. Require exactly 15 records and `raster_language == "en-GB"`.

- [ ] **Step 2: Move all drawing copy into one English label catalogue**

  Replace German literals in scene rendering with stable English text. Keep drawing IDs, filenames, dimensions, colours, camera framing, and engineering values stable unless the changed geometry requires reframing.

- [ ] **Step 3: Regenerate E01-E15 and inspect every image**

  Run `python scripts/manual/v5_figures.py`, then inspect all 15 PNGs for clipping, untranslated German, stale geometry, legibility, and correct callout targets.

- [ ] **Step 4: Run figure tests and commit**

  Run `python -m unittest tests.test_v5_figures -v`. Commit source, tests, PNGs, and `figures.json` with message `docs: publish canonical English assembly drawings`.

### Task 6: Rebuild README and six manuals

**Files:**
- Modify: `README.md`
- Modify: `scripts/manual/build_manual.py`
- Modify: `scripts/manual/manual_data.py`
- Modify: `scripts/manual/localize_manual.py`
- Modify: `scripts/manual/locales/*.json`
- Modify: `tests/test_v5_manual.py`
- Modify: `tests/test_v5_i18n.py`
- Modify: `tests/test_v5_readme.py`
- Modify: `release/v5/docs/*.docx`
- Modify: `release/v5/audits/manual.json`
- Modify: `release/v5/audits/manual-translations.json`

**Interfaces:**
- Consumes: the canonical English E01-E15 files, hero PNG, GIF path, and localized text catalogues.
- Produces: six manuals sharing identical technical and hero image bytes plus an English-only visual README.

- [ ] **Step 1: Add failing documentation tests**

  Require the hero as the first major visual in all manuals, identical embedded E01-E15 and hero media across locales, localized captions and alt text, no statement about German raster annotations, and README references only to English drawings plus the hero and GIF.

- [ ] **Step 2: Add the hero to the German source manual builder**

  Place it after title/subtitle and prototype warning, before the detailed assembly diagram. Add a factual caption describing the ten-rotor fence concept without safety or performance claims.

- [ ] **Step 3: Update localization source bindings and catalogues**

  Refresh the source hash and full text catalogues. Keep the shared raster bytes unchanged during localization, translate the hero caption and alternative description, and update the audit wording to say the drawings are English.

- [ ] **Step 4: Update the English README**

  Place the hero directly below the opening prototype statement, then embed the supplied GIF. Replace the existing German E15/E06 references with their canonical English counterparts and explain that all manuals share English engineering drawings.

- [ ] **Step 5: Build and audit all six DOCX files**

  Use the bundled document Python to rebuild German, English, Chinese, Hindi, Spanish, and French DOCX files. Run accessibility audits, canonical package checks, image-hash checks, and deterministic rebuild checks.

- [ ] **Step 6: Render and inspect every DOCX page if the bundled renderer exists**

  Use the packaged `render_docx.py` only. Inspect all pages at 100 percent. If bundled `soffice.exe` remains unavailable, record the blocked rendering state without using desktop LibreOffice.

- [ ] **Step 7: Run documentation tests and commit**

  Run the bundled document Python with `tests.test_v5_manual tests.test_v5_i18n tests.test_v5_readme -v`. Commit manuals, audits, README, catalogs, and builders with message `docs: add English visuals to every V5.2 manual`.

### Task 7: Final release index, review, and publication

**Files:**
- Modify: `release/v5/release-index.json`
- Modify: `README.md` only if final audit wording needs correction

**Interfaces:**
- Consumes: all committed V5.2 geometry, drawings, presentation media, manuals, audits, and catalogues.
- Produces: one hash-complete portable release and a reviewed Git branch.

- [ ] **Step 1: Regenerate the release index**

  Run the bundled document Python with `scripts/index_v5.py`. Require every release file, including hero and GIF, to have current size and SHA-256 metadata.

- [ ] **Step 2: Run the complete test suite**

  Run the CadQuery Python with `python -m unittest discover -s tests -v`, then run the document-runtime suite separately so no tests are skipped for missing python-docx/lxml dependencies.

- [ ] **Step 3: Run final consistency checks**

  Run `git diff --check` for authored text, verify no merge conflicts, inspect `git status`, and compare tracked GIF hash with the supplied source.

- [ ] **Step 4: Request independent code review**

  Review source, tests, generated manifests, image-language policy, and documentation claims against the V5.2 spec. Fix every Critical or Important finding and rerun affected tests.

- [ ] **Step 5: Commit and push**

  Commit remaining release-index changes with message `release: publish Windwall V5.2`, push the feature branch, and update or create the GitHub pull request against `master`.
