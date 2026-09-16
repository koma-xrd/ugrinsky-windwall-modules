# Task 4 report — free-running upright wire-roll turntable

## Scope and interface

Replaced the former payoff assembly with three printed members (`base`,
`spindle`, `platter`) and exactly three separate purchased 51105 members
(`lower_washer`, `bearing`, `upper_washer`). `WirePayoffParts` exposes those six
members plus `metadata`. `build_wire_payoff(tool_parameters, design_parameters)`
has no setting argument or compatibility wrapper. The platter is 150 mm across
with an integral chamfered 15 mm diameter by 20 mm high pilot.

Changed files:

- `src/windwall/wire_payoff.py`
- `tests/test_wire_payoff.py`
- `.superpowers/sdd/2026-09-16-simple-pin-adjustable-coil-winder/task-4-report.md`

No wheel, frame, assembly, exporter, drawing, documentation tree, or release
artifact was changed. Module documentation and metadata now describe the new
load paths, motion ownership, print orientations, service sequence, and limits.

## RED/GREEN evidence

Commands were run in the assigned worktree. Geometry interpreter:
`C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe`.

```powershell
$env:PYTHONPATH = "$PWD;$PWD/src"
& '..\..\.venv\Scripts\python.exe' scripts/run_geometry.py -m unittest tests.test_wire_payoff -v
```

The first focused interface test was written before replacement code. It failed
on the old implementation with `AssertionError: True is not false` at
`assertFalse(hasattr(parts, 'adjuster'))`: **1 test, 1 failure, 0.339 s**. The
initial attempt using system Python could not import CadQuery; that environment
error was not used as RED evidence. The configured geometry interpreter produced
the intentional assertion failure above.

The broader geometry suite was written before replacement and also failed on
the absent new members, retained old argument, and old footprint/interface.
The initial replacement reached **12 tests, OK**. Two further self-review
regressions each received a separate observed RED before fixes:

- A continuous 1.5 mm annular pilot-wall probe failed by 60.406 mm3. Narrowing
  the keyed plug from 10 mm to 8 mm preserved the wall around the blind socket.
- A spindle-downward probe found zero contact with the platter before the
  spindle could reach the stationary bore floor. Raising the upper detent
  cavity's lower face now catches the spindle first, removing that unintended
  rubbing path while preserving positive axial float.

Final command:

```powershell
$env:PYTHONPATH = "$PWD;$PWD/src"
& '..\..\.venv\Scripts\python.exe' scripts/run_geometry.py -m unittest tests.test_wire_payoff tests.test_winding_tool_parameters tests.test_parameters -v
```

**Unittest result: 23 tests, OK, 4.885 s, no failures, errors, or skips.** This
comprises 14 payoff tests and 9 parameter regressions. **Launcher process exit:
1 after the successful unittest summary**, consistent with the previously
recorded Windows/OCP native teardown behavior. The nonzero process status is
reported separately and is not presented as a clean process exit.

`git diff --check` passed. Git emitted only the repository's LF-to-CRLF working
copy notices.

## Load path and ownership

The canonical `build_51105_reference` supplies all three bearing shapes and
their dimensions; no washer thickness or bearing race is recreated in payoff
code. At default dimensions, the lower washer sits at Z=8 on the base's annular
floor, the rolling envelope occupies its canonical intermediate position, and
the upper washer ends at Z=19. The flat platter underside at Z=19 carries the
load on that upper washer. Axial contact tests use actual solid intersections
after a 0.05 mm probe and require over 75% of the nominal washer annulus at each
load-path interface; the smaller canonical rolling envelope determines the
limiting contact fraction.

The canonical 42.2 mm seat centers the lower washer. The canonical 24.8 mm
spindle journal centers the 25 mm bearing bores. Four-direction 0.25 mm radial
probes detect loss of actual support, while nominal positions have no rigid
overlap. The square plug carries the platter and spindle together. Weight-loaded
washer faces provide the intended stationary lower and rotating upper ownership;
the reference is an envelope, not an internal rolling-contact simulation.

Metadata explicitly owns base/lower washer as stationary,
platter/spindle/upper washer as rotating, and the rolling envelope as bearing
internal.

## Retention, service, and rotation

Two long, relieved lower spindle tongues carry ramped detents inside a continuous
annular base groove. Two smaller relieved upper tongues retain the platter's
keyed socket. The rounded relief ends reduce root stress concentration. Both
detent pairs have lead-in and withdrawal ramps. Actual CAD interference proves
unloaded retention and square-drive engagement. The nominal interfaces allow
0.15 mm axial travel without interference; the upper detents catch a descending
spindle before its end can touch the stationary base floor.

Service sequence is entirely from above: lift the platter so the upper tongues
cam inward, pull the exposed square spindle so the lower tongues cam inward,
then lift the upper washer, rolling member, and lower washer. Opposing finger
recesses expose the lower washer edge. The base has a continuous bench face;
service needs no bench opening or underside control.

Service tests use explicit 0.4 mm upper/0.6 mm lower inward tongue envelopes,
then check intermediate CAD translations against base and bearing members.
These are conservative rigid clearance checks for a released snap state, not
elastic deformation, release-force, fatigue, or manufacturability validation.
All three purchased members also have clear upward removal routes after the
spindle is withdrawn.

Full-turn checks combine conservative continuous solids of revolution containing
the actual spindle/platter with 30-degree rigid-motion samples. Those envelopes
have positive distance from the base, so unsampled angles are covered as well.
The two integral 12 x 50 mm clamp lands at X=+/-85 mm remain outside the platter
envelope. A clamp must stay on its land without projecting into moving geometry.

## Stability and printing

The 190 x 190 mm continuous bench footprint contains the entire centered 150 mm
platter projection. A quasi-static tipping check assumes a horizontal 1 N feed
at Z=43 mm, PLA density 1.24 g/cm3, at least 35% effective printed solid volume,
and zero helpful wire-roll mass. CAD-measured printed volume gives more than
twice the overturning moment in any horizontal direction. This is an explicit
conditional estimate, not force validation; clamp for a taller roll, larger
force, lower print mass, or possible sliding. Prototype mass and actual feed
height must be checked before using the unrestrained base.

Each printed master is a valid, positive-volume single solid. The base is
printed on its flat bench face, platter on its flat underside with pilot up,
and spindle with axis horizontal (90 degrees about Y), keeping slots clear.
Their documented orientations fit the 220 x 220 mm bed. The blind base groove
requires inspection of a short bridge, and spindle support cleanup must leave
the tongues and journal free. Independent fresh builds have matching volume,
area, face count, and zero geometric difference, without a shared cached shape.

## Negative checks and self-review

Mutation tests detect lower/upper washer displacement, missing axial contact,
loss of journal support, reduced axial float, platter/base collision, a service
obstruction above the initially clear assembly, an undersized bench footprint,
and reintroduced obsolete inventory names. Old setting calls are rejected.
Pilot/socket, print-bed, and platter/footprint parameter constraints are covered.

Reviewed source for obsolete brake mechanics, hidden fasteners, dead helpers,
unused imports, accidental drag faces, and duplicated 51105 dimensions. All old
felt/spring/adjuster/screw/nut geometry, adjustment states, service-key geometry,
and old ownership dictionaries are removed. The only source search match for
the old fastener words is the descriptive word `screwless`. Obsolete names in
tests occur solely in rejection regressions.

## Remaining concerns

- PLA fit, snap deflection/retention force, fatigue, print quality, actual
  turntable stability, wire protection, and hand stopping require physical
  prototype testing. No force or powered-operation validation is claimed.
- The canonical bearing model uses reference envelopes and deliberately
  simplified separate washers; internal race and rolling-element physics are
  not modeled here.
- The known native process teardown exit 1 remains unresolved.
- Downstream assembly/export/docs/release consumers still need the later tasks'
  migration to the new six-member interface. They were outside this task and
  were not run as part of the focused verification.

Committed with `refactor: simplify free-running wire payoff`; the commit hash
is supplied in the task handoff.

## Review fix round 1 — completed print-envelope validation

Addressed Important P2: the pilot diameter was not bounded by the nominal disc
check, so a 221 mm pilot could create a valid but oversized completed platter.
The builder now measures each completed printed member in its documented print
orientation (base/platter flat; spindle rotated 90 degrees about Y), and rejects
either bed-plane dimension exceeding `min(print_bed_mm, 220)` with a 1e-6 mm CAD
tolerance. The error identifies the oversized member and applicable bed limit.
This checks the actual finished shape, including integral features.

Focused RED command:

```powershell
$env:PYTHONPATH = "$PWD;$PWD/src"
& '..\..\.venv\Scripts\python.exe' scripts/run_geometry.py -m unittest tests.test_wire_payoff.WirePayoffTests.test_rejects_completed_platter_that_exceeds_the_print_bed -v
```

Before the production change: **1 test, 3 failing subtests, 1.572 s**. Each
failed with `ValueError not raised`: 221 mm pilot on the 220 mm bed, 221 mm pilot
despite a requested 300 mm bed, and 201 mm pilot on a requested 200 mm bed.

A positive boundary regression also builds a completed 200 mm diameter platter
on a 200 mm bed and measures all three actual shapes in their documented print
orientations. This boundary fixture checks printability only; it does not extend
the default 15 mm pilot's physical stability or wire-roll fit validation.

The incidental P3 cleanup was small: the axial contact annulus radii and spindle
sweep journal radius now derive from the shared `DesignParameters` fixture
instead of repeating canonical radii 21, 12.5, and 12.4 mm in the test helper.

Final GREEN command:

```powershell
$env:PYTHONPATH = "$PWD;$PWD/src"
& '..\..\.venv\Scripts\python.exe' scripts/run_geometry.py -m unittest tests.test_wire_payoff tests.test_winding_tool_parameters tests.test_parameters -v
```

**Unittest: 25 tests, OK, 6.477 s; no failures, errors, or skips** (16 payoff and
9 parameter tests). **Native launcher teardown: process exit 1 after `OK`**, as
previously recorded. The existing physical-validation limits remain unchanged.
Only the Task 4 source, tests, and this report changed in the fix.
