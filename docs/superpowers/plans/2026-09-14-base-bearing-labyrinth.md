# Base Bearing Labyrinth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a support-free, non-contact labyrinth cup to the rotating Base module that shields the 51105 bearing with 0.4 mm nominal radial clearance from the stationary generator-cover boss.

**Architecture:** Extend the existing `base_bearing_interface()` contract with named labyrinth radii, then construct one annular wall between the unchanged magnet-carrier plate and an enlarged 54 mm rotating load plate. Preserve the stationary cover and bearing geometry, and enforce the interface through point probes, protected-volume checks, assembly collision sweeps, and regenerated release artifacts.

**Tech Stack:** Python 3, CadQuery 2.8/OpenCascade, standard-library `unittest`, existing deterministic STEP/STL and DOCX release pipelines.

**Spec:** `docs/superpowers/specs/2026-09-14-base-bearing-labyrinth-design.md`

## Global Constraints

- The feature is a dirt/splash labyrinth, not a waterproof seal.
- The generator-cover boss remains 48.2 mm OD and unchanged.
- The rotating labyrinth is 49.0 mm ID, 54.0 mm OD, and has 0.4 mm nominal radial clearance per side.
- Preserve the carrier plate diameter, 5.0 mm thickness, bottom elevation, magnet pockets, M8 bore/nut interface, 51105 pilot and axial elevations.
- Preserve one connected Base solid, the current print orientation, and support-free added geometry.
- Physical fit and the 0.4 mm running gap remain unvalidated until a printed hand-rotation test passes.

---

### Task 1: Define and build the rotating labyrinth cup

**Files:**
- Modify: `tests/test_rotor_modules.py:144-240`
- Modify: `src/windwall/generator.py:130-146`
- Modify: `src/windwall/rotor_modules.py:119-194`

**Interfaces:**
- Consumes: `base_bearing_interface(p: DesignParameters) -> dict[str, float]`, `upper_magnet_face_z_mm(p) -> float`, and existing `RotorModuleModel` construction.
- Produces: `base_bearing_interface()` keys `labyrinth_inner_radius_mm` and `labyrinth_outer_radius_mm`; `build_base_module()` returns the integral 49/54 mm labyrinth geometry.

- [ ] **Step 1: Write the failing dimensional and continuity test**

Add this test to `RotorModuleTests` in `tests/test_rotor_modules.py`:

```python
def test_base_has_closed_0_4_mm_bearing_labyrinth(self):
    p = DEFAULT_PARAMETERS
    base = self.modules['base'].shape
    interface = base_bearing_interface(p)
    plate_bottom = upper_magnet_face_z_mm(p)
    plate_top = plate_bottom + p.generator.carrier_disc_thickness_mm

    self.assertAlmostEqual(interface['labyrinth_inner_radius_mm'], 24.5)
    self.assertAlmostEqual(interface['labyrinth_outer_radius_mm'], 27.0)
    self.assertAlmostEqual(
        interface['labyrinth_inner_radius_mm']
        - p.bearings.thrust_housing_seat_diameter_mm / 2 - 3,
        0.4,
    )

    for angle in range(0, 360, 10):
        direction = angle * pi / 180
        wall_radius = 25.5
        x, y = wall_radius * cos(direction), wall_radius * sin(direction)
        for z in (plate_top - 0.1, -7.0, -4.0, interface['shoulder_z_mm'] + 0.1):
            with self.subTest(angle=angle, z=z):
                self.assertTrue(base.val().isInside((x, y, z)))

    upper_plate_probe = (cq.Workplane('XY').circle(26.9).circle(26.0)
                         .extrude(0.2)
                         .translate((0, 0, interface['shoulder_z_mm'] + 0.1)))
    self.assertGreater(base.intersect(upper_plate_probe).val().Volume(), 4)
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_rotor_modules.RotorModuleTests.test_base_has_closed_0_4_mm_bearing_labyrinth -v
```

Expected: `ERROR` for missing `labyrinth_inner_radius_mm` or a failed material probe. Do not change production code until this failure is observed.

- [ ] **Step 3: Add the shared dimensions to the bearing interface**

In `base_bearing_interface()`, derive the fixed-cover radius once and return the two new values:

```python
cover_boss_radius = b.thrust_housing_seat_diameter_mm / 2 + 3
labyrinth_inner_radius = cover_boss_radius + 0.4
labyrinth_outer_radius = 27.0
return {
    # retain every existing key and value
    'boss_clearance_radius_mm': labyrinth_inner_radius,
    'labyrinth_inner_radius_mm': labyrinth_inner_radius,
    'labyrinth_outer_radius_mm': labyrinth_outer_radius,
    # retain the remaining existing keys
}
```

Do not alter `HousingDimensions.radial_clearance_mm`; that value controls the separate cassette pilot.

- [ ] **Step 4: Build the integral wall and enlarged upper plate**

In the Base-only block of `_build()`, use the interface values after the existing stationary-boss clearance cut:

```python
labyrinth_inner = interface['labyrinth_inner_radius_mm']
labyrinth_outer = interface['labyrinth_outer_radius_mm']
body = body.union(_ring(
    labyrinth_outer,
    labyrinth_inner,
    plate_bottom,
    interface['shoulder_top_z_mm'] - plate_bottom,
))
body = body.union(_disc(
    labyrinth_outer,
    shoulder,
    interface['shoulder_top_z_mm'] - shoulder,
))
```

Replace the existing 42 mm shoulder disc union rather than leaving two competing load-plate definitions. Retain the pilot disc, nut cut, shaft cut, magnet-pocket cut, and final `.clean()` operations.

- [ ] **Step 5: Run focused and rotor-module tests and confirm GREEN**

Run:

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_rotor_modules.RotorModuleTests.test_base_has_closed_0_4_mm_bearing_labyrinth tests.test_rotor_modules -v
```

Expected: all listed unittest cases report `OK`. Record a native OCP teardown exit separately if it occurs after `OK`.

- [ ] **Step 6: Commit the focused geometry change**

```powershell
git add src/windwall/generator.py src/windwall/rotor_modules.py tests/test_rotor_modules.py
git commit -m "feat: shield base bearing with labyrinth cup"
```

---

### Task 2: Prove stationary clearance and protected interfaces

**Files:**
- Modify: `tests/test_generator.py:101-125`
- Modify: `tests/test_rotor_modules.py:150-240`
- Modify if the tests expose a defect: `src/windwall/rotor_modules.py`

**Interfaces:**
- Consumes: the two labyrinth-radius keys and Base geometry produced by Task 1; `build_generator_assembly()` and its existing `collision_report()`.
- Produces: regression coverage proving the labyrinth does not contact stationary or protected hardware.

- [ ] **Step 1: Add the failing protected-volume and assembly-clearance tests**

Extend the Base test with a stationary boss keep-out using the exact 24.1 mm cover radius and full overlap height:

```python
cover_boss = (cq.Workplane('XY')
              .circle(p.bearings.thrust_housing_seat_diameter_mm / 2 + 3)
              .circle(12.5)
              .extrude(interface['boss_clearance_top_z_mm']
                       - interface['bearing_floor_z_mm'])
              .translate((0, 0, interface['bearing_floor_z_mm'])))
self.assertLess(base.intersect(cover_boss).val().Volume(), 0.01)
```

Add this assembly-level assertion to `tests/test_generator.py`:

```python
def test_base_labyrinth_clears_stationary_cover_through_rotation(self):
    assembly = build_generator_assembly(DEFAULT_PARAMETERS)
    for angle in range(0, 360, 15):
        rotated = assembly.base_module.shape.rotate((0, 0, 0), (0, 0, 1), angle)
        with self.subTest(angle=angle):
            self.assertLess(rotated.intersect(assembly.cover).val().Volume(), 0.01)
```

Use the existing generator assembly constructor/import spelling already present in the test file; do not introduce a second fixture or duplicate placement logic.

- [ ] **Step 2: Demonstrate that the new tests detect bad clearance**

Temporarily set `labyrinth_inner_radius = cover_boss_radius + 0.3`, run only the new tests, and confirm that at least the 0.4 mm dimensional assertion fails. Restore 0.4 immediately before continuing; do not commit the temporary value.

- [ ] **Step 3: Run the protection and collision suites**

Run:

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_rotor_modules tests.test_generator tests.test_assembly tests.test_generator_housing -v
```

Expected: `OK`, including existing magnet-pocket, carrier-thickness, M8, 51105 contact, stationary-clearance, and seam-continuity tests.

- [ ] **Step 4: Commit the interface regressions**

```powershell
git add tests/test_rotor_modules.py tests/test_generator.py src/windwall/rotor_modules.py
git commit -m "test: verify base labyrinth running clearance"
```

---

### Task 3: Regenerate and audit release geometry

**Files:**
- Modify: `release/v5/stl/base_rotor_module.stl`
- Modify: `release/v5/step/base_rotor_module.step`
- Modify: `release/v5/assembly/generator.step`
- Modify: `release/v5/assembly/rotor_locked.step`
- Modify: `release/v5/assembly/fence_assembly.step`
- Modify: `release/v5/manifest.json`
- Test: `tests/test_exports.py`
- Test: `tests/test_build_v5.py`

**Interfaces:**
- Consumes: `build_base_module(DEFAULT_PARAMETERS)` from Tasks 1–2 and the existing deterministic `scripts/build_v5.py` pipeline.
- Produces: printable and editable V5 Base artifacts plus assemblies and hashes consistent with source geometry.

- [ ] **Step 1: Build into a disposable verification directory**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py scripts\build_v5.py --output-dir build\v5-labyrinth-check
```

Expected stdout: `V5: 8 unique print candidates, 9 coupon solids, 3 STEP assemblies.` A post-output native OCP status may be nonzero and must be recorded separately.

- [ ] **Step 2: Run deterministic export and manifest tests**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_exports tests.test_build_v5 -v
```

Expected: all unittest cases report `OK`; exported Base STL has one component, zero boundary edges, zero non-manifold edges, zero degenerate faces, and positive signed volume.

- [ ] **Step 3: Publish the verified geometry to the tracked V5 release**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py scripts\build_v5.py --output-dir release\v5
```

Confirm `git status --short` changes only the Base artifacts, assemblies, manifest, and any deterministic files that genuinely embed the changed Base.

- [ ] **Step 4: Commit the release artifacts**

```powershell
git add release/v5/stl/base_rotor_module.stl release/v5/step/base_rotor_module.step release/v5/assembly/generator.step release/v5/assembly/rotor_locked.step release/v5/assembly/fence_assembly.step release/v5/manifest.json
git commit -m "release: publish base bearing labyrinth geometry"
```

---

### Task 4: Refresh visible documentation and perform final verification

**Files:**
- Modify if geometry changes are visible: `release/v5/drawings/*.png`
- Modify if figures changed: `release/v5/drawings/figures.json`
- Modify if figures changed: `release/v5/docs/*.docx`
- Modify if release hashes changed: `release/v5/release-index.json`
- Modify as needed: `README.md`
- Test: `tests/test_v5_figures.py`
- Test: `tests/test_v5_manual.py`
- Test: `tests/test_v5_i18n.py`
- Test: `tests/test_release_index.py`
- Test: `tests/test_v5_readme.py`

**Interfaces:**
- Consumes: tracked release geometry and manifest from Task 3.
- Produces: drawings/manuals that show the current Base and explicitly avoid claiming waterproofing; final repository verification evidence.

- [ ] **Step 1: Render the canonical drawings and inspect the changed set**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py scripts\manual\v5_figures.py --output-dir release\v5\drawings
git status --short
```

Inspect E04, E06, E07, E08 and E15 when changed. Confirm the 54 mm rotating cup surrounds but does not intersect the stationary bearing ring, and labels do not call it waterproof.

- [ ] **Step 2: Rebuild manuals only when their embedded drawing hashes changed**

Use the document-runtime Python configured for this workspace:

```powershell
& $documentPython -X utf8 scripts/manual/build_manual.py
& $documentPython -X utf8 scripts/manual/localize_manual.py
```

All six manuals must continue to embed the canonical English E01–E15 drawings. If drawing bytes did not change, leave DOCX files untouched.

- [ ] **Step 3: Refresh the release index and run documentation tests**

Run the repository's existing V5 index command identified in `scripts/index_v5.py --help`, then:

```powershell
& $documentPython -X utf8 -m unittest tests.test_v5_figures tests.test_v5_manual tests.test_v5_i18n tests.test_release_index tests.test_v5_readme -v
```

Expected: all documentation, hash, locale, and README tests report `OK`.

- [ ] **Step 4: Run the complete geometry regression suite**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest discover -s tests -t . -v
```

Read the complete unittest summary. Completion requires zero failures and zero errors; record a native teardown status independently if it occurs after `OK`.

- [ ] **Step 5: Review scope, safety wording, and repository state**

```powershell
git diff --check -- '*.py' '*.md'
git status --short
git log -5 --oneline
```

Confirm there are no placeholders, unrelated files, claims of waterproofing, stale generated hashes, or uncommitted source changes.

- [ ] **Step 6: Commit documentation changes when present**

```powershell
git add README.md release/v5/drawings release/v5/docs release/v5/release-index.json
git commit -m "docs: document base bearing labyrinth"
```

Omit unchanged paths rather than creating a no-op commit. Do not push until the user explicitly requests it or confirms the reviewed final state.
