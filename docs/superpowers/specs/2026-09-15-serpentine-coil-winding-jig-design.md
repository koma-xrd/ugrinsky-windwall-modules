# Serpentine Coil Winding Jig Design

Status: superseded by [the 2026-09-16 simple pin-adjustable coil-winder design](2026-09-16-simple-pin-adjustable-coil-winder-design.md).
This historical specification records the replaced mechanism; it is not the current build or operating guide.

## Purpose and scope

Add two independent, manually operated workshop modules for producing the
experimental 18-station serpentine winding used by the V5 generator cassette:

1. a centred, diameter-adjustable winding jig that first produces a flat round
   coil and exposes fixed positions for taping it, and
2. a passive payoff turntable for the enamelled-copper-wire supply spool.

The concept follows the workflow of the user-supplied Thingiverse reference
<https://www.thingiverse.com/thing:5941354>, but the geometry and mechanisms are
new, parametric parts matched to this repository's V5 coil cassette.

The first supported conductor is the existing 0.18 mm enamelled copper wire.
The tooling does not establish a final turn count, electrical rating, safe
rotational speed, or production-qualified winding process.

## Winding workflow

1. Set all six winding ribs to the required diameter with the central cam.
2. Lock the cam and place 10 mm tape strips in the 18 tape passages.
3. Anchor the wire without scraping or sharply bending its enamel.
4. Turn the hand crank while guiding the wire and allowing the separate supply
   spool to rotate under light, adjustable drag.
5. Close the 18 tape strips around the completed round coil.
6. Release the cam lock and retract the ribs by at least 2 mm radially.
7. Remove the taped coil and form it around the cassette's 18 alternating
   inner/outer guide positions.
8. Mark both leads and winding direction before fitting or testing the coil.

One circuit of all cassette guides remains one electrical turn, as defined by
the existing generator documentation.

## Adjustable winding head

### Geometry

- Six winding ribs are spaced at 60 degree intervals and move only radially.
- A concentric rotary cam plate moves all six ribs synchronously. Identical cam
  tracks and followers keep the winding contour centred on the drive axis.
- The supported nominal winding diameter is continuously adjustable from
  110 mm through 145 mm.
- A clearly engraved 127 mm index is the initial setting calculated from the
  current serpentine guide centreline. It is a prototype starting value, not a
  physically validated production dimension.
- A separate clamp locks the cam plate during winding. The clamp must not rely
  on follower friction alone.
- Captive mechanical end stops prevent every slider from leaving its guide at
  either adjustment limit.
- Unlocking and turning the cam inward provides at least 2 mm radial clearance
  from the wound diameter for coil removal.

The cam, slider, and rib interfaces are parameterised from one diameter value.
Public metadata reports the requested diameter, achieved rib radius, permitted
range, tape-station count, and release travel.

### Tape access

The head provides 18 visibly numbered tape stations at 20 degree intervals.
Each station has a passage at least 12 mm wide so a 10 mm tape strip can be
placed before winding and closed around the finished coil. Printed surfaces
must not trap the tape after the ribs retract. Tape passages, slider structure,
fasteners, and cam followers must remain mutually clear throughout the full
110--145 mm adjustment range.

All wire-contacting edges use generous radii or chamfers. No split line,
fastener end, or unsupported bridge may present a sharp edge to the enamel.

## Winding frame and drive

The winding axis is horizontal between two uprights on a stable table base.
Two standard 608 radial bearings support an 8 mm shaft. The adjustable winding
head is removable from the shaft and is retained by positive mechanical
fastening rather than a printed friction fit.

A hand crank with a freely rotating grip is the only approved drive for this
version. The shaft also includes a coaxial 6.35 mm female hex interface for a
future screwdriver bit. Providing the interface does not approve powered use;
the documentation must warn that speed, torque limiting, guarding, and safe
wire handling have not been designed or validated.

The base includes through-holes and accessible edge lands for either bench
screws or two clamps. The crank, head, and clamp controls must remain reachable
without placing a hand in the winding path.

## Wire-spool payoff turntable

The payoff unit is mechanically separate so the user can choose a low-friction
feed angle and distance.

- The rotating platter is nominally 150 mm in diameter.
- Its central spool pilot is 15 mm in diameter and 20 mm high, with a lead-in
  chamfer and no sharp wire-contacting edges.
- One existing 51105 thrust bearing (25 x 42 x 11 mm nominal) carries the axial
  platter load. Its housing washer remains stationary, its shaft washer rotates
  with the platter, and the rolling assembly remains separately identifiable.
- Printed bearing seats reuse the repository's explicit fit-clearance strategy;
  nominal dimensions are not represented as guaranteed printed press fits.
- A replaceable felt friction surface and spring-loaded adjustment provide
  light drag to prevent spool overrun. The adjustment must reach a free-running
  state and must not rigidly lock the platter during normal payoff.
- The spool remains removable without dismantling the bearing seat.
- A low, wide base includes the same screw/clamp mounting options as the winding
  frame.

The payoff turntable does not actively synchronize with the winding head. This
avoids transmitting a forced feed rate or damaging the 0.18 mm wire when the
operator pauses.

## Components and interfaces

CAD responsibilities are separated into focused modules:

- winding-head geometry: cam, followers, sliders, ribs, tape passages, limits,
  and diameter metadata;
- winding-frame geometry: base, uprights, 608 seats, shaft interfaces, crank,
  and head retention;
- payoff geometry: base, 51105 seats, platter, spool pilot, and drag mechanism;
- assembly and validation: placement, moving/stationary ownership, clearances,
  fastener inventory, and collision checks;
- export and documentation: printable bodies, STEP assemblies, drawings, bill
  of materials, operating sequence, and prototype warnings.

Existing bearing definitions are reused instead of duplicating 608 or 51105
nominal dimensions. New tooling parameters remain separate from generator
product geometry so experimental jig changes cannot silently alter the turbine.

Likely non-printed hardware consists of two 608 bearings, one 51105 bearing, an
8 mm shaft, metric fasteners and washers, a crank grip fastener, a cam-lock
fastener, six metal follower fasteners, springs, and replaceable felt. Exact
lengths and quantities are resolved in the implementation plan and then emitted
by the final bill of materials.

## Printable and release artifacts

The release includes:

- individual STL files for every printable part, oriented or documented for
  practical printing;
- STEP files for serviceable parts and complete assemblies of both modules;
- an exploded assembly view and dimensioned overview drawings;
- a German construction and operating guide;
- a hardware bill of materials;
- the calculated 127 mm setup and physical calibration procedure; and
- an indexed manifest matching the actual generated artifacts.

Large parts must fit a nominal 220 x 220 mm print bed without requiring the
user to split the 150 mm platter. No support-dependent hidden cavity may make a
bearing seat or tape passage impractical to print and clean.

## Validation and tests

Automated tests cover:

- valid, connected solids for every exported printable part;
- exactly six radial sliders with equal achieved radius at sampled settings;
- continuous adjustment and hard limits at 110 mm and 145 mm diameter;
- the marked 127 mm reference setting;
- at least 2 mm release travel;
- exactly 18 numbered, 20-degree tape stations with at least 12 mm clearance;
- absence of cam, follower, fastener, tape-passage, and frame collisions at the
  minimum, reference, and maximum settings;
- coaxial shaft, winding head, crank, and hex interface;
- two valid 608 seats around the 8 mm shaft;
- 150 mm platter and 15 x 20 mm spool pilot dimensions;
- correct moving/stationary ownership of all 51105 elements;
- drag-adjuster clearance and a non-locking free-running endpoint;
- print-bed envelope limits and complete STL/STEP/manifest exports; and
- agreement between CAD metadata, bill of materials, drawings, and guide.

Visual verification covers cam motion, tape insertion and closure access,
hand-clearance around the crank, coil release, supply-spool removal, practical
print orientation, and the assembled feed path. A physical prototype must
confirm the printed fits, useful drag range, enamel protection, 127 mm starting
diameter, and final fit on the generator cassette.

## Safety and limitations

The tooling is prototype workshop equipment. Long thin wire can cut skin,
tangle, snap, or unwind unexpectedly. Eye protection is required; loose hair,
clothing, and jewellery must be kept clear. The user must stop turning before
adjusting the cam, tape, drag brake, or wire path.

Powered operation is outside this version's validated scope even though a
standard hex interface is present. The winding head is not a flywheel-rated or
guarded rotating assembly. Printed bearing fits, strength, fatigue life, crank
loads, wire tension, and achievable winding quality require physical testing.
