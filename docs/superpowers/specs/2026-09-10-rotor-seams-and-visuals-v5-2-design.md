# Windwall V5.2 Rotor Seams and Visual Publishing Design

## Scope

V5.2 improves the printable base support, replaces the implicit blade tongue-and-groove construction with an explicit load-bearing seam, converts every technical drawing to English, and adds a realistic ten-rotor fence hero image plus the supplied animation. The generator architecture, seven-stage rotor height, counterclockwise wind-driven locking direction, central M8 shaft, bearing arrangement, magnet layout, and existing four-screw generator enclosure remain unchanged.

## Base support geometry

The base module shall remain one printable solid. Within the radial footprint of the large upper magnet-carrier plate, each blade root shall continue vertically down to the lowest printable plane of that plate. The continuation shall use the actual two blade footprints, not generic radial ribs. It shall support every blade-root region that would otherwise begin as an overhang when the base is printed on the plate.

The continuation must not obstruct magnet pockets, the 51105 stationary-boss clearance, the rotating bearing pilot, the captive M8 nut pocket, or the continuous shaft passage. Outside the plate footprint, the aerodynamic blade envelope remains unchanged. The result must remain a single valid, closed, manifold print body.

## Explicit blade tongue and groove

The current seam helper derives features from a broad set of horizontal faces. V5.2 shall replace that behaviour with a dedicated blade-seam builder derived only from the two aerodynamic blade cross-sections at the mating plane.

Every lower module shall expose two short upper tongues, one on each blade wall. Every upper mating module shall contain the corresponding two lower grooves. The features shall use the exact locked 60-degree phase between successive modules. Nominal PLA clearance shall be explicit in the design parameters and applied to both transverse directions without changing the external aerodynamic surface.

The seam shall satisfy all of the following:

- both blade surfaces meet without a visible axial gap in the locked pose;
- the groove fully receives the tongue without solid overlap;
- opposed tangential flanks provide positive torque contact in the counterclockwise operating direction;
- insertion and counterclockwise bayonet locking remain possible without rigid-body interference outside the intentionally elastic latch region;
- the tongue and groove do not become the only structural connection.

The permanent three-lug bayonet remains the primary module-to-module form lock. The blade seams share tangential loading and maintain aerodynamic registration. The lower captive M8 nut transfers the assembled rotor torque into the M8 shaft. The exposed upper M8 washer and nut clamp the stack axially.

## Verification and print coupons

Tests shall validate the actual solids, not metadata alone. Required checks include:

- base blade-root support down to the plate print plane;
- no support-blocking material in all protected generator, bearing, nut, and shaft volumes;
- two tongues and two grooves per applicable joint;
- correct 60-degree blade phase and zero axial seam gap in the locked pose;
- no locked-pose overlap and positive counterclockwise tangential contact;
- insertion-path sampling with the known elastic-latch limitation explicitly retained;
- single-solid validity and closed-manifold STL export;
- unchanged active blade envelope above the end-fitting region.

The joint coupon shall expose both representative blade seams as well as the bayonet interface so PLA fit can be checked before full modules are printed.

## English technical drawings

All 15 E01-E15 technical drawings shall be regenerated with English titles, labels, legends, notes, and callouts. English becomes the only tracked raster drawing language. The drawing manifest shall identify English as the raster language.

All six manuals shall embed the same English raster files. German, Chinese, Hindi, Spanish, and French manuals retain localized body text, captions, and alternative image descriptions. Documentation must no longer claim that shared drawings contain German annotations. README image references shall use only the English drawing set.

## Hero image and supplied animation

A new photorealistic, advertising-style hero image shall depict a plausible residential property with a modern house, garden, surrounding landscape, and one fence section containing approximately ten vertical Ugrinsky wind rotors. The rotors should visually correspond to the project concept while the image remains clearly presentational rather than a dimensional engineering drawing. It must not imply certification, validated output, or guaranteed outdoor safety.

The hero image shall appear near the beginning of all six manuals and at the top of the English README. Its alternative text and nearby captions shall preserve the prototype qualification.

The user-supplied `ugrinsky_windwall_10_rotors.gif` shall be copied unchanged into a tracked release media directory. The English README shall embed it directly below the hero introduction. DOCX files shall use the static hero image only; no attempt shall be made to embed or animate the GIF in Word.

## Release integration

The release shall include updated source, tests, STL and STEP exports affected by geometry, the joint coupon if its geometry changes, all affected assemblies, the 15 English drawings, the hero image, the supplied GIF, all six rebuilt manuals, audits, manifests, and release index.

Generated assets must remain reproducible where the current pipeline guarantees reproducibility. The externally generated hero image and supplied GIF shall be hash-bound in the release index but are not expected to be regenerated byte-for-byte by the CAD or drawing scripts.

## Known limits

CAD contact and clearance checks do not prove PLA strength, fatigue life, bayonet durability, real tongue-and-groove fit, rotor balance, safe speed, generator output, weather resistance, or fence structural capacity. These remain physical validation tasks. Document page rendering remains dependent on the bundled LibreOffice renderer; if it is unavailable, the release audit must state that limitation explicitly.
