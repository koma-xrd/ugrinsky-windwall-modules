# Manual winding-tool assembly

This PLA prototype consists of two independent tools: an open vertical wheel
with six removable contact shoes, and an upright free-running wire-roll
turntable. The assembly contains 19 printed occurrences from 12 unique masters,
two 608 bearings, and one complete 51105 thrust bearing. No assembly tools or
additional purchased retention parts are required. Optional bench clamps are
workshop equipment and must remain on the provided lands, clear of moving parts.

The normal drawing setting is 150 mm. The eleven labeled settings are 100, 110,
120, 130, 140, 150, 160, 170, 180, 190 and 200 mm. The wire-contact envelope is a
rounded six-sided form, so the setting is not a promise of a perfectly circular
finished winding or a measured diameter under wire tension.

The rounded contact guide has a 2.7 mm protective shoulder at the free front.
Its wheel-side rear runout stays at the nominal winding radius without a raised
lip. The selected diameter is measured at this contact bottom, not at the
shoulder tip. On the default shoe the nominal-radius runout extends through
construction Z=23.8 mm, covering the winding and upper tape mouth; the smooth
front rise reaches the shoulder at Z=26.5 mm.

## Print and inspect

Print the wheel with its rear face on the bed; the contact shoes with a
90-degree rotation about their construction X axis; the tower on its side;
the shaft and crank with their journals parallel to the bed; the bearing clips
and shaft collars flat; and the grip on its end. Print the payoff base and
platter flat, with the platter pilot upward. Print the payoff spindle with its
axis horizontal. Supports must leave the flexure slots free. Smooth journal
and wire-contact surfaces, removing every burr and support scar.

All finished masters fit a 220 x 220 mm bed in these orientations. Bed fit is
only a geometric check. Test the PLA snap and bearing fits before committing
to a complete build. Inspect the printed 8 mm shaft journals, enlarged drive
faces, snap roots and contact shoes before every use. Replace cracked, whitened,
loose, rough or distorted parts. PLA fit, creep and fatigue remain unvalidated.

## Assemble the winding jig

1. Push the tower's rectangular key into the base until both accessible side
   hooks engage. The key faces carry operating loads; the hooks retain the tower.
2. Insert the two 608 bearings from their respective outward faces. Squeeze the
   split outer-ring clips, insert them into the grooves, and release their ears.
   Both clips must be fully seated, with their ears accessible through the windows.
3. Insert the printed shaft from the open front through both 608 bores. The small
   rear polygon passes through the bearings. Never force a poor journal fit.
4. Snap the two open shaft collars into the grooves immediately beside the front
   bearing. Both collars are necessary: together they restrain forward and rearward
   shaft motion. Their split faces remain accessible through the tower openings.
5. Push the crank onto the rear polygon until its two hooks engage. Compress the
   split end of its integral grip journal and slide on the freely rotating grip.
6. Push the wheel onto the front polygon until the two front-accessible hooks
   engage. Check both axial retention directions and free hand rotation.
7. Insert all six shoes at the same numbered diameter. Each shoe's two middle
   rails narrow directly into 3.98 x 2.98 mm friction tongues for matching
   4.00 x 3.00 mm wheel openings. Both shoulders must stop flat against the
   wheel front. Count six matching labels and twelve seated tongues before winding.

The 608 outer rings belong to the stationary tower. Their shoulders and clips
contact only the outer-ring lands. The front bearing alone locates the printed
shaft through the two collars against its inner-ring lands. The rear outer ring
has axial float. Do not add preload across both bearing stacks or load the seals.
The 608 solids are simplified catalog envelopes; their internal rolling parts
are not separately modeled. Actual purchased bearing lands and clearances need
physical verification.

For replacement, reverse the snap sequence: release the wheel's front hooks,
release the grip end and crank tails, remove both shaft collars, and withdraw
the shaft forward. Squeeze each outer clip and withdraw it through its open
ear window before removing the corresponding bearing. Release the tower's two
exposed side tabs to lift its key from the base.

## Assemble the wire payoff

Place the 51105 lower housing washer on the base's annular floor, then its
rolling member, then its upper shaft washer. Keep these as the three separate
members of one complete purchased bearing. The lower washer stays with the
stationary base; the upper washer supports and turns with the platter. The
rolling envelope is bearing-internal. Printed bearing races are not substitutes
for the supplied washers.

The integrated tool accepts only canonical 8 x 22 x 7 mm 608 bearings and a
25 x 42 x 11 mm 51105 set. Every stored size record and the actual purchased CAD
members are checked against their catalog envelopes before assembly or BOM
approval. The BOM specification is formatted from those validated records.

Push the printed spindle into the base until its lower detents engage the
annular groove. Push the platter over its square upper plug until the upper
detents engage. The platter must remain free to rotate without touching the
base. The 150 mm platter's integral 15 x 20 mm pilot centers the upright wire
roll. The spindle hangs from the platter before it can reach the stationary
base floor, leaving axial freedom instead of compressing the bearing stack.
Keep the upward loading and release path open; the integrated CAD audit reserves
40 mm above the platter's complete envelope for lifting it off the upper plug.

Service is from above: lift the platter to release the ramped upper detents,
pull the exposed spindle to release its lower detents, then lift the upper
washer, rolling member and lower washer. The two finger recesses expose the
lower washer's edge. Check release force on the printed prototype first.

## Tape, wind and release

Prepare three 10 mm tape strips through each shoe's three passages. Each passage
has at least 12 mm tangential clearance for the strip width and a separate
12 mm axial clearance for the winding bundle. Tape width runs along local Y,
not along the axial Z loop height. There are 18 distinct, ordered passages.
The nominal 20-degree sequence numbers identify stations only: physical passage
angles vary with diameter and are not equally spaced, including at 150 mm.
Drawings and assembly metadata report the actual angles. Adjust the tape's final
distribution when forming the later serpentine if required.

Guide the 0.18 mm enamelled wire gently, using a rounded start attachment that
does not cut the enamel. Turn only by the hand crank. Stop the payoff platter
by hand when winding stops. Close all 18 tape wraps and mark winding direction
and leads while the six shoes remain friction fitted.

Support the taped winding with a helper. Grip the first shoe evenly at both
rails, overcome the close friction fit without canting, withdraw it completely
forward, then set it outside the winding's forward path. Repeat for all six
shoes. Do not substitute a one-hole inward shift:
neighboring shoes interfere at the smallest setting. The modeled route withdraws
each shoe 40 mm forward and parks it 40 mm radially outward. Every detached shoe
remains represented as a separate service occurrence throughout removal.
The high front shoulder moves away from the held winding during this motion;
the nominal-radius rear runout slides out beneath it. No radial shoe relief,
wire stretching, tape slip or bending over a rear lip is assumed.
Its ownership becomes service-detached immediately after complete withdrawal,
before parking.

Only after all six shoes are detached and the support clearance is at least
2 mm may the taped winding move forward. The wheel, printed shaft, tower,
crank and base stay assembled. The CAD route translates the coil and all 18
closed tape loops together through the open front; it never removes structural
parts to create an artificial opening. Inspect the first test winding for enamel
damage, changed dimensions and excessive release force before further use.

## CAD contract and limits

`WindingToolAssemblies` contains `winding_jig`, `wire_payoff`, `ownership`,
`parameters` and `audit`. The two dictionaries have separate tool-local origins.
Each occurrence has exactly one ownership record with its motion group, printed
or purchased source, and master identity. Printed records also give rotations
from construction coordinates into the print orientation. To recover winding-jig
construction coordinates, remove the wheel record's axis-height translation and
rotate -90 degrees about X. Payoff occurrences already use construction coordinates.
Translate each oriented master's minimum Z to the bed before export.

The release manifest records only design settings consumed by this tooling:
the two export tessellation tolerances, canonical bearing bore/outer/height
dimensions, the two housing-seat diameters and the 51105 rotating-pilot diameter.
Shared fastener, fit-coupon and unused seat-depth settings are omitted; the
shared V5 parameter model and its release serialization are unchanged.

The wheel's ownership record supplies selected diameter, installed axis height,
nominal station labels and actual tape angles. Those values do not replace
geometry checks. Treat occurrence Workplanes as immutable; a model edit replaces
the corresponding dictionary value with a newly constructed Workplane. Geometry
caches rely on that convention. `audit_winding_tool_assemblies(model)` returns
flat named boolean gates and rechecks the supplied solids. It builds all eleven settings using the
actual shoes, preserving any defects, and tests complete removal at 100, 150 and
200 mm. The builder fails if any gate fails. `winding_tool_bom` derives quantities
from occurrence records and groups the three 51105 members into one purchase.

`coil_removal_stages(model)` returns CAD poses with moving/fixed members,
translations and motion ownership. `audit_winding_tool_service`
can check the normal route or a supplied drawing route, including continuity.
The permitted-motion gate allows only each rigid shoe's straight withdrawal and
parking, followed by the held winding's forward translation. Structural
members must stay fixed, ownership transitions must match the service state, and
the clearance band is located at the actual winding pose. Moving the entire
tool cannot create an artificial clearance result.
Each translation is checked continuously using the initial solid and swept
boundary faces. Full revolutions use
enclosing solids whose containment is checked against actual geometry.
Every rotating occurrence is checked against stationary members, including the
shaft, both collars and the payoff's upper washer. Fused axial envelope sections
preserve the shaft and spindle journal interfaces while covering full rotation.
The winding follows the nominal-radius contact arcs
and their taut straight connecting spans: a rounded hexagon at larger settings,
reducing to a circle at 100 mm. The fixture is deliberately bounded: a 9 mm
axial winding with 1 mm radial build, and 18 closed tape loops with 10 mm
tangential strip width, 10 mm axial loop height and 0.25 mm walls. Their inner
and outer contours follow the curved contact arcs, separated radially by
4 mm; the cavity conservatively encloses the winding, including the inward
chords across the wide tape slots, without crossing it. The width gauge
is conservative for a strip measured along the slightly longer curved arc.
The winding occupies construction Z=12.5..21.5 mm with its inner surface
0.02 mm outside the nominal contact envelope. Its full axial width lies on the
constant-radius rear runout. The assembly checks this contact radius separately
from the front shoulder's outer limit and includes the shoulder in its rotation
envelope. A rigid 20 mm axial ring spanning both contact and shoulder is not
the declared winding fixture and would intersect the seated protective shoulder.
The widened passages retain 0.8 mm outer/mouth radii, with 0.2 mm radii on
the short inner returns at the sector ends. The 3.98 x 2.98 mm tongues retain
0.01 mm nominal clearance per side in 4.00 x 3.00 mm openings. Their narrowed
transition leaves positive shoulders against the wheel front, and their chamfered
rear tips project 1 mm for insertion and optional push-out access.

No physical validation is claimed. Actual shaft strength, PLA friction fit and
wear, bearing fit, winding dimensions, enamel protection, roll stability,
withdrawal force and continuous-use suitability require prototype tests. The payoff
stability estimate assumes light feed; clamp the tools where sliding or tipping
is possible. Wear eye protection and keep hair, clothing, fingers and loose wire
clear. Stop immediately if any printed component is damaged.

Akkuschrauberbetrieb ist nicht freigegeben
