# Task 3 — screwless printed wheel stand

## Scope and changed files

- Rewrote `src/windwall/winding_frame.py` with a base, one tower, two identical
  outer-ring clips, two purchased 608 references, a printed shaft, two identical
  shaft collars, a crank with integral grip journal, and a rotating grip.
- Rewrote `tests/test_winding_frame.py` with physical engagement, clearance,
  retention, service, invalid-configuration, print-envelope, and deterministic
  geometry checks, including deliberately defective geometry.
- Added this report. No Task 2 files or downstream assembly, exporter, payoff,
  drawings, release files, or user documentation changed.

Public output is exactly
`WindingFrameParts(base, tower, bearing_retainers, bearings, shaft, snap_collars,
crank, grip, metadata)`. The public builder takes the current
`WindingToolParameters` and canonical `DesignParameters`.

## Coordinator ruling: the rear enlargement must be removable

A single solid with fixed 14 mm sections at both ends cannot pass through an
8 mm bearing bore. The coordinator explicitly ruled that the requirement
describes the **assembled rotating support**, permitting a fixed 14 mm front
wheel drive and a smaller rear polygon inside the removable enlarged crank hub.

The shaft consequently has a fixed 14 mm wheel polygon, two uninterrupted 8 mm
journals, and an 8 mm circumdiameter rear polygon. The rear polygon and every
shaft feature behind the fixed front enlargement fit through an 8 mm bore.
The removable crank hub has a 14 mm outside diameter. No trapped bearing,
split bearing reference, metal shaft, or hidden permanent joint is used.

## Coordinates and downstream interface

Construction coordinates match the head: Z is the winding axis, positive Z is
forward, and local Y is up. To install the head or a construction-coordinate
part, rotate +90 degrees about X, then translate by `(0, 0, axis_height_mm)`.
All returned frame occurrences already have this transform. At the default
200 mm maximum diameter, the axis is 130 mm above the bench and forward is
world negative Y. The base bottom is world Z=0.

Metadata explicitly supplies the head transform, nominal bearing dimensions,
bearing centers, print rotations, and service sequence. It contains no CAD
shapes. `print_rotations_deg` applies in **construction coordinates**: first
undo the installed translation and X rotation, then apply the listed X/Y/Z
rotations in order and translate the lowest face to the print bed. The frame
does not own a transformed head or a second wheel master.

The wheel socket remains Task 2's six-sided 14.4 mm circumdiameter socket. The
shaft's mating 14.0 mm polygon is checked against the actual Task 2 wheel:
assembled clearance, 30-degree rotational interference, both axial stops, and
disengaged-drive rejection. The frame only consumes head socket/envelope
information and preserves complete forward shoe removal.

## Mechanical load path and service

The base is 160 x 110 mm with an 8 mm floor, a deep rectangular tower key,
two raised snap catches, two clamp lands, and four optional through holes.
Key faces carry operating shear and moment. Two independently accessible
cantilever hooks prevent lifting the tower out; pressing the exposed upper
tails inward releases them. External bench clamps are optional workshop
equipment, not product assembly hardware.

The two purchased 608 envelopes use the canonical 8 x 22 x 7 mm dimensions.
They sit at local Z=-40..-33 and -28..-21, with a 5 mm service gap between
the envelopes. Both have 22.2 mm radial seats, outer-ring axial shoulders,
and removable split printed clips in annular grooves. Clip ears project into
open upper service windows. Squeeze the ears together, withdraw the clip
axially, and slide the bearing out after removing the shaft.

Only the front bearing axially locates the shaft. Its outer ring has 0.1 mm
nominal clearance to each axial stop. The two shaft collars sit on opposite
sides of that bearing in 7 mm diameter grooves outside the journals. Each
collar is 1.8 mm thick in a 2.0 mm groove; its 10.2 mm outside diameter stays
within the inner-ring abutment region. There is 0.3 mm nominal collar-to-bearing
clearance on each side. The rear outer ring has 0.6 mm clearance to each axial
stop, accommodating axial tolerance instead of clamping both bearing stacks.

The bearings are simplified annular envelopes. Tests conservatively exclude
printed contact from the seal band between radii 5.25 and 9.6 mm, including
axial displacement; outer retention lands begin at radius 9.8 mm. Upper access
windows interrupt some shoulder circumference, while lower and side shoulders
retain positive axial engagement. No full-ring preload is claimed.

Assembly order:

1. Snap the tower into the base.
2. Insert both bearings from their outward faces and install the outer clips.
3. Insert the shaft from the front; its rear end passes through both bores.
4. Snap both shaft collars radially into the grooves beside the front bearing.
5. Slide the crank onto the rear polygon until its two integral hooks engage
   the rear groove. Spread the exposed tails outward to remove the crank.
6. Compress the integral split grip-journal end and slide on the rotating grip.
7. Push the wheel over its front polygon until the two front-accessible hooks
   retain it against the printed shoulder.

Reverse the sequence for service. Bearing removal does not require breaking a
clip or pressing a fixed enlargement through a bearing. The shaft has no
cross-hole through either journal. The crank has no powered-drive interface.

## Snap geometry and physical assumptions

- Base hooks have 0.2 mm catch overlap; the test verifies release at 0.3 mm
  inward movement. Beams are 1 mm thick with 0.6 mm root fillets. The hook is
  roughly 6 mm above the root: a simple beam estimate is near 1% surface strain
  at the needed deflection; actual printed behavior remains unmeasured.
- Wheel-hook flexures are approximately 1 mm thick with 0.35 mm root fillets
  and about 15 mm root-to-hook length. Both free tips fit inside the actual
  polygonal socket after a bounded 0.6 mm inward deflection. Their narrow hook
  faces avoid the interference caused by a broad rectangular hook at a hex
  vertex.
- Crank beams are 0.8 mm thick, have 0.3 mm outer root fillets, and a roughly
  7.5 mm root-to-hook span. They release by spreading outward through the two
  open hub windows. Estimated surface strain for 0.4 mm displacement is about
  0.9%; this is a prototype assumption, not a fatigue qualification.
- The grip journal has a 2.5 mm split, 0.8 mm root radii, and a roughly 19 mm
  root-to-hook span. Only the two side hooks enlarge its end. The full tips fit
  through the 8.6 mm grip bore after 0.6 mm inward displacement per side.
  A continuous oversized circular bead failed this test and was removed.
- Shaft collars have a 6.8 mm open throat that spreads over a 7 mm groove.
  Their accessible split faces are reached through the tower windows. They
  are printed flat; the continuous C arcs provide compliance without a
  short highly strained cantilever.
- Outer clips have 23.8 mm outside diameter inside 24.2 mm grooves. Their split
  and ears permit inward compression for insertion through the 22.2 mm seat.
  Actual squeeze force, fit and durability need printed-coupon testing.

Release-tip translations are geometric bounds on flexed tips, not elastic
finite-element analysis or validated insertion-force calculations. Nominal
8 mm PLA journals require finish/fit evaluation against the user's bearings.

## Access, sweep, print and determinism evidence

At 100, 150 and 200 mm, every rear shoe-latch approach probe clears the stand.
The complete tower lies behind local Z=-18.5, while shoes begin in front of
Z=-5. The base lies below local Y=-113. This plane separation proves stand
clearance for continuous forward withdrawal, beyond checking seated solids.
Task 2's closed-tape continuous withdrawal regression is also run unchanged.

A radius-63 mm cylinder spanning local Z=-87..-53 contains every crank and
grip position over the full 360-degree sweep. It clears the tower, base, wheel,
bench plane, and two specified 20 x 40 x 55 mm clamp envelopes over the lands.
This is a continuous rotational superset, not sparse angular sampling. It
does not promise compatibility with every possible external clamp shape.

Every unique master is checked valid, positive-volume, and exactly one solid.
The documented print orientations fit the 220 x 220 mm bed. The base is printed
on its bottom, tower on its side, shaft/crank journals parallel to the bed,
clips/collars flat, and grip on its end. Supports must not obstruct flexure
slots; journal surfaces need cleanup. Repeat uncached frame builds have equal
volume, topology counts, and sorted face-type/area signatures. Exact binary
STL/STEP hashes and reimport remain for the downstream export task.

## TDD and verification

All geometry commands used:

```powershell
$env:PYTHONPATH = "$PWD;$PWD/src"
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_winding_frame -v
```

Initial focused RED: one contract test failed because `WindingFrameParts`
still exposed `uprights`, old head retention, and hardware fields. This was
run before any production replacement. Adding the geometry tests then hit
the old builder's removed `shaft_diameter_mm` parameter; that API error is
reported separately from the valid initial RED assertion.

The first implemented full suite ran 12 tests in 25.094 seconds, with three
failures: grip front retention clearance, collar access, and a crank/shaft
overlap. Corrections left a 0.023577 mm³ hook-ramp overlap, which a focused
drive run then eliminated: one test, OK in 20.151 seconds.

Additional RED/GREEN evidence:

- Compressed wheel tips exceeded their socket by 0.229378 mm³ per side;
  compressed grip tips exceeded their bore by 1.294054 mm³ per side.
  All four failing subtests passed after narrowing wheel hooks and replacing
  the grip's circular bead with side hooks.
- The base hook still overlapped the catch by 0.48 mm³ after 0.3 mm release;
  reducing required hook deflection made the release check pass.
- Root-material probes and long-slot probes failed before adding filled shaft
  and grip root radii and increasing the crank/grip free spans.
- A crank-root material probe returned zero before its root fillet; a 26 mm
  bearing-seat mutation built silently before explicit seat limits were added.
- The complete intermediate frame module passed 15 tests in 26.324 seconds,
  then 17 tests in 26.582 seconds. Both unittest summaries said OK; each
  process subsequently exited 1 during the known native OCP teardown.

Final whole-frame plus whole-head regression command:

```powershell
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_winding_frame tests.test_winding_head -v
```

Final combined result: **37 tests ran in 251.887 seconds; unittest reported OK**
(19 frame tests and 18 unchanged Task 2 head tests). The launcher then exited
with process status **1**, matching the known native OCP teardown behavior.
The successful unittest outcome and failing native process status are separate
and neither was suppressed or rewritten. `git diff --check` also passed.

## Self-review and remaining limitations

Removed the former uprights, metal-shaft references, cross pins, head-retaining
hardware, preload mechanism, fastener inventory, and powered socket. No dead
old-frame helpers or unused imports remain. The only purchased inventory is
two 608 bearings. No Task 2 nominal/actual station-angle contract was changed.

Negative geometry tests reject missing or displaced outer clips, axially
displaced bearings, translated or unrestrained shafts, disengaged polygonal
drives, obstructed collar access, separated tower/base, a crank collision,
and cross-cut weakened journals. Shaft journals, snap interfaces and service
clearances are tested with actual CAD intersections rather than metadata alone.

The report and module docstring are the documentation changed in this task;
the downstream task owns the user guide and assembled/exported release.
Printed fit, shaft strength, latch fatigue, axial compliance under load, enamel
protection, hand forces, stability without bench clamps and export mesh quality
are not physically validated. Neither the tests nor the simple strain estimates
approve production use. The native OCP teardown status remains a separate
environment concern from the unittest outcomes.

Commit message: `feat: add screwless printed wheel stand`.

## Fix round 1 — continuous outer-clip ear withdrawal

Review found that the squeeze-ear windows covered the seated clips but stopped
before the housing's outward faces. The ears therefore hit an end lip after
leaving the annular groove. The original seated-access test could not establish
the documented service path. This section supersedes that service-clearance
claim in the original report.

The rear ear window now runs from local Z=-44.1 to -40.4, beyond the rear
housing face at -44. The front window runs from -21.1 to -18.4, beyond the
front housing face at -18.5. Both remain 10 mm wide, with their lower edge at
Y=10. The bearing seats, groove dimensions, clip masters, and lower/side
retaining lips are unchanged. Only the tower's two exit openings changed.

The new regression uses the actual clip CAD. It contracts the annular body
from 11.9 to 11.0 mm radius and retains the original uncompressed ears as a
conservative additional envelope. Thus the full 14.4 mm ear height remains
in the test; clearance cannot be obtained by replacing the clip with a small
ring or shrinking away the offending ears. As each clip has a constant axial
section, extending that section over six millimeters gives its continuous
outward withdrawal sweep. Both final clip positions are wholly beyond the
corresponding housing face. A deliberately restored thin exit lip is rejected
by the same intersection check on each side.

This is a bounded geometric compression/withdrawal proof. It does not simulate
clip strain, squeeze force or fatigue. The original physical-fit limitations
remain in effect.

Focused RED and GREEN command:

```powershell
$env:PYTHONPATH = "$PWD;$PWD/src"
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_winding_frame.WindingFrameTests.test_compressed_bearing_clips_clear_the_entire_outward_withdrawal -v
```

- Before production changes, the final conservative fixture ran one test in
  **13.756 seconds**, failing both direction subtests. The continuous sweep
  intersected the old tower by **29.467300564 mm³ rear** and **1.733371176 mm³
  front**. An earlier uniformly contracted-ear fixture also failed both sides;
  the final fixture intentionally preserves the full ear height instead.
- After extending only the exit openings, the same focused regression ran
  **one test in 13.643 seconds; unittest OK**. The process then exited **1**
  during the known native OCP teardown.
- Final complete frame and unchanged head command:
  `scripts/run_geometry.py -m unittest tests.test_winding_frame tests.test_winding_head -v`.
  Combined result: **38 tests in 246.284 seconds; unittest OK** (20 frame
  tests and 18 head tests). The launcher subsequently exited **1** during the
  known native OCP teardown. `git diff --check` passed.

Changed files for this fix are the frame source, its test module, and this
report. No downstream files or Task 2 source/tests changed. Self-review confirms
that the original axial/radial bearing engagement tests remain in the complete
regression and the new negative case detects a reintroduced exit obstruction.
