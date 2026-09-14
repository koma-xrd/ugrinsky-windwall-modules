# Flat Lower Rotor and Plain Blade Ends Design

## Purpose

Make the lower magnet rotor printable with its complete underside flat on the build plate, and simplify every stacked rotor-module blade transition by removing the separate tongue-and-groove features. The central bayonet remains the only positive rotational connection between rotor modules.

## Scope

This change affects the lower magnet rotor, all three rotor-module variants, the combined joint coupons and previews that currently contain blade tongue-and-groove geometry, their parameters and tests, and every release artifact or document that visibly or structurally depends on those parts.

The following remain unchanged:

- 18 magnets per rotor at the existing pitch circle;
- magnet diameter, pocket diameter, pocket depth and polarity convention;
- M8 threaded shaft and nut size;
- integral upper spacer sleeve on the lower magnet rotor;
- Base-module bearing labyrinth and 51105 load path;
- central bayonet dimensions, detent, direction and permanent-locking behavior;
- 70 mm nominal module height, analytic blade profile and 60-degree inter-module phase;
- stationary generator housing, coil cassette and cover geometry.

## Lower Magnet Rotor

### Flat print surface

The lower rotor keeps the existing 106 mm diameter and 5 mm magnet-carrier disc thickness. Its complete lowest exterior support surface lies on one common plane. The six radial ribs and the deeper central hub currently projecting below the disc are removed; the design must not compensate by thickening the entire carrier disc.

The lower surface may contain the intentional M8 hexagonal nut recess and central shaft bore. These are open cavities and do not count as protrusions or prevent the surrounding annular face from lying flat on the build plate. No other solid geometry may extend below the carrier-disc bottom.

### Nut pocket and sleeve

The existing bottom-open M8 hexagonal nut pocket moves upward with the flat carrier bottom. It retains the current across-flats clearance and pocket depth. The pocket must remain accessible from below after printing and must not break into any magnet pocket.

The 12 mm outside-diameter integral spacer sleeve remains above the magnet face and runs to the existing upper clamp-nut elevation. It retains the M8 clearance bore and remains fused to the carrier through the central disc region. Removing the lower hub must not disconnect or shorten this sleeve.

### Magnet pockets

The 18 magnet pockets remain open toward the stator-facing upper surface. Their blind floors, locations and depths remain unchanged. The flat-bottom change must preserve sufficient solid material between every pocket floor and the new print surface.

## Plain Blade Transitions

All separate blade tongue and groove solids are removed from Base, Standard and Top rotor modules. Each analytic blade wall terminates directly at its nominal lower and upper module planes. When adjacent modules are locked in their prescribed 60-degree relative phase and fully seated, corresponding blade surfaces meet flush with zero nominal axial gap.

The blade ends do not overlap and do not provide a keyed torque interface. Rotational torque between modules is transmitted only by the existing central bayonet. The blade-wall thickness and aerodynamic profile remain unchanged outside the deleted seam features.

The central end guides, local support structures and bayonet receiver/male geometry remain wherever they are needed for centering, seating and structural connection. Removing the blade seam must not remove the bayonet, create disconnected solids, reopen the shaft bore, or change the locked stage height.

## Dead-Code and Interface Cleanup

Remove the blade-seam builder, its data class, its configuration block and validation paths when no remaining production or calibration flow consumes them. Remove or revise seam-specific driver geometry, coupon assertions, preview annotations, assembly metadata, README text and manual wording.

The combined bayonet/joint coupon may retain representative plain blade-wall samples to show axial alignment, but it must not contain a tongue, groove or misleading seam-lock feature. Dedicated tongue-and-groove tests and unused seam parameters must not remain as dormant compatibility code.

## Printability

The lower magnet rotor is printed with its new flat underside on the build plate. The bottom-open nut pocket is an intentional recess; its roof is a bounded bridge and must be inspected in the slicer. The change must not require support under former ribs or hub projections.

The rotor modules retain their existing validated print orientations. Removing the small tongue-and-groove features must not introduce new unsupported lips at blade ends.

Prototype assumptions remain the Bambu Lab P2S, 0.4 mm nozzle and PLA for initial fitting. ASA remains the intended later outdoor-material trial.

## Geometry and Assembly Invariants

The implementation must prove all of the following:

1. The lower magnet rotor is one valid connected solid with a closed manifold export.
2. Its lowest solid Z equals the nominal 5 mm carrier-disc bottom across the usable annular support face.
3. No rib or hub material exists below the nominal carrier disc.
4. Carrier diameter and thickness remain 106 mm and 5 mm.
5. The M8 hex pocket is bottom-open at the new carrier bottom, retains its existing width and depth, and remains clear of the shaft and magnets.
6. The integral spacer sleeve retains its existing diameter, bore, upper elevation and continuous connection to the carrier.
7. All 18 magnet pockets retain their positions, dimensions, opening direction and blind floors.
8. No rotor module contains blade tongue or groove geometry.
9. Adjacent locked blade profiles meet at the common module plane with zero nominal axial gap and the prescribed 60-degree phase.
10. The bayonet remains the sole keyed torque-transfer interface and retains its current insertion, rotation, detent and locked geometry.
11. Base, Standard and Top modules each remain one valid connected solid; the complete seven-stage assembly remains collision-free.
12. The Base bearing labyrinth, generator clearances, M8 bore and top clamping interface remain unchanged.

## Testing Strategy

Development follows red-green TDD.

Lower-rotor regression tests must probe the bottom plane at representative radii and angles, reject material below that plane, verify the nut opening and pocket roof, confirm magnet floors, and verify the complete sleeve volume. A mutation or temporary legacy build with the old lower hub/ribs must fail the flatness test.

Rotor-module tests must demonstrate the absence of tongue/groove solids and verify coincident blade cross-sections at each locked Base-to-Standard, Standard-to-Standard and Standard-to-Top interface. Existing bayonet travel, detent, blade continuity, connected-solid, shaft-clearance and assembly-collision tests remain authoritative after seam-specific assertions are removed.

Export tests must confirm one closed manifold component for every changed STL. Deterministic V5 generation must refresh the lower magnet rotor, all affected rotor modules, relevant coupons and STEP assemblies, plus manifest hashes.

Documentation and canonical drawings must be regenerated when affected. All six manuals must use the same current English engineering drawings, and no text may continue to claim that blade tongues or grooves transfer torque.

## Limitations and Safety

The thinner lower-rotor structure has not been physically load-tested. Eliminating ribs reduces bending stiffness, so the printed rotor must be checked for warping and magnet-disc deflection before powered operation. The bottom-open nut pocket bridge, flat-bed adhesion and dimensional fit require slicer inspection and a prototype print.

Plain blade ends deliberately provide no secondary torque key. Every bayonet must be fully engaged and its detent verified before the rotor is spun. Outdoor, overspeed, storm, long-duration bearing protection and electrical operation remain unvalidated.
