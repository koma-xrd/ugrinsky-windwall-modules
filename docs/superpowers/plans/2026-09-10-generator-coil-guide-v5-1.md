# Generator Coil Guide V5.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an original-style open serpentine winding guide, four aligned M4 cover bosses, and an integral lower-rotor spacer sleeve.

**Architecture:** `generator_housing.py` owns all stationary winding-guide and fastener geometry. `generator.py` owns the fused rotating sleeve and assembly motion classification. Existing export, drawing and manual builders consume these public models and are updated to remove the obsolete separate spacer.

**Tech Stack:** Python 3, CadQuery/OpenCascade, standard-library `unittest`, python-docx release pipeline.

**Spec:** `docs/superpowers/specs/2026-09-10-generator-coil-guide-v5-1.md`

## Global Constraints

- Preserve the accepted rotor blade and bayonet geometry.
- Keep both nominal magnet-to-active-winding gaps at 1.5 mm.
- Keep stationary and rotating ownership explicit and collision-audited.
- Retain prototype and non-waterproof warnings.
- Run CadQuery tests through `scripts/run_geometry.py`; the Windows OCP runtime may return a native nonzero teardown status after unittest reports `OK`, which must be reported separately.

---

### Task 1: Four aligned cover fasteners

**Files:**
- Modify: `tests/test_generator_housing.py`
- Modify: `src/windwall/generator_housing.py`

**Interfaces:**
- Consumes: `GeneratorHousingParts.bottom_mount_tabs`, `cover_fasteners`
- Produces: four independent `CoverFastener` paths aligned angularly with four `BottomMountTab` paths

- [ ] **Step 1: Write failing tests** asserting four cover fasteners, matching normalized radial axes, separate radii, clear tool paths, and fused reinforcement between each boss, shell and tab.
- [ ] **Step 2: Run** `python scripts/run_geometry.py -m unittest tests.test_generator_housing -v` and verify failure because six diagonal fasteners exist.
- [ ] **Step 3: Implement** cardinal fastener axes and continuous boss-to-tab reinforcement in `generator_housing.py`.
- [ ] **Step 4: Run the same test command** and verify all housing tests report `OK`.

### Task 2: Open serpentine winding guide

**Files:**
- Modify: `tests/test_generator_housing.py`
- Modify: `src/windwall/generator_housing.py`
- Modify: `tests/test_generator.py`

**Interfaces:**
- Consumes: `build_coil_cassette(DesignParameters)` and `GeneratorHousingParts.winding_volume`
- Produces: one printable cassette solid with 18 rounded guide islands and a collision-free rotating center passage

- [ ] **Step 1: Write failing tests** that detect 18 alternating guide stations at the reference angular pitch, verify an open winding path and lead access, and verify no guide intersects the active winding envelope or rotating keep-out.
- [ ] **Step 2: Run the focused housing tests** and verify failure because the cassette currently has only annular walls.
- [ ] **Step 3: Implement** rounded guide islands fused to the cassette floor, with alternating inner/outer winding turns and lead gates at the cable passage.
- [ ] **Step 4: Run focused housing and generator tests** and verify `OK`.

### Task 3: Integral lower-rotor sleeve

**Files:**
- Modify: `tests/test_generator.py`
- Modify: `src/windwall/generator.py`
- Modify: `src/windwall/export.py`
- Modify: `tests/test_exports.py`

**Interfaces:**
- Consumes: `build_lower_magnet_rotor(DesignParameters)`
- Produces: lower rotor with fused 12 mm OD sleeve and no separate `spacer` assembly/export part

- [ ] **Step 1: Write failing tests** for connected sleeve geometry, 8.8 mm passage, 17.85 mm nominal reach, preserved nut access, and absence of a separate spacer export.
- [ ] **Step 2: Run generator/export tests** and verify failure because the spacer is separate.
- [ ] **Step 3: Fuse the sleeve** in `build_lower_magnet_rotor`, remove the separate assembly/export body, and keep it in rotating collision checks as part of the rotor.
- [ ] **Step 4: Run generator/export tests** and verify `OK`.

### Task 4: Release artifacts and documentation

**Files:**
- Modify: `README.md`
- Modify: `scripts/manual/manual_data.py`
- Modify: `scripts/manual/build_manual.py`
- Modify: relevant release validation tests
- Regenerate: `release/v5/**`

**Interfaces:**
- Consumes: revised public CAD builders and release scripts
- Produces: synchronized STL, STEP, drawings, English README and six-language DOCX set

- [ ] **Step 1: Update validation tests** for the new part inventory, four fasteners, serpentine guide and integral sleeve; verify they fail against the old artifacts.
- [ ] **Step 2: Update human-readable source documentation** to explain winding around the 18 guides and removal of the separate sleeve.
- [ ] **Step 3: Rebuild the V5 release** with `scripts/build_v5.py` and update the deterministic release index.
- [ ] **Step 4: Run all tests and artifact audits**, inspect the revised generator drawings, and record the native teardown limitation separately from unittest results.

### Task 5: Review and integration

**Files:**
- Review all modified files and generated artifacts

**Interfaces:**
- Consumes: completed V5.1 worktree
- Produces: reviewable commit ready for integration and later push

- [ ] **Step 1: Run cleanup checks** for stale spacer references, obsolete six-fastener wording, dead code and untracked generated files.
- [ ] **Step 2: Run fresh focused and full verification commands** and inspect `git diff --check` plus worktree status.
- [ ] **Step 3: Commit the focused V5.1 change** only after verification evidence is available.
- [ ] **Step 4: Present integration status** without pushing until the completed branch has passed review and the repository state is confirmed.

