# Final review fix wave 1/1 — serviceable winding tools

## Scope

Worktree: `C:/Users/fi87roy/Documents/GitHub/windwall/.worktrees/serpentine-coil-winding-jig`.
Branch: `codex/serpentine-coil-winding-jig`. Fix-wave baseline: `a7855a3`.
Whole-branch baseline: `0fbebe9`.

Read the complete final-review brief, progress ledger, implementation plan,
design specification, Task 1–8 reports, relevant source/tests, operator guide,
assembly contract, scripts and generated release. The supplied engineering
instructions apply. Used strict test-first regressions, systematic diagnosis
of the resulting geometric failures, and fresh verification before handoff.
No subagent, merge, push, unrelated refactor or new dependency was used.

## Findings and mechanical decisions

1. **Axial spindle restraint:** two custom steel shoulder collars are positively
   cross-pinned to the shaft on opposite sides of the left 608 inner ring.
   Each Ø10.4 mm nose leaves a nominal 0.1 mm face gap. The right 608 does not
   axially locate the shaft, avoiding preload across the support span. Two
   identical printed outer-ring caps bolt to the uprights. Upright shoulders
   and caps contact only radii 10–11 mm; collars contact radii 4.1–5.2 mm.
   A displaced shaft/collar engages its cross-pin; each collar engages the
   left inner ring in the relevant axial direction; outer-ring displacement
   engages either its shoulder or cap. Purchased bearing lands and actual
   endplay must be measured. Pin/hole and bearing internal clearance add to
   the two face gaps: 0.2 mm is not a total endplay claim.
2. **Complete removal:** retract all six ribs and their retained hardware by
   2 mm through a common cam position. A real annular taped-coil surrogate
   travels with the supported head. Remove four vertical head/locator pins
   and the side crank pin, pull the shaft 220 mm left, lift head/coil 200 mm,
   then slide the coil 50 mm axially off the ribs above the frame. Uprights
   and bearing caps remain installed. A helper holds the loose head stack,
   crank and collars; keepers are removed before the modeled pins. The route
   checks 21 positions in every stage at Ø110, Ø127 and Ø145.
   The surrogate bounds 10 mm axial winding width, 3 mm radial build and
   0.5 mm inward tape allowance; it does not certify arbitrary winding sizes.
   The full route additionally exposed an old pin/nut interference and a
   blind retaining-collar bore. Moving the front collar 10 mm forward, using
   M3x20 preload screws, shifting its pin axis 0.25 mm and providing a fully
   through bore for a Ø4x32 pin makes its withdrawal occur outside the coil.
3. **Brake anti-rotation:** two straight edges on the sliding adjuster flange
   engage the existing service-slot walls at both adjustment endpoints.
   The radial nut-loading slot extends through the keyed flange. Screw,
   spring, washer, captive nut and felt force paths remain intact.
4. **Mounted brake access:** four integral 24 mm feet leave the side and
   underside open to a short 2.5 mm hex key. Its actual B-rep fits the socket,
   clears a modeled bench and base through a 60-degree working stroke and
   inserts/removes sideways after disengagement. No bench access hole is
   required. Bench bolt allowance increases from bench thickness +18 mm to
   +42 mm for this module. The plate above the feet requires removable print
   support or a reviewed alternate slicer orientation.
5. **Flush frame mounting:** four M4x20 socket bolts now have actual heads,
   eight 0.8 mm washers and four 5 mm locknuts. The feet contact the base
   directly. Recessed head/lower-washer stacks react against 4.9 mm deep
   counterbores while retaining 0.1 mm nominal clearance above the Z=0 bench.
   Upper washers/nuts are accessible above each upright foot. The nominal
   20 mm shank reaches through the nut with positive thread projection.
6. **Strict types:** every `_mm` value must be a non-boolean real numeric
   value, finite and positive. Counts must be non-boolean integral types.
   Public frame/payoff validation occurs before cached construction so a
   numerically equal invalid dataclass (for example `rib_count=6.0`) cannot
   reuse valid cached geometry.
7. **Diameter labels:** physical cam engravings use the three validated
   diameter values rather than fixed strings. A non-default 112/128.5/144
   configuration is probed against the actual engraved CAD cuts and exported
   with matching configuration table, reference metadata and explicit
   `engraved_diameter_labels` in the manifest.

`windwall.winding_tool_service` contains isolated retention, mounting, tool
and removal gauges. The assembly audit consumes its five additional checks;
the drawing generator consumes the same physical removal stages. Existing
ownership, engagement, rotation, head hardware, tape and print audits remain
active. No mesh filtering, general healing or failure-status suppression was
introduced. The deterministic/fail-closed export path is preserved.

## Test-first evidence

Focused regressions were executed before their corresponding implementation:

| Issue group | Observed RED | Correction / focused GREEN |
| --- | --- | --- |
| Types and custom physical labels | 6 tests, 8.167 s: 13 failures and 16 errors; wrong types accepted or raised TypeError, custom glyph probes lacked cuts | Strict validation and generated glyphs; covered again by the final full tooling run |
| Axial retention, flush M4 stacks, brake keying and bench access | 4 tests, 11.599 s: 20 subtest failures; absent collars/caps; 25.1327 mm³ bolt/bench overlap; zero anti-rotation engagement; obstructed key/bench/socket | Positive collars/caps, complete recessed hardware, keyed flange, feet and socket |
| Complete service API and cached invalid count | 3 tests, 14.636 s: three failures | Real ordered service stages, physical audits, validation before cache |
| New printable cap inventory | 1 test, 15.503 s: complete-inventory coverage ValueError | One cap master with two congruent members; focused inventory regression green |
| Keyed adjuster nut service | First combined 19-test run retained four failures at 6–9 mm withdrawal | Extended the nut loading cut through the key; all 33 frame/payoff tests then reported OK in 13.968 s |
| Complete pin withdrawal | Route first found 0.02329059 mm³ collar-pin/preload-nut overlap, then 12.566 mm³ pin/collar overlap on withdrawal | Cleared the nut axis, moved the collar ahead of the coil, lengthened preload screws and opened the full pin bore |
| Custom export label inventory | 1 test, 389.952 s: `None != ['112', '128.5', '144']` | Added explicit manifest label values, retaining the separate physical glyph regression |
| Sealed 608 face exclusion | 1 test, 9.639 s: four failures; 12.2710609 mm³ seal/cap overlap and 1.26645454 mm³ seal/collar overlap under axial engagement | Ø10.4 mm noses and Ø20 mm shoulder/cap openings; all 39 frame/payoff/parameter tests OK in 14.041 s |

The additional sealed-bearing regression was prompted by a manufacturer-data
cross-check, not by a new review wave. The
[SKF 608-2RSH drawing](https://www.tme.eu/Document/83a59906c97cb2ff6c50c795411b45d2/SKF608-2RSH.pdf)
specifies a 10–10.5 mm shaft abutment and a maximum 20 mm housing-abutment
opening, with a 19.2 mm outer recess diameter. The preliminary Ø11 mm nose
and Ø18 mm housing relief were refined accordingly before commit. Tests use
an independent conservative flush annular exclusion for the sealed region.

After the collar/pin withdrawal change, the two focused full-route/service-negative
tests reported **OK, 2 tests, 234.486 s**. The route ran all three required
diameters against every stationary member. The audit rejected a locator
displaced 20 mm and a connected overhead obstruction in the supported lift.
An earlier diagnostic run predating the broad-phase/early-failure route
optimization was interrupted; it is not counted as verification.
Two incomplete final-suite attempts were also stopped when the sealed-bearing
refinement became necessary; the replacement complete runs are authoritative.

All geometry commands use:

```powershell
$env:PYTHONPATH = "$PWD;$PWD/src"
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py ...
```

The native Windows/OCP interpreter can return status 1 after unittest prints
`OK` or after the CLI publishes its manifest. Application/test outcomes and
native process status are recorded separately; no clean shutdown is implied.

## Final verification

Final verification commands, all through the geometry launcher and the
interpreter/PYTHONPATH recorded above:

```powershell
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_winding_tool_parameters tests.test_winding_head tests.test_winding_frame tests.test_wire_payoff tests.test_winding_tool_assembly tests.test_bearings -v
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_winding_tool_export -v
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_exports tests.test_release_index tests.test_run_geometry -v
```

The first command completed: **86 tests, OK, 1945.749 s**, native exit status 1.
All parameter, head, frame, payoff, assembly and bearing tests passed, with no
skips. This includes all three full diameter audits, the complete supported
removal route at each diameter, seal exclusion, actual fastener/bench stacks,
mounted hex-key access, anti-rotation, and negative displacement/obstruction
checks. No audit was patched out in the complete integration tests; isolated
component tests retain their explicitly documented construction-only patches.

The third command completed: **30 tests, OK, 147.127 s**, native exit status 1.
It covers unchanged V5 print sources, all unique part exports, manifold/STL
and STEP checks, canonical byte preservation through Git/Windows checkout,
shared failure publication, release-index hash bindings and launcher status
propagation.

The second command completed: **11 tests, OK, 2263.459 s**, native exit status 1.
All full-export, non-default diameter, unique-cap inventory, STEP reimport,
closed single-component STL, zero-degenerate-face, BOM/hash, drawing/guide
synchronization, CLI failure propagation, stale-manifest removal and fresh
artifact byte-equality cases passed. No cases were skipped.

**Final total: 127 passed, zero failures/errors, zero skips.** This includes
the complete 89-test tooling set, eight bearing tests and 30 shared regression
tests. Native process status was 1 after each successful unittest summary;
the application results are not represented as clean host-process shutdowns.

The tooling test inventory grew from 76 to 89 methods (13 new regressions).
Together with eight bearing and 30 shared-infrastructure tests, the final
commands cover 127 tests. The entire repository suite was not rerun during
this focused fix wave; the parent's Task 8 baseline covered 274 tests before
these 13 additions, with 22 documented skips. A whole-repository rerun, if
desired for integration, is `scripts/run_geometry.py -m unittest discover -s tests -v`.
No unrelated V5 document, external-reference or other CAD module is claimed
freshly verified beyond the explicitly listed regression commands.

### Real CLI rebuild and independent repeat

Executed the real CLI both for the release and for a separate, initially absent
output directory:

```powershell
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py scripts/build_winding_tool.py
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py scripts/build_winding_tool.py --output-dir build/final-review-repeat-release
```

Both final corrected builds published **14 unique print candidates and three
STEP assemblies**, followed by native process status 1. Resolved both exact
roots, enumerated relative paths, compared every file with
`[Linq.Enumerable]::SequenceEqual[byte]` and independently computed SHA-256:

```text
PASS: 37 identical corrected-release files; direct byte and SHA-256 equality; 38989420 bytes per tree
PASS: exact manifest inventory; 36 artifact hashes; 14 masters / 26 pieces; 44 hardware rows; source/release guide identical; 24 passing audit checks
```

The independent inventory check reconstructs manifest references from all part
STEP/STLs, assembly STEPs, supporting artifacts and BOM; verifies exact on-disk
inventory/no extras and every recorded hash; verifies every BOM row/quantity
appears in the guide; and compares source/release guide bytes directly.
The success manifest is absent until all release gates pass. All three final
corrected PNGs were again inspected at native resolution and are exactly the
repeat-build images. Final SHA-256 anchors:

- `manifest.json`: `b4832952b389273142bf91be39d9fc30e3e13e502b8669f09d4d37b78e719ec4`
- `bom.json`: `8da546d95d6d1f9845c1d2fea2671d70a020876311f3ad6da0ae9697aac8b304`

The final guide also explicitly keeps the head unpinned until the shaft has
been threaded through the already-mounted bearings and supported head stack.
Both CLI builds were repeated after this guide-only clarification. Their
three PNG hashes remain identical to the full-resolution images inspected
after the sealed-bearing correction:

- Reference: `b1f80a5719331b54c0ec5c3055205fc3981437f1b6a67b20a494f7d456697a40`
- Range/removal: `42c0e2f8efa5c9dee82689988d7666cbc22ee387b588aaaacecd7d3ec4a6fca8`
- Exploded: `798ab182b024977044f19b64cb9e173bb098177d6b658a3200b6574117376053`

After direct-byte/hash equality, the exact absolute
`build/final-review-repeat-release` path was resolved and checked against
the expected worktree and its prefix before native PowerShell recursive
removal. Only the verified duplicate rebuild was removed; the identical
release remains. The temporary collar-interference probe was also removed.

The final reference assembly audit has **24 passing checks**, no errors/collisions,
six ribs, 18 tape stations, 12 mm minimum tape clearance, 210 mm maximum X/Y
print envelope, 2 mm radial release, 1 mm rigid brake clearance and
14.76482306032329 mm crank-hand clearance. New service evidence records both
0.1 mm collar face gaps, 0.1 mm upright-fastener bench clearance, 14.5 mm
brake-key bench clearance and zero coil-removal collisions.

### Hygiene and isolation

`git diff --check` passes. A separate trailing-tab/space scan over all 16
changed source/test/doc files passes. Python AST parsing of all 14 changed
Python files found no unused-import candidates; the public service-stage
re-export uses an explicit same-name alias. The placeholder/unsupported
physical-or-powered-success scan found no matches. No obsolete source,
dependency or production configuration remained to remove.

`git diff --exit-code 0fbebe9 -- src/windwall/export.py scripts/build_v5.py release/v5`
is empty and returns zero. Existing `PRINT_SOURCES` and V5 production inventory
remain unchanged. Generated STEP bytes were not normalized or filtered.

After staging, `git diff --cached --check` and `git diff --check` both pass.
An independent comparison of `git ls-files release/winding-tool` with the
on-disk tree confirms all 37 release files are staged/tracked, without extras.
At that check, there were zero unstaged tracked changes and zero untracked
non-ignored files; the ignored report is explicitly force-added after final
results are recorded. The initial sandboxed staging attempt could not write
the shared Git index; the approved scoped Git escalation succeeded. No
repository setting, existing index data or unrelated work was discarded.

## Inventory and documentation

The cap adds **one unique print master and two printed pieces**: 14 masters,
26 pieces total. Six added hardware rows bring the hardware inventory to 44.
The release contains 37 files: 14 STEP/STL pairs, three assembly STEPs,
three PNGs, German guide, BOM and manifest.

Changed source: parameters, head, frame, payoff, assembly, export and the new
service-audit module. Changed tests: all six tooling test modules. The preview
script renders the revised hardware and full removal stages. Updated both
`docs/winding-tool-assembly.md` and the German source/release operator guide,
including hardware tables, assembly order, bench clearances, feet/supports,
keeper removal, supported head handling, free workspace and measured limits.
All affected release artifacts are regenerated; no V5 artifact or production
`PRINT_SOURCES` entry is changed.

## Visual inspection

Opened all three regenerated PNGs with `view_image`, `detail: original`, at
their native **2000 x 1400** resolution:

- **Reference:** two independent modules, shaft/manual crank, new bearing
  caps/left locator note, four payoff feet, bench and inserted short key are
  clear. The B-to-A wire arrow and legend remain readable without clipping.
- **Range/removal:** three head settings retain all 18 numbered tape stations.
  Below them, actual CAD snapshots show the 220 mm shaft pull, 200 mm head
  lift and final 50 mm axial coil exit. The brown annulus is distinguished
  from the head, and the caption states its finite axial/radial/tape bounds.
  Keeper/pin handling, helper support and unchanged uprights/caps are explicit.
- **Exploded:** both caps and the two left metal collars appear with the 608
  group. New feet remain visible under the payoff base. Labels distinguish
  one complete 51105 from its three motion members. The fastener groups and
  1–15 callouts are legible; this remains a grouped, not individual-fastener,
  explosion. No label is clipped or overlaps another text block.

All drawings retain their prototype/physically-unchecked footer and the exact
warning: **Akkuschrauberbetrieb ist nicht freigegeben**.

## Limitations and handoff

These are CAD-verified workshop prototypes, not validated machines. Printed
strength, supports, wear, actual bearing lands, pin fits, endplay, stiffness,
retainer keeper selection, spring properties, useful brake drag, enamel
protection, electrical properties and cassette fit require physical trials.
The contact circles remain default Ø110–145 with a calculated Ø127 reference.
The 6.35 mm hex interface remains future-only; powered operation is unapproved.
Motion/translation checks sample positions, not continuous certified sweeps.
Hands/support fixtures and detailed purchased keeper clips are not modeled.
Coil removal requires the documented helper and clear workspace.

All seven final-review findings are implemented and verified within this
single fix-wave commit. The staged change contains 38 focused files, including
this report and the synchronized generated artifacts. The next decision is
the parent's final review/integration; no merge or push was performed.

Commit subject: `fix: make winding tool serviceable`. The containing commit
hash and clean post-commit status are supplied in the parent handoff after
fresh Git checks; this report avoids a self-referential commit hash.
