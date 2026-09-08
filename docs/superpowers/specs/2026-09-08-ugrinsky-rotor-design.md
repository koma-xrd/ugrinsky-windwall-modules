# Parametric Ugrinsky Wind Wall Rotor Design

## Purpose

This project reconstructs the supplied Ugrinsky wind wall STL models as clean,
parametric CAD geometry. The first deliverable is a seven-stage rotor stack with
a wind-tightening bayonet interface, a continuous M8 threaded rod, and the
original dual-rotor axial-flux generator arrangement.

The design preserves the original Ugrinsky blade geometry as closely as
practical. Local changes are limited to structurally necessary hubs, blade-end
drivers, bayonet features, fastener access, and the top closure.

## Reference Geometry

The following supplied files are measurement references only and will not be
used as production solids:

- `1 Base.stl`
- `2 Coil_Former.stl`
- `3 magnet_ring (2).stl`
- `4 Stator_Cover_PLate.stl`
- `5 Top_Bearing.stl`
- `6 Ugrinsky_Base.stl`
- `7 Ugrinsky_Blade.stl`

Initial mesh inspection found the generator base parts mostly closed and
manifold. `5 Top_Bearing.stl`, `6 Ugrinsky_Base.stl`, and especially
`7 Ugrinsky_Blade.stl` contain non-manifold topology. The blade STL also
contains four disconnected components and degenerate faces. Production parts
will therefore be reconstructed rather than repaired through mesh booleans.

## Coordinate and Rotation Convention

- The rotor axis is the global Z axis.
- Positive Z points upward from the generator toward the top module.
- Rotation is viewed from above, looking down along negative Z.
- Normal wind-driven rotation is counterclockwise in this view.
- Every bayonet ramp and end stop shall be oriented so counterclockwise rotor
  torque drives the joint toward its locked end position.

## Rotor Stack

The nominal stack contains seven aerodynamically active stages and is about
490 mm high:

1. One base rotor module with the upper magnet rotor integrated into its lower
   structure.
2. Five identical standard rotor modules.
3. One top rotor module with a reinforced central M8 nut and washer seat.
4. One removable top closure disc above the top rotor module. The closure disc
   is not an additional aerodynamic stage.

All seven stages finish in the same angular orientation so the blade surfaces
are vertically aligned. The stack uses one continuous, ordinary M8 threaded
rod as its rotating shaft for the first prototype.

## Bayonet Interface

Each module-to-module joint uses three broad bayonet lugs distributed around
the central hub.

- The upper module is presented approximately 15 to 20 degrees clockwise from
  its final position.
- It is inserted axially and rotated counterclockwise to lock.
- The locked end stop places the blade profile exactly above the profile below.
- Shallow ramps generate light axial preload without wedging or splitting the
  printed hub.
- Large internal radii reduce stress concentrations.
- The interface remains printable in PLA and usable in ASA with parameter-only
  clearance changes.

Two blade-end drivers supplement the central bayonet. Each driver enters a
matching pocket during the same locking rotation. Drivers are positioned at
the two blade transition regions and use rounded geometry with local material
reinforcement. They share torque without materially changing the active blade
surfaces.

Two radially accessible, corrosion-resistant, thread-forming screws secure
each locked joint against reverse rotation during transport, braking,
turbulence, or momentary reverse loading. The screws are retainers rather than
primary torque carriers. Initial envelopes support 2.5 to 3 mm screw diameter
and 10 to 12 mm length; exact pilot diameter is a model parameter calibrated by
a test coupon.

## Shaft and Torque Transfer

The M8 threaded rod passes through every rotating component. The bayonet and
blade-end drivers transfer torque through the rotor stages, so multiple fixed
M8 nuts are not placed along the shaft.

The top rotor module contains:

- a reinforced central hub;
- a top-accessible captive M8 hex-nut pocket;
- a broad washer seat to distribute axial preload into the printed body; and
- access for adjustment before the closure disc is installed.

The base rotor module provides the lower torque-transfer interface to the M8
shaft and integrated upper magnet rotor. Nuts, locking nuts, washers, and
spacers locate and clamp the rotating generator parts without relying on a
printed thread.

The prototype accepts the dimensional and concentricity limitations of an M8
threaded rod. Bearing interfaces remain replaceable so a future smooth 8 mm
shaft or bearing sleeves can be introduced without changing the blade profile
or module interface.

## Axial-Flux Generator Arrangement

The generator retains two magnet rotors on the same continuous rotating M8
shaft:

- The upper magnet rotor is integrated into the base rotor module.
- The lower magnet rotor is a separate rotating part below the stator.
- The coil former, stator cover, generator base, and bearing supports remain
  stationary.
- Nuts and spacers establish the axial location and air gaps.

Magnet count, polarity sequence, coil winding, electrical phase arrangement,
air gap, charging electronics, and final generator optimization are explicitly
deferred until the mechanical reference geometry has been reconstructed and
the available magnets and coils have been physically verified. The CAD
separates these dimensions as parameters so the generator can be revised
without rebuilding the blade system.

## Top Closure

The top closure is a removable, approximately symmetric disc that:

- ties the two upper blade ends together;
- improves top-stage stiffness;
- covers the M8 nut and washer;
- permits later access for stack adjustment; and
- does not carry the primary axial clamping load.

Its retention must not depend on the rotor direction alone. It will use simple
serviceable printed or screwed retention selected during detailed design.

## Parametric CAD Structure

CadQuery is the authoritative source. STEP and STL are generated artifacts.
The implementation will separate:

- shared dimensional and manufacturing parameters;
- reconstructed Ugrinsky blade profile;
- hub and bayonet geometry;
- blade-transition drivers and pockets;
- base, standard, and top module construction;
- upper and lower magnet rotor construction;
- stationary generator parts;
- assembly placement and interference checks; and
- export and mesh validation.

The original STLs are used for measurements and visual comparison only. They
are not committed unless their license permits redistribution and the user
explicitly chooses to include them.

## Manufacturing Parameters

The initial prototype targets PLA. Outdoor parts will later use ASA.

Initial design values, all adjustable from one parameter source, are:

- bayonet contact clearance: 0.25 to 0.30 mm per side;
- captive M8 nut pocket: 13.2 to 13.4 mm across flats before calibration;
- locally loaded wall thickness: at least 3 mm where geometry permits;
- generous fillets at lug, pocket, hub, and driver roots; and
- an M8 shaft clearance suitable for a commercial threaded rod rather than a
  precision 8 mm shaft.

Small test coupons for the bayonet fit, blade-end driver, nut pocket, and screw
pilot hole will be exported before full-size parts.

## Deliverables

- Parametric CadQuery Python sources.
- STEP files for continued work in FreeCAD and other CAD systems.
- Print-ready STL files for each unique part.
- A seven-stage assembly model.
- Fit-calibration coupons.
- Assembly and printing documentation.
- A geometry validation report generated from the exported parts.

## Validation

Automated checks shall verify:

- closed, manifold exported meshes;
- no degenerate faces;
- one intended connected solid per printed part unless documented otherwise;
- absence of part interference in the locked assembly;
- collision-free axial insertion and locking rotation;
- exact final blade alignment at the counterclockwise end stop;
- free passage of the M8 threaded rod;
- nut and washer access in the top module;
- intended component count in the seven-stage assembly;
- minimum configured wall thickness in critical modeled features where it can
  be evaluated reliably; and
- successful STEP and STL export for every deliverable.

Physical validation proceeds from small coupons to one two-module joint, then
to the full seven-stage rotor. Full generator operation and outdoor loading are
not claimed until the printed assembly is tested with the actual shaft,
fasteners, magnets, bearings, and stator.

## Safety and Scope Boundaries

The first design is a mechanical prototype. It does not certify structural
survival in storms, overspeed behavior, electrical safety, grid connection, or
long-term outdoor durability. A brake or dump-load system, guards, reliable
overspeed control, weather-resistant material, and appropriate structural
mounting are required before unattended outdoor operation.

The initial electrical target is a future isolated 48 V lead-acid battery
system. Electrical design is deferred and does not change the approved rotor
stack architecture.
