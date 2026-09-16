# Task 8: final simple coil-winder verification

Status: complete with explicit runtime and physical-validation limitations.

## Scope and cleanup

Reviewed the approved specification, complete implementation plan, progress
ledger and rulings, Task 6/7 reports, every changed source/test module, the two
current guides, renderer, CLI, BOM and release manifest before final checks.
The Task 2 rulings remain authoritative: tape angles are actual,
diameter-dependent positions; all six shoes are completely removed before the
taped coil is withdrawn forward. No geometry, motion predicate or tolerance was
changed by Task 8.

The only behavioral cleanup is the approved tooling-manifest parameter subset.
The former complete shared manufacturing record included unused screw, nut,
washer and other fabrication settings. The tooling manifest now records only
the two consumed export tolerances and the nine consumed bearing nominal,
housing-seat and rotating-pilot dimensions. Shared `DesignParameters`, global
`PRINT_SOURCES` and V5 serialization are unchanged. The current assembly guide
documents this boundary. Both 2026-09-15 historical design/plan documents now
have explicit superseded banners linking to their 2026-09-16 replacements.

## Regression evidence

The new owning regression is
`tests.test_winding_tool_export.WindingToolExportTests.test_manifest_omits_design_settings_not_used_by_the_tooling`.
It publishes a real core release using the export module's existing real-CAD
fixture and inspects the resulting manifest. Only the expensive assembly audit
is replaced by that existing fixture; serialization, all master/assembly
exports and artifact hashing remain real. This focused case supplies an empty
supporting-artifact hook, so it does not render drawings or copy the guide.
Complete real-audit builds with all supporting artifacts are separately
exercised below.

- RED, before the exporter edit: one test ran in **71.879 s** and reported
  `FAILED (failures=2)`. Both expected subtests failed: manufacturing included
  unused hardware settings and bearings included unused coupon/seat-depth
  settings. Native process status was **-1073741819** after the failure summary;
  wall duration was **74.0340379 s**.
- GREEN, after the narrow serializer edit: one test ran in **71.384 s** and
  reported `OK`, with no failures/errors/skips. Native status was
  **-1073741819** after `OK`; wall duration was **73.0375629 s**.

Both used:

```powershell
$env:PYTHONPATH = "$PWD;$PWD/src"
python scripts/run_geometry.py -m unittest tests.test_winding_tool_export.WindingToolExportTests.test_manifest_omits_design_settings_not_used_by_the_tooling -v
```

Throughout this report, `python` denotes the repository environment at
`C:\Users\fi87roy\Documents\GitHub\windwall\.venv\Scripts\python.exe`.
Commands ran in the assigned `codex/serpentine-coil-winding-jig` worktree.
Logs and JSON native-status/timing records are retained under ignored
`build/task-8-*`; they are diagnostics, not release artifacts.

## Required test suites

Both commands use the explicit geometry interpreter described above and the
same `PYTHONPATH`. They ran in separate processes against the frozen final
source; no implementation files changed during either run.

```powershell
python scripts/run_geometry.py -m unittest tests.test_winding_tool_parameters tests.test_winding_head tests.test_winding_frame tests.test_wire_payoff tests.test_winding_tool_assembly tests.test_winding_tool_export tests.test_exports -v
python scripts/run_geometry.py -m unittest discover -s tests -v
```

The tooling/shared suite completed with **121 passed / 121 run**, zero
failures, zero errors and zero skips. Its exact unittest summary was:

```text
Ran 121 tests in 5030.956s

OK
```

Wall duration was **5034.186214 s**. Native process status was
**-1073740940**, after the complete `OK` summary; this is not a clean native
exit and is not counted as a unittest assertion failure.

The complete repository suite completed with **286 passed / 308 run**, zero
failures, zero errors and **22 skips**. Its exact unittest summary was:

```text
Ran 308 tests in 5818.900s

OK (skipped=22)
```

Wall duration was **5821.7982571 s**. Native process status was
**-1073741819**, after the complete `OK (skipped=22)` summary. Neither suite
had a unittest failure/error summary. Both include the new manifest-content
regression, full three-diameter removal, and two fresh real-audited release
builds with exact artifact-byte equality. The shared exporter tests also
rebuild and reimport the complete V5 master/coupon/assembly set.

Full logs are `build/task-8-tooling-suite.log` and
`build/task-8-repository-suite.log`; their matching `-status.json` records
retain native status and wall duration separately from unittest output.

The complete repository run reported these **22 skips**, each with its
existing runtime/environment reason:

| Scope | Count | Exact reason |
| --- | ---: | --- |
| `BladeProfileTests.test_active_sections_match_external_reference_in_both_directions` | 1 | `External reference path not configured` |
| `test_v5_i18n.V5TranslationTests` | 10 | `DOCX authoring requires bundled document Python` |
| `test_v5_manual.V5ManualTests` | 11 | `Run manual tests with the bundled document Python; see README` |

The geometry interpreter does not supply the bundled DOCX authoring runtime;
this task does not alter those existing skip guards or the V5 documents. The
missing external blade reference is likewise not fabricated for the test.

## Separate-process cold audits

All three additional cold processes passed. Each runs the existing read-only trace:

```powershell
python scripts/run_geometry.py build/task-7-diagnose-service.py
```

The trace wraps `_service_checks` solely to print the unchanged real result
before returning it. It calls the real cold assembly builder without mocking
an audit outcome or relaxing any geometric gate. Each process imports its own
fresh geometry caches and checks all eleven settings plus service at
100/150/200 mm.

| Cold process | Assembly gates | Service gates at 100/150/200 mm | Wall duration | Native status |
| --- | --- | --- | ---: | ---: |
| 1 | 40/40 true | 7/7 at each setting | 212.9056778 s | -1073741819 |
| 2 | 40/40 true | 7/7 at each setting | 219.0762774 s | -1073741819 |
| 3 | 40/40 true | 7/7 at each setting | 214.6310155 s | -1073740940 |

Every one of the nine service results reported empty `collisions` and `errors`
arrays, `continuous_translation_checks = true`, and
`radial_support_clearance_mm = 2.0`. The seven gates were `snap_access`,
`wound_closed_tape`, `route_continuity`, `motion_ownership`,
`all_shoes_detached`, `radial_support_clearance` and `complete_coil_removal`.
All completed their application evidence before the native shutdown failure.

Task 7's initial application failure of `removal_100` and `removal_200` remains
an unresolved historical observation. It was not a successful application
followed only by native teardown. The four earlier independent cold passes
and subsequent successful Task 7 builds did not establish its cause or fix it.
Task 8 preserves this distinction regardless of its fresh results.

## Release rebuild, inventory and reproducibility

The first final-source default CLI published successfully. Its exact command is:

```powershell
python scripts/run_geometry.py scripts/build_winding_tool.py
```

The original 32-file Task 7 release was moved with native PowerShell
`Move-Item -LiteralPath` to the exact worktree-local
`build/task-8-task7-release` backup. The worktree, source, destination and
parents were resolved and checked for exact paths, worktree containment and
reparse points. An initial `Split-Path -LiteralPath -Parent` parameter-set error
was nonterminating; after the move, the exact literal parents and complete
backup were rechecked under `ErrorActionPreference = 'Stop'` before any build.
All **32 original backup files** were also hashed with
`git hash-object --no-filters` and matched to their exact tree blobs in
Task 7 commit `1e56118`, independently confirming that recovery source.

The approved parameter cleanup intentionally changes only the manifest;
the original Task 7 comparison passed with all other **31 files byte-identical**.
The parsed manifest differs solely by removal of eleven unused manufacturing
keys and three unused bearing keys. The first CLI wall duration was
**343.8858719 s**, with native status **-1073741819** after its success summary.
The second final-source CLI used a verified absent independent destination:
`python scripts/run_geometry.py scripts/build_winding_tool.py --output-dir build/task-8-rebuild`.
It published successfully in **380.430375 s** wall time, followed by native
status **-1073740940**. The exact comparison passed with process status 0:

```powershell
python build/task-8-audit-release.py --compare build/task-8-rebuild
```

**All 32 paths and bytes are identical**, including manifest, BOM, all twelve
STL/STEP pairs, both assemblies, all three drawings and the German guide.
Neither real CLI build reproduced Task 7's removal-gate failure.

After both complete suites finished, both release comparisons were rerun
successfully with process status 0. Only the exact worktree-local directories
`build/task-8-task7-release` and `build/task-8-rebuild` were then removed with
native PowerShell `Remove-Item -LiteralPath -Recurse -Force`. Before removal,
both absolute targets and their literal ancestors were checked for exact
paths, worktree/build containment, directory type, 32-file inventories and no
reparse points in either tree. The original remains recoverable from Task 7
commit `1e56118`; the duplicate is reproducible from the retained final release.
The surviving release passed `python build/task-8-audit-release.py` afterward
with process status 0. No other pre-existing diagnostic or build directories
were manually removed.

The read-only audit command passed with process status 0:

```powershell
python build/task-8-audit-release.py --compare build/task-8-task7-release --allow-parameter-cleanup
```

It confirmed manifest = tracked = actual inventory: **32 files**, **31 valid
artifact hashes**, **12 unique masters / 19 printed occurrences**, the exact
two-608/one-51105 purchase set, all **40 true assembly gates**, all twelve
STL topology/orientation and STEP records, all eleven settings and their
actual tape angles, four support paths, complete exploded ownership,
three 2000 x 1400 PNGs and byte-identical source/release guide.

Manifest SHA-256:
`5c19adcb52a1dccdd596252c8b0dc75a0b64e721f43a7ef7b2e61d6a902997c7`.
Source/release guide SHA-256:
`4007972e2bd110774ebd0025a9353d6784afc918e5eac9f9c12b997381f0b312`.
The 32 release files total **68,642,313 bytes**.

## Full-resolution visual inspection

Opened all three images with original resolution at **2000 x 1400**. The initial
review used the preserved Task 7 bytes while the fresh release was building;
both final-source comparisons verified those drawings' bytes again. All three
fresh default-release images were also reopened at original resolution after
the builds, confirming the same findings directly on the final artifact paths.

- Reference: six gold shoes, the blue six-spoke wheel and both keyed hole rows
  are visible; the single-sided stand, hand crank and grip are distinct. The
  separate drive detail identifies the printed shaft, two 608 envelopes and
  two snap collars. The independent payoff, upright dashed roll example,
  150 mm platter, 15 x 20 mm pilot, 51105 label, rotation arrow and B-to-A feed
  arrow are clear. No labels or part silhouettes are clipped.
- Range: the three 100/150/200 mm settings, envelope circles, eleven-value
  setting list and station identities are legible. Physical offsets are
  explicitly **+/-19.65, +/-12.62 and +/-9.26 degrees** and the caption rejects
  equal physical 20-degree spacing. The enlarged rear shoe view exposes three
  separate tape passages, two keyed pins and release tabs. Tiny engraved CAD
  numerals are not the primary readable setting reference in these overview
  views; the explicit eleven-value list provides it.
- Exploded/removal: the 18 jig and 6 payoff occurrences are countable across
  the separated groups, including two 608s, two outer clips, the shaft, two
  collars, all six shoes, and the three distinct 51105 members. Captions state
  assembly order and bearing ownership. The complete lower sequence closes
  all tape stations, removes/parks all six shoes, then moves the taped coil
  forward while wheel, shaft, crank and stand remain assembled. The forward
  arrow and helper instruction are visible. No obsolete parts or clipping
  were found.

## Hygiene, isolation and documentation

The repeated final AST inspection parsed all **15 changed Python files** with no
unused-import candidates. Manual review found no dead new helpers, stale TODOs,
unused dependencies or unsupported physical-validation claims. The repeated
source/document/JSON whitespace scan passed across **32 paths**, including
the task reports; generated STEP formatting is excluded.
`git diff --check` and `git diff --cached --check` passed. The staged scope
was verified as exactly the seven authorized files listed below. Initial
sandboxed staging was denied access to the shared Git index; the authorized
scoped staging succeeded. The post-commit status and commit hash are returned
in the handoff.

The complete changed-source scan, current English/German guides, CLI, renderer,
manifest, BOM and release path inventory contain no obsolete production parts
or assembly hardware. Remaining old terms occur only in deliberate production
rejection guards and regression tests, optional bench-clamping instructions,
the ordinary snap-deflection verb
"cam inward", and explicitly superseded historical documents. There is no
active cam/slider/follower mechanism, rib bolt, adjustable brake, felt/spring
brake, two-upright frame, metal drive shaft or M3/M4/M8 tooling hardware.

The isolation command returned status 0 with no diff:

```powershell
git diff --exit-code 7912355ed52ccbc40ca49b47d3c6346f3b4a3249 -- src/windwall/export.py scripts/build_v5.py release/v5 src/windwall/parameters.py
```

Consequently the complete global exporter (including `PRINT_SOURCES`), V5
builder/release and shared parameter model are unchanged. Source/release guide
bytes and exact release inventory/hashes are independently covered by the
read-only comparison above. Raw release bytes also matched tracked blob IDs
for all 31 unchanged artifacts before staging. After staging, all **32 final
release files plus the source German guide (33 paths)** matched their exact
raw staged Git blob IDs, including the new manifest. Thus committing cannot
silently normalize any hashed release artifact or desynchronize the guide.

## Exact Task 8 changed files

- `src/windwall/winding_tool_export.py`
- `tests/test_winding_tool_export.py`
- `docs/winding-tool-assembly.md`
- `docs/superpowers/specs/2026-09-15-serpentine-coil-winding-jig-design.md`
- `docs/superpowers/plans/2026-09-15-serpentine-coil-winding-jig.md`
- `release/winding-tool/manifest.json` (regenerated only)
- `.superpowers/sdd/2026-09-16-simple-pin-adjustable-coil-winder/final-report.md`

## Limits and integration readiness

Ready for independent whole-branch review and an explicit integration
decision with the following limitations; this is not clean-native-exit or
physical-production approval. No new removal failure was reproduced in
the three cold audits, the real CLI builds or either complete test suite.
Task 7's earlier failure is still unexplained, not claimed fixed.

Physical printing and fit, printed 8 mm shaft strength/fatigue, PLA snap
retention/life, bearing fits, actual winding
diameter/repeatability, enamel protection, payoff stability/manual stopping,
coil-release force, electrical behavior and continuous/production use remain
unvalidated. The service checks use the documented 9 mm axial / 1 mm radial
winding and bounded closed-tape surrogates; they do not approve larger coils or
actual hand force. Powered operation is not approved.

The Windows/OCP native process-end failure remains unresolved and is recorded
separately from application/test results. No merge, push, worktree removal or
final independent whole-branch review is part of this Task 8 execution.
