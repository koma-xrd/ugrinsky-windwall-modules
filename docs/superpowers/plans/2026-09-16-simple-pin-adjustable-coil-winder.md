# Simple Pin-Adjustable Coil Winder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing cam/rib/frame winding tool with a screwless PLA coil wheel adjustable from 100 to 200 mm by six pin-mounted shoes, plus a free-running upright wire-roll turntable.

**Architecture:** Preserve the existing tooling package boundaries but replace their internals: `winding_head.py` becomes the wheel/shoe unit, `winding_frame.py` becomes the compact two-608 stand with printed shaft and crank, and `wire_payoff.py` becomes a brake-free 51105 turntable. Assembly, service audits, exporters, drawings, tests, documentation, BOM, and generated release are rebuilt around only the simplified parts; the V5 production exporter remains untouched.

**Tech Stack:** Python 3, CadQuery/OCP, unittest, deterministic STL/STEP/JSON export, Matplotlib drawings.

**Spec:** `docs/superpowers/specs/2026-09-16-simple-pin-adjustable-coil-winder-design.md`

## Global Constraints

- The previous cam, ribs, sliders, followers, clamps, two-upright frame, metal shaft hardware, and brake are superseded and must not remain in production code, BOM, documentation, drawings, or `release/winding-tool`.
- All printed parts use PLA and assemble without screws, nuts, threaded rods, metal shafts, or adhesive.
- Purchased hardware is exactly two 608 bearings and one 51105 thrust bearing unless a reviewed test proves an additional non-fastener item necessary.
- Nominal wheel settings are exactly 100 through 200 mm inclusive in 10 mm diameter steps.
- Six identical shoes provide 18 clear tape passages, each 12 mm wide for 10 mm tape.
- The platter is 150 mm diameter with an integral 15 mm diameter x 20 mm pilot and no brake.
- Every print master fits a 220 x 220 mm bed in its documented orientation.
- The exact guide sentence `Akkuschrauberbetrieb ist nicht freigegeben` is mandatory.
- Physical fit, fatigue, strength, enamel protection, dimensional accuracy, and production use remain explicitly unvalidated.
- `src/windwall/export.py`, `scripts/build_v5.py`, `release/v5/**`, and `PRINT_SOURCES` must remain unchanged.
- Geometry commands use `C:\Users\fi87roy\Documents\GitHub\windwall\.venv\Scripts\python.exe` with `PYTHONPATH` set to the active worktree root and `src`.
- The OCP wrapper may exit with status 1 after unittest reports `OK`; reports must distinguish unittest outcome from native teardown status.

## File responsibility map

- `src/windwall/winding_tool_parameters.py`: immutable dimensions/counts and strict validation for the simplified system only.
- `src/windwall/winding_head.py`: one wheel master, one reusable shoe master, diameter state, placement, tape geometry, and release placement.
- `src/windwall/winding_frame.py`: screwless base/tower, two bearing retainers, printed shaft, snap collars, crank, and grip.
- `src/windwall/wire_payoff.py`: brake-free base, printed spindle, 51105 placement, and platter.
- `src/windwall/winding_tool_assembly.py`: the two assemblies, ownership, collision/engagement audits, and BOM.
- `src/windwall/winding_tool_service.py`: forward coil-removal and tool-free latch/service-path audits only.
- `src/windwall/winding_tool_export.py`: simplified inventory, assemblies, manifest, BOM, documentation, and drawing publication.
- `scripts/preview_winding_tool.py`: reference, size-range, exploded, and operating/removal drawings.
- `docs/serpentine-coil-winding-tool-de.md`: German print, assembly, use, release, safety, and prototype guide.
- `release/winding-tool/**`: generated artifacts only; no stale superseded files.

---

### Task 1: Replace the parameter contract

**Files:**
- Modify: `src/windwall/winding_tool_parameters.py`
- Modify: `tests/test_winding_tool_parameters.py`

**Interfaces:**
- Consumes: no tooling implementation.
- Produces: `WindingToolParameters`, `validate_winding_tool_parameters(p)`, `diameter_settings_mm(p) -> tuple[float, ...]`.

- [ ] **Step 1: Replace old parameter expectations with a failing simplified contract test**

```python
def test_defaults_describe_simple_pin_wheel_and_free_payoff(self):
    p = WindingToolParameters()
    self.assertEqual(diameter_settings_mm(p), tuple(range(100, 201, 10)))
    self.assertEqual((p.spoke_count, p.shoe_pin_count, p.tape_station_count), (6, 2, 18))
    self.assertEqual((p.tape_clearance_mm, p.release_clearance_mm), (12.0, 2.0))
    self.assertEqual((p.platter_diameter_mm, p.spool_pilot_diameter_mm,
                      p.spool_pilot_height_mm), (150.0, 15.0, 20.0))
    self.assertFalse(hasattr(p, 'cam_track_eccentricity_mm'))
    self.assertFalse(hasattr(p, 'brake_max_travel_mm'))
```

- [ ] **Step 2: Run the test and prove RED**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_parameters.WindingToolParameterTests.test_defaults_describe_simple_pin_wheel_and_free_payoff -v`

Expected: FAIL because old cam/brake fields exist and the new fields/helper do not.

- [ ] **Step 3: Implement the minimal immutable parameter model**

Use explicit fields for `minimum_diameter_mm=100.0`, `maximum_diameter_mm=200.0`, `diameter_step_mm=10.0`, `spoke_count=6`, `shoe_pin_count=2`, `tape_station_count=18`, `tape_clearance_mm=12.0`, `release_clearance_mm=2.0`, `platter_diameter_mm=150.0`, `spool_pilot_diameter_mm=15.0`, `spool_pilot_height_mm=20.0`, `print_bed_mm=220.0`, and only dimensions actually consumed by later builders. Delete cam, follower, slider, rib, metal-fastener, and brake parameters.

```python
def diameter_settings_mm(p: WindingToolParameters) -> tuple[float, ...]:
    count = int(round((p.maximum_diameter_mm - p.minimum_diameter_mm)
                      / p.diameter_step_mm))
    return tuple(p.minimum_diameter_mm + index * p.diameter_step_mm
                 for index in range(count + 1))
```

- [ ] **Step 4: Add strict validation regressions**

Test that dimensions reject strings, `None`, booleans, zero, negative, NaN, and infinity; counts reject floats and booleans; range divisibility is exact; `spoke_count == 6`, `shoe_pin_count == 2`, `tape_station_count == 18`; and the maximum contact envelope does not exceed the bed.

- [ ] **Step 5: Run the complete parameter module**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_parameters -v`

Expected: all tests report `OK`.

- [ ] **Step 6: Commit**

```powershell
git add -- src/windwall/winding_tool_parameters.py tests/test_winding_tool_parameters.py
git commit -m "refactor: define simple coil wheel parameters"
```

---

### Task 2: Replace the cam head with the pin-adjustable wheel and shoes

**Files:**
- Rewrite: `src/windwall/winding_head.py`
- Rewrite: `tests/test_winding_head.py`

**Interfaces:**
- Consumes: `WindingToolParameters`, `diameter_settings_mm`.
- Produces: `WindingHeadState(diameter_mm, shoe_radius_mm, release_radius_mm)`, `WindingHeadParts(wheel, shoe_master, shoes, state, metadata)`, `build_winding_head(p, diameter_mm, released=False)`, `tape_station_angles(p)`.

- [ ] **Step 1: Write failing tests for all eleven physical settings**

```python
def test_six_identical_shoes_define_each_requested_envelope(self):
    p = WindingToolParameters()
    for diameter in diameter_settings_mm(p):
        head = build_winding_head(p, diameter)
        self.assertEqual(len(head.shoes), 6)
        self.assertTrue(all(shoe.val().isValid() for shoe in head.shoes))
        self.assertAlmostEqual(head.state.diameter_mm, diameter)
        self.assertAlmostEqual(head.state.shoe_radius_mm * 2.0, diameter)
        self.assertEqual(len({shape_signature(s) for s in head.shoes}), 1)
```

- [ ] **Step 2: Prove RED because the current cam/rib builder has the wrong interface**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_head.WindingHeadTests.test_six_identical_shoes_define_each_requested_envelope -v`

Expected: FAIL on missing `shoe_master`/`shoes` state.

- [ ] **Step 3: Build one printable six-spoke wheel**

Create a single valid solid with a central polygonal drive socket, six load-bearing spokes, two keyed radial hole rows per spoke, eleven marked positions, rear latch access, and rounded transitions. Position holes at 5 mm radial increments and engrave `100` through `200` from `diameter_settings_mm(p)`.

- [ ] **Step 4: Build one reusable contact-shoe master**

The shoe has two integral keyed pins, low-deflection PLA snap tabs, a shallow convex rounded contact face, and three physical 12 mm tape passages. Fillet every final wire-contact boundary after cuts. Do not use a living hinge or separate retainer.

- [ ] **Step 5: Place six rigid copies without reshaping the master**

Rotate/translate the same master at 60 degree increments. The master geometry and signature remain invariant across all eleven settings; only placement changes.

- [ ] **Step 6: Add negative and release regressions**

Cover mismatched shoe indices, missing pins, rotated shoes, blocked tape slots, sharp final mouth edges, and release placement. At 100, 150, and 200 mm, released shoes must reduce the radial support envelope by at least 2 mm without crossing the wheel hub.

- [ ] **Step 7: Run the full head module**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_head -v`

Expected: all tests report `OK` and no old cam/rib/slider assertions remain.

- [ ] **Step 8: Commit**

```powershell
git add -- src/windwall/winding_head.py tests/test_winding_head.py
git commit -m "feat: add pin-adjustable coil wheel"
```

---

### Task 3: Replace the frame with the screwless stand, printed shaft, and crank

**Files:**
- Rewrite: `src/windwall/winding_frame.py`
- Rewrite: `tests/test_winding_frame.py`

**Interfaces:**
- Consumes: `WindingHeadParts`, existing 608 reference dimensions from `DesignParameters`.
- Produces: `WindingFrameParts(base, tower, bearing_retainers, bearings, shaft, snap_collars, crank, grip, metadata)`, `build_winding_frame(tool_parameters, design_parameters)`.

- [ ] **Step 1: Write the failing hardware-free frame inventory test**

```python
def test_frame_is_screwless_and_uses_two_608_bearings(self):
    frame = build_winding_frame(WindingToolParameters(), DesignParameters())
    self.assertEqual(len(frame.bearings), 2)
    self.assertEqual(len(frame.snap_collars), 2)
    self.assertFalse(any('bolt' in name or 'nut' in name or 'washer' in name
                         for name in frame.metadata['owned_members']))
    self.assertEqual(frame.metadata['shaft_material'], 'printed PLA')
```

- [ ] **Step 2: Prove RED against the old two-upright metal-shaft frame**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_frame.WindingFrameTests.test_frame_is_screwless_and_uses_two_608_bearings -v`

Expected: FAIL on old hardware inventory and shaft material.

- [ ] **Step 3: Build the base and single bearing tower**

Use positive snap joints between base and tower, two adjacent 608 seats, removable snap retainers for both outer rings, rear access to shoe latches, a full crank-sweep envelope, and stable clamp lands. Keep each master inside the print bed.

- [ ] **Step 4: Build the printed shaft and axial retention**

Use two 8 mm bearing journals, enlarged approximately 14 mm shoulders outside the bearing span, polygonal wheel/crank interfaces, and two accessible removable snap collars. Prove bidirectional axial restraint while avoiding axial load across the 608 seals.

- [ ] **Step 5: Build the screwless hand crank and rotating grip**

The crank engages the shaft by a positive polygonal drive and uses an integral snap feature. The grip rotates on a printed journal and has a removable snap end. Do not include a hex-bit or powered-drive interface.

- [ ] **Step 6: Add physical negative tests**

Reject missing bearing retainers, displaced bearings, a translated shaft, disengaged polygonal drive, inaccessible snap collars, base/tower separation, crank collision through 360 degrees, and an 8 mm journal weakened by a cross-hole.

- [ ] **Step 7: Run the frame module**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_frame -v`

Expected: all tests report `OK`.

- [ ] **Step 8: Commit**

```powershell
git add -- src/windwall/winding_frame.py tests/test_winding_frame.py
git commit -m "feat: add screwless printed wheel stand"
```

---

### Task 4: Simplify the payoff to a free-running upright turntable

**Files:**
- Rewrite: `src/windwall/wire_payoff.py`
- Rewrite: `tests/test_wire_payoff.py`

**Interfaces:**
- Consumes: existing 51105 reference dimensions from `DesignParameters` and platter/pilot parameters.
- Produces: `WirePayoffParts(base, spindle, lower_washer, bearing, upper_washer, platter, metadata)`, `build_wire_payoff(tool_parameters, design_parameters)`.

- [ ] **Step 1: Write a failing brake-free interface test**

```python
def test_payoff_is_free_running_and_contains_no_brake_parts(self):
    parts = build_wire_payoff(WindingToolParameters(), DesignParameters())
    self.assertEqual(parts.platter.val().BoundingBox().xlen, 150.0)
    self.assertEqual(parts.metadata['pilot'], {'diameter_mm': 15.0, 'height_mm': 20.0})
    self.assertNotIn('brake', ' '.join(parts.metadata['owned_members']).lower())
    self.assertFalse(hasattr(parts, 'adjuster'))
```

- [ ] **Step 2: Prove RED against the existing brake assembly**

Run: `python scripts/run_geometry.py -m unittest tests.test_wire_payoff.WirePayoffTests.test_payoff_is_free_running_and_contains_no_brake_parts -v`

Expected: FAIL because adjuster/felt/spring members still exist.

- [ ] **Step 3: Build the screwless base and spindle**

The base positively supports the lower 51105 washer, retains a removable printed spindle without threads, exposes the bearing for service, and provides stable clamp lands. No brake pocket, spring seat, screw access, or adjuster slot remains.

- [ ] **Step 4: Build the removable platter**

The 150 mm platter loads the upper washer, clears the stationary base through full rotation, and includes the 15 x 20 mm chamfered pilot. Use a tool-free axial snap/plug interface that does not clamp the bearing stack.

- [ ] **Step 5: Add ownership, stability, and negative tests**

Verify distinct 51105 washers, axial load faces, radial pilot support, positive volume, free rotation, no rigid collision, accessible removal, and rejection of displaced washers, undersized base footprint, or a retained brake member.

- [ ] **Step 6: Run the payoff module**

Run: `python scripts/run_geometry.py -m unittest tests.test_wire_payoff -v`

Expected: all tests report `OK`.

- [ ] **Step 7: Commit**

```powershell
git add -- src/windwall/wire_payoff.py tests/test_wire_payoff.py
git commit -m "refactor: simplify free-running wire payoff"
```

---

### Task 5: Rebuild assemblies, service audits, and BOM; remove obsolete mechanics

**Files:**
- Rewrite: `src/windwall/winding_tool_assembly.py`
- Rewrite: `src/windwall/winding_tool_service.py`
- Rewrite: `tests/test_winding_tool_assembly.py`
- Modify: `docs/winding-tool-assembly.md`

**Interfaces:**
- Consumes: new head, frame, and payoff part records.
- Produces: `WindingToolAssemblies(winding_jig, wire_payoff, ownership, parameters, audit)`, `build_winding_tool_assemblies(...)`, `audit_winding_tool_assemblies(model) -> dict[str, bool]`, `coil_removal_stages(model)`, `audit_winding_tool_service(model)`, `winding_tool_bom(model)`.

- [ ] **Step 1: Write a failing assembly/BOM inventory test**

```python
def test_bom_contains_only_simple_wheel_and_free_payoff(self):
    model = build_winding_tool_assemblies()
    names = {row['name'] for row in winding_tool_bom(model)}
    self.assertIn('608 bearing', names)
    self.assertIn('51105 thrust bearing', names)
    self.assertFalse(any(token in name.lower() for name in names
                         for token in ('cam', 'rib bolt', 'follower', 'brake', 'm3', 'm4', 'm8')))
```

- [ ] **Step 2: Prove RED on stale old assembly ownership**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_assembly.WindingToolAssemblyTests.test_bom_contains_only_simple_wheel_and_free_payoff -v`

Expected: FAIL because old hardware and brake rows are present.

- [ ] **Step 3: Assemble the vertical wheel and independent payoff**

Place every printed and purchased member explicitly. Ownership must cover each member exactly once and identify rotating versus stationary groups. No old compatibility adapter remains.

- [ ] **Step 4: Replace old audits with simplified physical audits**

Audit all eleven settings for equal shoe placement, tape access, wheel/stand collision, bearing engagement, shaft restraint, crank sweep, print envelope, platter clearance, and 51105 washer ownership. Build winding surrogates at 100, 150, and 200 mm.

- [ ] **Step 5: Implement the full release path**

`coil_removal_stages(model)` must include wound, latched, inward-released, and forward-withdrawn states. Prove at least 2 mm radial clearance and collision-free forward withdrawal; add negative tests for one shoe left latched and an obstruction in front of the wheel.

- [ ] **Step 6: Replace the BOM and assembly documentation**

List printed quantities plus exactly two 608 and one 51105. Remove all screw/nut/washer/shaft/brake instructions. Document snap order, latch access, PLA wear inspection, and hand-only use.

- [ ] **Step 7: Delete dead old helpers and verify absence**

Run: `rg -n "cam|follower|slider|brake|M3|M4|M8|metal shaft" src/windwall/winding_* src/windwall/wire_payoff.py docs/winding-tool-assembly.md`

Expected: no production references except explicit negative compatibility assertions or migration prose.

- [ ] **Step 8: Run the assembly and service tests**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_assembly -v`

Expected: all tests report `OK`.

- [ ] **Step 9: Commit**

```powershell
git add -- src/windwall/winding_tool_assembly.py src/windwall/winding_tool_service.py tests/test_winding_tool_assembly.py docs/winding-tool-assembly.md
git commit -m "refactor: assemble simple winding tools"
```

---

### Task 6: Replace exporter inventory and enforce deterministic printable artifacts

**Files:**
- Modify: `src/windwall/winding_tool_export.py`
- Modify: `tests/test_winding_tool_export.py`
- Modify: `tests/test_exports.py`
- Modify: `scripts/build_winding_tool.py`

**Interfaces:**
- Consumes: audited simplified assemblies and BOM.
- Produces: `export_winding_tool(destination, parameters=...) -> WindingToolManifest` with only current print masters, two STEP assemblies, BOM, drawings, guide, and fail-closed manifest.

- [ ] **Step 1: Write a failing exact-inventory regression**

```python
def test_release_excludes_every_superseded_part(self):
    with temporary_build_directory() as destination:
        manifest = export_winding_tool(destination)
        joined = '\n'.join(item['name'] for item in manifest.data['print_parts'])
        for stale in ('cam', 'slider', 'rib', 'clamp', 'brake', 'adjuster', 'upright'):
            self.assertNotIn(stale, joined.lower())
        self.assertIn('coil_wheel', joined)
        self.assertIn('contact_shoe', joined)
```

- [ ] **Step 2: Prove RED because the old inventory is still emitted**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_export.WindingToolExportTests.test_release_excludes_every_superseded_part -v`

Expected: FAIL with stale filenames.

- [ ] **Step 3: Define the exact master inventory from part records**

Export one master per unique printable geometry, with occurrence quantities derived from assembly ownership. Do not preserve old filenames as aliases. Keep tooling isolated from V5 `PRINT_SOURCES`.

- [ ] **Step 4: Preserve topology, STEP, and deterministic gates**

Every master must pass positive-volume, single-solid, manifold STL, no-degenerate-facet, print-envelope, and STEP-reimport checks. Two complete builds in different directories must match byte-for-byte. Failure of any part, assembly, BOM, guide, drawing, or audit must remove the success manifest.

- [ ] **Step 5: Update the CLI and shared regression**

The explicit output-directory CLI remains supported and returns failure when publication fails. `tests/test_exports.py` must prove the V5 print inventory is byte-for-byte unchanged and excludes tooling.

- [ ] **Step 6: Run the export module**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_export tests.test_exports -v`

Expected: all tests report `OK`.

- [ ] **Step 7: Commit**

```powershell
git add -- src/windwall/winding_tool_export.py tests/test_winding_tool_export.py tests/test_exports.py scripts/build_winding_tool.py
git commit -m "refactor: export simple coil winder"
```

---

### Task 7: Replace drawings, German guide, and generated release

**Files:**
- Rewrite: `scripts/preview_winding_tool.py`
- Rewrite: `docs/serpentine-coil-winding-tool-de.md`
- Modify: `README.md`
- Generate: `release/winding-tool/**`
- Test: `tests/test_winding_tool_export.py`

**Interfaces:**
- Consumes: simplified assembly/export API and canonical BOM.
- Produces: synchronized reference, range, exploded/removal drawings; German guide; exact generated release.

- [ ] **Step 1: Add failing documentation/drawing content tests**

Require drawings to show six shoes, eleven marked sizes, 18 tape locations, two 608s, the printed shaft/snap collars, 51105, upright roll, forward removal, and rotation/feed arrows. Require the guide phrases `100 bis 200 mm`, `18 Klebebandpositionen`, `PLA`, `gedruckte Achse`, `Drehteller von Hand stoppen`, `Schutzbrille`, `Probespule`, and exactly `Akkuschrauberbetrieb ist nicht freigegeben`. Reject old cam/brake/metal-shaft assembly instructions.

- [ ] **Step 2: Prove RED against the existing drawings and guide**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_export.WindingToolExportTests.test_release_includes_synchronised_drawings_and_german_guide -v`

Expected: FAIL on missing simplified content or stale instructions.

- [ ] **Step 3: Render deterministic drawings from actual CAD**

Render a 150 mm reference setup, a range drawing overlaying 100/150/200 mm envelopes and pin positions, and an exploded/removal drawing showing both modules and tool-free sequence. Use fixed canvas, camera, colors, labels, and file names; avoid clipped or overlapping annotations.

- [ ] **Step 4: Rewrite the German guide**

Cover PLA orientations, surface cleanup, snap inspection, bearing insertion/removal, six equal shoe settings, tape loading, hand winding, manual payoff stopping, inward release, forward removal, lead/direction marking, test-coil inspection, eye/entanglement/wire hazards, and all unvalidated limits. Remove instructions and BOM rows for every superseded component.

- [ ] **Step 5: Build into a fresh release directory**

Move the old `release/winding-tool` to a verified worktree-local backup, run `python scripts/run_geometry.py scripts/build_winding_tool.py`, and compare actual files one-for-one with the new manifest. Delete the verified backup only after the new release passes all checks; use PowerShell `Move-Item`/`Remove-Item` with resolved paths.

- [ ] **Step 6: Inspect all drawings at full resolution**

Confirm legible diameter numbers, visible twin hole rows and shoe pins, correct two-bearing stack, open front removal, separate upright payoff, no stale parts, and no clipped labels. Record image dimensions and observations in the implementation report.

- [ ] **Step 7: Run the focused release suite twice**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_export -v`

Run again after the committed-release comparison. Expected both times: `OK`, with identical generated bytes.

- [ ] **Step 8: Commit**

```powershell
git add -- README.md docs/serpentine-coil-winding-tool-de.md scripts/preview_winding_tool.py tests/test_winding_tool_export.py release/winding-tool
git commit -m "docs: publish simple coil winder release"
```

---

### Task 8: Full cleanup, verification, and handoff

**Files:**
- Review: every file changed by Tasks 1 through 7.
- Create: `.superpowers/sdd/2026-09-16-simple-pin-adjustable-coil-winder/final-report.md`

**Interfaces:**
- Consumes: completed simplified tooling release.
- Produces: verified branch ready for independent whole-branch review and integration.

- [ ] **Step 1: Run obsolete-code and artifact scans**

Run targeted `rg` searches for cam, slider, follower, rib bolt, brake, felt, spring, M3/M4/M8 assembly hardware, metal shaft, old filenames, and false validation claims. Remove dead imports, helpers, tests, documentation, and generated files; retain historical design documents only when clearly marked superseded.

- [ ] **Step 2: Run all tooling and shared export tests**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_parameters tests.test_winding_head tests.test_winding_frame tests.test_wire_payoff tests.test_winding_tool_assembly tests.test_winding_tool_export tests.test_exports -v`

Expected: all tests report `OK`.

- [ ] **Step 3: Run the complete repository suite**

Run: `python scripts/run_geometry.py -m unittest discover -s tests -v`

Expected: all runnable tests report `OK`; document environment skips and native teardown status separately.

- [ ] **Step 4: Perform final reproducibility and hygiene checks**

Rebuild the release into a separate directory and compare exact paths and SHA-256 hashes with the committed release. Run `git diff --check`, verify a clean worktree after commit, confirm no tooling changes in the V5 exporter/release, and visually inspect all three drawings again.

- [ ] **Step 5: Write the final report**

Record changed files, exact commands/counts/results, generated inventory, drawing dimensions and observations, skipped tests, native teardown behavior, physical validation limits, and the remaining manual prototype tests.

- [ ] **Step 6: Commit only verified cleanup/report changes**

```powershell
git add -- .superpowers/sdd/2026-09-16-simple-pin-adjustable-coil-winder src tests scripts docs README.md release/winding-tool
git commit -m "test: verify simple coil winder release"
```

- [ ] **Step 7: Request final whole-branch review before integration**

Review from commit `a62447a` through the final implementation head against the approved 2026-09-16 spec. Fix all Critical and Important findings, rerun affected tests, and obtain a clean or merge-ready re-review before offering merge/push options.
