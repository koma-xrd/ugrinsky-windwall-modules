# Task 7 report: simple coil-winder release and operating guide

Status: complete; final release built, audited, visually inspected and tested.
Native teardown errors and the initial unreproduced audit failure remain explicit
limitations below, not hidden successes.
The final commit hash will be returned in the implementer handoff.

## Scope

- Replaced the old renderer with three fixed 2000 × 1400 CAD-derived drawings.
  Every assembly occurrence comes from the current model. Fixed orthographic
  cameras, fresh copied meshes, stable depth ordering, DejaVu Sans, palette,
  PNG metadata and filenames are explicit. No V5 geometry is consumed.
- Replaced the German operating guide completely, including all canonical
  printed masters and quantities, the two 608 bearings, one complete 51105 set,
  PLA orientations, wire-surface cleanup, screwless assembly/service, all eleven
  settings, honest physical tape angles, complete shoe removal and forward
  taped-coil removal. Safety and prototype limitations are explicit.
- Replaced only the exporter's empty support hook and its introductory docstring.
  The existing publication, containment, reserved-name cleanup, BOM, topology,
  STEP, audit, hashing and atomic-manifest gates are unchanged.
  Under the additional narrow ruling below, one stale coordinate-frame label
  was also corrected; no geometry or service direction changed.
- Updated only the README winding-tool section: two simple independent manual
  modules, 100–200 mm adjustment, screwless PLA, current links and V5 isolation.
- Added support-inventory/content, guide/BOM synchronization, actual exploded
  occurrence ownership, PNG dimensions, independent-render byte equality,
  complete manifest inventory/hashes and Windows checkout regressions.

## Recorded narrow scope ruling

The parent authorized one `.gitattributes` rule:
`docs/serpentine-coil-winding-tool-de.md text eol=lf`.
Without it, Windows `core.autocrlf=true` converts the source guide to CRLF while
the existing `release/winding-tool/** -text` rule preserves the generated LF
guide. That breaks the required source/release byte equality after checkout.
The new rule affects exactly the source guide; V5 rules, release byte-preservation
rules and generated STEP `-diff` rules remain intact.

The parent additionally authorized correcting the existing manifest's stale
`coordinate_frames.assembly_step` label from winding-jig axis X to axis Y
(forward −Y). `installed_shape` rotates construction Z +90° about X and the
audited final service motion is `(0, -120, 0)`. The focused regression exercises
that real transform and service direction, then reads the published manifest.
It failed against the old label in 72.839 s before the one-line metadata change.
The focused GREEN run passed in 73.220 s, followed by native launcher status 1.

## Strict TDD evidence

Before support implementation, the two focused support tests failed in 30.030 s:
all four required paths were absent from the Task 6 empty support hook. The
tests reached assertion failures, not import errors. They then passed in
230.462 s with all four files, exact current BOM/guide content, 2000 × 1400 PNGs,
complete occurrence groups and independent source-model render byte equality.
Minor subsequent drawing polish corrected the reference rotation arrow to use
the actual CAD projection and added the coil's forward-motion arrow.

The isolated Windows checkout test also ran RED before the attribute rule. Its
first attempt exposed read-only Git objects during fixture cleanup; the test's
own cleanup was corrected, then the expected source-CRLF/release-LF assertion
failed in 0.257 s. After the narrow rule, both attribute tests passed in 0.294 s.
The fixture uses a fresh temporary Git index and `checkout-index`, not a string
match pretending to exercise checkout. The failed temporary repository was
removed using its exact verified worktree-local path.

Each successful unittest run above printed `OK`; its launcher subsequently
returned 1 due to the known Windows/OCP teardown condition. A clean native exit
is not claimed.

## Real-build observation and cold-audit evidence

The first real default CLI failed before support publication:
`Winding-tool assembly invariants failed: removal_100, removal_200`.
This was an application failure, followed by native status -1073741819, not a
successful build followed only by teardown. No success manifest was created.
The source CAD and audit files were unchanged.

Three fresh separate-process cold diagnostic runs then wrapped the real
`_service_checks` only to print its result and called the real cold assembly
builder. Each imported the unchanged geometry/service code anew. All forty
assembly gates and all seven service gates at each of 100, 150 and 200 mm
passed in every run. Every service setting returned empty `collisions` and
`errors` arrays and `radial_support_clearance_mm = 2.0`.
No audit result was mocked and no geometric predicate, tolerance or gate was
relaxed. All three completed their audit output before native launcher status 1.
The original observation was not reproduced; its cause remains unresolved.

| Assembly gate | Cold 1 | Cold 2 | Cold 3 |
| --- | --- | --- | --- |
| required_members | true | true | true |
| ownership | true | true | true |
| valid_solids | true | true | true |
| bearing_catalog_dimensions | true | true | true |
| independent_tools | true | true | true |
| equal_shoe_positions | true | true | true |
| wire_contact_envelope | true | true | true |
| two_pin_engagement | true | true | true |
| tape_corridors | true | true | true |
| actual_tape_angles | true | true | true |
| head_rotation_clearance | true | true | true |
| bearing_608_engagement | true | true | true |
| locating_floating_load_path | true | true | true |
| shaft_axial_restraint | true | true | true |
| positive_polygon_drives | true | true | true |
| crank_full_rotation | true | true | true |
| jig_full_rotation_clearance | true | true | true |
| stand_snap_joint | true | true | true |
| member_collision_clearance | true | true | true |
| bearing_51105_ownership | true | true | true |
| bearing_51105_load_path | true | true | true |
| payoff_free_rotation | true | true | true |
| payoff_top_access | true | true | true |
| snap_access | true | true | true |
| complete_coil_removal | true | true | true |
| print_bed | true | true | true |
| setting_100_geometry | true | true | true |
| setting_110_geometry | true | true | true |
| setting_120_geometry | true | true | true |
| setting_130_geometry | true | true | true |
| setting_140_geometry | true | true | true |
| setting_150_geometry | true | true | true |
| setting_160_geometry | true | true | true |
| setting_170_geometry | true | true | true |
| setting_180_geometry | true | true | true |
| setting_190_geometry | true | true | true |
| setting_200_geometry | true | true | true |
| removal_100 | true | true | true |
| removal_150 | true | true | true |
| removal_200 | true | true | true |

Each service cell below gives results at **100 / 150 / 200 mm**, in that order.

| Service gate | Cold 1 | Cold 2 | Cold 3 |
| --- | --- | --- | --- |
| snap_access | true / true / true | true / true / true | true / true / true |
| wound_closed_tape | true / true / true | true / true / true | true / true / true |
| route_continuity | true / true / true | true / true / true | true / true / true |
| motion_ownership | true / true / true | true / true / true | true / true / true |
| all_shoes_detached | true / true / true | true / true / true | true / true / true |
| radial_support_clearance | true / true / true | true / true / true | true / true / true |
| complete_coil_removal | true / true / true | true / true / true | true / true / true |

## Visual review

All three final tracked PNGs were opened with local image tooling at their
full 2000 × 1400 resolution, after the final-source release build. The corrected
preview images had also been inspected before publication.

- Reference: six gold shoes on the vertical blue wheel, twin keyed hole rows,
  one-sided stand, hand crank and rotating grip are distinct. A clearly labeled
  second view exposes the printed shaft, both 608 envelopes and both shaft
  snap collars; larger outer-ring clips are distinct in the assembly groups.
  The independent payoff shows its 150 mm platter, 15 × 20 mm pilot and a dashed
  upright-roll loading example. The 51105 beneath the platter is identified;
  its separate members are visible in drawing 03. Rotation and B → A feed
  arrows are clear. No obsolete mechanism is shown.
- Range: the 100/150/200 mm envelopes and all eleven values 100–200 are readable.
  Six equal shoe settings and both hole rows remain visible. Stations 1–18
  identify actual passage locations without claiming physical 20-degree pitch.
  The actual per-shoe offsets are ±19.65°, ±12.62° and ±9.26° at the three shown
  diameters. The enlarged back-side shoe view clearly exposes three distinct
  tape passages, both keyed pins and their release tabs.
- Exploded/operation: all 18 jig and 6 payoff occurrences appear exactly once
  in the separated assembly groups. The 51105 lower washer, rolling member and
  upper washer remain separate and have explicit stationary/internal/rotating
  ownership. The two 608s, two outer clips, printed shaft and two snap collars
  are countable. The bottom sequence retains all actual members, including
  six detached shoes and the taped winding; it shows closed tape, complete
  shoe removal, then forward coil travel while structural parts remain fixed.
  Assembly/service order is stated. No label or geometry clipping was found.

## Safe release replacement

Before the first build, the exact resolved paths were checked:

- old release: the assigned worktree's `release/winding-tool`;
- backup: the same worktree's `build/task-7-previous-winding-tool`.

Both were checked against the literal intended worktree path; an existing
backup or any release reparse point would abort. Native PowerShell `Move-Item`
preserved the complete old 37-file release in that backup. The failed build
left the new destination empty. The retry verified that empty destination and
the still-present backup before running the unmodified real CLI again.
The backup was preserved through the complete final audit.

The exact CLI retry subsequently published all 32 expected files and its success
manifest before the known native teardown status -1073741819. That process
started before the approved axis-label correction, so the verified candidate
was moved to the separately resolved worktree-local
`build/task-7-pre-axis-release`. The final-source CLI then started from an absent
default output directory. It published all 32 files and printed its success
summary before native teardown status -1073740940. Both backups were preserved
until the full exporter suite completed. No release file was edited by hand.

After all tests passed, the final read-only release audit passed again with
exit 0. The exact worktree/build parents and both backup targets were resolved
again, checked against their literal absolute paths and checked for reparse
points. File counts remained 37 and 32. Only those two verified backup
directories were removed with native PowerShell `Remove-Item -LiteralPath`.
The obsolete release is recoverable from Git at Task 6 commit
`119c6b0293e14d7da17dd14e6bcbb33cd16608a4`; the intermediate candidate is
regenerable. The final release was not modified during cleanup.

## Final-source build and release audit

The exact default build command was run with the repository virtual environment:
`python scripts/run_geometry.py scripts/build_winding_tool.py`.
The CLI reported twelve unique print candidates, two STEP assemblies and the
default manifest path. Native teardown status is reported separately above.

The independent read-only audit completed with exit 0 and established:

- exactly 32 files: twelve STL/STEP pairs, two assemblies, BOM, three PNGs,
  German guide and manifest; no stale filenames or extra unmanifested files;
- all 31 non-manifest SHA-256 values match the manifest;
- twelve printed masters representing nineteen printed occurrences, two 608
  bearings and one complete 51105 bearing set;
- all forty assembly gates and every STL topology/orientation/STEP check pass;
- exactly four required supporting-artifact paths; all PNGs are 2000 × 1400;
- source and generated guide are byte-identical, README links exist and the
  approved Y / forward -Y frame description is present;
- no V5 source or generated release changed.

Final manifest SHA-256:
`eb1c938b29e870f58732f2da0dcbd8b98bf6bf63b72c3c120bd231bdd0a26980`.
Source and generated guide SHA-256:
`4007972e2bd110774ebd0025a9353d6784afc918e5eac9f9c12b997381f0b312`.
All 31 non-manifest artifacts are also byte-identical to the separately built
pre-axis candidate. Only its manifest's approved frame metadata differs.
The complete exporter suite's real-build regression subsequently passed two
additional uncached, fully audited builds. Their complete 32-file releases,
including manifests, are byte-identical; neither reproduced the removal failure.

Shared V5 exporter regression command:
`python scripts/run_geometry.py -m unittest tests.test_exports -v`.
All eleven tests passed in 145.138 s, followed by native teardown status
-1073741819. This is a passing unittest result, not a clean native exit.

Complete winding-tool exporter command:
`python scripts/run_geometry.py -m unittest tests.test_winding_tool_export -v`.
All twenty-three tests passed in 2275.902 s, with the explicit unittest result
`OK`, followed by native teardown status -1073740940. This includes the two
fresh real audited complete-release builds, independent source-model support
render byte equality, exact support inventory/content, canonical BOM/settings,
every master/assembly/hash gate, failure injection, reserved-manifest cleanup,
Windows path containment, source/release guide checkout equality and the
installed-transform/service-axis regression. No gate was skipped or relaxed.

## Self-review

- No obsolete cam, clamp, brake, steel-shaft/collar or superseded master wording
  remains in the renderer, source/release guide, BOM or manifest. The old
  exploded STEP assembly and old master filenames are removed from the release.
- The guide does not approve powered use, speed, electrical properties, fit,
  fatigue, strength, winding quality or physical operation. It explicitly calls
  for a supported trial coil, crack/white-stress checks and enamel inspection.
- BOM tables use canonical rows; angle tables use actual CAD angles. Their
  source/release byte equality is tested, rather than assumed from similar text.
- Exploded groups have explicit part IDs for readable layout, then validate
  exact occurrence coverage and carry the model's actual ownership. They are
  not a replacement print inventory; that still comes solely from Task 6.
- Actual source transforms and service translation support the axis metadata;
  no geometry, movement, predicate or tolerance was changed.
- README links resolve. Full-resolution labels and geometry fit every canvas.
  Every generated artifact is covered by a verified manifest hash.
- `git diff --check` passed. A scoped Git diff confirmed unchanged CAD/service
  files, shared V5 exporter/tests and all `release/v5` artifacts.
- `git check-attr` confirms LF only for the named source guide, `-text` for
  both release trees and `-diff` for winding-tool STEP files. The real Windows
  checkout regression preserves guide equality under `core.autocrlf=true`.
- Scoped staging contains exactly the intended 66 changed paths. All 32 release
  files and the source guide have Git index blob IDs identical to their raw
  working-file bytes (`git hash-object --no-filters`); staging introduced no
  line-ending or binary-byte changes. The staged whitespace check also passed.

## Verification summary

| Check | Result | Native status |
| --- | --- | --- |
| Complete winding-tool exporter suite | 23 passed; 2275.902 s | -1073740940 after `OK` |
| Shared V5 exporter suite | 11 passed; 145.138 s | -1073741819 after `OK` |
| Separate-process cold audits | 3 × 40 assembly gates; 3 × 3 × 7 service gates true | 1 after each completed output |
| Exact final-source default CLI | 32 files and success manifest published | -1073740940 after success summary |
| Final read-only inventory/hash audit | 31 hashes, BOM, gates, PNGs, guide, links and V5 isolation verified | 0 |
| Final tracked drawings | All three inspected at 2000 × 1400, original resolution | Not applicable |
| Verified backup cleanup | Only the 37-file and 32-file scoped backups removed | 0 |
| Diff whitespace review | `git diff --check` passed | 0 |
| Staged scope and raw-byte preservation | 66 scoped changed paths; 32 release files plus source guide byte-preserved | 0 |

## Files and limitations

Source changes: `.gitattributes`, `README.md`,
`docs/serpentine-coil-winding-tool-de.md`, `scripts/preview_winding_tool.py`,
`src/windwall/winding_tool_export.py`, `tests/test_winding_tool_export.py` and
this report. The generated release contains two assemblies, twelve STEP/STL
master pairs, BOM, three drawings, guide and manifest; every obsolete release
file has been removed. Ignored preview/diagnostic scripts are not release files.

Physical printing, fits, shaft strength/fatigue, snap life, winding dimensions,
enamel protection, stopping/stability, release force, electrical behavior,
speed and production use remain unvalidated. The unexplained initial cold
audit failure remains an unresolved observation despite all three required
fresh-process checks, subsequent exact CLI builds and both additional uncached
audited release builds passing. No unstable predicate has been identified or
corrected; no tolerance was relaxed. The Windows/OCP native teardown problem
also remains unresolved. Neither condition is presented as physically validated
or fixed by this documentation/release task.
