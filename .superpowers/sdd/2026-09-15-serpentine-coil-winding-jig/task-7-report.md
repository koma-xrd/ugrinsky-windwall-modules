# Task 7 report — workshop drawings, German guide and release

Status: implementation, release build, visual inspection and focused
verification complete. Commit subject: `docs: publish serpentine winding tool release`.

## Scope and implementation

- Added `scripts/preview_winding_tool.py`: three deterministic 2000 × 1400 PNGs
  from copied CAD meshes, fixed orthographic cameras, DejaVu Sans, fixed colors,
  stable depth sorting, bounded planar triangles and fixed PNG metadata.
- Added the complete German source guide, including 13 print-master rows
  (24 pieces), all 38 hardware BOM rows, print orientation/support caveats,
  assembly, mounting, bearing ownership, brake adjustment, winding/taping,
  radial release, forming, physical calibration and Probespule inspection.
- README links the guide and isolated tooling manifest, names both independent
  manual modules and distinguishes them from V5 production parts.
- The tooling exporter regenerates marked configuration/BOM tables from its
  authoritative parameters/BOM, copies the guide, renders the three drawings,
  hashes all four supporting artifacts and only then publishes the manifest.
  The default release guide matches the complete source guide exactly.
- The existing exploded-jig STEP presentation now separates the head groups
  farther and lifts each 608 above its upright. The same translated bodies
  feed the drawing, with every translation recorded in the manifest. No
  operating geometry, parts, assembly ownership or clearance audit changed.
- Matplotlib version is recorded with the existing pinned CAD runtime.
  No new dependency, V5 inventory/exporter change or PRINT_SOURCES entry.

Changed source files: `.gitattributes`, `README.md`, `docs/serpentine-coil-winding-tool-de.md`,
`scripts/preview_winding_tool.py`, `src/windwall/winding_tool_export.py`,
`tests/test_winding_tool_export.py`, this report, and the generated
`release/winding-tool/**` files.

## Strict TDD evidence

Working directory for all commands:
`C:\Users\fi87roy\Documents\GitHub\windwall\.worktrees\serpentine-coil-winding-jig`.
Interpreter: `C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe`.
Environment: `$env:PYTHONPATH = "$PWD;$PWD/src"`.

Before implementation:

```powershell
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_winding_tool_export.WindingToolExportTests.test_release_includes_synchronised_drawings_and_german_guide -v
```

RED: **1 test, FAILED (failures=1), 212.672 s**, status 1. The expected
`assertTrue(all((destination / name).is_file() for name in required))`
failed because the three PNGs and guide copy did not exist. This was a real
export followed by the inventory assertion, not a missing import or mock.

The new test also checks all support hashes, PNG signatures/native dimensions,
source/release guide synchronization, every BOM quantity/ID in the guide and
the exact one-for-one release file inventory. The existing failure-publication
test now includes the supporting-artifact boundary. Existing fresh-build tests
compare all artifact bytes, so they also cover drawings, guide, BOM and manifest.

## Generated STEP diff ruling and regression

Full staged whitespace review initially reported the native OCCT formatter's
trailing spaces in generated STEP syntax. Source, guide, JSON and binary-artifact
checks were clean. Parent ruling: add only
`release/winding-tool/**/*.step -diff`; preserve exact validated STEP bytes and
hashes, and leave V5 attributes untouched. The existing `-text` preserves bytes
on checkout; the new `-diff` treats generated CAD as binary for textual review,
which also suppresses STEP textual whitespace diagnostics. It is not a STEP
normalization or a claim that OCCT's textual output has no trailing spaces.

Before adding the attribute, added and ran a regression using real
`git check-attr diff` for two tooling STEP paths, a V5 STEP, the tooling guide
and the exporter source:

```powershell
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_winding_tool_export.WindingToolReleaseAttributeTests -v
```

RED: **1 test, FAILED, 0.044 s**; tooling STEP values were `unspecified`
instead of `unset`. After the exact scoped attribute, GREEN: **1 test, OK,
0.052 s**. Both processes returned native status 1. The regression confirms
V5 STEP, documentation and Python source still have unspecified diff attributes.

## Visual inspection and corrections

All images are 2000 × 1400 pixels, inspected with local image tooling in
`original` detail mode. No generated image or hand-drawn substitute was used.

The first preview exposed head-group occlusion in the inherited exploded
presentation. Increased the head separation, moved both 608 envelopes above
their seats and adjusted only the fixed exploded camera; regenerated and
inspected the result. An initial Matplotlib cache warning was resolved by
using the existing writable `build/matplotlib` location before import.

- Reference: separate A/B bases are clearly visible with ample space between
  them. The Ø127 label, six-rib/cam callouts, two-608 note, 150-mm platter,
  15 × 20-mm pilot and schematic B → A wire-feed arrow are legible. Rib side
  windows are visible; the assembled 51105 is intentionally under the platter
  and referred to the exploded bearing view. Text is outside the CAD panel;
  no text is clipped or overlaps another label.
- Range: three distinct actual head builds at 110/127/145 mm show six
  concentric radial ribs and changing cam-track positions. Each panel has
  18 legible external station numbers at 20° intervals and all three contact
  circles. The counterclockwise winding arrow is unambiguous. The front view
  shows the contour; the side-window depth is visible in the reference view.
  Tape-width/passage and 2-mm radial-release text remains separate below.
- Exploded: head clamp, cam, six rib/slider groups, backplate, frame/shaft and
  crank are identifiable in the upper panel. Both purple 608 envelopes are
  lifted clear of the upright seats. Lower panel separately shows base,
  housing washer, rolling envelope, shaft washer, platter/pilot and brake
  group. Callouts 11–13 explicitly describe one complete 51105 and its motion
  ownership. Some hardware remains with its service group, as stated in the
  legend; this is not an individual-fastener disassembly drawing. Numbered
  markers and separate text columns are readable and unclipped.

## Release build and independent inventory audit

```powershell
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py scripts/preview_winding_tool.py
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py scripts/build_winding_tool.py
```

Final preview and release runs both printed their completion messages; the
release reported **13 unique print candidates and 3 STEP assemblies** and
published its manifest. Both subsequently returned native process status 1.
This is application completion, not a claim of clean native shutdown.
All three final release PNGs were then inspected again in original detail.

Independent PowerShell verification loaded the manifest/BOM, enumerated every
actual file, recomputed SHA-256 for each referenced artifact, checked every
BOM row against the guide and compared preview versus release PNG hashes:

```text
PASS: 35 exact files; 34 hashes; 13 print masters; 38 hardware rows;
source guide identical; 3 preview/release PNG pairs byte-identical.
```

The 35 files are 13 STEP/STL pairs, three assembly STEPs, `bom.json`,
`manifest.json`, the three named PNGs and the German guide. The manifest is
the one file without a self-hash. The two independent render paths agree even
though the full release previously tessellates the source solids for export.
The existing `test_fresh_builds_have_identical_artifact_bytes` also passed:
two fresh complete exports with an unrelated export between them produced
identical bytes for every emitted file, including BOM, drawings, guide and
manifest. This is independent of the preview/release PNG-only comparison.

`git diff --cached --check` passed for all staged sources and artifacts after
the explicitly recorded STEP attribute ruling; source-only checks also passed.
A diff against Task 6
for `src/windwall/export.py`, `scripts/build_v5.py` and `release/v5` was empty.
No Task 8 full-suite, merge or push was requested or performed by this task.

## Final focused GREEN and handoff

```powershell
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_winding_tool_export -v
```

Result: **8 tests, OK, 1270.140 s**, followed by native process status **1**.
All CLI, failure-publication, complete-release determinism, drawing/guide
inventory, STEP reimport, BOM/hash, unique-master and rib-STL tests passed.
The scoped Git-attribute regression was added while this long run was already
active and therefore ran separately with the RED/GREEN result above. Together
the runs cover all **9 tests in the final focused module**, with no skipped or
failed tests. No clean native shutdown is claimed.

`git diff --check`, source-only `git diff --cached --check` and full
`git diff --cached --check` passed. The exact release inventory and every hash
were independently checked after the final build, and all final PNGs were
inspected at native resolution. No generated STEP bytes were normalized.

The report is committed with the implementation. Resolve the containing commit
without a self-referential hash using:

```powershell
git log -1 --format=%H -- .superpowers/sdd/2026-09-15-serpentine-coil-winding-jig/task-7-report.md
```

The final handoff records the resulting full commit hash and the post-commit
`git status --short` result. Next step: parent Task 7 review; Task 8 remains
outside this subtask.

## Limitations

Workshop prototypes only. No physical fit, strength, electrical, speed,
production or powered-operation validation is supplied. Supports, bearing
fits, custom hardware, wire enamel protection, useful brake drag, physical
Ø127 calibration and cassette fit require measured prototypes. The guide and
drawings state exactly: `Akkuschrauberbetrieb ist nicht freigegeben`.

The known native OCP shutdown can return status 1 after Python reports
success; application/unittest results and process status are reported separately.
