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
& .\.venv\Scripts\python.exe scripts/preview_blade.py $env:WINDWALL_REFERENCE_BLADE
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
shoulders/preload, blade-end drivers, reverse retainers, and loaded operation
are separate later work.
