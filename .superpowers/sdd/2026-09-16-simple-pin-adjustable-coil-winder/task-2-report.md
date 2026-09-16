# Task 2 — pin-adjustable wheel and reusable shoes

## Changes

- Replaced `src/windwall/winding_head.py` with a single six-spoke printable wheel,
  one reusable shoe master and rigidly transformed shoe occurrences.
- Replaced `tests/test_winding_head.py` with physical solid, clearance, engagement,
  retention, envelope, release, label and determinism regressions.
- Added this report. No downstream source, documentation, exports or releases
  were edited; this task intentionally replaces the upstream API.

## Coordinator rulings and the geometric obstruction

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
- Tape width is **axial Z**, with 12 mm clear width for 10 mm tape. The central
  relief is a slot; the other two open at the shoe ends. Positive contact lands
  remain between the three reliefs. Actual guide angles are computed from the
  transformed corridor anchors; passage identity is stable across all settings.
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
