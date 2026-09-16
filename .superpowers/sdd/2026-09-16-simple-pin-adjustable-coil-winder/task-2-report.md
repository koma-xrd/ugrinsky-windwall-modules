# Task 2 — pin-adjustable wheel and reusable shoes

## Changes

- Replaced `src/windwall/winding_head.py` with a single six-spoke printable wheel,
  one reusable shoe master and rigidly transformed shoe occurrences.
- Replaced `tests/test_winding_head.py` with physical solid, clearance, engagement,
  retention, envelope, release, label and determinism regressions.
- Added this report. No downstream source, documentation, exports or releases
  were edited; this task intentionally replaces the upstream API.

## Coordinator rulings and the geometric obstruction

The following records the initial rulings. The fix-round-1 section below
supersedes the midpoint-angle ruling and the original release verification.

The original task brief required three fixed global station rays per invariant
shoe at every diameter. The coordinator first permitted elongated corridors but
required them to remain in the 100 mm six-sector envelope. This is impossible:

    minimum shoe sector: 0 <= r <= 50 mm, -30 <= theta <= 30 degrees
    maximum placement: (x,y) -> (x+50,y)
    new angle: atan2(r*sin(theta), 50+r*cos(theta))

The maximum occurs at r=50, theta=30: (43.301270,25) becomes
(93.301270,25), whose angle is exactly 15 degrees. The +/-20-degree rays cannot
intersect that translated sector, even for zero-width corridors. A minimum
point at theta=40 degrees, (38.302222,32.139380), is needed to reach 20 degrees
after translation; it exceeds the permitted half-sector by 10 degrees.

The coordinator consequently ruled that the spec's **nominal** pitch controls:
keep 18 distinct physical passages on invariant shoes, use exact nominal guide
angles at the 150 mm midpoint reference, and report actual angles elsewhere.
`tape_station_angles` remains the nominal/reference tuple. The outer two
passages are open end reliefs. Their guide anchors are local X=-8 mm,
Y=+/-24.3860057 mm; the guide-corridor center lies in open space and does not
assert that the nominal ray lies on an outer contact land. Rounded lands end
slightly inside those outer nominal rays. This distinction must be preserved
in downstream drawings and instructions.

The first inward-release geometry also demonstrated neighboring shoe end
interference at the 100 mm setting. The coordinator ruled that complete
tool-free removal is the normative release method, as explicitly allowed by
the approved spec. No alternating axial stagger or imaginary inner pin position
was introduced. Press both tabs and withdraw each shoe forward. `released=True`
returns no assembled shoes and preserves six detached service occurrences in
metadata, located 40 mm forward and excluded from the winding-support envelope.

## Mechanical choices and interfaces

- Wheel rear plane Z=0, front Z=5 mm; six rounded spokes and a central hub are
  one connected body. Rounded transitions join the spokes to the hub.
- Drive socket: regular hexagon, 14.4 mm circumdiameter, through the wheel. The
  14.0 mm test shaft fits and its 30-degree rotated orientation interferes,
  demonstrating torque transfer through shape rather than friction.
- Two rectangular/keyed hole rows at local Y=-5 and +5 mm. Hole positions use
  `diameter_settings_mm` directly and sit 8 mm inside the contact radius, giving
  eleven positions 5 mm apart in radius. All eleven numeric labels are cut into
  every spoke from the parameter values.
- Each shoe has two integral keyed posts plus two independent 0.8 mm retention
  beams. Hooks protrude 0.2 mm beyond hole edges and have rear-accessible tails,
  sloping insertion faces and 0.2 mm inside root radii. Estimated outer-fiber
  strain at the 5.2 mm root-to-hook span is about 0.9%; physical PLA fatigue and
  force testing remain required.
- The short contact arc uses the minimum envelope curvature. One constant
  solid serves every setting. All final contact and tape-mouth edges receive
  0.8 mm fillets in one stable, geometrically sorted operation.
- Tape width is **axial Z**, with 12 mm clear width for 10 mm tape. All
  three reliefs open through the rear contact rim. Their fixed local centers are
  Y=-15, 0 and +15 mm at the default parameters, with positive contact lands
  between them. Actual guide angles use the transformed corridor centers;
  passage identity/order and physical separation are verified at all settings.
- `WindingHeadState(diameter_mm, shoe_radius_mm, release_radius_mm)` records the
  requested setting and assembled support radius. The future completely removed
  support radius is zero; in a released head the current support radius is also
  zero. Wheel material remains behind the winding plane and does not constitute
  a winding contact surface.
- `metadata['detached_shoes']` and `metadata['tape_passage_probes']` contain CAD
  shapes and are not JSON scalar metadata. Downstream exporters should select
  the documented scalar metadata keys explicitly. Detached shoes are service
  occurrences, not additional printable masters.

## Print orientation and limits

- Wheel: rear XY face on the bed, Z upward.
- Shoe master: rotate +90 degrees around X. Pins and tab beams then lie in the
  layer plane; any supports must be confined to inward faces/foot and removed
  without leaving contact-face scars. Wire-contact surfaces require smoothing.
- Both masters are checked for validity, a positive volume and exactly one
  solid. The documented footprint orientations fit within 220 x 220 mm.
- Automated CAD tests do not validate printed fit, snap fatigue, print support
  removal or enamel protection. The design remains a physical-test prototype.

## TDD and verification evidence

Interpreter used for geometry:
`C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe`.
The initial invocation with the default Python 3.14 failed because that Python
does not have CadQuery. It was not treated as RED evidence.

Initial RED command (PowerShell):

```powershell
$env:PYTHONPATH = "$PWD;$PWD/src"
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_winding_head -v
```

Initial RED: one contract test failed because `WindingHeadState` still contained
the superseded requested-diameter/contact-radius fields. After the remaining
requirements were encoded, the suite reported 13 tests, one failure and twelve
errors against the old implementation (missing new API and removed parameter
attributes). No replacement production code preceded these failures.

Additional RED/GREEN cycles:

- Complete-removal release regression failed on the previous inward pose's six
  assembled shoes, then passed after applying the coordinator's removal ruling.
- Root-radius regression failed with zero material at the intended concave root
  fill, then passed after the two root fillets were added.
- Mouth fillet construction initially failed inside OCCT when sequential contour
  operations met at three-way corners. A single stable all-edge fillet resolves
  the final corners and passes the rounded-mouth check and sharp-mouth mutant.
- One early full run was interrupted while its per-probe wheel boolean checks
  were excessively slow. The final suite batches physical empty-space probes
  into one compound and checks intervening material with point classification,
  retaining coverage of every hole and glyph without repeated full-wheel booleans.

Final whole-module command is the same geometry-launcher command above.
Final count/result: **15 tests ran in 230.606 seconds; unittest reported OK**.
The launcher process exited with status **1** after unittest completed, matching
the known native OCP teardown behavior also seen in focused passing runs. The
unittest result and native exit status are distinct; neither is hidden or
rewritten. The parameter suite was also rerun with the same interpreter and
launcher: **5 tests, OK, process exit status 0**.

## Self-review

- No obsolete mechanics, compatibility wrappers, dead helpers or imports remain.
- No duplicate diameter table; labels and holes derive from the parameter API.
- No per-setting shoe remodeling: masters are cached by parameters and all
  diameter changes are rigid transformations.
- Fresh-build signatures compare volume and sorted face geometry/area plus
  topology counts; they match without relying on cached shape identity. Exact
  binary STL/STEP determinism and reimport are for the downstream export task.
- Negative geometry regressions detect missing pins, partial engagement, missing
  hooks, rotated shoes, a mismatched diameter, blocked passages, sharpened mouth
  edges and inadequate release. Axial withdrawal uses the hook's compressed
  clearance envelope; it does not simulate elastic strain or contact force.
- `git diff --check` passed. Numeric dimension labels depend on the installed CAD
  font environment; fresh-build stability was checked on this configured host.

## Handoff concerns

The exact-all-diameter angular requirement and inward minimum-setting release
were replaced only by explicit coordinator rulings. Downstream consumers must
honor nominal/actual angle distinctions and complete removal. The native OCP
teardown issue remains separate from unittest outcomes. Physical PLA fits,
latch life, winding diameter under tension, enamel protection, and final export
mesh quality remain unvalidated.

Commit message: `feat: add pin-adjustable coil wheel`. The containing commit hash
is returned separately in the task handoff.

## Fix round 1 — current release and tape-station contract

This section supersedes the earlier midpoint-angle ruling and the earlier
release proof. Review identified two real defects in the first implementation:

1. The continuous rear/lower contact rim swept through a closed tape loop's
   inner leg during forward shoe removal. The old surrogate outside the winding
   radius could not detect this.
2. Outer corridor identities reversed at 100 mm, and neighboring feed corridors
   overlapped at 100, 110 and 120 mm. Checking only unique angles and each
   corridor's own shoe missed both defects.

### Why the exact midpoint physical angle was removed

For a passage anchor inside the minimum 50 mm radius and its +/-30-degree shoe
sector, translating outward by 25 mm must produce a 20-degree angle at the
150 mm setting under the former ruling. The outermost admissible point obeys:

    theta = 20 degrees + asin(0.5 * sin(20 degrees))
          = 29.84655194 degrees
    (x,y) = (43.36806916, 24.88394215) mm

Its neighboring shoe's symmetric anchor is at most
`2 * 50 * sin(30 degrees - theta) = 0.26781707 mm` away. Anchors at smaller
radius approach the sector boundary further, reducing that separation to zero.
Thus exact midpoint angles are incompatible with distinct 3 mm feed corridors
inside this invariant-shoe envelope. Enlarging corridors cannot resolve this.

The coordinator explicitly removed **all** exact-20-degree physical-center
requirements. `tape_station_angles()` now supplies conceptual sequence labels
only; it makes no geometric claim at any diameter. The obsolete
`reference_diameter_mm` metadata key was removed.

The new fixed side offsets are 15% of minimum diameter: +/-15 mm by default.
Guide centers have local X=-8 mm, so their actual side angles are:

| Setting | Actual side guide angle |
| --- | --- |
| 100 mm | +/-19.65382406 degrees |
| 150 mm | +/-12.61932229 degrees |
| 200 mm | +/-9.26022153 degrees |

At 100 mm neighboring outer guide anchors are 16.01923789 mm apart. Even the
inner corner of each 3 mm-wide feed probe stays within its sector: its largest
absolute angle is `atan2(16.5,32) = 27.27676338 degrees`. Separation increases
as the shoes move outward. Tests verify strict cyclic identity order, honest
angles measured from the actual CAD corridor centers, all-pair corridor
disjointness and clearance from the assembled shoes at all eleven settings.

### Continuous closed-tape release proof

All three relief cuts now continue through the rear/lower contact rim. The
front/upper bridge keeps the shoe connected; there is no trailing outer rim
behind a tape inner leg. The foot remains inward of the central tape fixture.

The regression uses a real closed rectangular tape ring: radial span 4 mm,
axial span 10 mm, 0.25 mm wall thickness, 1 mm tangential width. The central
inner leg starts at local X=-0.5 mm; outer-station inner legs at X=-3 mm and
Y=+/-15 mm follow the curved contact face. Each closed ring is checked clear in
the seated pose.

For the 40 mm axial withdrawal, the exact inverse-motion sweep of each ring is
the rectangular prism covering its radial span and Z=-28 through +22 mm. The
horizontal legs' swept intervals overlap, making this an exact continuous
envelope, not a sparse set of sampled poses. The compound includes all 18 tape
rings; zero overlap with the representative shoe proves its whole withdrawal
clear of its own and neighboring rings. Six-fold rotation symmetry covers all
shoes. This is checked at 100, 150 and 200 mm. It remains a CAD clearance proof
for the explicit fixture dimensions, not a force/friction or elastic-tape model.

### RED/GREEN evidence

All commands used the existing geometry interpreter and launcher shown above.

Initial RED command:

```powershell
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_winding_head.WindingHeadTests.test_closed_tape_ring_clears_the_entire_forward_removal_sweep tests.test_winding_head.WindingHeadTests.test_station_identity_order_is_preserved_at_all_eleven_settings tests.test_winding_head.WindingHeadTests.test_neighboring_physical_passages_are_disjoint_at_all_eleven_settings -v
```

RED result: **3 tests, 25 failed assertions/subtests, 20.827 seconds**. The
continuous closed-tape sweep overlapped the shoe by **2.232737385 mm³**. At
100 mm, neighboring identity angles were **30.1402724 then 29.8597276 degrees**.
Passage overlap was **124.707658145 mm³** at the minimum, with additional overlap
at 110 and 120 mm. These failures preceded the production corrections.

P1-only GREEN command selected
`test_closed_tape_ring_clears_the_entire_forward_removal_sweep` after opening the
rear rims: **1 test, OK, 14.819 seconds**, process exit 1 after native teardown.

Combined focused GREEN selected the three RED tests plus
`test_actual_tape_angles_describe_physical_corridors_without_nominal_claims`:
**4 tests, OK, 17.470 seconds**, process exit 1 after native teardown. Coverage
was then expanded from the central ring to all three rings and all 18 global
sweeps, and from nearest-neighbor pairs to every physical corridor pair.

Final complete head-module command:

```powershell
& 'C:/Users/fi87roy/Documents/GitHub/windwall/.venv/Scripts/python.exe' scripts/run_geometry.py -m unittest tests.test_winding_head -v
```

Result: **18 tests, unittest OK, 264.508 seconds**. The launcher exited **1**
after the successful unittest summary, consistent with the existing native OCP
teardown behavior. `git diff --check` also passed.

### Scope and residual limits

Only `src/windwall/winding_head.py`, `tests/test_winding_head.py`, and this report
changed. No downstream consumers were edited. The public dataclass/function
contract, two keyed pins, wheel geometry, six invariant shoe occurrences,
nominal envelope and complete-removal service state are preserved. Physical
PLA behavior, real tape friction/compliance, and binary export quality remain
prototype-validation work. The native OCP exit status remains separately
reported from unittest results.
