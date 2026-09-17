# Asymmetric Contact-Shoe Cradle Implementation Plan

> **Task 2 mechanical correction:** The original shoulder orientation and the
> corresponding Task 1/2 snippets below are historical and superseded by the
> updated design spec. Physical tests showed that either a 2.7 mm or 1.3 mm rear
> shoulder crosses the fixed winding before the pins clear the wheel. The final
> design therefore has a zero-height nominal-radius rear runout through Z=23.8
> and a rounded 2.7 mm free-front shoulder at Z=26.5. The declared winding and
> 10 × 4 × 10 mm tape fixtures remain unchanged; each shoe withdraws purely
> forward. Use the updated spec and implemented regressions for acceptance.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the winding shoe's flat wire-contact surface with a directly constructed rounded asymmetric U-cradle that guides the wire without obstructing tape application or coil removal.

**Architecture:** Build the outer shoe shell from an explicit axial-radial profile whose inner wall and mounting interfaces retain their current coordinates. The nominal winding radius passes through the cradle bottom; only the rear and free-side shoulders project outward. Existing tape cutters are applied to the completed profile and must cut through both shoulders.

**Tech Stack:** Python 3, CadQuery/OCP, `unittest`, deterministic STL/STEP and PNG release tooling.

**Spec:** `docs/superpowers/specs/2026-09-17-asymmetric-contact-shoe-cradle-design.md`

## Global Constraints

- `wire_payoff.py`, all wire-payoff artifacts, and all V5 production files and artifacts remain byte-identical.
- The cradle bottom defines the selected nominal winding diameter.
- Rear shoulder height is 2.5–3.0 mm; free-front shoulder height is 1.0–1.5 mm.
- The cradle is a continuous rounded surface with no separate insert or individual guide noses.
- The shoe foot, keyed pins, latch locations, and wheel-hole interfaces remain unchanged.
- Each tape passage preserves at least 12 mm tangential and axial clearance and cuts through both shoulders.
- Service validation uses closed tape strips measuring 10 mm tangentially, 4 mm radially, and 10 mm axially.
- Digital validation does not claim physical fit, strength, enamel safety, snap life, or removal force.

---

### Task 1: Construct the asymmetric cradle profile

**Files:**
- Modify: `src/windwall/winding_head.py`
- Modify: `tests/test_winding_head.py`

**Interfaces:**
- Consumes: `WindingToolParameters`, `_rounded_annulus`, `_build_shoe`, `build_winding_head`.
- Produces: `_asymmetric_shoe_shell(minimum_radius: float, bottom: float, top: float) -> cq.Workplane` and metadata keys `cradle_bottom_radius_offset_mm`, `rear_shoulder_height_mm`, `free_shoulder_height_mm`.

- [ ] **Step 1: Add a failing real-geometry cradle test**

Add this test to `WindingHeadTests` in `tests/test_winding_head.py`. The helper samples narrow solids away from all three tape passages, so it measures actual material rather than metadata:

```python
def test_contact_surface_is_a_rounded_asymmetric_wire_cradle(self):
    head = build_winding_head(P, 150)
    shoe = head.shoe_master

    def outer_x_at(z):
        sample = shoe.intersect(box(-6, 7.2, z - .2, 10, .6, .4))
        self.assertGreater(sample.val().Volume(), 0)
        return sample.val().BoundingBox().xmax

    rear = outer_x_at(7.0)
    bottom = outer_x_at(16.5)
    free = outer_x_at(26.5)
    self.assertAlmostEqual(bottom, 0.0, delta=.15)
    self.assertGreaterEqual(rear - bottom, 2.5)
    self.assertLessEqual(rear - bottom, 3.0)
    self.assertGreaterEqual(free - bottom, 1.0)
    self.assertLessEqual(free - bottom, 1.5)
    self.assertGreater(rear, free)
```

- [ ] **Step 2: Verify RED against the current flat shoe**

Run:

```powershell
$env:PYTHONPATH="$PWD;$PWD/src"
C:\Users\fi87roy\Documents\GitHub\windwall\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_winding_head.WindingHeadTests.test_contact_surface_is_a_rounded_asymmetric_wire_cradle -v
```

Expected: `FAIL` because `rear - bottom` is approximately zero. Record the unittest result separately from any known native Windows/OCP teardown status.

- [ ] **Step 3: Add explicit profile constants and a direct profile builder**

In `src/windwall/winding_head.py`, define:

```python
_CRADLE_BOTTOM_Z = 16.5
_REAR_SHOULDER_HEIGHT = 2.7
_FREE_SHOULDER_HEIGHT = 1.3
_CRADLE_HALF_WIDTH = 10.0
```

Add `_asymmetric_shoe_shell`. Construct one closed XZ profile with the existing inner-wall coordinates and an outer sequence that passes through these functional points after the existing `-minimum_radius` translation:

```python
outer_points = (
    (minimum_radius + _REAR_SHOULDER_HEIGHT, bottom + 1.0),
    (minimum_radius + _REAR_SHOULDER_HEIGHT, _CRADLE_BOTTOM_Z - _CRADLE_HALF_WIDTH),
    (minimum_radius, _CRADLE_BOTTOM_Z),
    (minimum_radius + _FREE_SHOULDER_HEIGHT, _CRADLE_BOTTOM_Z + _CRADLE_HALF_WIDTH),
    (minimum_radius + _FREE_SHOULDER_HEIGHT, top - 1.0),
)
```

Use tangent arcs or splines between the three cradle control regions; do not cut a cylinder from a pre-existing annulus. Close the profile along the same inner radius used by the current six-millimetre shell, revolve it about the winding axis, intersect it with the existing sector, and translate it by `-minimum_radius`. Verify the resulting shell is one valid solid before applying the tape cutters.

- [ ] **Step 4: Preserve foot and pin interfaces**

Keep `_keyed_pin`, `_PIN_ROWS`, `_PIN_SETBACK`, the foot box coordinates, and all pin translations unchanged. Add assertions to the new test that compare the unchanged pin/foot envelope against the committed baseline values:

```python
bounds = head.shoe_master.val().BoundingBox()
self.assertLessEqual(bounds.xmin, -12.0)
self.assertAlmostEqual(head.metadata['pin_rows_y_mm'], (-5.0, 5.0))
```

Do not move the seated shoe radius in `build_winding_head`; only the profile shoulders project beyond it.

- [ ] **Step 5: Publish truthful cradle metadata**

Add to `build_winding_head(...).metadata`:

```python
'cradle_bottom_radius_offset_mm': 0.0,
'rear_shoulder_height_mm': _REAR_SHOULDER_HEIGHT,
'free_shoulder_height_mm': _FREE_SHOULDER_HEIGHT,
'wire_guidance': 'rounded asymmetric U-cradle; lower free-front shoulder',
```

Extend the test to assert these exact values, while retaining the geometric assertions as the authoritative evidence.

- [ ] **Step 6: Verify GREEN and the complete head contract**

Run:

```powershell
$env:PYTHONPATH="$PWD;$PWD/src"
C:\Users\fi87roy\Documents\GitHub\windwall\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_winding_head -v
```

Expected: all winding-head tests pass, including raw STL manifold checks, all eleven diameter settings, rounded mouths, and the new cradle test.

- [ ] **Step 7: Commit Task 1**

```powershell
git add src/windwall/winding_head.py tests/test_winding_head.py
git commit -m "feat: add asymmetric wire cradle to winding shoes"
```

---

### Task 2: Prove tape clearance and continuous removal

**Files:**
- Modify: `src/windwall/winding_tool_service.py`
- Modify: `tests/test_winding_tool_assembly.py`
- Modify: `tests/test_winding_frame.py`
- Modify: `docs/winding-tool-assembly.md`

**Interfaces:**
- Consumes: `build_winding_head`, its cradle metadata, `build_taped_winding_fixture`, and `audit_winding_tool_service`.
- Produces: service evidence for the new shoulder geometry at 100, 150, and 200 mm.

- [ ] **Step 1: Add a failing passage-through-shoulders regression**

Add a service test which intersects each real 12 mm passage probe with the seated shoe and checks both shoulder regions are open:

```python
def test_tape_passages_cut_through_both_cradle_shoulders(self):
    for diameter in (100, 150, 200):
        head = build_winding_head(P, diameter)
        for probe in head.metadata['tape_passage_probes']:
            self.assertLess(volume_overlap(head.shoes[0], probe), 1e-6)
```

If the existing rotated-probe arrangement requires selecting the three probes belonging to shoe zero, use `head.metadata['tape_passage_probes'][:3]`; do not replace the physical intersection with a metadata-only assertion.

- [ ] **Step 2: Verify RED if a shoulder leaves a web**

Run:

```powershell
$env:PYTHONPATH="$PWD;$PWD/src"
C:\Users\fi87roy\Documents\GitHub\windwall\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_winding_tool_assembly.WindingToolServiceTests.test_tape_passages_cut_through_both_cradle_shoulders -v
```

Expected: fail if the Task 1 profile projects beyond the current passage cutter. If it already passes because Task 1 correctly sized the cutter, preserve the test and demonstrate RED by temporarily shrinking only the passage cutter in the working tree, then restore it before continuing.

- [ ] **Step 3: Extend cutters only as far as the physical profile requires**

In `winding_head.py`, derive the passage outer X limit from the larger shoulder:

```python
_PASSAGE_OUTER_X = _REAR_SHOULDER_HEIGHT + .4
```

Keep `_PASSAGE_INNER_X` unchanged. The added 0.4 mm is cutter overrun, not claimed usable clearance. Update `actual_tape_angles_deg` automatically through the existing passage-center calculation.

- [ ] **Step 4: Preserve the full-width closed tape fixture**

In `winding_tool_service.py`, keep the fixture dimensions explicit and unchanged:

```python
'tangential_width_mm': 10.0,
'radial_thickness_mm': 4.0,
'axial_height_mm': 10.0,
```

Add a regression assertion that the fixture metadata reports those values and that the closed strip has zero intersection with every seated shoe at all three verification diameters.

- [ ] **Step 5: Re-run continuous shoe and coil removal**

Run:

```powershell
$env:PYTHONPATH="$PWD;$PWD/src"
C:\Users\fi87roy\Documents\GitHub\windwall\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest tests.test_winding_tool_assembly tests.test_winding_frame -v
```

Expected: all tests pass, including obstruction-between-endpoints, one-shoe-left-latched, relaxed parked shoes, and final forward coil exit at 100, 150, and 200 mm.

- [ ] **Step 6: Update the assembly guide**

In `docs/winding-tool-assembly.md`, describe:

```text
The rounded U-cradle guides the wire axially. Its wheel-side shoulder is higher;
the lower free-front shoulder remains the removal side. The selected diameter is
measured at the bottom of the cradle, not at the shoulder tips.
```

Retain the warnings that physical enamel protection, PLA fatigue, fit, and removal force are unvalidated.

- [ ] **Step 7: Commit Task 2**

```powershell
git add src/windwall/winding_head.py src/windwall/winding_tool_service.py tests/test_winding_tool_assembly.py tests/test_winding_frame.py docs/winding-tool-assembly.md
git commit -m "test: validate cradle tape and removal clearance"
```

---

### Task 3: Regenerate and verify the release

**Files:**
- Modify generated files under: `release/winding-tool/`
- Modify: `docs/serpentine-coil-winding-tool-de.md`
- Modify: `tests/test_winding_tool_export.py`

**Interfaces:**
- Consumes: final shoe geometry, service audit, deterministic exporter, support renderer.
- Produces: checked-in deterministic STL/STEP assemblies, drawings, guide, and manifest for the asymmetric cradle.

- [ ] **Step 1: Add release assertions for cradle metadata and unchanged payoff**

Extend `tests/test_winding_tool_export.py` to assert the manifest serializes the cradle fields and retains the exact existing payoff inventory:

```python
self.assertEqual(manifest['winding_head']['rear_shoulder_height_mm'], 2.7)
self.assertEqual(manifest['winding_head']['free_shoulder_height_mm'], 1.3)
self.assertEqual(manifest['bom']['purchased'], {
    '608_bearing': 2,
    '51105_thrust_bearing': 1,
})
```

Use the manifest's existing nesting names if they differ; assert against the actual authoritative section rather than duplicating the data under a second key.

- [ ] **Step 2: Verify the new release assertion is RED**

Run the new single exporter test with the geometry wrapper. Expected: fail because the tracked manifest predates cradle metadata.

- [ ] **Step 3: Update exporter metadata serialization**

Modify `src/windwall/winding_tool_export.py` only if required to carry the four cradle metadata fields from the winding-head audit into the existing winding-head manifest section. Do not serialize unrelated shared `DesignParameters` fields.

- [ ] **Step 4: Rebuild into a separate destination**

Run:

```powershell
$env:PYTHONPATH="$PWD;$PWD/src"
C:\Users\fi87roy\Documents\GitHub\windwall\.venv\Scripts\python.exe scripts\run_geometry.py scripts\build_winding_tool.py --output-dir build\cradle-release-a
C:\Users\fi87roy\Documents\GitHub\windwall\.venv\Scripts\python.exe scripts\run_geometry.py scripts\build_winding_tool.py --output-dir build\cradle-release-b
```

Require both application-level build summaries to report success. Record any later native Windows/OCP status separately.

- [ ] **Step 5: Compare both builds byte-for-byte**

Use the repository's release-audit helper or a read-only PowerShell hash comparison. Require the same relative 32-file inventory and identical SHA-256 bytes for every corresponding file. Verify all manifest hashes against their referenced artifacts.

- [ ] **Step 6: Visually inspect all three drawings**

Open the three generated 2000×1400 PNG files at full resolution. Confirm the asymmetric cradle is visible and correctly labeled, the free side is unambiguous, tape passages remain visible, and no annotation is clipped.

- [ ] **Step 7: Install the verified generated release**

Replace only `release/winding-tool/` with the already verified `build/cradle-release-a` output using one PowerShell process and literal resolved paths within the worktree. Re-run the read-only release audit against the installed directory.

- [ ] **Step 8: Run affected suites**

Run:

```powershell
$env:PYTHONPATH="$PWD;$PWD/src"
$python="C:\Users\fi87roy\Documents\GitHub\windwall\.venv\Scripts\python.exe"
& $python scripts\run_geometry.py -m unittest tests.test_winding_head tests.test_winding_frame tests.test_winding_tool_assembly tests.test_winding_tool_export tests.test_winding_tool_parameters tests.test_wire_payoff -v
```

Expected: zero unittest failures/errors. `tests.test_wire_payoff` proves the intentionally unchanged subsystem still passes.

- [ ] **Step 9: Confirm V5 and payoff isolation**

Compare the final branch against the Task 2 commit. Require no changed files below `release/v5/` and no changes to `src/windwall/wire_payoff.py`. Compare the payoff STL/STEP artifact hashes before and after release generation and require exact equality.

- [ ] **Step 10: Commit Task 3**

```powershell
git add src/windwall/winding_tool_export.py tests/test_winding_tool_export.py docs/serpentine-coil-winding-tool-de.md release/winding-tool
git commit -m "docs: publish asymmetric winding shoe release"
```

---

### Task 4: Final verification and independent review

**Files:**
- Verify all branch changes from spec commit `2c6b434` through final HEAD.

**Interfaces:**
- Consumes: all implementation, tests, documentation, and generated release files.
- Produces: a review-approved branch ready for the integration decision.

- [ ] **Step 1: Run the complete repository suite**

```powershell
$env:PYTHONPATH="$PWD;$PWD/src"
C:\Users\fi87roy\Documents\GitHub\windwall\.venv\Scripts\python.exe scripts\run_geometry.py -m unittest discover -s tests -t . -v
```

Require a complete unittest summary with zero failures/errors. Document expected environment skips and treat any native shutdown status after `OK` separately.

- [ ] **Step 2: Run repository hygiene checks**

```powershell
git diff --check 2c6b434..HEAD
git status --short
```

Expected: no whitespace errors and an empty worktree.

- [ ] **Step 3: Request independent final review**

The reviewer must inspect the entire diff `2c6b434..HEAD`, the spec, tests, release inventory, drawings, and evidence. It must specifically verify nominal diameter at the cradle bottom, asymmetric real geometry, complete passage cuts, continuous removal, unchanged payoff/V5 content, and honest physical-validation limits.

- [ ] **Step 4: Resolve review findings using TDD**

For each Critical or Important finding, add a regression that fails for the reported defect, implement the smallest correction, regenerate only affected release files, and re-run the affected suite. Request one final read-only re-review.

- [ ] **Step 5: Present the integration decision**

After final approval and a clean worktree, use `superpowers:finishing-a-development-branch` and offer local merge, push/PR, or keeping the branch unchanged. Do not merge or push without the user's explicit choice.
