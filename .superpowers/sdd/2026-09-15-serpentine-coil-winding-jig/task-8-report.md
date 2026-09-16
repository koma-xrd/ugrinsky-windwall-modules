# Task 8 report — release verification and integration readiness

## Scope and environment

Worktree: `C:\Users\fi87roy\Documents\GitHub\windwall\.worktrees\serpentine-coil-winding-jig`.
Branch: `codex/serpentine-coil-winding-jig`. Implementation examined: `e758c0f`.
Comparison baseline: `0fbebe9` (recorded branch start).
Interpreter: `C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe`.

Read the Task 8 brief, complete implementation plan and design specification,
progress ledger, Task 6/7 reports, all six tooling source modules, both tooling
scripts, all six tooling test modules, changed export regressions, assembly
contract, German guide, README changes, and Git attributes. No additional
AGENTS.md was present in this worktree or its repository/worktree ancestors;
the supplied engineering guidelines apply.

This task adds this verification report only. The cleanup review found no
justified source, test, dependency, or generated-artifact change. No behavior
changed, so no new regression or separate focused cleanup rerun was needed.
No merge, push, whole-branch review, physical build or powered trial was started.

## Complete suite

From the worktree root:

```powershell
$env:PYTHONPATH = "$PWD;$PWD/src"
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest discover -s tests -v
```

Final unittest output:

```text
Ran 274 tests in 3526.968s

OK (skipped=22)
```

**252 passed, 22 skipped, zero failures/errors.** All winding-tool tests ran
and passed, including all three nominal diameter audits, deliberate collision
and displaced-engagement regressions, service access, failure-publication,
complete-release byte reproducibility, artifact inventory, and rib STL checks.

The skips are existing environment conditions, not passing tests:

- 1 blade-profile comparison: `External reference path not configured`.
- 10 `test_v5_i18n.V5TranslationTests` cases: `DOCX authoring requires bundled document Python`.
- 11 `test_v5_manual.V5ManualTests` cases: `Run manual tests with the bundled document Python; see README`.

This required CAD-interpreter run therefore did not execute the external-reference
comparison or those 21 Word-document authoring tests. No document runtime or
external reference was substituted, and no V5 document source changed.

After unittest printed `OK`, the process returned **status 1**, the known native
Windows/OCP teardown status. The unittest result is successful with skips;
the native process exit is not clean. The launcher preserves failure statuses,
and no exit code was intercepted or rewritten.

## Real CLI rebuild and release comparison

The existing release was moved only after resolving and checking both absolute
paths. The original release contained 35 tracked files and the backup did not
already exist. PowerShell performed both the move and later removal:

```powershell
$task8Root = (Resolve-Path -LiteralPath '.').Path
$task8ExpectedRoot = 'C:\Users\fi87roy\Documents\GitHub\windwall\.worktrees\serpentine-coil-winding-jig'
if ($task8Root -ne $task8ExpectedRoot) { throw 'Unexpected worktree' }
$task8Release = (Resolve-Path -LiteralPath 'release/winding-tool').Path
$task8Backup = [IO.Path]::GetFullPath((Join-Path $task8Root 'build/task-8-winding-tool-backup'))
if ($task8Release -ne (Join-Path $task8Root 'release/winding-tool')) { throw 'Unexpected release path' }
if (-not $task8Backup.StartsWith($task8Root + '\') -or (Test-Path -LiteralPath $task8Backup)) { throw 'Unsafe or existing backup' }
Write-Output "Verified source: $task8Release"
Write-Output "Verified backup: $task8Backup"
Move-Item -LiteralPath $task8Release -Destination $task8Backup
$env:PYTHONPATH = "$PWD;$PWD/src"
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py scripts/build_winding_tool.py
```

The real CLI printed:

```text
Winding tool: 13 unique print candidates, 3 STEP assemblies.
Manifest: C:\Users\fi87roy\Documents\GitHub\windwall\.worktrees\serpentine-coil-winding-jig\release\winding-tool\manifest.json
```

Application publication completed. Native process status was **1** afterward,
consistent with the previously recorded Windows/OCP teardown limitation. This
is not described as a clean process exit or suppressed by a wrapper.

For both resolved trees, `Get-ChildItem -LiteralPath ... -File -Recurse` produced
relative paths through `[IO.Path]::GetRelativePath`, normalized to `/` and
sorted. `Compare-Object` found no inventory difference. Each pair was checked
using both exact byte comparison and SHA-256:

```powershell
foreach ($task8Relative in $task8OldPaths) {
    $task8OldFile = Join-Path $task8Old $task8Relative
    $task8NewFile = Join-Path $task8New $task8Relative
    $task8Before = [IO.File]::ReadAllBytes($task8OldFile)
    $task8After = [IO.File]::ReadAllBytes($task8NewFile)
    if (-not [Linq.Enumerable]::SequenceEqual[byte]($task8Before, $task8After)) { throw "Byte mismatch: $task8Relative; preserve backup" }
    if ((Get-FileHash -LiteralPath $task8OldFile -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $task8NewFile -Algorithm SHA256).Hash) { throw "Hash mismatch: $task8Relative" }
    $task8ByteCount += $task8After.LongLength
}
```

Exact output from the independent PowerShell checks:

```text
PASS: 35 identical paths; direct byte equality and SHA-256 equality; 36591723 bytes per tree
PASS: exact manifest/tracked/file inventory; 34 verified manifest hashes; no extras
PASS: 13 print masters, 24 pieces, 38 hardware rows; source/release guide bytes identical
```

The inventory comprises 13 part STEP/STL pairs, three assembly STEPs, three
PNGs, the German guide, BOM and manifest. All 35 files, including the manifest's
audit records and runtime metadata, matched exactly. Independently reconstructed
the 34 artifact references from `printable_parts`, `assemblies`,
`supporting_artifacts` and `bom_path`; recomputed all their hashes and compared
that inventory plus `manifest.json` against actual files and `git ls-files
release/winding-tool`. No pending manifest, stale drawing, missing file or
untracked extra was present. All 51 printable/hardware BOM rows and quantities
appear in the release guide. The safety phrase remains exact.

The reproduced reference-setting audit contains 19 passing checks, six ribs,
18 tape stations, 12 mm minimum measured tape clearance, 210 mm maximum X/Y
print envelope, 2 mm radial release, 1 mm minimum rigid brake clearance, and
14.6710599481625 mm crank-hand-envelope clearance. Its motion sample step is
30 degrees. These are recorded CAD measurements, subject to the physical
limitations below.

SHA-256 anchors, unchanged by the rebuild:

- `manifest.json`: `2cbccf041428720c8f7050e0b7cb71c7b444f2c724b605ad3e7c8d3d8b3b0fd0`
- `bom.json`: `4368d3f74f78c1afaeab27e7c5c4364c86c2f9c517817c64766bcbaa72242a23`

After the successful comparison, re-resolved and printed the deletion target:
`C:\Users\fi87roy\Documents\GitHub\windwall\.worktrees\serpentine-coil-winding-jig\build\task-8-winding-tool-backup`.
Checked exact equality to that Task 8 path, the expected worktree and its
directory prefix, and checked the rebuilt manifest still existed. Only then
ran `Remove-Item -LiteralPath $task8Backup -Recurse -Force`. The removed tree
was a verified duplicate; the rebuilt release remains and its original bytes
are recoverable from Git. `git status --short -- release/winding-tool` was empty.

## Hygiene and V5 isolation

Commands run from the worktree:

```powershell
git diff --check
git diff --check 0fbebe9 HEAD -- src tests scripts docs README.md .gitattributes ':!release/**/*.step'
git diff --check 0fbebe9 HEAD -- ':!release/**/*.step'
git diff --exit-code 0fbebe9 HEAD -- src/windwall/export.py scripts/build_v5.py release/v5
rg -n 'winding_head|wire_payoff|winding-tool' src/windwall/export.py scripts/build_v5.py release/v5/manifest.json
rg -n 'PRINT_SOURCES' src/windwall/export.py
$task8Files = @(git diff --name-only 0fbebe9 HEAD -- src tests scripts docs README.md .gitattributes)
rg -n -i 'powered.*validated.*true|physical.*verified.*true|\bTODO\b|\bFIXME\b|\bTBD\b|placeholder|NotImplemented|coming soon' -- $task8Files
rg -n -i 'powered.*validated.*true|physical.*verified.*true|\bTODO\b|\bFIXME\b|\bTBD\b|placeholder' release/winding-tool -g '*.json' -g '*.md'
```

All whitespace checks returned status 0. Claim/placeholder/coupling searches
returned no matches (the expected `rg` status 1). A separate direct
`Select-String -Pattern '[\t ]+$'` over all 19 changed source/test/doc/config
files also found no trailing whitespace. Generated STEP formatting was not
altered: its pre-existing scoped `-diff` attribute is documented by Task 7;
the explicit source/non-STEP check does not depend on that attribute.

A Python AST pass over changed Python files compared imported local names
against loaded names: `Unused-import candidates: []`, status 0. Manual review
found no dead helpers, obsolete configuration, or stale generated files.
The component modules retain small local CAD construction/validation helpers;
consolidating these would be unrelated refactoring. Bearing builders and fit
parameters remain shared with the existing bearing definitions; literal
nominal hardware selections and independent audit gauges are documented.
No dimension refactor was justified by this verification task.

The V5 exporter, builder and complete `release/v5` tree have an empty diff
against `0fbebe9`. `PRINT_SOURCES`, V5 manifest production entries and V5 STL
inventory contain the same eight names:

```text
base_rotor_module
standard_rotor_module
top_rotor_module
lower_magnet_rotor
generator_housing
coil_cassette
generator_cover
top_support
```

No winding-head or payoff member was added to that production inventory.

## Visual inspection

Opened each of the three final committed PNGs from the preserved release
backup using `view_image` with `detail: original`, at its native **2000 × 1400**
resolution. The subsequent direct byte comparison proved the rebuilt final
PNGs are precisely those inspected images.

- **Reference:** A and B have clearly separate bases and clear intervening
  space. Six orange ribs and their side tape windows are visible; central cam,
  clamp, shaft and outboard hand grip can be distinguished. Ø127, Ø150,
  Ø15 × 20 and Ø8 labels are readable. The two-608 label explains outer/inner
  ring ownership. The assembled 51105 is hidden under the platter and the
  legend explicitly refers to the exploded view. The long feed arrow points
  from B toward A and is identified as schematic. Labels and footer are not
  clipped or superimposed on other text.
- **Range:** Three distinct head states show the six ribs spreading from
  Ø110 through Ø127 to Ø145 and the changing cam position. All three panels
  have legible external numbers 1–18; contact circles and line styles agree
  with the legend. The counterclockwise arrow agrees with the German operating
  direction. Tape width, at-least-12-mm passage and 2-mm radial release are
  printed in a clear lower text block. This front view illustrates station
  alignment; tape-window depth is visible in the reference view. No label
  clipping or overlap obscures the diameter information.
- **Exploded:** Separate upper jig and lower payoff views use callouts 1–15.
  Clamp, cam, rib/slider groups, backplate, frame/shaft and crank are visually
  distinguishable. Both purple 608 envelopes sit above their upright seats.
  The lower view separates the housing washer, rolling envelope and shaft
  washer, explicitly identified as one complete 51105 with correct ownership.
  Platter/pilot and side brake group remain distinct. Some small hardware
  stays with its service group and can partially overlap in projection; this
  is a montage of service groups, not an individual-fastener assembly drawing.
  Number markers, leaders and the right-hand legend are readable and unclipped.

Each image retains the prototype/physically-unchecked footer and the exact
phrase **Akkuschrauberbetrieb ist nicht freigegeben**. No drawing change was
needed or performed.

## Documentation, limitations and handoff

Documentation updated: this report. Operator guide, assembly contract, README
and release documentation were reviewed and remain synchronized with the
verified release. No new dependency or production-part change was introduced.

CAD checks and deterministic artifact reproduction do not establish physical
fit, strength, fatigue, print support suitability, useful brake drag, enamel
protection, Ø127 calibration, electrical properties or cassette fit. Motion
checks sample 30-degree rotation and 0.5-degree cam release; they are not
continuous collision certification. Some purchased retention hardware is
specified in the BOM without detailed geometry. Physical prototypes remain
necessary. Powered operation remains unapproved.

Initial `git status --short` and the status after reproducible rebuilding were
empty. The report is in the ignored SDD directory and is explicitly staged
with `git add -f`. The measured pre-commit `git status --short` is:

```text
A  .superpowers/sdd/2026-09-15-serpentine-coil-winding-jig/task-8-report.md
```

`git diff --check` and `git diff --cached --check` both passed after staging.
The staged change contains this report alone. Commit subject:
`test: verify serpentine winding tool release`. The containing hash is obtained
without a self-referential report edit using:

```powershell
git log -1 --format=%H -- .superpowers/sdd/2026-09-15-serpentine-coil-winding-jig/task-8-report.md
git status --short
git diff --check
```

The post-commit status and hash are provided in the task handoff after those
commands run. Task 8 verification is complete; the next step belongs to the
parent's whole-branch review and integration decision.
