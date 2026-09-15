# Flat Lower Rotor and Plain Blade Ends Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the lower magnet rotor a completely planar 5 mm print-side disc with a raised bottom-open M8 nut pocket, and remove every blade tongue-and-groove feature so stacked blade walls meet directly while the central bayonet carries all inter-module torque.

**Architecture:** Add one shared lower-carrier-bottom elevation used by both solid construction and clamp hardware, omit the lower rotor's rear ribs/hub, and rebuild its 34 mm hub toward the stator side so the 6.8 mm bottom-open nut pocket remains enclosed. Separately remove blade-seam additions/cuts from module construction, then delete the unused seam subsystem and revise the joint coupon and documentation around plain, phased blade ends.

**Tech Stack:** Python 3, CadQuery 2.8/OpenCascade, standard-library `unittest`, deterministic STEP/STL exporters, Matplotlib CAD drawing pipeline, python-docx/lxml document pipeline.

**Spec:** `docs/superpowers/specs/2026-09-14-flat-lower-rotor-and-plain-blade-ends-design.md`

## Global Constraints

- Lower magnet carrier remains 106 mm diameter and exactly 5 mm thick; do not replace the removed hub/ribs with a 10 mm solid disc.
- The complete exterior support surface of the lower rotor shares one lowest Z plane; only the bottom-open M8 hex recess and shaft bore interrupt that surface.
- Preserve all 18 upper-facing blind magnet pockets, the 12 mm OD integral spacer sleeve, M8 bore, existing nut across-flats clearance and 6.8 mm nut-pocket depth.
- Rebuild the 34 mm central hub only toward the stator-facing side; it must remain inside the 62 mm stationary centre opening.
- Remove blade tongues and grooves from Base, Standard and Top; locked analytic blade walls meet directly at zero nominal axial gap and 60-degree phase.
- The permanent counterclockwise three-lug bayonet is the sole keyed inter-module torque interface and retains its dimensions, detent and locked height.
- Preserve the Base bearing labyrinth, 51105 load path, generator air gaps, module height, blade profile and wall thickness.
- Remove unused seam code, parameters, tests and descriptions; do not leave compatibility stubs or commented-out code.
- Physical stiffness, bridge printability, fit, outdoor use and powered operation remain unvalidated.

---

### Task 1: Flatten the lower magnet rotor and raise its nut pocket

**Files:**
- Modify: `src/windwall/generator.py:94-175,320-340`
- Modify: `tests/test_generator.py:18-180`

**Interfaces:**
- Consumes: `GeneratorParameters.carrier_disc_thickness_mm`, existing `_carrier()`, `lower_magnet_face_z_mm()` and `build_generator_assembly()`.
- Produces: `lower_carrier_bottom_z_mm(p: DesignParameters) -> float`; `_carrier(..., raised_hub: bool = True)`; flat `build_lower_magnet_rotor()` and correctly placed `lower_nut` reference.

- [ ] **Step 1: Add the failing flat-bottom and nut-position tests**

Add `lower_carrier_bottom_z_mm` to the test import and add these assertions to `GeneratorTests`:

```python
def test_lower_rotor_has_one_flat_five_mm_print_side(self):
    p, rotor = DEFAULT_PARAMETERS, self.assembly.lower_rotor
    magnet_face = self.assembly.magnets['lower'].val().BoundingBox().zmax
    expected_bottom = magnet_face - p.generator.carrier_disc_thickness_mm
    self.assertAlmostEqual(lower_carrier_bottom_z_mm(p), expected_bottom, places=6)
    self.assertAlmostEqual(rotor.val().BoundingBox().zmin, expected_bottom, places=6)

    for angle in range(0, 360, 15):
        x, y = 30 * cos(radians(angle)), 30 * sin(radians(angle))
        first_layer = (cq.Workplane('XY').circle(0.5).extrude(0.1)
                       .translate((x, y, expected_bottom)))
        below_bed = first_layer.translate((0, 0, -0.1))
        with self.subTest(angle=angle):
            self.assertGreater(rotor.intersect(first_layer).val().Volume(), 0.05)
            self.assertLess(rotor.intersect(below_bed).val().Volume(), 0.01)

def test_lower_nut_pocket_opens_at_flat_carrier_bottom(self):
    p, assembly = DEFAULT_PARAMETERS, self.assembly
    bottom = lower_carrier_bottom_z_mm(p)
    magnet_face = assembly.magnets['lower'].val().BoundingBox().zmax
    nut = assembly.clamp_hardware['lower_nut']
    self.assertAlmostEqual(nut.val().BoundingBox().zmin, bottom, places=6)
    self.assertLess(nut.intersect(assembly.lower_rotor).val().Volume(), 0.01)
    self.assertGreater(
        nut.translate((0, 0, p.manufacturing.nut_pocket_depth_mm + 0.05))
        .intersect(assembly.lower_rotor).val().Volume(),
        0.05,
    )

    hub = (cq.Workplane('XY').circle(16.9).circle(8.0)
           .extrude(p.generator.carrier_height_mm)
           .translate((0, 0, bottom)))
    self.assertLess(hub.cut(assembly.lower_rotor).val().Volume(), 0.01)
    outside_hub = (cq.Workplane('XY').circle(30.9).circle(17.1)
                   .extrude(4.8).translate((0, 0, magnet_face + 0.1)))
    self.assertLess(
        assembly.lower_rotor.intersect(outside_hub).val().Volume(),
        0.01,
    )
```

Use the existing module-level `cos`, `radians` and `sin` imports. The first test deliberately samples radius 30 mm, outside the M8 pocket and inside the carrier rim.

- [ ] **Step 2: Run the two tests and verify RED**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_generator.GeneratorTests.test_lower_rotor_has_one_flat_five_mm_print_side tests.test_generator.GeneratorTests.test_lower_nut_pocket_opens_at_flat_carrier_bottom -v
```

Expected: missing helper error or a Z-minimum mismatch because the legacy hub/ribs extend 5 mm below the carrier disc.

- [ ] **Step 3: Make rear reinforcement optional and define the bottom elevation**

Change `_carrier` without altering default callers:

```python
def _carrier(p: DesignParameters, radial_ribs: bool = True,
             raised_hub: bool = True) -> cq.Workplane:
    """Local pocket face Z=0; optional reinforcement points toward +Z."""
    _validate(p)
    g, m = p.generator, p.manufacturing
    bore = p.shaft.clearance_hole_diameter_mm / 2
    body = _ring(g.carrier_diameter_mm / 2, bore, 0,
                 g.carrier_disc_thickness_mm)
    if raised_hub:
        body = body.union(_ring(g.carrier_hub_diameter_mm / 2, bore, 0,
                                g.carrier_height_mm))
    # retain radial-rib construction only inside `if radial_ribs`
```

Add the shared elevation beside `lower_magnet_face_z_mm`:

```python
def lower_carrier_bottom_z_mm(p: DesignParameters) -> float:
    """Flat print-side elevation of the five-millimetre lower carrier disc."""
    return lower_magnet_face_z_mm(p) - p.generator.carrier_disc_thickness_mm
```

- [ ] **Step 4: Build the lower rotor from the flat disc and move the pocket**

Use the same mirrored pocket direction but omit rear reinforcement:

```python
face = lower_magnet_face_z_mm(p)
body = _carrier(p, radial_ribs=False, raised_hub=False).mirror('XY').translate((0, 0, face))
rear = lower_carrier_bottom_z_mm(p)
upper_hub = _ring(
    p.generator.carrier_hub_diameter_mm / 2,
    p.shaft.clearance_hole_diameter_mm / 2,
    rear,
    p.generator.carrier_height_mm,
)
body = body.union(upper_hub)
```

Retain the existing spacer sleeve, then cut the unchanged 6.8 mm M8 hex pocket from `rear`. The 10 mm high upper hub starts on the common bottom plane and ends 5 mm above the magnet face, enclosing the pocket roof while remaining inside the 62 mm stator opening. In `build_generator_assembly()`, replace `rear = lower_face-g.carrier_height_mm` with `rear = lower_carrier_bottom_z_mm(p)` so the hardware reference and real pocket share one source of truth.

- [ ] **Step 5: Verify lower rotor, bearing and generator behavior**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_generator tests.test_generator_housing tests.test_bearings -v
```

Expected: all unittest cases report `OK`; record a native process status separately if it occurs after `OK`.

- [ ] **Step 6: Commit the flat rotor**

```powershell
git add src/windwall/generator.py tests/test_generator.py
git commit -m "feat: flatten lower magnet rotor print surface"
```

---

### Task 2: Make every module blade end plain and flush

**Files:**
- Modify: `src/windwall/rotor_modules.py:1-210`
- Modify: `tests/test_rotor_modules.py:1-330`
- Modify: `tests/test_assembly.py`

**Interfaces:**
- Consumes: `build_blade_stage(p)`, the existing three module builders, central bayonet interface, and 60-degree assembly phase.
- Produces: Base/Standard/Top solids with analytic blade walls ending exactly at Z=0 and Z=70 mm and no added/cut blade-seam geometry.

- [ ] **Step 1: Replace seam-feature expectations with a failing plain-end contract**

Remove tests whose sole requirement is tongue/groove dimensions or load sharing. Add a geometry regression at the established outer blade-tip probes, outside the central joint region:

```python
def test_locked_modules_use_plain_flush_blade_ends(self):
    p = DEFAULT_PARAMETERS
    height = p.rotor.stage_height_mm
    for lower_name, upper_name in (
            ('base', 'standard'), ('standard', 'standard'), ('standard', 'top')):
        lower = self.modules[lower_name].shape.val()
        upper = self.modules[upper_name].shape.rotate(
            (0, 0, 0), (0, 0, 1), p.blade.twist_deg
        ).translate((0, 0, height)).val()
        for phase in (p.blade.twist_deg, p.blade.twist_deg + 180):
            angle = phase * pi / 180
            x = 59.5 * cos(angle) - 0.5 * sin(angle)
            y = 59.5 * sin(angle) + 0.5 * cos(angle)
            with self.subTest(pair=(lower_name, upper_name), phase=phase):
                self.assertTrue(lower.isInside((x, y, height - 0.001)))
                self.assertFalse(lower.isInside((x, y, height + 0.001)))
                self.assertFalse(upper.isInside((x, y, height - 0.001)))
                self.assertTrue(upper.isInside((x, y, height + 0.001)))
```

Retain or rewrite the existing locked-adjacency test so it checks coincident corresponding blade cross-sections for Base→Standard, Standard→Standard and Standard→Top at the common interface plane and the 60-degree locked phase.

- [ ] **Step 2: Run the plain-end test and verify RED**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_rotor_modules.RotorModuleTests.test_locked_modules_use_plain_flush_blade_ends -v
```

Expected: current Base/Standard upper tongues and Standard/Top lower grooves produce a nonzero symmetric difference.

- [ ] **Step 3: Remove blade-seam operations from module construction**

In `rotor_modules.py`:

- remove `BladeSeamInterface` and `build_blade_seam` imports;
- remove `seam = build_blade_seam(p)`;
- update the seating comment so it refers only to bayonet insertion and 60-degree phase;
- remove the final union of `seam.tongues`;
- remove the final cut of `seam.groove_clearance`.

Do not alter the female receiver, male bayonet, end guides, shaft cut, Base labyrinth or Top washer plate.

- [ ] **Step 4: Strengthen the direct-interface regression**

For every adjacent pair, retain the existing whole-solid collision check and verify analytic blade slice volumes match across the interface:

```python
source = build_blade_stage(p)
lower_tip = source.intersect(
    cq.Workplane('XY').circle(62).circle(20).extrude(0.05)
    .translate((0, 0, p.rotor.stage_height_mm - 0.05))
)
upper_root = source.rotate(
    (0, 0, 0), (0, 0, 1), p.blade.twist_deg
).translate((0, 0, p.rotor.stage_height_mm)).intersect(
    cq.Workplane('XY').circle(62).circle(20).extrude(0.05)
    .translate((0, 0, p.rotor.stage_height_mm))
)
self.assertAlmostEqual(lower_tip.val().Volume(), upper_root.val().Volume(), places=2)
```

Assert zero nominal stage-height change and retain the existing bayonet locked-angle checks.

- [ ] **Step 5: Run module and assembly suites**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_rotor_modules tests.test_assembly tests.test_bayonet -v
```

Expected: `OK`, with Base/Standard/Top each one connected valid solid and all locked stages at the existing elevations and phases.

- [ ] **Step 6: Commit plain module ends**

```powershell
git add src/windwall/rotor_modules.py tests/test_rotor_modules.py tests/test_assembly.py
git commit -m "feat: join rotor stages with plain blade ends"
```

---

### Task 3: Remove the obsolete blade-seam subsystem and revise coupons

**Files:**
- Delete: `src/windwall/blade_seam.py`
- Delete: `docs/blade-seams.md`
- Create: `docs/plain-blade-ends.md`
- Modify: `src/windwall/parameters.py:50-65,200-212`
- Modify: `src/windwall/drivers.py:1-100`
- Modify: `src/windwall/bayonet.py:1-15`
- Modify: `src/windwall/assembly_validation.py:45-140`
- Modify: `scripts/preview_joint_coupon.py`
- Modify: `tests/test_drivers.py`
- Modify: `tests/test_preview_joint_coupon.py`
- Modify: `tests/test_parameters.py`
- Modify: `tests/test_rotor_modules.py`

**Interfaces:**
- Consumes: plain module behavior from Task 2 and existing `build_joint_coupon()`/`export_coupon()` APIs.
- Produces: seam-free parameters and production imports; combined joint coupon with two plain blade-wall samples; validation metadata describing bayonet-only torque transfer.

- [ ] **Step 1: Write failing coupon and static-cleanup tests**

Replace seam-count expectations in `tests/test_drivers.py` and `tests/test_preview_joint_coupon.py` with:

```python
def test_coupon_uses_plain_blade_samples_without_tongue_or_groove(self):
    coupon = build_joint_coupon(DEFAULT_PARAMETERS)
    self.assertEqual(coupon.blade_sample_count, 2)
    self.assertFalse(hasattr(coupon, 'tongue_count'))
    self.assertFalse(hasattr(coupon, 'groove_count'))

def test_preview_reports_bayonet_only_torque_interface(self):
    with temporary_build_directory() as destination:
        report = export_coupon(DEFAULT_PARAMETERS, destination)
        self.assertNotIn('blade_seam', report)
        self.assertEqual(report['torque_interface'], 'central_bayonet_only')
        self.assertEqual(report['blade_ends'], 'plain_flush_samples')
```

Add `blade_sample_count: int = 0` to the existing `JointCoupon` dataclass and return `blade_sample_count=2` from `build_joint_coupon()`. Add a parameter contract assertion:

```python
self.assertFalse(hasattr(DEFAULT_PARAMETERS, 'blade_seam'))
```

- [ ] **Step 2: Run the focused tests and confirm RED**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_drivers tests.test_preview_joint_coupon tests.test_parameters -v
```

Expected: failures because seam metadata and `DesignParameters.blade_seam` still exist.

- [ ] **Step 3: Simplify the combined joint coupon**

Remove the seam import and tongue union/groove cut from `drivers.py`. Keep two short analytic blade-wall samples attached to the male and female coupon carriers, but terminate both samples at their nominal planes. Replace seam counts in the coupon result with one explicit `blade_sample_count: int = 2` field.

In `scripts/preview_joint_coupon.py`, remove the seam builder import and `blade_seam` report object. Emit:

```python
'torque_interface': 'central_bayonet_only',
'blade_ends': 'plain_flush_samples',
```

Retain bayonet motion samples, M8 calibration pocket, printable solid checks and existing output filenames.

- [ ] **Step 4: Delete unused seam configuration and code**

Remove `BladeSeamParameters` and the `blade_seam` field from `DesignParameters`. Delete `src/windwall/blade_seam.py`. Remove seam-only validation tests and imports rather than weakening them into no-op checks.

Update `bayonet.py` comments to state that module builders add plain blade ends and that the bayonet owns locking and torque transfer. Update `assembly_validation.py` comments and `contact_semantics` to:

```python
'contact_semantics': (
    'Named 51105 washer/support contacts; permanent bayonet stops; '
    'plain flush blade ends without keyed load sharing'
),
```

- [ ] **Step 5: Replace obsolete seam documentation and scan for dead references**

Create `docs/plain-blade-ends.md` describing the 60-degree phase, zero nominal axial gap, bayonet-only torque path and physical inspection requirements. Delete `docs/blade-seams.md`.

Run:

```powershell
rg -n "blade_seam|BladeSeam|tongue_height|groove_depth|transverse_clearance|tongue-and-groove|Nut.?Feder" src tests scripts docs README.md
```

At this task boundary, matches are allowed only in historical dated specs/plans and user-facing README/manual sources scheduled for Task 5. No active Python production/test/preview match may remain.

- [ ] **Step 6: Run coupon, parameter, module and validation tests**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_parameters tests.test_drivers tests.test_preview_joint_coupon tests.test_rotor_modules tests.test_assembly -v
```

Expected: all tests report `OK` and no import references the deleted module.

- [ ] **Step 7: Commit subsystem cleanup**

```powershell
git add src/windwall/parameters.py src/windwall/drivers.py src/windwall/bayonet.py src/windwall/assembly_validation.py scripts/preview_joint_coupon.py tests/test_parameters.py tests/test_drivers.py tests/test_preview_joint_coupon.py tests/test_rotor_modules.py docs/plain-blade-ends.md
git rm src/windwall/blade_seam.py docs/blade-seams.md
git commit -m "refactor: remove keyed blade seam subsystem"
```

---

### Task 4: Regenerate and audit all affected release geometry

**Files:**
- Modify: `release/v5/stl/lower_magnet_rotor.stl`
- Modify: `release/v5/stl/base_rotor_module.stl`
- Modify: `release/v5/stl/standard_rotor_module.stl`
- Modify: `release/v5/stl/top_rotor_module.stl`
- Modify: `release/v5/coupons/joint_female.stl`
- Modify: `release/v5/coupons/joint_male.stl`
- Modify: corresponding files under `release/v5/step/`
- Modify: `release/v5/assembly/generator.step`
- Modify: `release/v5/assembly/rotor_locked.step`
- Modify: `release/v5/assembly/fence_assembly.step`
- Modify: `release/v5/manifest.json`
- Test: `tests/test_exports.py`
- Test: `tests/test_build_v5.py`

**Interfaces:**
- Consumes: flat lower rotor, plain module ends and revised coupon from Tasks 1–3.
- Produces: deterministic V5 STL/STEP/coupon/assembly artifacts and matching manifest hashes.

- [ ] **Step 1: Build a clean disposable release**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py scripts\build_v5.py --output-dir build\v5-flat-plain-check
```

Expected stdout: `V5: 8 unique print candidates, 9 coupon solids, 3 STEP assemblies.` The blade seam has no dedicated release artifact, so removing its code must not change this inventory.

- [ ] **Step 2: Run export and reproducibility tests**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_exports tests.test_build_v5 -v
```

Expected: all unittest cases report `OK`. The four module/lower-rotor STL files and joint coupons each have one component, zero boundary edges, zero non-manifold edges, zero degenerate faces and positive signed volume.

- [ ] **Step 3: Publish from a clean deterministic build**

Build into a new disposable directory, verify its manifest and copy the complete verified generated set into `release/v5` using the established Windows-safe publication process. Do not overwrite STEP files in place when that triggers the repository's reproducible Windows `Errno 22`; document byte equality between verified disposable output and tracked output.

- [ ] **Step 4: Audit geometry-specific requirements**

Record in the task report:

- lower-rotor Z minimum equals `lower_magnet_face_z_mm(p) - 5.0`;
- lower-rotor outer diameter remains 106 mm;
- 18 pockets and full spacer sleeve are present;
- module bounding heights and locked assembly elevations are unchanged;
- no active artifact metadata contains blade tongue/groove counts;
- all manifest SHA-256 values match tracked bytes.

- [ ] **Step 5: Commit release geometry**

```powershell
git add release/v5/manifest.json release/v5/stl release/v5/step release/v5/coupons release/v5/assembly
git commit -m "release: publish flat lower rotor and plain blade ends"
```

Before committing, use `git status --short` and exclude any unchanged or unrelated release files.

---

### Task 5: Update drawings, manuals and public documentation

**Files:**
- Modify: `README.md`
- Modify: `scripts/manual/v5_figures.py`
- Modify: `scripts/manual/manual_data.py`
- Modify: `scripts/manual/locales/*.json`
- Modify: `scripts/manual/localize_manual.py`
- Modify: `tests/test_v5_figures.py`
- Modify: `tests/test_v5_manual.py`
- Modify: `tests/test_v5_i18n.py`
- Modify: `tests/test_v5_readme.py`
- Modify: `release/v5/drawings/*.png`
- Modify: `release/v5/drawings/figures.json`
- Modify: `release/v5/docs/*.docx`
- Modify: `release/v5/audits/*.json`
- Modify: `release/v5/release-index.json`

**Interfaces:**
- Consumes: final release geometry and manifest from Task 4.
- Produces: canonical English drawings, six synchronized manuals, README and release index describing flat lower-rotor printing and bayonet-only module torque transfer.

- [ ] **Step 1: Add failing documentation assertions**

Update active documentation tests to require all of these concepts in English source/README and the appropriate translated manual content:

```text
flat 5 mm lower magnet rotor print surface
bottom-open M8 nut pocket
plain flush blade ends
central bayonet is the sole keyed torque interface
physical stiffness and fit remain unvalidated
```

Remove assertions that require tongue, groove or blade-seam load sharing. Add a repository-source scan test covering `README.md`, active manual source dictionaries and `scripts/manual/v5_figures.py` that rejects the obsolete English and German terms while excluding dated historical plans/specs.

- [ ] **Step 2: Run documentation tests and verify RED**

Use the workspace document runtime:

```powershell
& $documentPython -X utf8 -m unittest tests.test_v5_manual tests.test_v5_i18n tests.test_v5_readme -v
```

Expected: failures against current README/manual wording and pinned source hashes.

- [ ] **Step 3: Revise canonical drawings and prose**

In `v5_figures.py`, replace E02/E03 tongue/groove labels with plain blade-end and bayonet-only labels. Update E05 to show and label the flat print-side carrier, raised bottom-open M8 pocket and upper integral sleeve. Remove `blade_seam` from serialized figure design parameters.

Update README, German manual source and all five locale dictionaries so assembly instructions say to align the bayonet insertion windows, lock counterclockwise, verify flush blade contact and inspect the latch. Do not claim the blade walls transfer torque or that the lower rotor has been strength-tested.

- [ ] **Step 4: Render drawings and rebuild all six manuals**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py scripts\manual\v5_figures.py --output-dir release\v5\drawings
& $documentPython -X utf8 scripts/manual/build_manual.py
& $documentPython -X utf8 scripts/manual/localize_manual.py
```

Update locale source hashes and pinned test hashes through the existing deterministic localization workflow. All manuals must embed the same 15 canonical English engineering drawings.

- [ ] **Step 5: Render and visually verify DOCX pages**

Follow the documents skill's `render_docx.py` workflow for all six manuals. Inspect every rendered page for clipping, missing glyphs, broken tables, stale tongue/groove callouts and incorrect lower-rotor orientation. If the configured LibreOffice renderer is unavailable, record the exact failure in both audit JSON files and do not claim page-level visual approval.

- [ ] **Step 6: Rebuild the release index and run document tests**

```powershell
& $documentPython -X utf8 scripts/index_v5.py --project-root .
& $documentPython -X utf8 -m unittest tests.test_v5_manual tests.test_v5_i18n tests.test_release_index tests.test_v5_readme -v
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_v5_figures -v
```

Expected: all documentation, translation, figure, hash and release-index tests report `OK`.

- [ ] **Step 7: Run the complete final regression suite**

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest discover -s tests -t . -v
```

Read the complete unittest summary and require zero failures/errors. Run the document-runtime suite separately so document tests skipped by the CadQuery runtime are still evidenced. Record any process exit after an `OK` summary separately without guessing its cause.

- [ ] **Step 8: Perform the final dead-code and wording scan**

```powershell
rg -n "blade_seam|BladeSeam|tongue_height|groove_depth|transverse_clearance|tongue-and-groove|Nut.?Feder" src tests scripts README.md docs/plain-blade-ends.md
git diff --check -- '*.py' '*.md' '*.json'
git status --short
```

Expected: no obsolete seam implementation or user-facing claim remains. Dated historical specifications and plans are intentionally outside this active-source scan.

- [ ] **Step 9: Commit synchronized documentation**

```powershell
git add README.md scripts/manual tests/test_v5_figures.py tests/test_v5_manual.py tests/test_v5_i18n.py tests/test_v5_readme.py release/v5/drawings release/v5/docs release/v5/audits release/v5/release-index.json
git commit -m "docs: explain flat lower rotor and plain blade joints"
```

Do not push until the user explicitly requests publication of the reviewed final state.
