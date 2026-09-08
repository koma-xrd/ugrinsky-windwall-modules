# Parametric Ugrinsky Rotor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, export, and validate a clean seven-stage parametric Ugrinsky rotor with a counterclockwise-locking bayonet, blade-transition drivers, continuous M8 threaded shaft, dual magnet rotors, and a serviceable top closure.

**Architecture:** CadQuery Python modules are the authoritative CAD source. Reference STL files are measured by a read-only analysis tool, while production solids are reconstructed from explicit parameters and exported independently as STEP and STL. Unit tests cover dimensions and interface conventions; assembly tests cover insertion, locking, alignment, clearances, interference, and export validity.

**Tech Stack:** Python 3, CadQuery/OpenCascade from the working CQ-editor environment, standard-library `unittest`, NumPy for reference mesh analysis, Git.

**Spec:** `docs/superpowers/specs/2026-09-08-ugrinsky-rotor-design.md`

## Global Constraints

- The global rotor axis is Z; positive Z points upward from the generator.
- Rotation is viewed from above, looking down along negative Z.
- Normal rotation and bayonet locking are counterclockwise.
- The completed rotor has one base stage, five standard stages, and one top stage, nominally 490 mm high.
- Final module transforms are identical; the retained +60-degree within-stage
  twist means aerodynamic skins are not continuous at the seams.
- The prototype shaft is one ordinary M8 threaded rod.
- The upper magnet rotor is integrated into the base rotor module; the lower magnet rotor remains separate.
- Production solids must be reconstructed and must not contain the reference STL meshes.
- Initial material is PLA; all fit and manufacturing allowances remain central parameters for later ASA tuning.
- The original STL files remain external reference inputs and are not committed.
- Electrical charging, magnet polarity, winding, and grid connection remain outside this implementation.

## Planned File Map

- `README.md` — setup, CQ-editor use, build, validation, printing, and assembly instructions.
- `.gitignore` — generated CAD, caches, local environments, and external reference files.
- `src/windwall/parameters.py` — immutable dimensional and manufacturing parameter records.
- `src/windwall/reference_mesh.py` — dependency-light binary STL measurement and topology inspection.
- `src/windwall/blade_profile.py` — clean parametric Ugrinsky blade profile and blade body construction.
- `src/windwall/bayonet.py` — three-lug male/female joint, end stops, ramps, and fit coupon.
- `src/windwall/drivers.py` — blade-transition drivers, receiving pockets, and driver coupon.
- `src/windwall/rotor_modules.py` — base, standard, and top rotor stage solids.
- `src/windwall/generator.py` — integrated upper and separate lower magnet rotor plus stationary reference parts.
- `src/windwall/top_closure.py` — removable symmetric top closure.
- `src/windwall/assembly.py` — seven-stage placements, exploded/locked assemblies, and collision checks.
- `src/windwall/export.py` — deterministic STEP/STL export and manifest generation.
- `scripts/analyze_references.py` — command-line reference report.
- `scripts/build_all.py` — command-line production and coupon export.
- `tests/` — standard-library unit and integration tests matching the modules above.
- `reference/.gitkeep` — documents the local-only reference input location.
- `build/` — ignored generated STEP, STL, JSON manifests, and reports.

---

### Task 1: Establish the Tested CadQuery Project and Parameter Contract

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/windwall/__init__.py`
- Create: `src/windwall/parameters.py`
- Create: `tests/__init__.py`
- Create: `tests/test_parameters.py`
- Create: `reference/.gitkeep`

**Interfaces:**
- Consumes: CadQuery environment used by CQ-editor.
- Produces: `DesignParameters`, `ManufacturingParameters`, and `DEFAULT_PARAMETERS` for every later task.

- [ ] **Step 1: Write failing parameter-contract tests**

```python
# tests/test_parameters.py
import unittest

from windwall.parameters import DEFAULT_PARAMETERS


class ParameterContractTests(unittest.TestCase):
    def test_stack_and_rotation_contract(self):
        p = DEFAULT_PARAMETERS
        self.assertEqual(p.rotor.stage_count, 7)
        self.assertEqual(p.rotor.standard_stage_count, 5)
        self.assertEqual(p.rotor.rotation_direction, "counterclockwise_from_top")
        self.assertAlmostEqual(p.rotor.stage_height_mm, 70.0)
        self.assertAlmostEqual(p.rotor.nominal_stack_height_mm, 490.0)

    def test_prototype_fit_contract(self):
        p = DEFAULT_PARAMETERS
        self.assertEqual(p.shaft.nominal_diameter_mm, 8.0)
        self.assertGreater(p.shaft.clearance_hole_diameter_mm, 8.0)
        self.assertEqual(p.bayonet.lug_count, 3)
        self.assertGreaterEqual(p.manufacturing.minimum_loaded_wall_mm, 3.0)
        self.assertGreater(p.manufacturing.nut_pocket_across_flats_mm, 13.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and confirm the missing module failure**

Run from the CQ-editor Python environment:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest tests.test_parameters -v
```

Expected: `ModuleNotFoundError: No module named 'windwall.parameters'`.

- [ ] **Step 3: Implement immutable parameter records**

```python
# src/windwall/parameters.py
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ManufacturingParameters:
    radial_clearance_mm: float = 0.30
    axial_clearance_mm: float = 0.25
    minimum_loaded_wall_mm: float = 3.0
    nut_pocket_across_flats_mm: float = 13.30
    nut_pocket_depth_mm: float = 6.8
    washer_outer_diameter_mm: float = 24.0
    screw_nominal_diameter_mm: float = 3.0
    screw_pilot_diameter_mm: float = 2.3
    screw_length_mm: float = 12.0
    export_linear_tolerance_mm: float = 0.08
    export_angular_tolerance_rad: float = 0.12


@dataclass(frozen=True)
class ShaftParameters:
    nominal_diameter_mm: float = 8.0
    clearance_hole_diameter_mm: float = 8.8


@dataclass(frozen=True)
class RotorParameters:
    stage_height_mm: float = 70.0
    stage_count: int = 7
    standard_stage_count: int = 5
    rotor_diameter_mm: float = 121.5
    rotation_direction: str = "counterclockwise_from_top"

    @property
    def nominal_stack_height_mm(self) -> float:
        return self.stage_height_mm * self.stage_count


@dataclass(frozen=True)
class BayonetParameters:
    lug_count: int = 3
    insertion_offset_deg: float = 18.0
    hub_outer_diameter_mm: float = 34.0
    lug_radial_depth_mm: float = 4.0
    lug_axial_thickness_mm: float = 3.2
    ramp_rise_mm: float = 0.45
    root_fillet_mm: float = 1.5


@dataclass(frozen=True)
class DesignParameters:
    manufacturing: ManufacturingParameters = field(default_factory=ManufacturingParameters)
    shaft: ShaftParameters = field(default_factory=ShaftParameters)
    rotor: RotorParameters = field(default_factory=RotorParameters)
    bayonet: BayonetParameters = field(default_factory=BayonetParameters)


DEFAULT_PARAMETERS = DesignParameters()
```

- [ ] **Step 4: Add repository hygiene and exact environment instructions**

`.gitignore` must ignore `build/`, `reference/*.stl`, `__pycache__/`, `*.pyc`, `.venv/`, and `.pytest_cache/`. `README.md` must explain how to locate the Python executable bundled with CQ-editor, set `PYTHONPATH`, run `unittest`, open `scripts/build_all.py` in CQ-editor, and keep reference STLs local.

- [ ] **Step 5: Run the parameter tests**

Run: `python -m unittest tests.test_parameters -v`

Expected: two tests pass.

- [ ] **Step 6: Commit the tested project contract**

```powershell
git add .gitignore README.md reference src/windwall/__init__.py src/windwall/parameters.py tests
git commit -m "chore: establish parametric CAD project"
```

---

### Task 2: Automate Reference STL Measurement and Defect Reporting

**Files:**
- Create: `src/windwall/reference_mesh.py`
- Create: `scripts/analyze_references.py`
- Create: `tests/test_reference_mesh.py`
- Create: `tests/fixtures/tetrahedron_binary.stl`

**Interfaces:**
- Consumes: `pathlib.Path` pointing to binary STL files.
- Produces: `MeshReport`, `analyze_binary_stl(path: Path) -> MeshReport`, and JSON-compatible report dictionaries.

- [ ] **Step 1: Add a failing topology test using a four-face tetrahedron fixture**

```python
# tests/test_reference_mesh.py
import unittest
from pathlib import Path

from windwall.reference_mesh import analyze_binary_stl


class ReferenceMeshTests(unittest.TestCase):
    def test_closed_tetrahedron_is_one_manifold_component(self):
        report = analyze_binary_stl(Path("tests/fixtures/tetrahedron_binary.stl"))
        self.assertEqual(report.triangle_count, 4)
        self.assertEqual(report.component_count, 1)
        self.assertEqual(report.boundary_edge_count, 0)
        self.assertEqual(report.nonmanifold_edge_count, 0)
        self.assertEqual(report.degenerate_face_count, 0)
```

- [ ] **Step 2: Run the test and confirm it fails on the missing analyzer**

Run: `python -m unittest tests.test_reference_mesh -v`

Expected: import failure for `windwall.reference_mesh`.

- [ ] **Step 3: Implement the binary STL analyzer**

Implement `MeshReport` as a frozen dataclass with filename, triangle count, unique vertex count, component count, minimum XYZ, maximum XYZ, size XYZ, boundary edge count, non-manifold edge count, degenerate face count, and signed volume. Parse the 80-byte header, little-endian triangle count, and 50-byte triangle records. Reject files whose length is not exactly `84 + triangle_count * 50`. Deduplicate exact float32 vertices, count undirected edge incidence, union connected vertices, and classify face area below `1e-10 mm²` as degenerate.

- [ ] **Step 4: Add a command-line report with explicit reference discovery**

```python
# scripts/analyze_references.py
import argparse
import json
from pathlib import Path

from windwall.reference_mesh import analyze_binary_stl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference_dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("build/reference-report.json"))
    args = parser.parse_args()
    reports = [analyze_binary_stl(path).as_dict() for path in sorted(args.reference_dir.glob("*.stl"))]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run unit and real-reference analysis**

Run:

```powershell
python -m unittest tests.test_reference_mesh -v
python scripts/analyze_references.py "C:\Users\fi87roy\Downloads\Ugrinsky Wind Wall Module - 6236759\files"
```

Expected: the fixture test passes; the report contains seven files and records 478 non-manifold edges and four degenerate faces for `7 Ugrinsky_Blade.stl`.

- [ ] **Step 6: Commit the reproducible reference audit**

```powershell
git add src/windwall/reference_mesh.py scripts/analyze_references.py tests
git commit -m "test: automate source STL quality audit"
```

---

### Task 3: Reconstruct and Validate the Shared Ugrinsky Blade Body

**Files:**
- Create: `src/windwall/blade_profile.py`
- Create: `tests/test_blade_profile.py`
- Create: `scripts/preview_blade.py`
- Modify: `src/windwall/parameters.py`

**Interfaces:**
- Consumes: `DesignParameters`.
- Produces: `build_blade_profile(parameters) -> cq.Wire` and `build_blade_stage(parameters) -> cq.Workplane`.

- [ ] **Step 1: Add failing geometry-contract tests**

```python
# tests/test_blade_profile.py
import unittest

from windwall.blade_profile import build_blade_stage
from windwall.parameters import DEFAULT_PARAMETERS


class BladeProfileTests(unittest.TestCase):
    def test_stage_matches_reference_envelope(self):
        shape = build_blade_stage(DEFAULT_PARAMETERS).val()
        box = shape.BoundingBox()
        self.assertAlmostEqual(box.xlen, 121.5, delta=0.6)
        self.assertAlmostEqual(box.ylen, 120.732, delta=0.6)
        self.assertAlmostEqual(box.zlen, 70.0, delta=0.1)

    def test_stage_is_single_valid_solid(self):
        shape = build_blade_stage(DEFAULT_PARAMETERS).val()
        self.assertTrue(shape.isValid())
        self.assertEqual(len(shape.Solids()), 1)
```

- [ ] **Step 2: Run the tests and confirm the missing implementation failure**

Run: `python -m unittest tests.test_blade_profile -v`

Expected: import failure for `windwall.blade_profile`.

- [ ] **Step 3: Extract the original mid-height silhouette for measurement**

Add a measurement helper to `scripts/preview_blade.py` that loads the reference blade mesh only for analysis, intersects triangles with `z=35.0`, joins the resulting XY segments within `0.05 mm`, and writes `build/blade-midplane.csv`. Fit the two Ugrinsky circular arc families with NumPy least squares, then print circle centers, radii, tangent points, envelope, and RMS fit error. Reject a fit above `0.20 mm` RMS rather than silently accepting it.

- [ ] **Step 4: Encode the measured profile as explicit parameters and clean arcs**

Add `BladeParameters` to `parameters.py` with rotor radius, wall thickness, two arc centers, two arc radii, tangent transition points, hub blend radius, and stage height. In `blade_profile.py`, build closed 2D wires exclusively from CadQuery lines and tangent arcs, mirror/rotate the complementary blade, fuse the central hub blend, and extrude once to the stage height. Do not import or boolean the STL in this module.

- [ ] **Step 5: Compare production geometry against the reference**

Extend the tests to sample the production profile and assert maximum nearest-point deviation below `0.60 mm` outside the central 20 mm hub region. Assert that local hub reinforcement does not extend into the active outer 85 percent of the blade radius.

- [ ] **Step 6: Run blade tests and visually inspect in CQ-editor**

Run: `python -m unittest tests.test_blade_profile -v`

Open `scripts/preview_blade.py` in CQ-editor and confirm one clean solid, correct handedness, counterclockwise convention marker, and close overlay with the reference silhouette.

- [ ] **Step 7: Commit the clean shared blade geometry**

```powershell
git add src/windwall/parameters.py src/windwall/blade_profile.py scripts/preview_blade.py tests/test_blade_profile.py
git commit -m "feat: reconstruct clean Ugrinsky blade stage"
```

---

### Task 4: Build and Prove the Counterclockwise Three-Lug Bayonet

**Files:**
- Create: `src/windwall/bayonet.py`
- Create: `tests/test_bayonet.py`
- Create: `scripts/preview_bayonet.py`

**Interfaces:**
- Consumes: `DesignParameters` and a Z-plane placement.
- Produces: `build_male_bayonet(parameters)`, `build_female_bayonet(parameters)`, `build_bayonet_coupon(parameters)`, and `locked_angle_deg(parameters) -> float`.

- [ ] **Step 1: Add failing direction, count, validity, and clearance tests**

```python
# tests/test_bayonet.py
import unittest

from windwall.bayonet import build_bayonet_coupon, locked_angle_deg
from windwall.parameters import DEFAULT_PARAMETERS


class BayonetTests(unittest.TestCase):
    def test_locking_motion_is_counterclockwise(self):
        self.assertEqual(locked_angle_deg(DEFAULT_PARAMETERS), 18.0)

    def test_coupon_is_valid_and_has_three_lugs(self):
        coupon = build_bayonet_coupon(DEFAULT_PARAMETERS)
        self.assertTrue(coupon.male.val().isValid())
        self.assertTrue(coupon.female.val().isValid())
        self.assertEqual(len(coupon.lug_centers_deg), 3)

    def test_locked_coupon_has_positive_clearance(self):
        coupon = build_bayonet_coupon(DEFAULT_PARAMETERS)
        self.assertLess(coupon.locked_intersection_volume_mm3(), 0.01)
        self.assertGreaterEqual(coupon.minimum_locked_clearance_mm(), 0.20)
```

- [ ] **Step 2: Run the tests and confirm the missing implementation failure**

Run: `python -m unittest tests.test_bayonet -v`

Expected: import failure for `windwall.bayonet`.

- [ ] **Step 3: Implement the male lugs and female tracks**

Construct one lug from a rounded rectangular radial solid, apply the configured root fillet, and polar-array it at `0`, `120`, and `240` degrees. Construct each female track as an insertion window plus an 18-degree swept locking channel. The channel rises only by `ramp_rise_mm`; its counterclockwise endpoint contains a solid stop face. Subtract the female clearance envelope using separate radial and axial clearances.

- [ ] **Step 4: Implement sampled motion validation**

For angles from 0 through 18 degrees in 1-degree steps, place the male member at the corresponding angle and insertion height. Assert that planned contact occurs only on ramp/stop faces and that unrelated solids do not intersect. Explicitly test that a clockwise torque from the locked position moves away from the stop while a counterclockwise torque presses into it.

- [ ] **Step 5: Export and physically calibrate the small bayonet coupon**

Run `scripts/preview_bayonet.py` to export `build/coupons/bayonet_male.stl` and `build/coupons/bayonet_female.stl`. Print only these parts in PLA. Record the smallest clearance that inserts without force, locks without cracking, and has no perceptible radial rocking; update the single manufacturing clearance parameter if required.

- [ ] **Step 6: Run the bayonet tests**

Run: `python -m unittest tests.test_bayonet -v`

Expected: all tests pass, including the counterclockwise end-stop assertion.

- [ ] **Step 7: Commit the proven bayonet interface**

```powershell
git add src/windwall/bayonet.py scripts/preview_bayonet.py tests/test_bayonet.py src/windwall/parameters.py
git commit -m "feat: add counterclockwise locking bayonet"
```

---

### Task 5: Add Blade-Transition Drivers and Screw Retention

**Files:**
- Create: `src/windwall/drivers.py`
- Create: `tests/test_drivers.py`
- Create: `scripts/preview_joint_coupon.py`
- Modify: `src/windwall/parameters.py`

**Interfaces:**
- Consumes: the reconstructed blade transition coordinates and `DesignParameters`.
- Produces: `build_drivers(parameters)`, `build_driver_pockets(parameters)`, `build_screw_pilots(parameters)`, and `build_joint_coupon(parameters)`.

- [ ] **Step 1: Add failing driver and fastener tests**

```python
# tests/test_drivers.py
import unittest

from windwall.drivers import build_joint_coupon
from windwall.parameters import DEFAULT_PARAMETERS


class DriverTests(unittest.TestCase):
    def test_joint_uses_two_transition_drivers_and_two_screws(self):
        coupon = build_joint_coupon(DEFAULT_PARAMETERS)
        self.assertEqual(len(coupon.driver_centers), 2)
        self.assertEqual(len(coupon.screw_axes), 2)

    def test_locked_joint_has_no_unplanned_interference(self):
        coupon = build_joint_coupon(DEFAULT_PARAMETERS)
        self.assertLess(coupon.unplanned_intersection_volume_mm3(), 0.01)
```

- [ ] **Step 2: Run the tests and confirm the missing implementation failure**

Run: `python -m unittest tests.test_drivers -v`

Expected: import failure for `windwall.drivers`.

- [ ] **Step 3: Implement rounded drivers and swept receiving pockets**

Place one driver at each blade transition outside the central bayonet hub. Use a rounded trapezoidal footprint, at least 3 mm root thickness, and no sharp internal corner. Generate each pocket from the full 0-to-18-degree swept volume plus configured clearance so it cannot collide during locking. Add a solid counterclockwise load face in the locked position.

- [ ] **Step 4: Implement radial screw guides**

Place two radial screw axes between bayonet lugs where a driver or active blade surface is not weakened. The outer part receives a clearance hole; the inner receiving part receives the configured 2.3 mm PLA pilot. Preserve at least 3 mm material from pilot edge to free edge. Keep screw heads externally accessible after all seven stages are assembled.

- [ ] **Step 5: Export and print the combined joint coupon**

Run `scripts/preview_joint_coupon.py`. It must export a compact lower/upper pair containing one representative bayonet lug, one transition driver, one screw clearance hole, one pilot hole, and the M8 nut pocket. Print and record fit before any full rotor stage.

- [ ] **Step 6: Run the driver tests**

Run: `python -m unittest tests.test_drivers -v`

Expected: all tests pass.

- [ ] **Step 7: Commit the secondary torque and retention features**

```powershell
git add src/windwall/drivers.py scripts/preview_joint_coupon.py tests/test_drivers.py src/windwall/parameters.py
git commit -m "feat: add blade drivers and joint retainers"
```

---

### Task 6: Construct Base, Standard, and Top Rotor Modules

**Files:**
- Create: `src/windwall/rotor_modules.py`
- Create: `tests/test_rotor_modules.py`
- Modify: `src/windwall/parameters.py`

**Interfaces:**
- Consumes: blade stage, bayonet, drivers, screw pilots, shaft parameters.
- Produces: immutable `RotorModuleModel` records containing `shape: cq.Workplane`, `shaft_clearance_radial_mm: float`, `nut_pocket_across_flats_mm: float | None`, and `washer_seat_diameter_mm: float | None`; `build_base_module(parameters)`, `build_standard_module(parameters)`, and `build_top_module(parameters)` each return one record.

- [ ] **Step 1: Add failing unique-module tests**

```python
# tests/test_rotor_modules.py
import unittest

from windwall.parameters import DEFAULT_PARAMETERS
from windwall.rotor_modules import build_base_module, build_standard_module, build_top_module


class RotorModuleTests(unittest.TestCase):
    def test_all_module_types_are_single_valid_solids(self):
        for builder in (build_base_module, build_standard_module, build_top_module):
            shape = builder(DEFAULT_PARAMETERS).shape.val()
            self.assertTrue(shape.isValid())
            self.assertEqual(len(shape.Solids()), 1)

    def test_shaft_hole_remains_clear(self):
        for builder in (build_base_module, build_standard_module, build_top_module):
            self.assertGreaterEqual(builder(DEFAULT_PARAMETERS).shaft_clearance_radial_mm, 0.35)

    def test_top_has_exposed_m8_nut_and_washer_access(self):
        top = build_top_module(DEFAULT_PARAMETERS)
        self.assertIsNone(top.nut_pocket_across_flats_mm)
        self.assertGreaterEqual(top.washer_seat_diameter_mm, 24.0)
```

- [ ] **Step 2: Run the tests and confirm the missing implementation failure**

Run: `python -m unittest tests.test_rotor_modules -v`

Expected: import failure for `windwall.rotor_modules`.

- [ ] **Step 3: Build the standard stage**

Fuse the clean blade body, reinforced central hub, bottom male bayonet, bottom transition drivers, and top female tracks/pockets into one solid. Cut the M8 clearance bore and two radial screw features. Preserve exactly one intended printable solid.

- [ ] **Step 4: Build the base stage**

Reuse the standard upper female interface and blade body. Replace its lower male interface with the reinforced integrated upper magnet-rotor carrier and lower shaft torque interface defined in Task 7. Keep the aerodynamically active blade surface identical to the standard module.

- [ ] **Step 5: Build the top stage**

Reuse the standard lower male interface and blade body. Replace the upper female interface with a reinforced hub containing an 8.8 mm shaft passage, a shallow 24.6 mm centering recess for the 24 mm OD washer, and separate closure seats. The exposed M8 nut sits above the washer, so the washer bears directly on the hub and spreads its clamp load. This Task 6 correction supersedes the captive top hex pocket; that 13.30 mm by 6.8 mm pocket remains in the calibration coupon only. A wrench is required during assembly, and the closure must provide headroom above the nominal blade height.

Task 6 also explicitly phases both joint members +100 degrees, placing the
radial screws at 170/280 degrees, and relieves only the outer bottom 0.70 mm
edge for the axial ramp motion. End supports bridge the +60-degree source skin
to the common joint frame. No aerodynamic seam continuity is claimed. The
base's lower flange remains a Task 7 carrier/shaft-interface integration face.

- [ ] **Step 6: Run all module tests and inspect all three parts in CQ-editor**

Run: `python -m unittest tests.test_rotor_modules -v`

Expected: all tests pass; the three overlaid modules share the same active blade envelope.

- [ ] **Step 7: Commit the three-module family**

```powershell
git add src/windwall/rotor_modules.py src/windwall/parameters.py tests/test_rotor_modules.py
git commit -m "feat: build modular seven-stage rotor parts"
```

---

### Task 7: Reconstruct the Dual-Magnet Generator Geometry

**Files:**
- Create: `src/windwall/generator.py`
- Create: `tests/test_generator.py`
- Create: `scripts/preview_generator.py`
- Modify: `src/windwall/parameters.py`
- Modify: `src/windwall/rotor_modules.py`

**Interfaces:**
- Consumes: measured generator reference dimensions, M8 shaft parameters, and base module body.
- Produces: `build_upper_magnet_carrier(parameters)`, `build_lower_magnet_rotor(parameters)`, `build_stationary_generator_reference(parameters)`, and air-gap measurement helpers.

- [ ] **Step 1: Add failing generator arrangement tests**

```python
# tests/test_generator.py
import unittest

from windwall.generator import build_generator_assembly
from windwall.parameters import DEFAULT_PARAMETERS


class GeneratorTests(unittest.TestCase):
    def test_two_magnet_rotors_share_the_m8_axis(self):
        assembly = build_generator_assembly(DEFAULT_PARAMETERS)
        self.assertEqual(assembly.magnet_rotor_count, 2)
        self.assertEqual(assembly.rotating_axis_diameter_mm, 8.0)
        self.assertTrue(assembly.upper_rotor_integrated_with_base)

    def test_stator_is_between_rotors_without_collision(self):
        assembly = build_generator_assembly(DEFAULT_PARAMETERS)
        self.assertGreater(assembly.upper_air_gap_mm(), 0.0)
        self.assertGreater(assembly.lower_air_gap_mm(), 0.0)
        self.assertLess(assembly.rotor_stator_intersection_volume_mm3(), 0.01)
```

- [ ] **Step 2: Run the tests and confirm the missing implementation failure**

Run: `python -m unittest tests.test_generator -v`

Expected: import failure for `windwall.generator`.

- [ ] **Step 3: Encode measured generator envelopes without committing source meshes**

Add generator parameters from the reference report: coil former `118 × 118 × 12 mm`, upper/lower magnet carrier envelope approximately `103.994 × 103.994 × 10 mm`, stator cover `112 × 112 × 2 mm`, and base envelope `120 × 120 × 27 mm`. Treat magnet holes and bearing seats as separately measured parameters. Every uncertain functional fit must be measured from the physical magnet or bearing before being marked print-ready.

- [ ] **Step 4: Build clean upper and lower magnet carriers**

Construct carriers from parametric discs, magnet pockets, stiffening ribs, M8 shaft interface, and axial clamping faces. Fuse the upper carrier into the base rotor module as one printable solid. Keep the lower carrier separate. Generate a magnet-pocket coupon before exporting either full carrier.

- [ ] **Step 5: Build stationary clearance-reference solids**

Reconstruct simplified, valid stationary solids for the coil former, stator cover, base, and bearing envelopes. These first versions validate fit and assembly only; they must not claim finalized coil winding or electrical performance.

- [ ] **Step 6: Run generator tests and inspect the section view**

Run: `python -m unittest tests.test_generator -v`

Open `scripts/preview_generator.py` in CQ-editor and inspect a Z-axis section confirming two rotating magnet carriers, stationary stator between them, continuous shaft, adjustable spacer regions, and no collision.

- [ ] **Step 7: Commit the dual-rotor generator geometry**

```powershell
git add src/windwall/generator.py src/windwall/rotor_modules.py src/windwall/parameters.py scripts/preview_generator.py tests/test_generator.py
git commit -m "feat: reconstruct dual magnet rotor generator"
```

---

### Task 8: Add the Serviceable Top Closure and Seven-Stage Assembly

**Files:**
- Create: `src/windwall/top_closure.py`
- Create: `src/windwall/assembly.py`
- Create: `tests/test_assembly.py`
- Create: `scripts/preview_assembly.py`

**Interfaces:**
- Consumes: three rotor module types, generator assembly, and design parameters.
- Produces: `build_top_closure(parameters)`, `build_locked_rotor_assembly(parameters)`, and `build_exploded_rotor_assembly(parameters)`.

- [ ] **Step 1: Add failing complete-assembly tests**

```python
# tests/test_assembly.py
import unittest

from windwall.assembly import build_locked_rotor_assembly
from windwall.parameters import DEFAULT_PARAMETERS


class AssemblyTests(unittest.TestCase):
    def test_locked_stack_has_expected_stage_composition(self):
        assembly = build_locked_rotor_assembly(DEFAULT_PARAMETERS)
        self.assertEqual(assembly.base_count, 1)
        self.assertEqual(assembly.standard_count, 5)
        self.assertEqual(assembly.top_count, 1)
        self.assertEqual(assembly.aerodynamic_stage_count, 7)

    def test_blades_are_aligned_and_stack_is_nominal_height(self):
        assembly = build_locked_rotor_assembly(DEFAULT_PARAMETERS)
        self.assertLess(assembly.maximum_stage_angle_error_deg(), 0.01)
        self.assertAlmostEqual(assembly.aerodynamic_height_mm(), 490.0, delta=0.5)

    def test_locked_stack_has_no_unplanned_intersections(self):
        assembly = build_locked_rotor_assembly(DEFAULT_PARAMETERS)
        self.assertLess(assembly.unplanned_intersection_volume_mm3(), 0.01)
```

- [ ] **Step 2: Run the tests and confirm the missing implementation failure**

Run: `python -m unittest tests.test_assembly -v`

Expected: import failure for `windwall.assembly`.

- [ ] **Step 3: Build the removable top closure**

Create a symmetric disc tying both blade ends to the reinforced top hub. Use the two blind pilot seats at local XY=(24,0) and (-24,0), diameter 2.3 mm and depth 8 mm, outside the washer load path. Provide clearance above the washer, exposed nut and actual rod projection: with a 2 mm washer the nut starts at local z=71.5 mm, above the 70 mm blade height. Ensure removal exposes the nut and washer without disturbing any bayonet joint.

- [ ] **Step 4: Place the complete locked and exploded assemblies**

Place base at Z=0, five standard modules at successive 70 mm increments, and top at Z=420 mm. All locked module transforms have zero final angular offset. Add generator parts below the base and a simple M8 shaft reference cylinder through the full assembly. The exploded view shows each upper module 15 mm above and 18 degrees clockwise from its locked position.

- [ ] **Step 5: Validate insertion and final alignment**

Sample the insertion path for every unique joint type, test intended clearances, and calculate intersection volumes. Assert exact stage counts, 490 mm aerodynamic height, common shaft axis, and zero final angular mismatch.

- [ ] **Step 6: Run assembly tests and review the full model in CQ-editor**

Run: `python -m unittest tests.test_assembly -v`

Open `scripts/preview_assembly.py` and visually inspect locked, exploded, and sectioned views.

- [ ] **Step 7: Commit the complete assembly**

```powershell
git add src/windwall/top_closure.py src/windwall/assembly.py scripts/preview_assembly.py tests/test_assembly.py
git commit -m "feat: assemble seven-stage Ugrinsky rotor"
```

---

### Task 9: Export, Mesh-Validate, and Document the Printable Release

**Files:**
- Create: `src/windwall/export.py`
- Create: `scripts/build_all.py`
- Create: `tests/test_exports.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: every unique production part and coupon builder.
- Produces: deterministic `build/step/*.step`, `build/stl/*.stl`, `build/coupons/*.stl`, `build/assembly/*.step`, and `build/manifest.json`.

- [ ] **Step 1: Add a failing end-to-end export test**

```python
# tests/test_exports.py
import tempfile
import unittest
from pathlib import Path

from windwall.export import export_all


class ExportTests(unittest.TestCase):
    def test_all_unique_parts_export_as_valid_step_and_stl(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = export_all(Path(directory))
            expected = {
                "base_rotor_module",
                "standard_rotor_module",
                "top_rotor_module",
                "top_closure",
                "lower_magnet_rotor",
            }
            self.assertTrue(expected.issubset(manifest.part_names()))
            for part in manifest.production_parts:
                self.assertTrue(part.step_path.exists())
                self.assertTrue(part.stl_path.exists())
                self.assertEqual(part.boundary_edge_count, 0)
                self.assertEqual(part.nonmanifold_edge_count, 0)
                self.assertEqual(part.degenerate_face_count, 0)
```

- [ ] **Step 2: Run the test and confirm the missing exporter failure**

Run: `python -m unittest tests.test_exports -v`

Expected: import failure for `windwall.export`.

- [ ] **Step 3: Implement deterministic export and manifest generation**

Export STEP through CadQuery exporters. Export STL with the configured linear and angular tolerances. Reuse `reference_mesh.analyze_binary_stl` to validate every STL. Fail the build on invalid CadQuery solids, missing output, boundary edges, non-manifold edges, degenerate faces, or unexpected connected-component count. Store dimensions, volume, triangle count, SHA-256, parameters, and validation results in `manifest.json`.

- [ ] **Step 4: Add the build entry point**

```python
# scripts/build_all.py
from pathlib import Path

from windwall.export import export_all


if __name__ == "__main__":
    manifest = export_all(Path("build"))
    print(f"Exported and validated {len(manifest.production_parts)} production parts")
```

- [ ] **Step 5: Document printing and staged physical verification**

Update `README.md` with exact commands, CQ-editor preview files, suggested PLA orientation, support guidance, hardware list, counterclockwise locking procedure, screw-retention procedure, M8 stack tightening warning, and the test order: bayonet coupon, combined joint coupon, magnet pocket coupon, two-stage joint, seven-stage dry assembly, hand-spin generator clearance test. State explicitly that outdoor, overspeed, storm, and electrical operation remain unvalidated.

- [ ] **Step 6: Run the complete automated verification**

Run:

```powershell
python -m unittest discover -s tests -v
python scripts/build_all.py
git status --short
```

Expected: all tests pass; all production STLs report zero boundary, non-manifold, and degenerate geometry; generated files appear only beneath ignored `build/`; Git status contains only the intended source and documentation changes.

- [ ] **Step 7: Inspect every generated production part**

Open the STEP assembly and each unique STL in CQ-editor or FreeCAD. Confirm orientation, shaft passage, accessible fasteners, nut access, magnet pocket direction, and that no thin unintended membranes close holes or pockets.

- [ ] **Step 8: Commit the reproducible release pipeline**

```powershell
git add README.md src/windwall/export.py scripts/build_all.py tests/test_exports.py
git commit -m "build: export and validate printable rotor parts"
```

## Final Review Gate

Before calling the mechanical prototype complete:

1. Run the entire test suite and clean export from an empty `build/` directory.
2. Confirm the manifest contains all unique parts and coupons.
3. Confirm all STL topology counters are zero for defects.
4. Inspect locked, exploded, and generator section views.
5. Print and approve the coupons before printing a complete rotor stage.
6. Print and approve a two-stage connection before producing all seven stages.
7. Record any measured PLA compensation by changing only central parameters and regenerate every artifact.
8. Document physical test results separately from automated CAD validation.
