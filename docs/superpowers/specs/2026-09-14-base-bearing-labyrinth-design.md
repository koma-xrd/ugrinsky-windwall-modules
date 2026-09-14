# Base Bearing Labyrinth Design

## Purpose

Protect the 51105 thrust-bearing area against falling dirt and splash water without allowing the rotating Base module to contact the stationary generator cover. This prototype feature is a non-contact labyrinth, not a waterproof shaft seal.

## Scope

The change is limited to the Base rotor module and the geometry contracts and release artifacts affected by it. The generator cover, 51105 reference geometry, M8 shaft and nut interfaces, magnet pockets, blade profile, bayonet joint, and nominal magnet-carrier plate thickness remain unchanged.

## Selected Architecture

The Base receives an integral rotating cup above the magnet-carrier plate:

- The stationary generator-cover bearing boss has a 48.2 mm outside diameter (24.1 mm radius).
- The rotating cup has a 49.0 mm inside diameter (24.5 mm radius), providing 0.4 mm radial clearance per side at nominal geometry.
- The upper rotating bearing/load plate grows to 54.0 mm outside diameter (27.0 mm radius).
- The resulting cup wall is nominally 2.5 mm thick.
- The cup wall extends downward and fuses continuously to the existing magnet-carrier plate.
- The enlarged upper plate, cup wall, carrier plate, and existing blade-root reinforcement form one connected rotating solid.
- The stationary cover boss enters the cup from below and remains radially separated throughout its axial overlap.
- The existing axial clearance above the stationary boss is retained. The cup must not introduce contact with the cover, housing washer, rolling envelope, shaft washer, or cassette.

This creates a dead-end, upward-turning contamination path: debris or splash must first travel upward through the 0.4 mm annular running clearance and then turn beneath the enlarged upper plate. No rubbing lip or sacrificial contact surface is introduced.

## Printability

The Base retains its current print orientation with the large magnet-carrier plate on the build plate. The new wall grows upward from that plate. The upper closure is supported at its inner edge by the existing rotating bearing structure and at its outer edge by the new wall; the added radial bridge is small and must not require generated support material. No geometry may extend below the existing nominal carrier-plate bottom.

The prototype remains dimensioned for the Bambu Lab P2S with a 0.4 mm nozzle. The 0.4 mm running clearance is an unvalidated nominal CAD value and must be checked by hand for free rotation before powered operation, particularly with PLA and an M8 threaded rod.

## Geometry Invariants

The implementation must preserve all of the following:

1. The Base is one valid connected solid.
2. The magnet-carrier plate retains its existing diameter, thickness, elevation, and magnet pockets.
3. The blade walls remain connected to the carrier plate for torque transfer.
4. The 51105 rotating pilot, axial load shoulder, M8 bore, and nut pocket retain their existing functional dimensions and elevations.
5. The stationary generator-cover boss remains unchanged and has no intersection with the Base at nominal placement or during sampled shaft rotation.
6. The annular radial clearance between the 24.1 mm stationary radius and 24.5 mm rotating inner radius is 0.4 mm.
7. The contamination barrier is closed between the enlarged upper plate and magnet-carrier plate except for the intentional annular running opening around the stationary cover boss and the required central shaft/nut geometry.
8. The new geometry does not enter magnet pockets or the rotating/stationary keep-outs already enforced by the generator assembly.

## Implementation Boundaries

The Base construction remains owned by `src/windwall/rotor_modules.py`. Shared dimensions that are needed by both Base construction and collision tests must come from the existing generator/bearing parameter and interface functions rather than duplicated literals. A small named helper or explicit interface values may be added if that makes the clearance contract auditable.

Release generation must refresh the Base STL and STEP files, the affected generator/rotor/fence assemblies, and `release/v5/manifest.json`. Documentation images and manuals only need regeneration if their generated geometry visibly includes the modified Base; prose must continue to describe the feature as splash/dirt protection rather than waterproofing.

## Verification

Development follows a red-green test cycle. Before changing production geometry, add tests that fail against the current Base and establish:

- 0.4 mm nominal radial separation from the generator-cover boss;
- continuous material joining the 54 mm upper plate to the magnet-carrier plate around the complete circumference;
- no intersection with the stationary cover, bearing parts, magnet pockets, shaft bore, or nut pocket;
- unchanged carrier-plate bottom and nominal plate thickness;
- one valid connected Base solid and a closed manifold exported STL;
- collision-free generator assembly across the existing rotation samples.

Run the focused rotor-module and generator-housing tests first, followed by the generator, assembly, and export suites. As in the existing project, a native Windows OCP teardown status may be nonzero after `unittest` reports `OK`; the unittest result and process status must be recorded separately.

## Limitations and Safety

The labyrinth does not make the generator waterproof, does not replace drainage or an outdoor enclosure, and has not been physically validated. A 0.4 mm nominal radial gap may be insufficient if the printed parts warp or the threaded shaft runs eccentrically. Assembly must be rotated manually through a complete revolution and inspected for rubbing before installing magnets or connecting electrical loads.
