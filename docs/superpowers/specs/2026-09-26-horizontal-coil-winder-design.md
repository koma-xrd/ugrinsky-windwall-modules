# Horizontal 51105-supported coil-winder design

Date: 2026-09-26  
Status: Approved in conversation; awaiting review of this written specification  
Supersedes: the vertical coil-wheel module in
`2026-09-16-simple-pin-adjustable-coil-winder-design.md`

## 1. Purpose

Replace the unstable upright coil-wheel stand with a low horizontal winder. The
wheel rotates about a vertical axis on one 51105 thrust bearing, using exactly
the same unchanged printed base as the existing wire-payoff turntable.

The redesign retains the existing single-piece adjustable wheel, eleven marked
diameter settings from 100 through 200 mm, six removable contact shoes, and 18
tape stations. It removes the tall tower, both 608 bearings, their retainers,
the horizontal printed shaft, shaft collars, and the present side crank.

The result remains a PLA workshop prototype. Physical fit, bearing life,
powered operation, winding repeatability, and structural capacity are not
validated by the CAD model.

## 2. Approved layout

The coil wheel lies horizontally and rotates around a vertical central axis.
The stationary member is the existing `wire_payoff_base` master without any
geometric change. Its actual footprint remains 190 x 190 mm; the earlier
approximate 170 x 170 mm discussion is superseded by exact base reuse.

From bottom to top, the installed load path is:

1. bench;
2. unchanged `wire_payoff_base` floor and 51105 seat;
3. stationary lower 51105 washer;
4. 51105 rolling assembly;
5. rotating upper 51105 washer;
6. new printed horizontal-winder hub;
7. existing adjustable coil wheel; and
8. removable hand crank or a later low-speed driver bit.

The base owns the stationary washer and supports the full axial load. The hub
owns the rotating washer and carries the wheel. A long clearance-fit printed
pilot through the bearing and base bores provides radial guidance; the thrust
bearing is not claimed to locate radial load by itself.

If both tools are operated simultaneously, the BOM contains two occurrences of
the same printed base master and one 51105 bearing stack per tool. There is no
second base geometry or second base export.

## 3. Hub, wheel, and drive

The horizontal-winder hub is a new removable printed part. It interfaces with
the unchanged payoff base and canonical 51105 stack but does not need to match
the payoff platter or spool pilot. It must:

- seat positively on the rotating upper washer;
- use the base and bearing bores as a clearance-fit radial guide;
- provide a positive polygonal drive to the existing wheel;
- establish at least 25 mm clear vertical workspace between the underside of
  the wheel and the top surface of the base outside the central bearing boss;
- retain the wheel under gravity and normal downward winding force without
  fragile locking noses; and
- permit the wheel and hub to be lifted vertically for service.

The wheel-to-hub connection carries torque by shape, not by friction. A flat
axial stop defines the seated height. No screw, threaded rod, adhesive, or
permanent snap is part of the drive connection.

The upper drive interface is a centered female 1/4-inch hex socket sized for a
standard 6.35 mm male hex. The printed hand crank has a matching straight male
hex and is inserted and removed without a latch. Removing the crank leaves the
top of the wound coil unobstructed. The same socket may later receive a cordless
driver bit, but powered use remains explicitly unvalidated and restricted to
slow, controlled experiments.

## 4. Open-top contact shoes

The six shoes retain their current two-tongue friction mounting, numbered wheel
positions, rounded wire-contact surface, and three tape passages per shoe. Their
wire-contact profile changes for horizontal operation:

- the wheel-side lower edge remains a rounded supporting shoulder that prevents
  gravity-driven downward escape;
- the contact surface remains on the selected nominal winding radius;
- the upward edge is smoothly rounded but has exactly 0 mm radial projection
  beyond the nominal winding radius;
- there is no upper lip, centering shoulder, undercut, or other overhang; and
- every tape passage remains open through the final profile.

Gravity keeps the wire against the lower support during winding. After taping,
the finished coil must move straight upward over all six still-installed shoes.
The shoes are not moved inward and are not removed for normal coil release.

The central hub may remain installed during release because it lies inside the
open center of every supported coil. Only the hand crank or driver bit must be
removed before lifting the coil.

## 5. Tape access and operating sequence

The 25 mm minimum free space below the wheel is an operating clearance, not a
nominal overall tool height. The base has no new outer wall, guard, or support
that blocks access from any azimuth. The operator must be able to guide 10 mm
tape through each of the 18 existing passages and beneath the winding while the
wheel remains mounted on the bearing stack.

The normal sequence is:

1. place one unchanged payoff base and one 51105 stack on the bench;
2. install the horizontal-winder hub and adjustable wheel;
3. fit all six shoes at the same marked diameter;
4. insert the removable hand crank into the top hex socket;
5. wind by hand while guiding the wire and manually controlling the independent
   payoff turntable;
6. stop rotation and close all 18 tape wraps with the wheel still mounted;
7. remove the crank or driver bit;
8. lift the taped coil vertically over the six installed open-top shoes; and
9. inspect the wire insulation, shoe surfaces, hub, and bearing stack.

No step in normal release requires unplugging a contact shoe.

## 6. Ownership and release inventory

The horizontal winding module owns these printed occurrences:

- one `wire_payoff_base` occurrence, shared by exact master identity with the
  payoff module;
- one new horizontal-winder hub;
- one existing coil wheel;
- six identical revised open-top contact shoes;
- one removable hex hand crank; and
- one free-spinning rotating crank grip.

It owns one canonical purchased 51105 stack consisting of the two washers and
rolling member. It owns no 608 bearings, tower, bearing clips, shaft collars, or
upright-frame parts. Superseded upright-frame exports and BOM rows must be
removed from the winding-tool release once the replacement is implemented.

The payoff module remains otherwise unchanged. Exact base reuse must not alter
its geometry, fits, stability metadata, assembly, or service sequence.

## 7. CAD and verification requirements

Automated physical checks must cover all of the following:

- exact solid/master identity between the payoff base and the winding-module
  base;
- byte-identical payoff-base STL and STEP artifacts for both module occurrences;
- canonical 51105 washer ownership and axial load path;
- hub contact with the upper washer and base support beneath the lower washer;
- radial pilot engagement through the bearing and base bores without contact
  with the blind base floor;
- positive torque engagement between hub and wheel;
- at least 25 mm wheel-to-base working clearance outside the central boss;
- unblocked tape access at all 18 stations for 100, 150, and 200 mm coils;
- free slow rotation without wheel, hub, crank, base, or bench collision;
- six equal shoe placements at all eleven diameter settings;
- exactly 0 mm upper radial projection on every shoe contact profile;
- continuous collision-free upward release of taped winding surrogates at 100,
  150, and 200 mm while all six shoes remain seated;
- failure of the release audit when any upper lip or other trapping projection
  is introduced;
- hand-crank insertion, torque engagement, and straight withdrawal at the
  1/4-inch hex socket;
- printable orientation and the 220 x 220 mm bed limit for every unique master;
- valid single solids, manifold STL output, successful STEP reimport, and
  deterministic drawings, manifest, BOM, and artifact hashes; and
- complete removal of obsolete upright-frame inventory from the isolated
  winding-tool release.

Negative regression tests must reject a modified shared base, displaced 51105
members, insufficient radial pilot engagement, less than 25 mm tape workspace,
blocked tape passages, a retained upper shoe lip, an unseated wheel, and a drive
that depends only on friction.

## 8. Documentation and drawings

The German assembly guide and release drawings must show the horizontal
orientation, the exact shared payoff base, the 51105 stack order, the 25 mm
minimum work gap, top hex drive, tape routing, and straight-up coil release with
all shoes installed.

The guide must distinguish the two uses of the common base and state that two
printed occurrences are required for simultaneous winding and payoff. It must
also state that the 51105 parts are purchased bearing members, not printed
races.

## 9. Safety and validation limits

Manual operation is the validated design intent. A cordless driver may only be
described as a future low-speed option. The documentation must not assign an
approved speed, torque, duty cycle, or production use before physical testing.

The following remain unvalidated:

- actual PLA-to-bearing and pilot fits;
- printed hub and hex-drive strength;
- crank retention by straight plug fit;
- stability under real wire tension and operator force;
- smoothness and life of the 51105 in this application;
- enamel protection and achievable winding accuracy;
- tape access with the operator's actual tape and hand size;
- coil-release force; and
- cordless-driver operation.

Eye protection is required. Hair, clothing, fingers, loose wire, and tape must
remain clear of rotating parts. The operator must stop immediately if the hub,
hex drive, shoes, wheel, bearing seat, or base shows cracking, looseness, or
abnormal wear.
