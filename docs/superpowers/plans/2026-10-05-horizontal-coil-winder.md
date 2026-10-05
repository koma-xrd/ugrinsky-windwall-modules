# Horizontal Coil Winder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Replace the upright winding stand with a horizontal 51105-supported wheel whose taped coil lifts upward over installed shoes.

**Architecture:** Reuse the payoff base and bearing reference directly. Replace the frame builder with a horizontal hub and removable hex crank, retain the wheel's existing socket, and update authoritative occurrence audits and global master grouping for the shared base.

**Tech Stack:** Python, CadQuery/OCP, unittest, existing deterministic STL/STEP exporter and Matplotlib drawings.

**Spec:** `docs/superpowers/specs/2026-09-26-horizontal-coil-winder-design.md`

## Global Constraints

- Unchanged `wire_payoff_base`, actual footprint 190 x 190 mm; preserve its existing STL and STEP bytes.
- One canonical 51105 per module: two complete purchased bearings for simultaneous use.
- At least 25 mm clear wheel-to-base workspace outside the bearing boss.
- Eleven settings, 100–200 mm in 10 mm increments; six shoes and 18 tape stations.
- Upper shoe projection 0 mm; straight upward coil removal with all shoes seated.
- Preserve 3.40 x 2.90 mm tongues in 3.50 x 3.00 mm wheel openings.
- PLA, 220 x 220 mm print envelope, removable 6.35 mm male hex crank and female socket.
- No drive screws or locking noses; powered use remains unvalidated.
- Preserve existing uncommitted shoe-fit work; do not overwrite unrelated changes.

## Review Focus

- Standard hex dimensions are across flats: a circular-diameter interpretation must fail the drive test (Task 2).
- Gravity-supported hub must not bottom on the base's blind bore (Task 2).
- Closed tape loops, not just bare coils, must clear seated shoes continuously (Task 3).
- Identical base masters span two assemblies and must collapse to quantity two (Task 4).
- At maximum diameter the rotating envelope and crank must clear the stationary base throughout rotation (Task 3).

## Verification commands

Use repository `.venv/Scripts/python.exe` with `PYTHONPATH` containing the repository and `src`. Invoke tests through `scripts/run_geometry.py -m unittest <module> -v`. Read unittest's final result separately from the known OCP shutdown status. Run each task's focused tests first; run the relevant winding suites once at integration, and avoid repeated unrelated turbine rebuilds without a new failure.

### Task 1: Open-top shoes

**Files:** `src/windwall/winding_head.py`, `tests/test_winding_head.py`.

**Interfaces:** Retain `build_winding_head(p: WindingToolParameters, diameter_mm: float, released: bool = False) -> WindingHeadParts`. Keep local Z as the upward shaft direction. Produce lower support, nominal-radius contact runout and upper shoulder metadata equal to 0.

- [x] Write `test_open_top_shoe_clears_upward_winding_sweep`: at 100, 150, 200 mm assert zero overlap for a continuous +Z sweep of the existing taped winding fixture over every seated shoe. Inject an upper lip and assert the sweep detects collision. Assert the lower supporting shoulder lies below the winding and retains rounded wire edges.
- [x] Run this test and verify it fails on the existing 2.7 mm upper shoulder.
- [x] Modify the explicit revolved shoe profile to retain a rounded lower support and remove the upper projection. Preserve tongue center positions, lead-in, stops, tape passage dimensions and wheel geometry.
- [x] Run `tests.test_winding_head`; update obsolete shoulder/removal assertions to physical open-top behavior. Preserve mesh and reproducibility tests.
- [x] Commit the focused shoe geometry and tests, including the previously approved fit correction where overlapping changes cannot be separated safely.

### Task 2: Horizontal hub and top crank

**Files:** Replace `src/windwall/winding_frame.py`; update `tests/test_winding_frame.py`. Consume `build_wire_payoff(...)` and `build_51105_reference(...)` without editing payoff geometry.

**Interfaces:** `WindingFrameParts(base, lower_washer, bearing, upper_washer, hub, crank, grip, metadata)`; retain `build_winding_frame(tool_parameters: WindingToolParameters, design_parameters: DesignParameters) -> WindingFrameParts`. Return bench coordinates directly, shaft axis +Z. Metadata supplies `wheel_bottom_z_mm`, print rotations, bearing dimensions, hex across-flats and service sequence.

- [x] Write failing tests named `test_horizontal_frame_reuses_payoff_base`, `test_hub_carries_51105_without_bottoming`, `test_wheel_gap_is_at_least_25_mm`, and `test_crank_uses_removable_635_mm_across_flats_hex`. Assert base symmetric difference below 1e-6 mm³, all three bearing occurrences match payoff locations, guide bottom above blind floor, actual wheel bottom minus base top >=25, and a literal 6.35 mm across-flats hex gauge fits the socket but cannot rotate 30 degrees inside it. Assert the crank pulls straight upward without flexure compression.
- [x] Verify failures against the existing upright record.
- [x] Build the new hub with its shoulder on the upper washer, guide compatible with the existing bores, and plain 14 mm circumdiameter wheel polygon mating the existing 14.4 mm socket. Place the wheel bottom at base top +25 mm; require enough pilot engagement before selecting upper stem height. Use 6.35 mm across flats for the male crank, initially 6.45 mm across flats for the female socket, with a shallow entry chamfer and positive depth stop. Retain a removable rotating grip.
- [x] Remove tower, 608 and collar builders and obsolete tests. Verify solids, radial and axial contact, journal clearance, torque transfer, free crank sweep and print orientation with `tests.test_winding_frame`.
- [x] Commit the new frame and physical regression tests.

### Task 3: Assembly and upward release

**Files:** `src/windwall/winding_tool_assembly.py`, `src/windwall/winding_tool_service.py`, `tests/test_winding_tool_assembly.py`.

**Interfaces:** Preserve `WindingToolAssemblies`, `build_winding_tool_assemblies(...)`, `audit_winding_tool_assemblies(model)`, `coil_removal_stages(model)`, and `audit_winding_tool_service(model, stages=None)`. Use a translation-only head installation at `wheel_bottom_z_mm`, no X rotation. `coil_removal_stages` produces seated winding, crank withdrawal and coil +Z removal with explicit moving/fixed ownership.

- [x] Write failures for two distinct 51105 purchase sets, shared base identity, all eleven horizontal settings, >=25 mm working gap, all 18 tape corridors, and continuous upward removal of the coil plus closed 10 mm tape loops with all six shoes fixed. Require no shoe-withdrawal stages. Inject displaced washers, short pilot, blocked tape, upper lip, raised/unseated wheel and base collision; assert the corresponding audit fails.
- [x] Run the targeted tests and inspect expected failures.
- [x] Replace upright occurrence layout with base/hub/crank/grip/wheel/six shoes and three 51105 members. Give both base occurrences canonical master identity `wire_payoff/base`; use separate bearing purchase-set identities. Update transforms, bearing ownership, contact checks, setting enumeration and rotating envelopes. Remove 608-specific gates and withdrawn-shoe service paths. Preserve payoff audits unchanged.
- [x] Run assembly and service tests; ensure mutated actual solids fail even when metadata claims success. Verify the full 100/150/200 mm taped-coil sweep and maximum rotating envelope.
- [x] Commit assembly, service and tests.

### Task 4: Shared master exports and BOM

**Files:** `src/windwall/winding_tool_export.py`, BOM code in `src/windwall/winding_tool_assembly.py`, `tests/test_winding_tool_export.py`.

**Interfaces:** Preserve `export_winding_tool(destination, ...) -> WindingToolManifest` and `winding_tool_bom(model)`. Printed masters group by explicit canonical identity across tools; base exports once as `wire_payoff_base`, quantity two. Inventory records all `(tool, member)` occurrences rather than assuming members belong to one tool.

- [x] Write failing tests: one base export with quantity two; all three 51105 occurrences per module yield purchased quantity two; no 608/tower/retainer/collar/old-shaft inventory; pre-change payoff base STL/STEP hashes unchanged. Assert guide, occurrence transforms, all artifact hashes and print footprints agree with actual geometry.
- [x] Run targeted tests and confirm failures.
- [x] Group global masters before export, compare representative solids for every grouped occurrence, and reject conflicting shared geometry. Remove obsolete shaft rotation override. Update manifest axes, upward service data, prototype limits and purchased quantities. Preserve deterministic ordering and fail-closed publication.
- [x] Run export tests relevant to inventory, topology, ownership, hashes and synchronized support artifacts.
- [x] Commit publisher and regression tests.

### Task 5: Drawings, instructions and release

**Files:** `scripts/preview_winding_tool.py`, `docs/serpentine-coil-winding-tool-de.md`, `docs/winding-tool-assembly.md`, `README.md` where applicable, generated `release/winding-tool/**`.

**Interfaces:** Retain `render_winding_tool_drawings(model, destination)` and `winding_tool_guide(model, bom)`, consuming current occurrence poses and canonical BOM.

- [x] Update existing support-artifact tests to require horizontal drawing inventory, correct shared-base quantities and matching guide bytes; run RED before changing rendering behavior.
- [x] Draw horizontal assembly, 51105 exploded stack, 25 mm tape workspace, diameter settings and upward removal with shoes seated. Update instructions to install two common bases for simultaneous operation, plug in the crank, tape on the installed wheel, remove crank and lift the coil. Remove obsolete 608/tower/shoe-withdrawal instructions.
- [x] Build into a worktree-local staging directory using `scripts/run_geometry.py scripts/build_winding_tool.py --output-dir <staging>`. Inspect PNGs and verify the inventory and base hashes before replacing generated release files. Remove only obsolete release artifacts resolved inside `release/winding-tool`.
- [x] Run winding head/frame/payoff/assembly/parameters/export suites once after integration, inspect every failure, run `git diff --check`, and review the finished geometry and release against the specification. Record the physical prototype fit limitation.
- [x] Commit the complete release and documentation. Keep merge/push decisions separate from construction; report the new printable shoe and hub files with the tests actually passed.

## Execution outcome

Executed inline on 2026-10-05. The complete winding head/frame/payoff/parameters/assembly/export suites reported 92 tests OK in 4474.721 seconds. The native CAD process still exits with status 1 after the OK footer; clean native shutdown is not claimed.

The release contains eight STL and eight STEP masters, fourteen printed occurrences, two complete purchased 51105 bearings, two STEP assemblies, three drawings, the synchronized German guide, BOM and manifest: 24 files with 23 verified artifact hashes. Both fresh full-audit exports and independent drawings are byte-identical. All six payoff STL/STEP artifacts preserve their pre-redesign bytes.

One fresh-context whole-branch review found a gravity-seating defect. The single fix pass raised the lower support, positioned the winding surrogate at its actual seat, added an independent six-shoe support gate and verified its negative regression. A bounded 0.002 mm numerical clearance avoids tangent noise without relaxing collision budgets. Review findings are resolved; physical PLA fit, strength, winding behavior and powered operation remain unvalidated. Print-ready and physical-validation flags intentionally remain false.

The five obsolete upright print masters and their ten STL/STEP files were removed from the release with a recoverable local backup. Merge/push remain a separate integration decision.
