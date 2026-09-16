# Simple pin-adjustable serpentine coil winder design

Date: 2026-09-16  
Status: Approved in conversation; awaiting review of this written specification  
Supersedes: `2026-09-15-serpentine-coil-winding-jig-design.md`

## 1. Purpose

Replace the existing mechanically complex six-rib cam winder with a much simpler,
fully manual workshop jig inspired by the open, single-wheel layout of the
[Serpentine Coil Winding Machine](https://www.thingiverse.com/thing:6863041).

The new system has two independent modules:

1. a vertical hand-cranked coil wheel with six radially repositionable wire-contact shoes; and
2. a free-running horizontal turntable carrying the copper-wire roll upright.

The design is a PLA prototype for winding 0.18 mm enamelled copper wire. It is
not electrically, structurally, dimensionally, or operationally validated by
physical testing. Powered operation is outside scope.

## 2. Design priorities

In descending order:

1. simple construction and operation;
2. tool-free diameter adjustment and coil removal;
3. no screws, nuts, threaded rods, or metal shafts;
4. reuse of the available two 608 bearings and one 51105 thrust bearing;
5. printable parts within a 220 x 220 mm print bed;
6. replaceable wear parts rather than a permanently assembled mechanism.

## 3. Coil-wheel module

### 3.1 Layout

The coil wheel is vertical and accessible from the front. A compact single-sided
stand supports the wheel through two adjacent 608 bearings. This retains the
simple open layout of the reference while providing better resistance to tilt
than a single bearing.

The printable wheel is a single six-spoke part. Each spoke contains two parallel
radial rows of keyed holes. Six identical removable contact shoes plug into the
rows. Both pins on a shoe must engage the same numbered radial position, so the
shoe cannot rotate under wire tension.

### 3.2 Diameter range

The wheel provides eleven discrete nominal winding diameters:

`100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200 mm`.

Adjacent pin positions therefore differ by 5 mm in radius. Every position is
permanently and legibly marked on the wheel. All six shoes must use the same
numbered position.

The setting is the nominal envelope across the six wire-contact shoes. Because
the same short shoes serve all diameters, the wound form is a softly rounded
hexagon rather than a mathematically exact circle. This is intentional and
acceptable because the taped winding is subsequently reshaped into a serpentine
coil.

### 3.3 Contact shoes

Each of the six identical shoes has:

- two integral keyed insertion pins;
- PLA-compatible resilient retention tabs accessible from the rear;
- a short, shallow-convex wire-contact face;
- generous radii on every surface that can touch enamelled wire;
- three 12 mm clear tape passages for 10 mm tape; and
- no threaded or separate retention hardware.

Together the shoes provide 18 tape stations at a nominal angular pitch of 20
degrees. Small gaps between neighboring shoes remain open for handling and tape
access. The contact faces must not introduce sharp edges or local undercuts that
trap the finished winding.

### 3.4 Coil release

After all 18 tape wraps are closed, the operator releases each shoe from behind
and moves it at least one radial position inward or removes it completely. The
resulting reduction in support envelope must create at least 2 mm radial release
clearance everywhere around the winding. The taped winding is then removed
forward from the open wheel without withdrawing a shaft or opening a surrounding
frame.

### 3.5 Printed shaft and crank

The central shaft is fully printed in PLA. It uses 8 mm journals through the two
608 inner rings and increases to approximately 14 mm outside the bearing span.
Polygonal drive interfaces transmit torque to the wheel and crank without relying
on friction alone.

Printed snap collars provide bidirectional axial retention. Each collar, the
shaft, wheel, crank, and rotating grip remains individually removable and
replaceable without screws. Snap features must have accessible release faces and
must not require excessive bending for assembly.

The crank is for hand operation only. No drill-bit socket or powered-drive
interface is included in this simplified design.

### 3.6 Stand

The stand consists of a stable printable base and compact bearing tower joined by
positive snap features. It must:

- support the two 608 outer rings positively;
- retain the bearings without screws or adhesive;
- allow bearing removal without destroying the stand;
- remain stable throughout a complete crank rotation;
- leave the rear shoe latches accessible; and
- provide clamp lands or holes for optional bench clamping without making
  fasteners part of the product assembly.

## 4. Wire-roll turntable

The payoff module is independent of the coil wheel. The copper-wire roll stands
upright on a horizontal 150 mm diameter platter.

The platter has an integral central pilot 15 mm in diameter and 20 mm high. It
rotates freely on the existing 51105 thrust bearing. The lower bearing washer is
supported by the stationary base and the upper washer carries the platter. The
bearing washers remain separate purchased parts and are not replaced by printed
races.

The base, central printed spindle, bearing seat, and platter use tool-free
snap/plug interfaces. The platter must be removable for loading a roll. There is
no felt pad, spring, adjuster, or other brake. The operator stops the roll by hand.

The base provides a stable footprint and optional clamp lands. It must not tip or
drag against the rotating platter under the intended light wire tension.

## 5. Operating sequence

1. Inspect the printed shaft, snap tabs, contact shoes, and all wire-contact
   surfaces for cracks, burrs, or sharp edges.
2. Insert all six shoes at the same marked diameter.
3. Place three tape strips in each shoe, adhesive side prepared for later closure.
4. Place the copper-wire roll upright on the payoff platter.
5. Secure the wire start in a rounded, non-cutting start feature on one shoe.
6. Rotate the wheel only with the hand crank while guiding the wire manually.
7. Stop the payoff platter by hand when winding stops.
8. Close all 18 tape wraps and mark winding direction and leads.
9. Release and move all six shoes inward by at least one position, or remove them.
10. Remove the taped winding forward and form it into the serpentine layout.
11. Inspect the winding and jig after a test coil before making further coils.

## 6. Materials and printing

All printed parts are designed for PLA. Snap tabs use low preload, generous root
radii, and limited deflection appropriate to PLA rather than relying on long
living hinges. The shaft and latches are replaceable wear parts.

Print orientation must keep principal layer planes favorable for the shaft,
contact-shoe pins, and snap tabs. Wire-contact surfaces require cleanup and light
smoothing before use. No support scar may remain on a wire-contact surface.

Every unique printed master must fit within 220 x 220 mm in its documented print
orientation. The design must avoid splitting the wheel unless the completed
single-piece geometry cannot meet that envelope.

## 7. CAD and verification requirements

Automated checks must verify:

- all eleven diameter settings from 100 through 200 mm;
- six equal shoe radii at every setting;
- positive two-pin engagement and retention of every shoe;
- 18 open 12 mm tape passages at the assembled setting;
- rounded wire-contact surfaces;
- at least 2 mm release clearance after moving shoes inward;
- collision-free forward removal of winding surrogates at 100, 150, and 200 mm;
- full crank rotation without stand collision;
- positive radial and axial support of both 608 bearings;
- positive 51105 washer ownership and free platter rotation;
- 150 mm platter diameter and 15 x 20 mm pilot;
- every printed master within the 220 x 220 mm bed envelope;
- valid positive-volume CAD solids;
- closed, manifold STL exports without collapsed facets;
- successful STEP reimport;
- deterministic BOM, manifest, drawings, and artifact hashes; and
- no coupling to the V5 turbine production inventory or `PRINT_SOURCES`.

Negative regression tests must reject mismatched shoe positions, missing retention,
blocked tape passages, inadequate release, displaced bearings, inaccessible snap
tabs, and non-printable envelopes.

## 8. Deliverables

- parametric CAD source for both modules;
- STL and STEP for every unique printable part;
- STEP assemblies for the coil wheel and wire-roll turntable;
- exploded and operating drawings;
- deterministic BOM and release manifest;
- German print, assembly, adjustment, winding, release, and safety guide; and
- automated geometry, export, inventory, and regression tests.

Existing release files for the superseded cam/rib/frame design must be removed or
replaced so the release contains only the simplified approved design.

## 9. Safety and validation limits

The guide must state exactly: `Akkuschrauberbetrieb ist nicht freigegeben`.

The following remain unvalidated until physical prototype testing:

- printed 8 mm shaft strength and fatigue;
- PLA snap-tab life and retention;
- bearing press/snap fit;
- actual winding diameter and repeatability;
- enamel protection under wire tension;
- turntable stability and hand stopping;
- coil-release force; and
- suitability for continuous or production use.

Eye protection is required. Hair, clothing, fingers, and loose wire must be kept
clear of the rotating wheel and free-running payoff. The operator must stop if the
printed shaft, latches, shoes, or stand show damage.
