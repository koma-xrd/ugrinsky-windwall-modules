# Ugrinsky Wind Wall assembly manual design

## Purpose

Create a German-language construction manual for the seven-stage Ugrinsky Wind
Wall prototype. Deliver both an editable DOCX and a print-ready PDF. The manual
must connect every printed and purchased part to numbered exploded drawings,
explain the mechanically validated assembly order, and provide a safe empirical
method for developing a serpentine stator winding for a future 48 V lead-acid
battery system.

The manual is for a technically interested maker using a Bambu Lab P2S with a
0.4 mm nozzle. It must remain usable without CAD experience.

## Deliverables

- `output/Ugrinsky-Wind-Wall-Bauanleitung.docx`
- `output/pdf/Ugrinsky-Wind-Wall-Bauanleitung.pdf`
- high-resolution source figures under `output/manual-figures/`

The DOCX and PDF contain the same released content. Intermediate renderings and
QA files are not deliverables.

## Document structure

1. Scope, prototype status, safety and key dimensions.
2. Printed-parts bill of materials with quantities and file references.
3. Purchased-parts bill of materials, separating required, provisional and
   electrically selected parts.
4. PLA prototype settings for the P2S and notes for later ASA production.
5. Preparation and coupon tests.
6. Generator mechanical assembly.
7. Magnet installation and polarity verification.
8. Serpentine test-coil construction.
9. Electrical measurement and final-turn calculation.
10. Seven-stage rotor assembly and CCW self-tightening bayonets.
11. Top clamp, closure, alignment and balance checks.
12. Commissioning, inspection schedule and troubleshooting.
13. Appendices containing formulas, measurement sheets and drawing index.

## Mechanical content

The manual uses the current parametric model and release manifest as its
mechanical source of truth. It documents one base rotor module, five identical
standard modules, one top module, one top closure and one separate lower magnet
rotor. The upper magnet carrier remains integrated into the base module.

The ordinary M8 threaded rod remains continuous through the entire rotor. M8
nuts and washers transmit axial clamping force. Twelve radial M3
self-threading screws are reverse-release retainers only and must not pull the
joints together or carry axial preload. The loaded module pitch is 69.64 mm,
the seven-stage aerodynamic height is 487.84 mm, and the modeled rod envelope
is 559.64 mm. Actual rod cut length is determined from measured bearings,
washers, nuts and end support geometry.

Viewed from above, wind-driven rotation and bayonet locking are counterclockwise.
Each upper stage enters 18 degrees clockwise from its final aligned position and
locks counterclockwise. The source blade retains 60 degrees of internal twist,
so each aligned stage produces a documented minus-60-degree seam phase jump.

## Exploded drawings

Figures are generated from actual STEP/CadQuery solids, not redrawn silhouettes.
Use a consistent isometric projection, restrained group colors, numbered leader
lines and a legend linked to the bills of materials. Required views are:

- complete seven-stage wind module;
- generator stack with stationary and rotating groups separated;
- upper integrated magnet carrier and base rotor interface;
- lower magnet rotor, spacer, bearing and clamp hardware;
- one standard rotor joint showing three bayonet lugs, two drivers and two
  radial retainers;
- top rotor, washer, exposed M8 nut and removable closure;
- magnet polarity map for both 18-pocket rotors;
- serpentine winding path, winding jig and lead identification;
- locked versus insertion orientation viewed from above;
- critical sectional views for shaft, air gaps and pocket floors.

Every figure identifies whether shown non-printed solids are actual selected
hardware or provisional reference envelopes.

## Generator and magnets

Use 36 nominal 10 x 2 mm neodymium disc magnets, 18 per rotor. The existing
carrier pockets are nominally 11 mm diameter and 2 mm deep. The manual requires
the 10.8, 11.0 and 11.2 mm pocket coupon to be printed first. Adhesive,
centrifugal retention and magnet grade are not declared validated.

Adjacent magnets on each rotor alternate north and south. At every opposed
position, the upper and lower magnets present opposite poles toward each other
and therefore attract across the stationary winding. The polarity procedure
uses a marked reference magnet or compass and includes a complete dry-layout
check before adhesive is applied.

The nominal 1.5 mm air gaps are valid only for flush or recessed magnets.
Installed protrusion is measured and recorded before rotation.

## Serpentine winding method

The stator starts with one continuous air-core serpentine test winding. The
conductor alternates between the inner and outer winding radii around the full
circumference so successive active radial legs cross successive alternating
magnetic poles. All turns follow the same path and winding direction. Start and
finish leads are labelled before removal from the jig.

The test program starts with the user's existing nominal 0.18 mm enamelled
copper wire. Every spool, including additional ordered diameters, is measured
across the enamel with a micrometer before use; nominal labels are recorded but
never substituted for the measured diameter. No wire diameter is designated as
the final choice in advance.

For each available diameter, wind separate 20-, 40- and 80-turn serpentine test
coils when they fit the former without forced packing. If a planned coil does
not fit, record that result rather than compressing or damaging the enamel. The
manual shows a reusable printable or board-and-insulated-pin jig, controlled
bend radii, temporary binding, continuity testing, placement in the former and
conservative potting guidance. It prohibits sharp metal tools against enamel
and records measured diameter, turn count, wire length, coil dimensions, DC
resistance and temperature.

Each test winding is driven at the same set of measured rotor speeds. Record
open-circuit RMS voltage and frequency, then voltage, current and temperature
under the same defined resistive test loads. Calculate voltage per turn,
resistance per metre, internal voltage drop and approximate copper loss so
different wire diameters and turn counts remain comparable. For a chosen design
speed, estimate final turns with:

`N_final = N_test * V_ac_target / V_ac_test`

The target voltage is derived from the chosen rectifier and 48 V lead-acid
charge controller, not assumed to be exactly 48 V. Wire gauge, final winding
count, series or parallel grouping and thermal rating remain conditional on the
test results and available stator volume. If the calculated winding does not fit
or has excessive resistance, the manual directs redesign rather than silently
reducing safety margins.

## Electrical boundary and safety

The generator must not connect directly to the battery. The conceptual chain is
generator, suitably rated rectifier, overcurrent protection, wind-generator
charge controller with diversion or dump-load capability, battery-side fuse and
48 V lead-acid bank. Exact controller, rectifier, cable, fuse and dump-load
ratings require measured generator voltage, current, speed and battery
configuration and therefore appear as selection fields rather than invented
part numbers.

The manual warns about rotating parts, strong magnets, stored battery energy,
short-circuit current, hydrogen ventilation, polarity mistakes, overspeed,
water ingress and hot windings. First electrical tests use current limiting and
no unattended outdoor operation.

## Evidence and uncertainty

Mechanical dimensions and topology come from the current source, tests and
release manifest. Original STL measurements are identified separately from
reconstruction decisions. External references may explain the serpentine
principle and general axial-flux practice, but the manual must not repeat
unverified performance claims.

Each uncertain item is marked as one of:

- verify by coupon or measurement;
- provisional reference geometry;
- select after electrical test;
- not yet approved for outdoor service.

## Verification

- Generate every figure at print-readable resolution.
- Build the DOCX with headings, captions, repeating table headers, page numbers
  and accessible alternative text.
- Render the DOCX to page PNGs and PDF using the bundled document runtime.
- Inspect every rendered page for clipping, overlap, unreadable labels, broken
  tables and missing images.
- Reopen the PDF, confirm its page count and extract text as a structural check.
- Confirm that all BOM item numbers appear in at least one exploded drawing and
  every drawing number is referenced in the instructions.
- Confirm that no unmeasured electrical value is presented as a validated final
  design value.
