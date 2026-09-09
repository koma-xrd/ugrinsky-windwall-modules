# Windwall

Parametric CadQuery source for a seven-stage Ugrinsky wind-wall rotor. The
current tracked release is `release/v5/`; `release-index.json` covers the complete
release and `manifest.json` remains the geometry inventory authority.
Exploratory and historical generated output belongs in the local `build/` directory.

## Current V5 manual and release

The German [V5 assembly and experiment manual](release/v5/docs/Ugrinsky-Wind-Wall-V5-Bauanleitung.docx)
covers twelve printed bodies from eight different STL files: one base, five
standard modules, one top, one lower magnet rotor, one housing, one coil cassette,
one stationary cover and one upper bearing support. The upper magnet carrier is
integrated into the base. Both carriers rotate; the coil, cassette, housing,
cover and upper support remain stationary. The lower carrier runs inside the
housing below the coil. V5 uses a 51105 axial bearing (25 × 42 × 11 mm), a 608 upper
radial bearing (8 × 22 × 7 mm), six M4 cover fasteners with captive nuts, four
bottom mounting tabs and four wood screws for the upper support. The fence
assembly includes the extended M8 shaft.

The [final release index](release/v5/release-index.json) binds geometry, all 15
drawings, the DOCX and their inventories to repository-relative paths, SHA-256
hashes, file sizes, roles, quantities, dimensions and available validation evidence.
`scripts/index_v5.py` regenerates it after validating the geometry/drawing source
binding and the hash-bound [manual inspection](release/v5/audits/manual.json).
The audit binds the reviewed geometry manifest, figures inventory, exact E01–E15
filename-to-SHA256 mapping, and DOCX bytes. Changed CAD, PNG, DOCX or source-manifest
bytes cannot inherit that prior review; the index builder rejects mismatches and
unlisted files. Regeneration does not perform or approve a new manual review,
and the index does not imply physical approval.

The user reported that the printed V4.3 bayonet coupon fits and closes. Its
assembly force and durability remain unmeasured. Rigid CAD sweeps encounter
the permanent pawls and, when lifted to clear the blade tongue, the lug roof;
the motion audit reports these overlaps and leaves elastic assembly unverified.
Installed geometry remains collision-free within the stated numeric tolerance.
The joint coupon retains the approved 4.2 mm open-spoke hex calibration recess;
it is not a full-depth M8 nut socket and has no continuous hexagonal load floor.
Running-clearance measurements exclude intentional snap-pawl and stop faces.

The manual includes all E01–E15 figures, nine coupon files, the three assembly
STEP references, PLA/Bambu P2S 0.4 mm nozzle guidance, later ASA trials, actual
assembly order, cassette service access and the experimental 20/40/80 winding
matrix for 0.18 mm wire and each later measured wire diameter. It explicitly
prohibits direct connection to a 48 V lead battery. No final winding, safe speed,
load rating, watertightness or outdoor-operation approval is claimed. The nominal
1.5 mm distances run from each magnet face to the active winding face and include
the intervening plastic: the 1.00 mm cover diaphragm above and the 1.00 mm cassette
floor below. Mechanical magnet-to-plastic clearances are 0.35 mm above and 0.50 mm
below; cassette-to-cover retention travel is separately 0.15 mm. These nominal
distances apply only with flush or subflush magnets; actual fits and retention
require physical tests. E06/E07 show all 18 alternating winding-facing poles on
each ring in a common angular projection, with opposite poles at matching angles.
The housing rejects cassette heights below 11.85 mm, derived from its fixed cable
boss and cover envelope; the 12 mm default is unchanged. The figure renderer
rejects requested geometry parameters that differ from its source manifest.

`scripts/manual/manual_data.py` reads only the current V5 manifest and drawing
index for release data, checks the drawing index's manifest SHA-256, and rejects
missing assets or a changed inventory. `scripts/manual/build_manual.py` provides
`build_v5_manual(project_root: Path, output_path: Path) -> Path`. It imports no CAD
code and does not regenerate drawings. Fixed document metadata and ZIP timestamps
make the DOCX byte-reproducible for the same inputs and bundled document runtime.

Use the bundled document runtime returned by the Codex workspace dependency
loader for DOCX builds and tests. Do not use the repository CAD Python or system
Python for these operations. On this Windows setup, the commands are:

```powershell
$documentRuntime = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime"
$documentPython = "$documentRuntime/dependencies/python/python.exe"
$documentNode = "$documentRuntime/dependencies/node/bin/node.exe"
$documentSkill = "$documentRuntime/plugins/openai-primary-runtime/plugins/documents/skills/documents"
# Run once immediately before FIRST authoring for a new artifact operation.
# The committed V5 DOCX operation already ran this successfully; do not repeat it for rebuilds.
# & $documentNode "$documentSkill/container_tools/mark_artifact_operation_started.mjs" --operation-kind create --expected-output-count 1 --output-format docx
& $documentPython scripts/manual/build_manual.py
& $documentPython -m unittest tests.test_v5_manual -v
& $documentPython "$documentSkill/scripts/a11y_audit.py" release/v5/docs/Ugrinsky-Wind-Wall-V5-Bauanleitung.docx
```

The eleven focused manual tests pass, including A4/18 mm margins, German
language, 13 logical chapters, exact inventory, captions and meaningful alt text,
inline images, repeated table headers, light-gray table borders, black headings,
current content, input binding and byte-identical rebuilds. During a CAD-runtime
full-suite run they explicitly skip; run the command above separately.

The packaged renderer was attempted with `--emit_pdf`, but this bundled Windows
runtime contains no `soffice.exe`. Rendering and every-page visual QA are **blocked,
not passed**; no PDF or page images are supplied. The DOCX is structurally verified
and requires page-by-page review when a bundled LibreOffice renderer is available.
Do not substitute desktop/system LibreOffice. Once a bundled renderer is available:

```powershell
& $documentPython "$documentSkill/render_docx.py" release/v5/docs/Ugrinsky-Wind-Wall-V5-Bauanleitung.docx --output_dir build/manual-v5/render --emit_pdf
```

Inspect every generated page PNG before claiming layout approval. The current
sources are `release/v5/manifest.json` and `release/v5/drawings/figures.json`; after
a geometry release rebuild, regenerate the drawings before rebuilding the manual.

## Historical development notes before V5

The remaining sections record earlier development stages. Their closure, radial
fastener, provisional bearing and older `build/` inventory descriptions are
historical and do not describe the current V5 assembly. Use the V5 manual and
manifest above for the current build.

## Rebuild and inspect the release candidates

Use the existing project-local environment from the repository root. All CLI
commands that import CadQuery must go through the process-local crash-dialog
launcher; it preserves Python and native failure statuses. These commands
write files only and never send a print job:

```powershell
$env:PYTHONPATH = "$PWD;$PWD\src"
# Optional: enables the measured-source comparison; the STL stays external.
$env:WINDWALL_REFERENCE_BLADE = "<external-reference-directory>/7 Ugrinsky_Blade.stl"
& .\.venv\Scripts\python.exe scripts/run_geometry.py -m unittest discover -s tests -v
$testExit = $LASTEXITCODE
& .\.venv\Scripts\python.exe scripts/run_geometry.py scripts/build_all.py --inspect
$buildExit = $LASTEXITCODE
Write-Output "Test process exit: $testExit; build process exit: $buildExit"
```

Omit the reference variable or substitute your actual external path if that
download is unavailable. A missing variable causes one explicit test skip;
a configured but missing/wrong reference fails the comparison. Record the
unittest result separately from the process status. The known native shutdown
failure described below remains unresolved: valid files and passing assertions
do not make this environment a clean CLI/CI release.

`windwall.export.export_all(Path("build"), parameters)` is the central release
API. `parameters` defaults to `DEFAULT_PARAMETERS`. It exports the magnet
pocket coupon before either full carrier, all four joint coupon bodies, five
unique production candidates, and both complete assemblies. It rejects invalid
solids, failed STEP round trips, empty/nonfinite/negative-volume STL meshes,
boundary or non-manifold edges, degenerate triangles, wrong component counts,
envelope/volume drift, and failed assembly collision/motion/service checks.
STL linear/angular tolerances come from the centralized manufacturing
parameters (0.08 mm / 0.12 radians). STEP volumes use explicit adaptive
integration tolerance to avoid representation-dependent default quadrature.

| Output | Contents |
| --- | --- |
| `build/step/*.step` | All five production candidates and five coupon solids; CAD assembly frames retained |
| `build/stl/*.stl` | Base, standard, top, closure and lower magnet rotor; each bottom translated to Z=0 |
| `build/coupons/*.stl` | `bayonet_male`, `bayonet_female`, `joint_male`, `joint_female`, `magnet_pocket_coupon` |
| `build/assembly/rotor_locked.step` | 34 named valid solids; seven seated stages with zero nominal rotation |
| `build/assembly/rotor_exploded.step` | Same 34 solids, with entry/withdrawal poses and service separation |
| `build/manifest.json` | Relative paths, quantities, all centralized parameters, CAD bounds/volumes, triangle and component counts, STL topology, SHA-256 for every STEP/STL, assembly audit and unvalidated physical gates |
| `build/inspection/*.png` | With `--inspect`: ten individual STEP/STL projection and section sheets |
| `build/assembly/assembly_inspection.png` | With `--inspect`: locked/exploded STEP projections and top/generator sections |

The production quantity is nine bodies: one base, five copies of the same
standard, one top, one closure and one lower magnet rotor. The upper carrier
is already fused into the base. Stationary generator solids, spacer, sleeve,
rod and fasteners are clearly identified reference envelopes in the assembly;
they are not additional certified print files. Preview exports are isolated
under `build/previews/`; they never overwrite manifest-listed release assemblies.
The manifest is the authoritative release inventory.

Rebuilds overwrite these exact paths and preserve unrelated local files. The
previous manifest is removed at the start and a replacement is published only
after every check passes; without a current manifest, partial output is not a
validated build. No recursive cleanup is needed. Same parameters and runtime
produce the same STEP/STL bytes: named STEP products, an epoch timestamp and
file-local occurrence IDs remove OCCT's time/process metadata. Release STEP
assemblies are uncolored because OCCT's color-record ordering varies between
processes; CQ-editor previews and static sheets provide visual colors. Geometry
and entity references are unchanged. Cross-version OCCT reproducibility is not
promised. Native process exit status is observable only after termination and
cannot be certified by the in-process manifest.

To regenerate inspection sheets from already exported files, with SHA-256
verification before viewing:

```powershell
& .\.venv\Scripts\python.exe scripts/run_geometry.py scripts/inspect_exports.py build/manifest.json
$inspectionExit = $LASTEXITCODE
```

For CQ-editor, open the portable application manually, use File → Open on the
desired Python file below, then press Render. The preview scripts add `src/`
to their import path; run them from this checkout and keep the external
reference variable set before starting CQ-editor if you want the overlay.
`build_all.py` is the CLI exporter; use these preview files in CQ-editor:

| Preview file | View |
| --- | --- |
| `scripts/preview_blade.py` | Source blade, section overlay and positive CCW marker |
| `scripts/preview_bayonet.py` | Male/female coupon and insertion ghost |
| `scripts/preview_joint_coupon.py` | Full joint coupon with drivers and radial retention |
| `scripts/preview_modules.py` | Base, standard and top module |
| `scripts/preview_generator.py` | Opposed carriers, stationary references and clamp envelopes |
| `scripts/preview_assembly.py` | Locked, exploded and sectioned full rotor |

Running `scripts/preview_assembly.py` from the CLI writes to
`build/previews/assembly/` by default. Pass `--output-dir` only for a disposable
preview destination; use `scripts/build_all.py` to regenerate release files and
their matching manifest hashes.

Inspect the generated STEP assemblies and each manifest-listed STL in a CAD
viewer or slicer as well. The static sheets read actual exported files; they
are not screenshots of interactive CQ-editor. Interactive QA remains pending.
Check through-shaft openings, blind pocket floors, bayonet roofs, driver stops,
radial screw access, top nut/washer access and opposed magnet pocket direction.

## PLA prototype orientation and physical gates

Suggested starting orientations are geometric guidance, not validated slicer
profiles. Use the exported Z-up orientation first for the coupon pair, standard
and top stages, and lower magnet rotor. Standard/top males project downward;
the blade/support transitions above them need careful support placement. The
bayonet female's closed undercut roofs require tested bridging or removable
support; do not leave inaccessible support inside locking tracks. Keep support
scars and elephant-foot expansion off running faces and screw pilots.

The base's upper magnet pockets open downward in the assembled frame. Its
Z-up STL therefore starts on the carrier's pocket face, requiring particular
attention to the 2 mm pocket roofs and the captive nut ceiling. Compare a
flipped orientation in the slicer only after checking blade support and nut
access; translating to Z=0 does not optimize orientation automatically. Print
the magnet coupon with its three pockets open upward. The closure's central
cavity opens downward and its roof may require bridging/support; flipping the
closure may improve that cavity but creates an overhang under the outer plate.
Inspect the complete layer preview and ensure all supports can be removed.

Loaded walls are at least the configured 3 mm in designed structural regions;
the aerodynamic blade skin is intentionally 1.5 mm. Layer adhesion, perimeter
count, infill, shrinkage, creep and build-plate grip need physical validation.
PLA is the prototype material only; no outdoor temperature, UV or weather
durability has been established.

Hardware represented in the complete CAD model:

- One nominal M8 rod, 8 mm diameter; model length 559.64 mm. Measure the actual
  assembly before cutting stock or setting the top projection.
- Three M8 nuts: base captive torque nut, lower rotor clamp nut and exposed
  top clamp nut. Model envelopes use 13 mm across flats and reserve 6.8 mm
  height; the printable captive pocket is 13.30 mm across flats.
- Two nominal 24 mm OD × 2 mm washers, below the top nut and above the lower
  nut. Check their actual bores and flat bearing contact.
- Fourteen nominal 3 mm × 12 mm screws: twelve radial screws (two at each of
  six seams) and two closure screws. The 2.3 mm blind PLA pilots need suitable
  thread-forming/self-tapping screws; modeled head envelopes are 5.5 × 3 mm.
  Match actual thread, head and driver, not diameter/length alone.
- One spacer envelope, 12 mm OD, 8.8 mm bore, 17 mm long at default gaps; its
  material and compression capability are unresolved. The 12 × 8 × 6 mm
  bearing sleeve is provisional, not a selected bearing product.
- Each carrier has eighteen nominal 11 mm × 2 mm blind magnet pockets. This
  records the source geometry and does not select magnets, polarity, electrical
  poles or a retention method. Bearings, stator fabrication and magnet retention
  must be engineered and checked before any powered or wind-driven operation.

For each joint, hold the lower stage fixed. Looking down from +Z, start the
upper stage 18 degrees clockwise from its final zero-angle blade frame, lower
its male into the three windows, and rotate it 18 degrees counterclockwise to
the positive stops. The upper stage rises 0.45 mm along that motion. Do not
force it beyond the stops. Both drivers must engage. Each stage retains +60
degrees of internal blade twist, so the next zero-angle stage introduces a
**-60-degree seam phase jump**; the stack is not a continuous helical skin.

After the joint is fully locked, insert its two radial retainers through the
outer 3.3 mm-wide, vertically relieved guides into the blind pilots at assembly
angles 170/280 degrees. The relief permits the upper printed body to settle
0.36 mm onto the bayonet's printed axial seats when the M8 stack is tightened;
the retainers remain clear and do not become axial load pins.
Seat lightly after coupon testing; do not use screws to drag an unseated joint
into place. Their purpose is reverse-release retention; bayonet/driver faces
provide the geometric torque stops. Check screw length and floor clearance.
Remove radial screws before clockwise unlocking or axial withdrawal.

Fit the base captive nut before access is constrained by the lower mechanism.
At the top, place the washer on the reinforced recessed hub, then the exposed
M8 nut. Set the rod projection using the actual hardware. Tighten the M8 stack
gradually and evenly until all six printed bayonet seats engage, while checking
free rotation and gaps. The loaded stage pitch is 69.64 mm and the modeled
seven-stage aerodynamic height is 487.84 mm; **no safe torque/preload value
has been established**. Excess tightening can crush PLA, distort blade ends,
bind the bearing or close the generator gaps. The removable closure clears
the clamp and must not carry its axial load. Attach the closure with its two
screws only after measuring clearance; remove them and lift the cap to service
the nut, then remove the nut before lifting the washer.

Complete physical checks in this order; no step has yet been performed:

1. Bayonet coupon: insertion, CCW stop, axial retention, release, rocking and
   cracking; calibrate the 0.30 mm radial/0.25 mm axial defaults as needed.
2. Combined joint coupon: both drivers, screw/pilot fit, head/tool access, M8
   pocket fit and resistance to reverse release with retainers installed.
3. Magnet pocket coupon: measure the actual magnets against 10.8/11.0/11.2 mm
   pockets left-to-right. Confirm depth/protrusion and develop retention before
   relying on the full carrier. Exporting the coupon is not passing this gate.
4. Two-stage joint: verify blade/interface clearance through insertion and
   locking, removable supports, screw access, rod alignment and joint stiffness.
5. Seven-stage dry assembly: verify one base/five standards/one top, six seated
   joints, all retainers, straight rod, top washer/nut service and closure gap.
6. Restrained, unpowered hand-spin generator clearance check: establish bearing
   fit/axial retention and support, inspect actual magnet protrusion, measure
   both gaps through a full revolution, and stop at any rub, looseness or wobble.
   The nominal 1.5 mm gaps assume flush or recessed magnets. This check does not
   validate speed, load, magnetic retention or electricity generation.

Outdoor exposure, overspeed, storm loading and electrical operation remain
unvalidated. The deliverable is a reproducible set of CAD prototype candidates,
not a structural, outdoor, overspeed or electrical certification.

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
30 degrees relative to the bottom section. The completed base, standard and top
modules retain identical angular transforms; that convention does not remove
the internal twist or make the aerodynamic skin continuous across their
integrated end fittings.

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
bosses near z=65–70 mm are replaced by the integrated module supports, shaft
clearance, bayonet, drivers and serviceable end fittings. The standalone blade
solid remains the shared aerodynamic source body.

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
an envelope restriction on these approved fittings. Module integration keeps
this intrusion localized and blends the interface into its end region.

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
integration now provides the printed axial seating path and unloaded-to-loaded
retainer relief; physical preload capacity remains unverified. The combined
coupon below includes transition-adjacent drivers and reverse retainers.

## Historical joint driver experiment

The transition-adjacent radial drivers and retaining screws were replaced by
the permanent V4.3 bayonet. Their unused builders and tests have been removed.
The previous implementation is retained in Git history before `cdd1c2d`.
The current `windwall.drivers` module keeps its import path and exposes only
`build_joint_interface`, `build_joint_coupon` and `joint_interface_height_mm`.
Use the current V5 instructions above for the open-spoke calibration recess and
the unverified elastic assembly behavior.

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
`build_exploded_rotor_assembly`. In the loaded locked model the base is at Z=0,
five standards are at Z=69.64/139.28/208.92/278.56/348.20, and the top is at
Z=417.84. Every stage rotation is zero and the seated aerodynamic height is
487.84 mm. Before M8 compression, the nominal 70 mm pitch gives 490 mm. The
+60-degree internal twist remains:
blade phase jumps back 60 degrees at each seam. Structural supports bridge
the ends; a continuous helical skin or aerodynamic performance is not claimed.

The 34 named solids include seven stages, one closure, twelve radial seam
screws, two closure screws, the lower generator references and clamps, top
nut/washer, and one M8 rod from Z=-60.5 to Z=499.14 mm (559.64 mm nominal length).
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
standard, top, closure and lower magnet rotor. Release outputs under `build/assembly/`
and preview outputs under `build/previews/assembly/`
include 34-solid locked/exploded STEP files, `assembly_fit.json`, a top section
SVG and `assembly_inspection.png` rendered from exported STEP solids. Every STL
must be one closed manifold component without degenerate faces, at print Z=0.
The script also supplies locked, exploded and sectioned CQ-editor views;
interactive inspection remains unverified. No print is sent. Physical coupons,
two-stage fit, support/bridging, balance, strength, magnet/bearing retention
and generator operation remain unverified.
