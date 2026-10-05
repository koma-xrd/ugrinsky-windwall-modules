# Horizontal manual winding-tool assembly

The PLA prototype consists of two independent manual modules: a horizontal coil
wheel and an upright-wire-roll payoff turntable. Both use the unchanged
190 × 190 mm payoff base and one complete purchased 51105 (25 × 42 × 11 mm).
For simultaneous operation print the common base twice and buy two bearings.
The BOM contains 14 printed occurrences from eight masters; bearing washers and
rolling members are purchased components, not printed races.

See the [German operating guide](serpentine-coil-winding-tool-de.md) for the
canonical BOM, print orientations, tape-angle table and operating precautions.
The [horizontal design](superpowers/specs/2026-09-26-horizontal-coil-winder-design.md)
defines the intended arrangement.

## Winder assembly and operation

1. Put the lower 51105 washer, rolling member and upper washer in the base seat.
2. Insert the horizontal hub through the bearing and base bores. Its guide ends
   at bench Z=1.5 mm, above the 1 mm blind floor. The upper washer carries weight;
   the long clearance pilot supplies radial guidance.
3. Seat the existing wheel on the 14 mm circumdiameter polygon. The flat stop
   sets its underside to Z=33 mm: 25 mm above the base surface outside its boss.
4. Fit all six shoes at the same marked setting, 100–200 mm in 10 mm increments.
   The two 3.40 × 2.90 mm rigid tongues enter 3.50 × 3.00 mm openings with
   0.05 mm nominal clearance per side. Their wider rails form positive stops.
5. Insert the removable top crank and fit its freely rotating printed grip.
   The male hex is 6.35 mm across flats; the female socket is 6.45 mm across flats.
   There is no latch or drive screw. The raised arm clears the shoe tops.
6. Turn slowly by hand, guide the wire and stop the independent payoff by hand.
7. Stop rotation and close all 18 tape wraps through the three channels per shoe.
   Each channel reserves at least 12 mm tangential and axial clearance for 10 mm tape.
8. Remove the crank and grip upward. Lift the taped coil vertically over all six
   still-seated shoes; do not move the shoes inward or unplug them for release.

The shoes retain a rounded 2.7 mm lower support but have zero upper radial
projection. Tape channels open upward, with no crossbar trapping closed loops.
The actual winding is a rounded six-sided envelope, not a calibrated circle.

## Unchanged wire payoff

Use the second common base and second 51105. Retain the payoff's printed spindle,
square platter plug and existing removable detents. The Ø150 mm platter's
Ø15 × 20 mm integral nipple centers the upright supply roll. The platter and
spindle are not mechanically linked to the crank.

For payoff service lift the platter, then the spindle, then the bearing members.
The existing ramps and flexible tongues release the two payoff plugs. Their fit,
elastic behavior and life still need physical verification. The upper plug hangs
the spindle before its guide reaches the blind floor. The payoff geometry,
service checks and common-base STL/STEP bytes are unchanged by this redesign.

## Print and prototype limits

The STL masters are already oriented and translated to minimum Z=0. Print the
base and wheel flat; the shoes rotated −90° about Y onto their flat inward foot
face; the hub and crank rotated
90° about Y; the grip upright. The payoff spindle also lies horizontally.
Use support where required, keeping fits and tape passages clean. All masters
fit a 220 × 220 mm bed. First test a shoe and the drive/bearing fits, deburr
carefully and inspect the first coil for enamel damage.

The loose plug crank and removable grip have no positive transport retention.
Remove them before carrying the tool. Gravity seats the wheel and hub; there is
no fragile snap keeping the horizontal winder assembled. Secure the common base
on its clamp lands if real wire tension causes sliding or tipping.

Wear eye protection. Keep hair, clothing, fingers, tape and loose wire clear.
Inspect for cracks, whitening, looseness and rough wire-contact edges before use.
Stop on abnormal resistance. PLA strength, wear, creep, bearing life, winding
accuracy, stability, enamel protection and release force remain unvalidated.
The bit socket is a future interface, not motor-operation approval:
Akkuschrauberbetrieb ist nicht freigegeben.

## CAD interfaces and release gates

`WindingToolAssemblies` owns two tool dictionaries, occurrence ownership,
parameters and audit results. Both tools use independent bench origins with
vertical Z axes. Head installation is translation-only at `wheel_bottom_z_mm`.
Recover local head coordinates by subtracting that translation, without rotation.

Each occurrence has a source and motion role. Printed occurrences also have a
global `canonical_master` identity and documented print rotations. Both bases
use `wire_payoff/base`. Each module has its own bearing `purchase_set`; the
three physical 51105 members count as one complete purchased set per module.
Mutations replace immutable Workplanes rather than editing cached shapes.
The legacy `release_clearance_mm` parameter is retained for caller compatibility,
but is ignored by horizontal release: shoes do not move radially.

The assembly audit verifies actual solids rather than trusting `model.audit`.
It repositions the actual shoes through all eleven settings, preserving defects.
Continuous full-revolution envelopes must contain the real parts and clear
stationary material. Axial sections preserve narrow hub/spindle guide journals.
The winder load path, pilot floor clearance, polygon torque engagement, working
gap, complete canonical bearing poses, tape corridors and base identity are gates.

`coil_removal_stages` retains all occurrences in three poses: held winding,
upward crank/grip removal and upward taped-coil removal. The service audit checks
ownership, fixed-member continuity and every swept boundary face, not just motion
endpoints. All six shoes stay fixed throughout. The fixture is bounded to a
9 mm axial winding with 1 mm radial build and eighteen closed tape loops having
10 mm tangential width, 10 mm axial height, 4 mm radial span and 0.25 mm walls.
It follows the curved contact arcs and taut spans between them. Its height is
found by descending the actual reference coil to the rounded lower support;
the production audit separately requires contact within a 0.02 mm downward
probe at all six actual shoes. The closed tape and upward sweep use that same
gravity-seated pose, not a floating nominal height.

The schema-3 manifest records all `assembly_occurrences` of each global master,
including the shared base across both tools. Export rejects conflicting grouped
geometry, malformed ownership, incorrect quantities or failed audits. It checks
single solids, closed manifold meshes, STL bed orientation, STEP reimports and
all artifact hashes before publishing success. Drawings consume current CAD;
guide tables consume the same BOM. V5 geometry and its `PRINT_SOURCES` are unchanged.

`physical_validation_verified`, `powered_operation` and `print_ready` remain
false: the files are geometrically checked prototype candidates, not physical
production or motor-operation approval.
