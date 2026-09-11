# Blade seams and the V5.2 joint coupon

Each applicable rotor joint has two blade-wall seam pairs. Base and standard
stages carry upper tongues; standard and top stages contain lower grooves.
The three-lug permanent bayonet remains the primary lock. The blade seams
provide aerodynamic registration and supplementary tangential contact.

`build_blade_seam()` returns the two tongues and two groove cutters in the
bottom blade frame, with the mating plane at z=0. Upper module ends rotate
these features by the stage's 60-degree blade twist. The builder consumes only
the two analytic aerodynamic section faces shared with the blade loft; it
does not inspect horizontal faces on assembled hubs or receiver fittings.

The keyed region is the largest connected outer section of each blade wall,
outside the bayonet envelope. The inner return stays unkeyed. Insetting and
overlapping sections through the shallow groove depth reserves the exterior
skin despite the blade twist. Rounded wire offsets apply clearance equally
in every transverse direction. Nominal locked stage pitch remains 70 mm, and
the blade skins meet directly at the seam.

| Parameter | Default |
| --- | --- |
| Tongue height | 0.8 mm |
| Groove depth | 1.05 mm |
| Transverse clearance per side | 0.12 mm |
| Reserved blade skin | 0.35 mm |
| Bayonet seating headroom | 1.0 mm |

Insert the upper stage at the bayonet entry orientation, 18 degrees clockwise
from its final position. Keep it 1 mm above the nominal seam while rotating
counterclockwise to the final 60-degree blade phase, then lower it axially
onto the blade skins. The receiver's additional headroom raises its roof while
preserving the minimum 3 mm loaded roof and floor. The locked bayonet retains
zero ramp rise, three lugs, tangential stops, permanent latch and open centre.

The joint coupon includes both representative blade seams on short walls,
connected by spokes to their respective bayonet halves. It retains the
4.2 mm deep, open-spoke M8 hex calibration recess. Its receiver and blade
features require a fresh coupon print; earlier coupon dimensions are obsolete.

CAD tests sample insertion, raised rotation and final seating, verify the
remaining skin against actual blade sections, and check positive CCW tongue
contact and collision-free locked solids. Only the bounded permanent-latch
region may interfere along the sampled path. These checks do not establish a
continuous collision proof or validate elastic latch deflection, PLA strength,
fatigue, fit, balance or safe operation. The thin seam walls and 0.12 mm nominal
clearance require physical calibration with the intended printer and settings.
