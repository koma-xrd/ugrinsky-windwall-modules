# Task 6 report: deterministic simple winding-tool core release

Status: complete and verified. The commit hash is returned in the handoff.

## Implemented scope

- Replaced the obsolete exporter inventory with the exact Task 5 occurrence
  ownership and canonical BOM. There are 12 unique printed masters and 19
  printed occurrences; no old aliases or compatibility inventory remain.
- Exported exactly two independent named STEP assemblies:
  `simplified_winding_jig` and `free_running_wire_payoff`. Their component
  geometry, placement and ownership come directly from the audited model.
- Each unique master is exported through the shared `export_part` gates: one
  valid positive-volume CAD solid, STEP round trip, one closed-manifold binary
  STL component, no boundary/nonmanifold/degenerate facets, bed Z=0, portable
  paths and SHA-256 records. The winding-tool exporter does not filter, delete,
  repair or otherwise rewrite STL triangles.
- `bom.json` and `manifest.json` use sorted UTF-8/LF JSON. The manifest records
  PLA, quantities, roles, dimensions/bounds, print orientation and footprint,
  settings 100--200 mm, actual diameter-dependent tape centers versus nominal
  sequence labels, audit evidence, prototype limits and powered operation false.
- Publication removes a stale success manifest first, verifies every core and
  optional-support hash, writes a pending manifest, then atomically replaces
  the success manifest. Part, mesh, STEP, assembly, inventory, BOM, audit,
  support and tamper failures all withhold the success manifest.
- The default support-artifact inventory is intentionally empty under the
  recorded Task 6 ruling. An injectable fail-closed support hook remains for
  Task 7; no drawing, guide or generated release content was authored here.
- The existing CLI signature remains usable with an explicit destination,
  propagates failures, and does not mutate the tracked release for other output
  directories.
- Shared V5 code and artifacts are unchanged. Its regression now explicitly
  rejects every tooling master from global `PRINT_SOURCES` and uses a current
  winding-tool filename in the Windows byte-preservation fixture.

## Exact derived inventory

| Master | Quantity |
| --- | ---: |
| `winding_jig/base` | 1 |
| `winding_jig/bearing_tower` | 1 |
| `winding_jig/coil_wheel` | 1 |
| `winding_jig/contact_shoe` | 6 |
| `winding_jig/bearing_retainer` | 2 |
| `winding_jig/printed_shaft` | 1 |
| `winding_jig/snap_collar` | 2 |
| `winding_jig/hand_crank` | 1 |
| `winding_jig/rotating_grip` | 1 |
| `wire_payoff/base` | 1 |
| `wire_payoff/printed_spindle` | 1 |
| `wire_payoff/platter` | 1 |

The sum is 19 printed occurrences. The BOM additionally contains exactly two
608 bearings and one canonical 51105 bearing assembly. The winding-jig assembly
has 18 named components and the payoff assembly has 6; purchased bearing members
remain separate occurrences and are never emitted as print masters.

## Strict TDD and diagnostic evidence

The required stale-inventory regression ran before exporter implementation.
Against the untouched exporter it reached the real build and errored after
459.693 s at the removed nested `audit['valid']` contract. The rewritten test
module against the old production code then produced 22 errors across 13 tests
in 16.565 s, demonstrating missing ownership-derived inventory, current
assemblies, fail-closed hooks and manifest fields before implementation.

The first real core export exposed two source topology defects. Under the parent
scope ruling, focused raw-STL regressions were added before either source edit.
At unchanged release tolerances they failed in 15.975 s with:

| Fresh source master | Components | Boundary | Nonmanifold | Degenerate |
| --- | ---: | ---: | ---: | ---: |
| contact shoe before repair | 1 | 18 | 18 | 18 |
| payoff spindle before repair | 1 | 0 | 4 | 0 |
| both current sources | 1 each | 0 | 0 | 0 |

The final focused source run passed both tests in 34.953 s. These tests call
raw `exportStl` directly on fresh masters at the default absolute linear and
angular tolerances, so the result cannot be attributed to exporter sanitation.

### Source-level topology corrections

- The shoe shell now revolves a rounded axial profile and constructs the six
  0.8 mm upper mouth lips as analytic quarter-rounds after stable vertical-exit
  fillets. This eliminates the collapsed three-way fillet caps while retaining
  the approved tape corridors, contact surfaces, keyed pins, mouth radius,
  service geometry and outer envelope. Default-master CAD volume changed from
  6089.518161882361 to 6095.997782191569 mm3: +6.479620309208 mm3, approximately
  +0.1064%. All Task 2 geometry/contact/service regressions pass.
- The payoff spindle's four transverse upper reliefs now overlap the longitudinal
  relief by 0.1 mm. Their outside extent remains exactly +/-6.5 mm; only the
  former exact-touch inner limit moves from +/-2.5 to +/-2.4 mm. This replaces
  four-sheet knife edges with real cut overlap without changing drive, journal,
  detent, bearing, axial-contact or service interfaces. All Task 4 regressions pass.

The assembly-derived printed shaft was topologically valid but its round tangent
meshed about 0.001 mm above the CAD bed datum. A focused regression was RED
before the release orientation record existed. The effective `(90, -30, 0)`
Euler orientation preserves the Task 5 axis-parallel placement while phasing a
real planar drive face onto the bed. The manifest records both the Task 5
ownership rotation and effective release rotation. CAD volume and mesh facets
are unchanged; no tolerance or origin gate was relaxed.

## GREEN verification

All commands used the repository virtual environment, `scripts/run_geometry.py`
and `PYTHONPATH=$PWD;$PWD/src` from the assigned worktree.

| Suite | Result | Runtime | Launcher status after `OK` |
| --- | --- | ---: | ---: |
| `tests.test_winding_tool_export` | 14 tests, `OK` | 1522.053 s | 1 |
| `tests.test_exports` | 11 tests, `OK` | 144.037 s | 1 |
| `tests.test_winding_tool_assembly` | 25 tests, `OK` | 1123.739 s | 1 |
| `tests.test_winding_head` | 19 tests, `OK` | 743.255 s | 1 |
| `tests.test_wire_payoff` | 17 tests, `OK` | 7.530 s | 1 |

The five complete modules total 86 passing tests. Status 1 is the repository's
known Windows/OCP native shutdown condition after unittest has printed `OK`; no
application exception, failed test or clean process exit is claimed. The CLI
negative subprocess independently returned nonzero as required.

Exporter coverage includes exact derived inventory and quantities, all 12 real
STEP/STL masters, both named assemblies, canonical BOM/settings/semantics,
portable paths and hashes, empty default support inventory, each fail-closed
boundary, stale-manifest deletion, tampered artifact detection, explicit CLI
destination and two complete builds in different directories with identical
artifact bytes. Shared exports retained the exact eight-part V5 production
inventory and validated every generated V5 artifact hash.

## Files changed and documentation

- `src/windwall/winding_tool_export.py`
- `src/windwall/winding_head.py`
- `src/windwall/wire_payoff.py`
- `tests/test_winding_tool_export.py`
- `tests/test_winding_head.py`
- `tests/test_wire_payoff.py`
- `tests/test_exports.py`
- this report

The exporter and source helpers have focused docstrings/comments explaining
publication boundaries and the two topology constructions. `scripts/build_winding_tool.py`,
the shared V5 exporter, global V5 `PRINT_SOURCES`, `.gitattributes`, dependencies
and tracked generated releases did not change.

## Self-review and remaining limits

- `git diff --check` passed. The stale-name scan found obsolete terms only in
  the explicit rejection list and negative tests. No temporary diagnostics,
  generated release, dead compatibility helper, broad exception suppression or
  output-directory-dependent serialization remains.
- Inventory counts are computed from ownership; the tests compute their expected
  set and sum independently rather than hardcoding a former release count.
- Physical printing, PLA shaft strength/fatigue, snap and bearing fits, actual
  winding diameter/repeatability, enamel protection, payoff stability, release
  force and continuous/production use remain unvalidated. Hand-crank operation
  only is recorded; powered operation is not approved.
- Task 7 must provide and verify the new drawings and German operating guide via
  the retained support hook before committing a complete tracked release.

## Review round 1: publication boundary hardening

This round closes the three Task 6 P2 findings without adding Task 7 content,
changing the default empty support inventory, altering source CAD, filtering or
repairing a mesh, or committing a generated release.

- Supporting-artifact inventory paths can no longer claim the publisher-owned
  root `manifest.json` or `manifest.pending.json`. Validation is
  case-insensitive and rejects Windows aliases such as trailing dots/spaces;
  existing filesystem aliases to either publisher manifest are also rejected.
- Support paths are parsed as portable POSIX-relative paths. Backslashes,
  rooted/absolute paths, drive or alternate-data-stream colons, traversal,
  control characters and non-portable trailing-dot/space components are
  rejected. Accepted paths are normalized, resolved against the release root,
  proven to remain beneath it and only then hashed. Duplicate Windows aliases
  and duplicate resolved targets are rejected.
- The public export boundary now owns cleanup for both publisher manifests.
  Both are removed before a build and again in a `finally` block on every
  unsuccessful exit, including a support provider that writes either file and
  then returns a reserved inventory entry or raises.

### Review-round TDD evidence

The reserved-name and external-path tests were added before the hardening.
Against the pre-fix implementation, the two focused tests failed in 14.963 s
with 15 failing subtests: all nine publisher-name aliases were accepted, while
Windows traversal, drive/rooted and external paths were either accepted or
reached hashing outside the release. The two publication-cleanup regressions
then failed in 123.069 s: reserved manifest inventory published with the wrong
hash, and a provider exception left its written success manifest behind.

The focused GREEN reruns passed the two path tests in 16.901 s and the two
publication-cleanup tests in 122.379 s. Existing BOM, audit, six-boundary and
tamper failure tests now seed or check both publisher manifests, proving the
cleanup invariant across every unsuccessful export boundary in this module.

The previous report sentence saying exporter coverage included "two complete
builds in different directories" was imprecise: that former test reused the
fixture model and mocked successful audits. It has been replaced by an exact
fresh-source test. The new test clears every winding-tool geometry cache before
each build, calls the public exporter twice without dependency or audit mocks,
inserts an unrelated export between them, and compares every emitted core file
byte-for-byte across both release trees. The fresh build and real-audit form of
this test already passed against the pre-hardening production path in 595.267 s,
demonstrating that it adds real determinism coverage rather than disguising a
behavior fix.

### Review-round GREEN verification

All commands used the assigned worktree, repository virtual environment,
`scripts/run_geometry.py` and `PYTHONPATH=$PWD;$PWD/src`.

| Suite | Result | Runtime | Launcher status after `OK` |
| --- | --- | ---: | ---: |
| `tests.test_winding_tool_export` | 18 tests, `OK` | 1335.935 s | 1 |
| `tests.test_exports` | 11 tests, `OK` | 142.138 s | 1 |
| focused fresh shoe + spindle raw-STL topology tests | 2 tests, `OK` | 13.891 s | 1 |

The full exporter run includes the two uncached, independently constructed,
real-audit builds and byte comparison. The focused source checks still report
zero boundary, nonmanifold and degenerate facets at unchanged release
tolerances. As in the original verification, status 1 is the known Windows/OCP
native shutdown after unittest printed `OK`; no clean process exit is claimed.

Files changed in this review round are
`src/windwall/winding_tool_export.py`,
`tests/test_winding_tool_export.py` and this report. The earlier source CAD
repairs, approved dimensions/interfaces, shared V5 sources and tracked release
content remain unchanged.
