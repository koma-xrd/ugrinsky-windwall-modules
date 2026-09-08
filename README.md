# Windwall

Parametric CadQuery source for a seven-stage Ugrinsky wind-wall rotor. The
source files are authoritative; generated STEP and STL output belongs in the
local `build/` directory.

## CadQuery environment

Use a project-local Python **3.12** virtual environment for geometry commands.
The local runtime is Python 3.12.14, CadQuery 2.8.0, OCP 7.9.3.1.1,
VTK 9.6.2, CasADi 3.7.2, NLopt 2.9.1, and NumPy 2.3.3 on Windows x64.
Create it with an available 3.12 interpreter
(or substitute that executable for `py -3.12`):

```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = "$PWD;$PWD\src"
& .\.venv\Scripts\python.exe scripts/run_geometry.py -m unittest discover -s tests -v
```

The portable CQ-editor 0.7 package contains only `CQ-editor.exe` and has no
standalone Python. Use it as an interactive viewer by opening
`scripts/preview_blade.py` and pressing Render. Do not modify system Python.
CadQuery recommends virtual environments and cautions about bleeding-edge Python
dependencies in its [installation guidance](https://cadquery.readthedocs.io/en/stable/installation.html).

**Known environment limitation:** geometry assertions can complete successfully,
but this local runtime subsequently exits with native Windows status
`-1073741819` (access violation). `import cadquery` alone reproduces it without
project code. The earlier CadQuery 2.6.1/OCP 7.8.1.1.post1 combination also
failed during shutdown, with `-1073740940` (heap corruption); both statuses were
also observed during bayonet verification in the current runtime. These are not clean
CLI exits, and `pip check` alone does not detect the native problem. Resolve
the runtime before using this environment for unattended export/CI. CQ-editor
preview execution has not been visually verified because its UI automation was
unstable; a generated section-overlay PNG and STEP preview were inspected/exported.

Use `scripts/run_geometry.py` for CLI commands that import CadQuery. Before
loading the requested script or module, this launcher sets process-local Windows
`SetErrorMode` flags `SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX` (`0x0003`),
preserving inherited flags. This suppresses native error dialogs without
catching failures or converting exit statuses to success. It changes no registry
or system setting. Record unittest output and `$LASTEXITCODE` separately. Four
subprocess tests verify the flags, argument forwarding, and preserved exit code.

## Run the parameter tests

From the repository root, make both the repository package and `src/` visible,
then run the standard-library test suite:

```powershell
$env:PYTHONPATH = "$PWD;$PWD\src"
python -m unittest tests.test_parameters -v
```

The repository root is included because Python 3.14 safe-path behavior does
not add the current directory when `PYTHONPATH` is set, and `tests` is an
importable package.

## Local reference meshes

Place downloaded reference STL files in `reference/` for measurement and
visual comparison only. They are intentionally ignored by Git and must remain
local. Production solids are reconstructed from parameters; do not import the
reference meshes into production geometry.

## Reference STL audit

The reference audit requires NumPy. In a clean Python environment, install the
project's declared dependency before running it:

```powershell
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the read-only binary-STL audit against a directory of reference meshes:

```powershell
$env:PYTHONPATH = "$PWD;$PWD\src"
& .\.venv\Scripts\python.exe scripts/analyze_references.py "C:\path\to\reference-files"
```

The command writes `build/reference-report.json`, containing mesh envelopes,
signed volumes, connected-component counts, and boundary, non-manifold, and
degenerate-face counts. The input meshes are never copied into this project.

## Shared blade reconstruction

`src/windwall/blade_profile.py` builds tangent 24 mm and 60 mm circular arc
centerlines with a 1.5 mm wall, a complementary 180-degree blade, and a 13 mm
radius central hub. Dimensions are in `BladeParameters`; stage height remains
authoritative in `RotorParameters`. The arcs meet at `(12, 0)` in the bottom
section's shaft frame. No production code imports STL geometry.

The source twists **60 degrees counterclockwise over 70 mm**. Nine analytic
sections are lofted through that twist; a straight extrusion would lose the
original surface and cannot match its full envelope. The midplane is rotated
30 degrees relative to the bottom section. Later modules retain identical nominal
placement transforms; that convention does not remove the internal twist or
prove compatibility of their future end fittings.

Reproduce the external comparison without copying the mesh into the repository:

```powershell
$env:PYTHONPATH = "$PWD;$PWD\src"
$env:WINDWALL_REFERENCE_BLADE = "C:\path\to\7 Ugrinsky_Blade.stl"
& .\.venv\Scripts\python.exe scripts/run_geometry.py scripts/preview_blade.py $env:WINDWALL_REFERENCE_BLADE
& .\.venv\Scripts\python.exe scripts/run_geometry.py -m unittest tests.test_blade_profile tests.test_preview_blade -v
```

The command slices triangles at z=35 mm, joins edges within 0.05 mm, writes
`build/blade-midplane.csv` and `build/blade-fit.json`, and rejects circle fits
above 0.20 mm RMS. Eight wall-surface fits have RMS residuals of 0.014–0.018 mm.
Production centerlines regularize those measurements to exact tangent circles.
CQ-editor shows the clean solid, red CAD section, green reference section, and
blue counterclockwise marker viewed from +Z. Its overlay reads the external
environment variable or the previously generated local CSV.

Tests require one valid solid, the 121.5 × 120.732 × 70 mm envelope within
tolerance, retained twist, and less than 0.60 mm symmetric section deviation
outside radius 20 mm at z=5, 17.5, 35, 52.5, and 60 mm. The external comparison
is explicitly skipped without its environment variable. Original end fastener
bosses near z=65–70 mm are replaced in later module tasks. The solid hub is an
intermediate body; those later tasks also add the shaft clearance and fittings.

The disconnected reference blades require a connecting radius above 11.25 mm.
A literal exclusion of the outer 85 percent of the 60.75 mm radius would allow
only 9.11 mm and cannot connect them. The hub uses the approved central-radius-
20-mm exception and is capped at one configured loaded-wall thickness beyond
the minimum blade contact radius.

## Counterclockwise bayonet coupon

`src/windwall/bayonet.py` builds a three-lug male hub and receiver independently
of the blade solid. `build_male_bayonet`, `build_female_bayonet`, and
`build_bayonet_coupon` take `DesignParameters` and an optional `z_plane_mm`.
The default builds are placed in the locked assembly frame: the male is at
0 degrees, and the receiver bottom is at the supplied Z plane.
`locked_angle_deg` returns the positive travel from insertion to lock, 18 degrees.
`coupon.male_at_travel(0)` places insertion at -18 degrees (clockwise viewed from
+Z); increasing travel counterclockwise to 18 degrees produces the final zero
orientation and raises the male by 0.45 mm.

The hub is 34 mm across, with three 4 mm deep, 8 mm wide, 3.2 mm thick rounded
lugs and 1.5 mm concave root fillets. Receiver insertion windows follow the
offset lug/root outline. Radial sections at intervals below one degree form
ruled rising channels; the finite lug envelope includes radial and axial
manufacturing clearances of 0.30 and 0.25 mm. The receiver is approximately
48.92 mm across and 12.03 mm high. Its roughly 24.46 mm radius is localized
interface structure; the earlier 20 mm aerodynamic comparison exclusion is not
an envelope restriction on these approved fittings. Later module integration
must keep this intrusion localized and blend the interface into its end region.

The locked lug faces contact solid counterclockwise stops, so the minimum
distance between the entire parts is intentionally zero. The coupon's
`minimum_locked_clearance_mm()` measures radial and axial running faces,
excluding tangential stop/window walls; the default measured running gap is
0.30 mm. Tests sample axial insertion, every degree of locking, intermediate
half-degree positions, and both torque directions at the stop. No nominal
motion has a positive intersection volume; +0.5 degree CCW overtravel intersects
the stops, while -0.5 degree CW reverses freely. A 2 mm axial pull is obstructed
in the locked position. These checks establish geometry, not load capacity,
friction, preload, print fit, or radial rocking.

Export without sending a print job:

```powershell
$env:PYTHONPATH = "$PWD;$PWD\src"
& .\.venv\Scripts\python.exe scripts/run_geometry.py scripts/preview_bayonet.py
$exportExit = $LASTEXITCODE
& .\.venv\Scripts\python.exe scripts/run_geometry.py -m unittest tests.test_bayonet tests.test_preview_bayonet -v
$testExit = $LASTEXITCODE
```

The script writes `build/coupons/bayonet_male.stl` and `bayonet_female.stl`, each
with its bottom at Z=0, plus `bayonet_locked.step`, top/isometric SVGs, and
`bayonet_fit.json`. It validates one connected, closed manifold mesh with no
degenerate faces per part and records motion/stop measurements. Tests re-import
the STEP assembly and require two solids. Open `scripts/preview_bayonet.py` in
CQ-editor to show the pair, elevated insertion ghost, and CCW direction marker.
Interactive rendering remains unverified; static solid-section and mesh views
were inspected. The female undercut may need slicer bridging/support tuning.

Physical PLA calibration is outstanding and no coupon has been printed. Retain
the central clearance defaults until an authorized coupon print establishes
insertion force, locking force, cracking resistance, and radial rocking. Module
shoulders/preload and loaded operation are separate later work. The combined
coupon below adds transition-adjacent drivers and reverse retainers.

## Transition-adjacent drivers and radial retention coupon

`src/windwall/drivers.py` consumes the same `DesignParameters` and the existing
bayonet frame. Its public builders are `build_drivers`, `build_driver_pockets`,
`build_screw_pilots`, and `build_joint_coupon`. The first three return two-solid
Workplanes for integration; the coupon returns connected `male` and `female`
print parts, `driver_centers`, `screw_axes`, registration metadata, and the same
`male_at_travel` motion helper as the bayonet. Translate/rotate both members
explicitly when registering a module interface.

The true blade transitions `(12, 0)` and `(-12, 0)` lie inside the receiver.
Exactly two rounded trapezoidal drivers therefore sit at nearby small-arc
stations `(22.234, 19.660)` and its 180-degree copy (radius approximately 29.68 mm).
They use 6 mm radial length, 8/6 mm inner/outer widths, 0.8 mm corner radii,
4 mm engagement and 3 mm shoulder thickness. Short local bridges connect them
to the hub and receiver. These are transition-adjacent interface fittings;
their intrusion stays local to the ends and they are not continuous blade-skin
tabs. The source blade geometry and external reference-STL policy are unchanged.

The open-top pocket cutters cover the -18-to-zero-degree rotation and the
0.45 mm axial rise. Their one-degree envelope includes the configured 0.30 mm
radial clearance plus an explicit between-sample displacement allowance
(approximately 0.29 mm), and 0.25 mm axial clearance. This conservative envelope
has more play than the nominal clearance alone. Leading trapezoid flats meet
solid CCW stops at zero; clockwise release is clear. Local receiving pads extend
3 mm beyond the swept pocket boundary and retain a floor below it.

Two 3 mm × 12 mm screw envelopes at 70 and 180 degrees pass through 3.3 mm outer
clearance holes into 2.3 mm blind PLA pilots. Three-millimeter solid annuli around
the holes are tested away from the intentional radial openings. Six-millimeter
screwdriver corridors extend outward beyond the rotor radius and are clear of
the isolated coupon. Full seven-stage blade/tool access remains a module and
assembly integration check. Dimensions and angles are in `DriverParameters`;
fastener and manufacturing defaults remain in `ManufacturingParameters`.

The combined coupon keeps the complete three-lug ring and both driver/screw
features to preserve ring stiffness during calibration, rather than cutting out
a single lug sector. Its male also includes a top-accessible 13.30 mm across-flats,
6.8 mm deep M8 nut sample. This coupon-only pocket does not imply captive nuts
in every rotor stage. Exported male/female envelopes are approximately
52.44 × 47.31 × 12.50 mm and 69.10 × 54.48 × 13.44 mm.

```powershell
$env:PYTHONPATH = "$PWD;$PWD\src"
& .\.venv\Scripts\python.exe scripts/run_geometry.py scripts/preview_joint_coupon.py
$exportExit = $LASTEXITCODE
& .\.venv\Scripts\python.exe scripts/run_geometry.py -m unittest tests.test_drivers tests.test_preview_joint_coupon -v
$testExit = $LASTEXITCODE
```

Outputs under `build/coupons/`: `joint_male.stl`, `joint_female.stl`,
`joint_locked.step`, top/isometric SVGs, and `joint_fit.json`. Each mesh is one
closed manifold component with no degenerate faces and bottom at Z=0. Tests
re-import the STEP as two solids. The exporter checks insertion at 1 mm intervals,
the locking path at 0.5-degree intervals, directional driver stops, and radial
tool access. A static actual-solid inspection is available locally as
`joint-inspection.png`; interactive CQ-editor rendering remains unverified.

Both parts use a zero-angle locked joint frame. Registration metadata preserves
the measured +60-degree blade twist and zero nominal module rotation, and marks
`module_end_registration_verified=false`. Identical nominal transforms do not
make the lower stage's +60-degree top blade section continuous with the next
stage's zero-degree bottom. Module construction below explicitly sets the fitting
phase, local end supports, and blade/tool clearance. The pocket sweep does not
absorb the 60-degree mismatch.

No physical coupon has been printed. Record pilot engagement, nut fit, insertion
and locking force, reverse retention and cracks before full-stage printing.
Strength, print support/bridging and screw-head fit remain unverified. Assembled
blade/tool access is checked by the module geometry below. CLI assertion/export
completion still precedes the known native
runtime shutdown failure; record the nonzero exit separately.

## Base, standard and top rotor modules

`src/windwall/rotor_modules.py` supplies `build_base_module`,
`build_standard_module`, and `build_top_module`. Each returns a frozen
`RotorModuleModel` containing one printable `shape` and its shaft/seat metadata.
Every module has an 8.8 mm continuous shaft passage, giving 0.40 mm radial
clearance around the nominal M8 rod. All three retain the same source blade
frame and +60-degree twist; place the modules at successive 70 mm Z increments
with zero nominal angular offsets.

The standard module consumes the reusable `build_joint_interface` pair: bottom
male lugs/drivers and blind pilots, top female tracks/pockets and radial guides.
The coupon-only hex pocket is excluded. A single explicit
`ModuleParameters.joint_phase_deg=100` rotates both fitting members, placing
the two module screw axes at 170 and 280 degrees. The upper module still enters
18 degrees clockwise from its final nominal orientation and rotates CCW to
zero. This fitting phase is not a rotation of the module or its source blade.

`module_joint_depth_mm` returns 17.141922 mm. The lower male is translated by
minus that depth; the upper receiver starts at local z=52.858078 mm. A 3 mm
support plate below the receiver and a 3 mm lower root plate use a 36 mm radius
to join the fittings to the blades. The standard and top solids extend down to
z=-12.5 mm for engagement, so their print envelopes are approximately
121.49 x 120.93 x 82.50 mm despite their 70 mm nominal stage pitch.

At radius above 36 mm, only the bottom 0.70 mm of blade is relieved for the
0.45 mm ramp displacement plus 0.25 mm axial clearance. That removes
161.30 mm3, or 0.246 percent of the source stage volume. The source skin above
this edge is retained; receiver pads add local material out to radius 36.351 mm.
Material outside radius 36.4 mm is unchanged above the relief. For base/standard
receivers, reconstruction in the
upper 17.14 mm additionally displaces 1901.56 mm3 of source blade material
between radii 20 and 36 mm before installing structural fittings. The middle
blade remains unchanged; the structural end regions have an aerodynamic
impact that has not been measured. No aerodynamic continuity across the
60-degree seam is claimed.

The base replaces its lower male with a 34 mm diameter, 3 mm deep shaft flange
and the integrated upper magnet carrier described below. Its nominal bounds
are z=-13..70 mm, yielding an 83 mm print height. The carrier has an
open-bottom captive M8 torque-nut pocket; the top module retains its exposed nut.

The top uses a reinforced washer-bearing hub with a 24.6 mm diameter,
0.5 mm deep recess for a 24 mm OD washer. Its floor is at z=69.5 mm. The exposed
M8 nut sits above the washer and is accessible to a wrench before the closure
is fitted. This corrects the original captive-top-nut plan: a washer above a
buried nut would not distribute that nut's clamp load. Accordingly,
`nut_pocket_across_flats_mm` is `None` for standard/top and 13.30 for the base,
while the top's `washer_seat_diameter_mm` is 24.6. The independent joint coupon
retains its 13.30 mm across-flats, 6.8 mm deep nut fit sample.

Closure pilots are at XY=(24,0) and (-24,0), 2.3 mm diameter and 8 mm blind
depth, with at least 3 mm surrounding material and a blind floor. The closure
must clear the washer, exposed nut and actual rod projection. With a 2 mm
washer, the nut starts at z=71.5 mm, above the 70 mm blade ends; the closure
must not take the M8 axial clamping load.

```powershell
$env:PYTHONPATH = "$PWD;$PWD\src"
& .\.venv\Scripts\python.exe scripts/run_geometry.py -m unittest tests.test_rotor_modules tests.test_preview_modules -v
$testExit = $LASTEXITCODE
& .\.venv\Scripts\python.exe scripts/run_geometry.py scripts/preview_modules.py
$exportExit = $LASTEXITCODE
```

Outputs under `build/modules/` include the three STLs placed at print Z=0,
three STEP files preserving their assembly frames, individual isometric SVGs,
`two_modules_locked.step`, and `module_fit.json`. The module exporter now
generates `magnet_pocket_coupon.stl`/STEP before the base carrier. Tests round-trip every STEP
and require each STL to be one connected closed manifold with no degenerate
faces. The export checks all three unique adjacent pairings at lock and their
6 mm radial screwdriver corridors. The standard/top pair checks locking every
0.5 degree and insertion every 1 mm; all measured intersection volumes are
zero. Changed joint phases are rejected if they obstruct a blade/tool corridor.
These are solid-envelope checks, not a calibrated screw-head, wrench or print
fit certification.

`scripts/preview_modules.py` also displays the three parts in CQ-editor. Actual
exported STEP meshes, blade seam sections, top seat and locked screw/tool
sections were inspected in the local static image
`build/modules/module-inspection.png`; interactive CQ-editor rendering remains
unverified. No physical parts were printed. Validate coupons, support/bridging,
loaded walls, torque, rod alignment and two-stage fit before full-stack printing.

## Dual magnet generator reconstruction

`src/windwall/generator.py` builds clean analytic upper/lower magnet carriers,
stationary clearance solids, nominal M8 rod/clamps, and an adjustable central
spacer. `build_upper_magnet_carrier`, `build_lower_magnet_rotor`, and
`build_stationary_generator_reference` consume `DesignParameters`.
`build_generator_assembly` returns the integrated base module, separate lower
rotor, stationary parts, shaft, spacer and clamp envelopes. Its gap helpers use
actual solid Z bounds; collision helpers intersect the actual solids.

Measurements came from external STL sections, never imported mesh solids.
The magnet ring measures about 103.994 mm OD with a 3 mm disc and a 10 mm
overall boss height. Eighteen approximately 11.004 mm diameter blind pockets
lie on a 44.5 mm radius; the source pocket floor is at z=0.998 mm and the
opening at z=3 mm. The reconstruction regularizes the pockets to 11 x 2 mm,
increases the web from 1 to 3 mm, and grows the OD to 106 mm to retain a 3 mm
outer rim. The resulting disc is 5 mm thick, with a 34 mm central hub and six
3 mm wide rear ribs reaching the 10 mm overall height. Hole count records the
reference pattern only; it does not select electrical poles or polarity.

The upper carrier faces downward and fuses through the base flange. A 13.30 mm
across-flats, 6.8 mm deep hex opens from below; its ceiling leaves 3.2 mm of
hub material beneath the fusion face. It receives the same coupon-gated M8
torque-nut fit as the existing joint coupon. The lower carrier faces upward;
its rear hub has a flat 24 mm washer load face and a nominal lower nut envelope.
The nuts and spacer reserve a mechanical clamping path; hardware tolerances,
preload, anti-loosening, torque capacity and centrifugal magnet retention have
not been validated. Magnet pockets are open and need a proven retention method.

The coil former is conservatively represented by a 118 mm OD, 12 mm thick
annulus with the measured 12.4 mm center passage. Its entire winding zone is
occupied clearance volume; no coil shape or potting construction is inferred.
The separate 112 mm OD, 62 mm ID, 2 mm cover sits above it, reserving 14 mm
total stator height. The original cover may nest into the former; that seating
detail is deliberately not certified by this conservative reference.
The cup retains the measured 120 mm OD, 114 mm cavity, 27 mm height and 3 mm
floor, with a new central bore/support for the common rotating shaft.

The source top-bearing feature has an approximately 12.305 mm bore and 20 mm
boss; it does not establish a specific M8 bearing product. A **provisional
12 x 8 x 6 mm sleeve envelope** sits in a parameterized 12.3 mm seat and 20 mm
support. Its length and inner/outer diameters are assumptions for clearance
work, not procurement dimensions. Axial bearing retention, alignment and
threaded-rod running fit remain unresolved. Stationary solids are clearance
references, not completed printable generator supports.

| Part or region | Default nominal Z bounds, mm |
| --- | --- |
| Upper carrier, integrated into base | -13 to -3 |
| Stator cover | -16.5 to -14.5 |
| Coil-former reference | -28.5 to -16.5 |
| Lower rotating carrier | -40 to -30 |
| Central 12 mm OD spacer | -30 to -13 |
| Lower washer / nut envelopes | -42 to -40 / -48.8 to -42 |
| Stationary cup | -55.5 to -28.5 |
| Provisional sleeve bearing | -55.5 to -49.5 |

Both carrier-to-stator gaps are 1.5 mm. These are magnet air gaps only when
the installed magnets are flush or below their pocket planes; measure actual
magnet thickness/protrusion before relying on them. Gap parameters remain
adjustable, and the central spacer changes with their sum. Increasing the
lower gap consumes clearance below the lower clamp; incompatible cup height,
gap, bearing and clamp combinations are rejected. For example, a 3 mm lower
gap is tested with a 30 mm cup instead of the default 27 mm cup.
The default spacer-to-former radial clearance is 0.2 mm and the sleeve-to-seat
radial clearance is 0.15 mm, both physically unverified.

```powershell
$env:PYTHONPATH = "$PWD;$PWD\src"
& .\.venv\Scripts\python.exe scripts/run_geometry.py scripts/preview_generator.py
$exportExit = $LASTEXITCODE
& .\.venv\Scripts\python.exe scripts/run_geometry.py -m unittest tests.test_generator tests.test_preview_generator -v
$testExit = $LASTEXITCODE
```

Outputs under `build/generator/` include the magnet-pocket coupon, integrated
base and separate lower carrier in STEP/STL, an 11-solid colored assembly STEP,
isometric/section SVGs, and `generator_fit.json`. Coupon diameters increase along
the coupon's +X direction: 10.8, 11.0 and 11.2 mm; each is 2 mm deep above a
3 mm floor. Both full-carrier export paths generate and topology-check the
coupon first. This is a CAD generation gate; it does not claim a physical
coupon was printed or passed. Report flags explicitly retain unverified
magnet fit, bearing fit/retention, magnet retention and electrical design.

The base preserves Task 6's +100-degree joint phase, 0.70 mm edge relief and
unchanged active blade; standard/top geometry and exposed top clamp remain.
The relief comment now correctly states that the upper stage starts below its
locked height and rises during locking. Static actual-solid generator section
inspection is supplied locally as `build/generator/generator-inspection.png`.
CQ-editor interactive verification, physical coupons,
support/bridging, strength and operation remain unverified. Every CadQuery CLI
process still uses the dialog-suppressing launcher and records native shutdown
failure separately from assertion/export results.

## Serviceable top closure and complete rotor

`src/windwall/top_closure.py` builds a symmetric 121.5 mm disc seated at the
top module's local Z=70 mm. Its 5 mm plate ties both blade ends to the existing
reinforced pilot pads at X=+/-24 mm. Two nominal M3 x 12 mm screws engage 7 mm
of each 8 mm blind pilot through 3.3 mm clearance holes. Nominal 5.5 mm diameter,
3 mm tall heads fit inside the 6 mm tool corridors. Verify actual hardware.

The raised center has a 24.6 mm cavity, 3 mm wall and 3 mm roof. A 24 x 2 mm
washer bears on the reinforced hub at local Z=69.5 mm, beneath the exposed M8
nut at Z=71.5 mm. Its reserved 6.8 mm height and a 3 mm rod projection put the
shaft tip at Z=81.3 mm, 0.25 mm below the roof. The closure ends at Z=84.55 mm.
The cavity clears the washer, nut and rod, so the disc does not carry the M8
clamping load. Remove its two screws and lift straight up to expose the nut
without unlocking a module joint. Remove the nut before lifting the washer.
The closure is not weather-sealed.

`src/windwall/assembly.py` supplies `build_locked_rotor_assembly` and
`build_exploded_rotor_assembly`. The locked base is at Z=0, five standards at
Z=70/140/210/280/350, and the top at Z=420. Every nominal stage rotation is zero
and the aerodynamic height is 490 mm. The +60-degree internal twist remains:
blade phase jumps back 60 degrees at each seam. Structural supports bridge
the ends; a continuous helical skin or aerodynamic performance is not claimed.

The 34 named solids include seven stages, one closure, twelve radial seam
screws, two closure screws, the lower generator references and clamps, top
nut/washer, and one M8 rod from Z=-60.5 to Z=501.3 mm (561.8 mm nominal length).
The upper magnet carrier is fused into the base and appears only once. Rod
length is an envelope, not a stock-cutting instruction: measure actual hardware.
Both generator gaps remain 1.5 mm for flush/subflush magnets.

Exploded stages are 18 degrees clockwise from their own locked frames. Entry
is 0.45 mm below lock; 15 mm lift from each entry gives cumulative 14.55 mm
increments above nominal stage placement, fully separating each joint. Each
stage is illustrated relative to its own locked lower frame; this is not a
simultaneous insertion motion between all exploded pieces. Radial screws
withdraw first, the closure lifts separately, and the real rod keeps its length.

`assembly_validation.py` intersects all actual component pairs, allowing only
each named M3 shank's bounded thread-forming overlap in its designated blind
pilot. Stops and washer/closure seating are zero-volume contacts. All three
unique pairings (base/standard, standard/standard, standard/top) sample axial
insertion every 1 mm and locking every 0.5 degree. CCW overtravel must meet
both bayonet and driver stops, CW release must remain clear, and a 2 mm locked
pull must meet the retention roof. Running clearance is measured on the
reusable bayonet interface, excluding intentional stop contact. All six seams
check actual shank/head/tool access at 170 and 280 degrees. Top closure,
wrench and washer service paths and generator clearances are also audited.
Sampling is CAD evidence, not a proof of continuous motion or physical fit.

```powershell
$env:PYTHONPATH = "$PWD;$PWD\src"
& .\.venv\Scripts\python.exe scripts/run_geometry.py -m unittest tests.test_assembly tests.test_preview_assembly -v
$testExit = $LASTEXITCODE
& .\.venv\Scripts\python.exe scripts/run_geometry.py scripts/preview_assembly.py
$exportExit = $LASTEXITCODE
```

The exporter validates the magnet pocket coupon first, then STEP/STL for base,
standard, top, closure and lower magnet rotor. Outputs under `build/assembly/`
include 34-solid locked/exploded STEP files, `assembly_fit.json`, a top section
SVG and `assembly_inspection.png` rendered from exported STEP solids. Every STL
must be one closed manifold component without degenerate faces, at print Z=0.
The script also supplies locked, exploded and sectioned CQ-editor views;
interactive inspection remains unverified. No print is sent. Physical coupons,
two-stage fit, support/bridging, balance, strength, magnet/bearing retention
and generator operation remain unverified.
