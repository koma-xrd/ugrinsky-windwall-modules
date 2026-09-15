# Winding-tool assembly contract

`windwall.winding_tool_assembly` combines the winding head, horizontal manual
frame, and passive spool payoff. `build_winding_tool_assemblies()` returns two
independent named dictionaries: `winding_jig` and `wire_payoff`. Their origins
are local to each tool; they are not mounted on a common base or synchronized.
Use the two dictionaries as separate CAD assemblies.

The model publishes printable parts, component references, parameters, and
per-tool `rotating`, `stationary`, `bearing_internal`, `adjustable`, and
`hardware_reference` sets. The first three sets partition each assembly;
adjustability and hardware status are additional annotations. The sealed 608
envelopes are assigned to their fixed seats because their internals are not
modeled. The 51105 housing washer stays fixed, its shaft washer rotates, and
its rolling envelope remains bearing-internal.

## Geometry audits

The builder calls `audit_winding_tool_assemblies()` and raises `ValueError`
listing failed checks. The audit can also inspect a modified model and returns
JSON-safe checks, distances, print envelopes, and collision records. It uses
the named dictionary B-reps, rather than trusting component validity labels.

Checks cover valid individual solids, exact ownership, required members,
moving/fixed collisions, all 18 tape passages, retained sliders and their end
stops, physical cam/follower clearance, clamp closing clearance, 2 mm radial
coil release with common-cam travel, the 608/shaft/drive interfaces, a crank
hand envelope, 51105 nesting, the brake hard stop, head-hardware clearance,
head service access, and every printable body's X/Y bed envelope.

Rotation is sampled every 30 degrees and cam release every 0.5 degrees. The
hand envelope is a continuous annular sweep with a 20 mm radial allowance and
5 mm allowance beyond each grip end. Tape clearance is a measured lower bound
using a 10 mm-high rectangular gauge through each rib wall; the width search
resolution is 0.0625 mm. The model is tested at 110, 127, and 145 mm. These are
CAD clearance checks, not continuous collision certification, physical fit
approval, strength testing, or approval of powered winding.

Engagement evidence is returned in `bearing_608_engagement`,
`bearing_51105_engagement`, and `cam_follower_engagement`. Each 608 must occupy
its corresponding upright seat: annular probes overlap its radial seat wall
and axial shoulder, and a core probe overlaps the shaft through the bearing.
The 51105 requires base-floor and housing-wall support, a platter pilot inside
the stack, support above the shaft washer, and an occupied rolling-stack
probe. Internal alignment alone is insufficient if the entire bearing has
been displaced from its supports.

Every follower requires shoulder material inside both its slider bore and cam
track, shoulder material through its washer, thread material through its nut,
and a retaining head above the washer. Additional probes verify washer/nut
material, the nut pocket's loaded roof, and a nearby physical cam-track wall.
Support and core probes require over 95% occupied volume. Probes sit beyond
nominal assembly gaps, and mating distances permit up to 0.2 mm clearance
(0.05–0.35 mm at the follower washer/cam gap). Thus a part displaced into open
space cannot pass just because it no longer collides with another part.

## Retained head hardware and assembly order

The six cam followers are nominal custom 4 mm shoulder screws with M3 threaded
tips, top washers, and underside-loaded captive M3 nuts. The shoulder leaves
running clearance above the cam. The ribs use M3 through-bolts, two washers
each, and locknuts. The pin axis is below the wire-contact shell so hardware
can rotate and withdraw from an isolated slider/rib assembly. Closed pin bores
remain in both the keyed tongue and slider fork.

Each outer guide stop is an M3 screw in an outboard captive-nut boss. Its tip
limits maximum slider travel, while its head is accessible from outside the
wire envelope. The screw direction is 59 degrees from its guide's radial
direction. These replace integral stops that would have trapped the sliders.
There are still 15 printed head bodies; screws, washers, and nuts are hardware.

For initial assembly:

1. Attach each rib to its slider using the M3 bolt, washers, and locknut.
2. Insert the six follower nuts into the slider pockets from underneath.
3. With cam and outer stop hardware removed, slide each rib/slider assembly
   radially into its guide from outside the backplate.
4. Load each outer-stop nut from above, then install its washer and stop screw.
5. Fit the cam, follower screws and washers, and clamp. Install the head in the
   frame using the positive torque pins, shaft cross-pins, and preload screws.

For rib service, remove the head from the frame after releasing preload and
shaft retainers. Remove the clamp and follower screws/washers, then lift the
cam. Remove the selected outer-stop screw, washer, and nut. Slide the complete
bolted slider/rib assembly outward. Only then undo and withdraw the rib bolt
and locknut. Keep the follower nut for reassembly. Reverse this order to refit;
all stops, followers, and retainers must be installed before winding.

No in-situ tangential rib-bolt withdrawal is claimed. The service tests cover
radial removal of the bolted subassembly, outward stop-screw withdrawal, and
bolt/nut rotation and withdrawal on the isolated subassembly.

## Purchasing and physical verification

`winding_tool_bom(model)` returns literal quantities and service notes. A
complete 51105 is one purchased bearing, despite its three modeled members.
The BOM includes two 608 bearings, one 8 mm cross-drilled shaft, six follower
assemblies, six rib-fastener assemblies, six guide-stop assemblies, frame and
crank hardware, and the payoff's replaceable felt, spring, washer, screw, and
nut. Bench bolts and clamps are alternatives within a choice group for each
tool; do not buy both as mandatory mounting hardware.

All screw/pin lengths are nominal CAD selections. The custom follower shoulder,
rib bolt length, brake screw length, shaft drilling, nut pockets, and fits need
physical verification. Grip-axle grooves, retaining rings, cross-pin keeper
clips, upright washers/nuts, and bench washers/nuts are purchasing selections
whose detailed geometry is not modeled. The guide-floor and bolt-end recesses
also require a printed strength and wear trial; local backplate material is
2.5 mm thick at the bolt-end reliefs. The rib pin bore has 0.6 mm of material
below its nominal clearance hole. Spring rate and resulting wire tension are
unmeasured. The tool is a manual prototype.
