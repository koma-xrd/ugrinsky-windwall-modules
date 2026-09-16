# Task 5 — independent simplified tool assemblies

## Scope and contract

Replaced the assembly and service modules, their integration tests, and the
assembly guide. Task 1 parameters, Task 2 wheel/shoe geometry, Task 3 frame and
Task 4 payoff records are consumed unchanged. No exporter, drawing generator,
root README, German operating guide, generated release or upstream test changed.

`WindingToolAssemblies` has exactly five fields: `winding_jig`, `wire_payoff`,
`ownership`, `parameters`, `audit`. The builder defaults to 150 mm. The public
assembly audit returns a flat `dict[str, bool]`; the builder fails closed if any
gate fails. Re-audits ignore the previously stored `model.audit` values.

Ownership is one record per occurrence, rather than overlapping sets. Records
identify the motion group, printed/purchased source and master. Printed records
carry their construction-to-print rotations. The wheel record also carries the
selected diameter, installed axis height, nominal sequence labels and honest
actual tape angles. The two independent dictionaries use separate local origins.

The winding jig contains 18 occurrences: wheel, six shoes, base, tower, two
outer-ring clips, printed shaft, two shaft collars, crank, grip and two 608s.
The payoff contains six: base, spindle, platter and the separate lower washer,
rolling member and upper washer of one 51105 bearing. Normal motion ownership is
rotating, stationary or bearing-internal. Service poses additionally identify
each parked shoe as service-detached while retaining its actual occurrence.

## Derived inventory

The BOM derives 19 printed occurrences from 12 unique master identities:

| Master | Quantity |
| --- | ---: |
| winding_jig/base | 1 |
| winding_jig/bearing_tower | 1 |
| winding_jig/coil_wheel | 1 |
| winding_jig/contact_shoe | 6 |
| winding_jig/bearing_retainer | 2 |
| winding_jig/printed_shaft | 1 |
| winding_jig/snap_collar | 2 |
| winding_jig/hand_crank | 1 |
| winding_jig/rotating_grip | 1 |
| wire_payoff/base | 1 |
| wire_payoff/printed_spindle | 1 |
| wire_payoff/platter | 1 |

Purchases are exactly two 608 bearings and one 51105 set. The three 51105 CAD
occurrences share a purchase-set identity and remain separately owned and placed.
Optional workshop bench clamps are documented, not added as product BOM rows.

## Mechanical audit method

- All eleven settings are constructed by rigidly repositioning the **supplied**
  six shoe solids. Defects in an input shoe therefore survive every setting.
  Component records provide gauge dimensions, not replacement passing geometry.
- Equal placement uses actual solid centers and the selected radial contact
  envelope. Each shoe must reach the contact band without protruding beyond it.
  Both pin cores must occupy their intended holes, fit the actual wheel and
  retain against a bounded axial displacement. Each hook has its own material
  and loaded-seat probe, so one surviving hook cannot hide a missing second one.
  Pin-seat material is cropped from the actual wheel once per spoke to omit
  remote engraving from booleans.
- Eighteen physical corridor probes must remain open, at least 12 mm axially,
  non-overlapping and cyclically ordered. Their measured center angles must
  match published actual angles. Nominal 20-degree labels are never treated as
  physical pitch, in accordance with the recorded Task 2 rulings.
- Both 608s require actual journal material, four-direction inner-ring/journal
  contact under 0.05 mm displacement, radial seat engagement and positive
  shoulder/clip stops. The rear outer ring must retain its axial float. The front
  bearing and both shaft collars must carry bidirectional axial restraint.
  Conservative seal-band exclusions keep printed stops on their ring lands.
- Actual wheel/shaft and crank/shaft solids require nominal clearance, positive
  polygonal interference after relative rotation, and two axial retention stops.
  The grip must rotate independently and retain at both ends. The tower/base key
  and snaps must engage physically. Nominal member intersections are rejected.
- Continuous enclosing solids cover the full wheel/shoe and crank/grip
  revolutions. Their containment is checked against actual solids; the crank
  must clear the stand, wheel and bench. The initial wheel-bound implementation
  used bounding-box corners, which were too conservative; the final circular
  envelope is explicitly checked to contain the real wheel and shoes.
- Each 51105 interface requires actual axial face support and four-direction
  radial engagement. Platter and spindle sweeps must clear the base, preserve
  float and suspend the spindle before it can contact the stationary floor.
  A continuous upward envelope also reserves the platter's top service space.
- Rear shoe tabs, shaft collars, outer clips, tower snaps, wheel hooks, crank
  tails and the grip end have explicit approach probes. Every printed occurrence
  is measured in its documented print orientation, with a hard 220 mm bed cap.

## Complete coil removal

The default route has a wound/latched pose, followed by four stages per shoe:
release its two tabs, withdraw it 40 mm forward, let its tabs relax back to the
full original solid, and park it 40 mm radially outward. After all six shoes are
service-detached, the taped winding moves 120 mm forward. Wheel, shaft, tower,
base, collars, crank, grip and previously detached shoes stay in every pose.
The winding is held stationary until all shoes are removed; no part teleports
out of the collision set.

The explicit fixture follows the convex rounded-hex offset of the six translated
contact arcs, including the taut straight spans between them. At the minimum
setting it reduces to a circle. It has a 9 mm axial winding with 1 mm radial
build and 18 closed tape loops. Tape spans are 4 mm radial and 10 mm axial, with 1 mm
tangential width and 0.25 mm walls. The closed inner tape legs remain present
through shoe withdrawal. A support-band probe expands around the complete taped
winding by the required 2 mm before winding motion. The route is checked at
100, 150 and 200 mm, using the complete shoe-removal ruling from Task 2.

Every straight translation is checked continuously using initial/end solids and
the union of boundary-face prisms. Sweeping the simpler body inversely describes
the same relative motion. Remote fixed geometry is cropped only outside the
swept bounding box, so it cannot hide an intermediate obstruction. Zero-volume
parallel-face prisms are excluded; an isolated OCCT diagnostic confirmed they
otherwise appear as nominal solids and cause expensive, degenerate booleans.
The full relaxed shoe bounds the tab-relaxation step. Continuity checks compare
each stage to the previous endpoint and bound every latch-state substitution.

## RED/GREEN evidence

All geometry commands used the configured interpreter and launcher:

```powershell
$env:PYTHONPATH = "$PWD;$PWD/src"
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_winding_tool_assembly -v
```

The initial exact simplified BOM test was run before either production module
changed. It reported **1 assertion failure in 0.001 s** because the old assembly
requested the removed `reference_diameter_mm` parameter. The assertion explicitly
reported that the simplified component records must assemble. With the broader
tests added, the old implementation produced **16 tests: 1 failure and 15 errors,
29.812 s**, including the removed `shaft_reference` frame interface.

Early integrated and timing runs were interrupted without completed unittest
summaries while diagnosing costly full-wheel and degenerate swept-face operations.
Later redundant intermediate suites and an 80-test combined run were also stopped
to apply review regressions and run the final upstream checks in a fresh native
process. None of those interrupted runs is reported as a passing suite.
Separate diagnostic invocations established passing 150 mm head, frame, payoff
and complete service checks. The service diagnostic reported no collisions and
2 mm support clearance; these diagnostics are separate from unittest evidence.

Additional review regressions received their own RED/GREEN runs:

- Parked full-shoe geometry: RED **1 test, 1 failure, 38.440 s**. Each compressed
  representation was short by **0.660714286 mm³**. Explicit full-shape relaxation
  before parking made the focused test GREEN: **1 test, OK, 38.243 s**.
- Payoff top access: a connected overhead guard cleared the seated platter but
  prevented lifting. RED **1 test, 1 failure, 0.852 s**; after adding the actual
  upward access envelope, GREEN **1 test, OK, 0.878 s**.
- Rounded winding fixture: the initial nominal circular ring omitted real taut
  spans at 150 and 200 mm. The focused test failed both diameter subtests:
  **1 test, 2 failures, 13.443 s**. The replacement offsets the regular hexagon of
  contact-arc centers, using the component's minimum contact radius. The same
  rounded profile also defines the pre-removal radial clearance band. Focused
  GREEN: **1 test, OK, 13.464 s**, followed by native teardown exit 1.
- Individual engagement: a missing second shoe hook and an enlarged 608 inner
  bore both passed aggregate/core-only checks. Focused RED: **2 tests, 2 failures,
  39.786 s**. Separate hook-material/loaded-seat probes and actual four-direction
  journal/inner-ring displacement contact replace those insufficient checks.
  Focused GREEN: **2 tests, OK, 40.181 s**, followed by native teardown exit 1.

Each focused GREEN process subsequently exited **1** during native teardown,
matching the known Windows/OCP behavior. Unittest `OK` and the nonzero process
exit are reported separately and neither is suppressed.

## Final verification

The unchanged upstream regression command was:

```powershell
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_winding_tool_parameters tests.test_parameters tests.test_winding_head tests.test_winding_frame tests.test_wire_payoff -v
```

Result: **63 tests, unittest OK, 735.597 s**, with no failures, errors or skips.
This comprises 9 parameter, 18 head, 20 frame and 16 payoff tests. The launcher
subsequently exited **1** during native shutdown, separately from unittest `OK`.

The full assembly/service command was:

```powershell
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_winding_tool_assembly -v
```

Result: **21 tests, unittest OK, 1732.192 s**, with no failures, errors or skips
(14 assembly and 7 service tests). This includes all eleven physical settings,
complete taped-winding removal at 100/150/200 mm, and every required negative
regression. The launcher subsequently exited **1** during native shutdown,
separately from unittest `OK`. Together the two completed suites cover **84 tests**.
Runtime is substantial: CAD booleans and continuous three-diameter service checks
are expensive, and the two processes overlapped for part of their execution.

The only production edit after that integration process started was removal of
one unused service-function import. A fresh module-based smoke check imported
both current modules and asserted the five-field dataclass plus every public
entry point. All assertions completed (the one-loop runner printed its result,
1.23 s), followed by native exit **1**. An earlier `-c` smoke invocation was
rejected because the geometry launcher accepts modules or scripts, not `-c`;
that invocation is not test evidence. No geometry or audit implementation
changed after the final full-suite processes started.

Final `git diff --check` completed with exit **0**. A search of the two production
modules and assembly guide found no obsolete cam/follower/slider, rib-bolt, brake,
M3/M4/M8, metal-shaft, felt, spring or adjuster names. The ignored task report is
explicitly included in this task's commit.

## Documentation and self-review

The assembly guide now describes print orientations, tool-free snap order, the
one-locating/one-floating 608 load path, separate 51105 washer ownership, six equal
shoe settings, 18 honest tape positions, complete shoe withdrawal and relaxation,
forward removal, printed-shaft inspection and hand-only operation. It contains
the exact required sentence `Akkuschrauberbetrieb ist nicht freigegeben`.

The new source removes all obsolete ownership, imported records, compatibility
arguments and service helpers. The tests reject the former mechanism and
threaded/purchased retention inventory. Connected obstruction fixtures verify
real collision paths rather than merely relying on invalid multi-solid parts.
The report records only this task's work and no downstream publication claims.

## Remaining limits

No physical validation was performed or claimed. PLA shaft fit and strength,
snap fit and fatigue, bearing dimensions/fit, actual winding dimensions, enamel
protection, stability, release force and production suitability require physical
prototype testing. The compressed-hook envelope is the bounded Task 2 clearance
model, not an elastic-material or force simulation. Bearing references remain
simplified catalog envelopes. Larger or thicker coils and arbitrary workshop
obstacles are not certified by the explicit fixture. Native OCP teardown remains
an environmental concern separate from unittest outcomes. Exporter, drawings,
German operating guide and generated release await their later tasks.

Commit message: `refactor: assemble simple winding tools`. The commit hash is
returned in the handoff rather than embedded self-referentially in this report.
