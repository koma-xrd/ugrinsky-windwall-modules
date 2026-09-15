# Serpentine Coil Winding Jig Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and release a hand-cranked, concentrically adjustable round-coil winding jig and a separate 51105-supported copper-wire payoff turntable for forming the V5 generator's 18-station serpentine coil.

**Architecture:** Three focused CadQuery modules own the adjustable winding head, the 608-supported frame/drive, and the independent 51105 payoff unit. A tooling assembly module validates their interfaces and motion ownership, while a separate tooling exporter produces printable parts, named STEP assemblies, manifest data, drawings, and German instructions without changing the turbine's production-part inventory.

**Tech Stack:** Python 3, CadQuery 2.8, OpenCascade/OCP, standard-library `unittest`, JSON release manifests, Matplotlib drawings

**Spec:** `docs/superpowers/specs/2026-09-15-serpentine-coil-winding-jig-design.md`

## Global Constraints

- Support 0.18 mm enamelled copper wire without sharp wire-contacting edges.
- Keep all six ribs concentric and synchronously adjustable from 110 mm through 145 mm nominal winding diameter.
- Mark 127 mm as a calculated, physically unvalidated starting setting.
- Provide exactly 18 numbered tape stations at 20 degree intervals, each at least 12 mm wide for 10 mm tape.
- Provide at least 2 mm radial release travel after winding.
- Use a horizontal 8 mm shaft in two 608 bearings, a hand crank, and an unapproved future-use 6.35 mm female hex interface.
- Keep the payoff module separate, with a 150 mm platter, 15 x 20 mm spool pilot, and one 25 x 42 x 11 mm 51105 thrust bearing.
- Keep powered operation outside the validated scope.
- Fit every unsplit printable part within a nominal 220 x 220 mm print bed.
- Keep tooling parameters independent from generator product geometry.

## File structure

- Create `src/windwall/winding_tool_parameters.py`: immutable tooling-only dimensions and validation.
- Create `src/windwall/winding_head.py`: cam, six sliders/ribs, tape layout, state metadata, and printable head parts.
- Create `src/windwall/winding_frame.py`: base, uprights, 608 seats, shaft reference, head retention, and crank.
- Create `src/windwall/wire_payoff.py`: base, 51105 interfaces, platter, pilot, felt brake, and adjustment hardware references.
- Create `src/windwall/winding_tool_assembly.py`: positioned assemblies, ownership, collision and print-envelope audits, and bill of materials.
- Create `src/windwall/winding_tool_export.py`: isolated STL/STEP/manifest export under `release/winding-tool`.
- Create `scripts/build_winding_tool.py`: fail-closed release build entry point.
- Create `scripts/preview_winding_tool.py`: reference, min/max, and exploded preview images.
- Create `tests/test_winding_tool_parameters.py`, `tests/test_winding_head.py`, `tests/test_winding_frame.py`, `tests/test_wire_payoff.py`, `tests/test_winding_tool_assembly.py`, and `tests/test_winding_tool_export.py`.
- Create `docs/serpentine-coil-winding-tool-de.md`: German construction, calibration, winding, taping, forming, and safety guide.
- Modify `README.md`: link the optional workshop tool without adding it to the turbine production inventory.
- Generate `release/winding-tool/**`: printable STL, STEP parts/assemblies, manifest, BOM, drawings, and guide copy.

---

### Task 1: Tooling parameters and invariants

**Files:**
- Create: `tests/test_winding_tool_parameters.py`
- Create: `src/windwall/winding_tool_parameters.py`

**Interfaces:**
- Consumes: no product-geometry state; literal accepted design dimensions from the spec
- Produces: `WindingToolParameters`, `DEFAULT_WINDING_TOOL_PARAMETERS`, and `validate_winding_tool_parameters(parameters) -> None`

- [ ] **Step 1: Write tests for defaults, independence, and invalid values**

```python
import unittest
from dataclasses import replace

from windwall.parameters import DEFAULT_PARAMETERS
from windwall.winding_tool_parameters import (
    DEFAULT_WINDING_TOOL_PARAMETERS, validate_winding_tool_parameters)


class WindingToolParameterTests(unittest.TestCase):
    def test_defaults_match_approved_design(self):
        p = DEFAULT_WINDING_TOOL_PARAMETERS
        self.assertEqual((p.minimum_diameter_mm, p.reference_diameter_mm,
                          p.maximum_diameter_mm), (110.0, 127.0, 145.0))
        self.assertEqual((p.rib_count, p.tape_station_count), (6, 18))
        self.assertEqual((p.tape_width_mm, p.tape_passage_width_mm), (10.0, 12.0))
        self.assertEqual((p.platter_diameter_mm, p.spool_pilot_diameter_mm,
                          p.spool_pilot_height_mm), (150.0, 15.0, 20.0))
        self.assertEqual((p.shaft_diameter_mm, p.hex_socket_across_flats_mm), (8.0, 6.35))
        self.assertIsNot(p, DEFAULT_PARAMETERS)

    def test_validation_rejects_bad_ranges_counts_and_clearances(self):
        p = DEFAULT_WINDING_TOOL_PARAMETERS
        invalid = (
            replace(p, minimum_diameter_mm=146),
            replace(p, reference_diameter_mm=109),
            replace(p, rib_count=5),
            replace(p, tape_station_count=17),
            replace(p, tape_passage_width_mm=9.9),
            replace(p, release_travel_mm=1.9),
            replace(p, platter_diameter_mm=221),
        )
        for candidate in invalid:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                validate_winding_tool_parameters(candidate)
```

- [ ] **Step 2: Run the new test to verify it fails because the module is absent**

Run: `python -m unittest tests.test_winding_tool_parameters -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'windwall.winding_tool_parameters'`.

- [ ] **Step 3: Add the immutable parameter model and explicit validator**

```python
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class WindingToolParameters:
    minimum_diameter_mm: float = 110.0
    reference_diameter_mm: float = 127.0
    maximum_diameter_mm: float = 145.0
    rib_count: int = 6
    tape_station_count: int = 18
    tape_width_mm: float = 10.0
    tape_passage_width_mm: float = 12.0
    release_travel_mm: float = 2.0
    shaft_diameter_mm: float = 8.0
    hex_socket_across_flats_mm: float = 6.35
    platter_diameter_mm: float = 150.0
    spool_pilot_diameter_mm: float = 15.0
    spool_pilot_height_mm: float = 20.0
    print_bed_size_mm: float = 220.0


def validate_winding_tool_parameters(p: WindingToolParameters) -> None:
    values = tuple(value for value in vars(p).values() if isinstance(value, float))
    if not all(isfinite(value) and value > 0 for value in values):
        raise ValueError('Winding-tool dimensions must be positive and finite')
    if not p.minimum_diameter_mm <= p.reference_diameter_mm <= p.maximum_diameter_mm:
        raise ValueError('Reference diameter must lie inside the winding range')
    if p.rib_count != 6 or p.tape_station_count != 18:
        raise ValueError('The winding head requires six ribs and 18 tape stations')
    if p.tape_passage_width_mm < p.tape_width_mm + 2:
        raise ValueError('Tape passages require 1 mm clearance on each side')
    if p.release_travel_mm < 2:
        raise ValueError('Coil release travel must be at least 2 mm')
    if p.platter_diameter_mm > p.print_bed_size_mm:
        raise ValueError('The payoff platter must fit the unsplit print bed')


DEFAULT_WINDING_TOOL_PARAMETERS = WindingToolParameters()
validate_winding_tool_parameters(DEFAULT_WINDING_TOOL_PARAMETERS)
```

- [ ] **Step 4: Run the parameter test and the existing parameter suite**

Run: `python -m unittest tests.test_winding_tool_parameters tests.test_parameters -v`

Expected: all tests report `OK`.

- [ ] **Step 5: Commit the isolated parameter model**

```powershell
git add -- src/windwall/winding_tool_parameters.py tests/test_winding_tool_parameters.py
git commit -m "feat: define serpentine winding tool parameters"
```

---

### Task 2: Six-rib synchronised winding head

**Files:**
- Create: `tests/test_winding_head.py`
- Create: `src/windwall/winding_head.py`

**Interfaces:**
- Consumes: `WindingToolParameters`
- Produces: `WindingHeadState`, `WindingHeadParts`, `build_winding_head(parameters, diameter_mm) -> WindingHeadParts`, and `tape_station_angles(parameters) -> tuple[float, ...]`

- [ ] **Step 1: Write failing behavioural tests for adjustment, tape access, and release**

```python
import unittest

from windwall.winding_head import build_winding_head, tape_station_angles
from windwall.winding_tool_parameters import DEFAULT_WINDING_TOOL_PARAMETERS as P


class WindingHeadTests(unittest.TestCase):
    def test_six_ribs_remain_concentric_at_range_samples(self):
        for diameter in (110.0, 127.0, 145.0):
            head = build_winding_head(P, diameter)
            self.assertEqual(len(head.ribs), 6)
            self.assertTrue(all(abs(radius - diameter / 2) < 1e-6
                                for radius in head.state.rib_contact_radii_mm))
            self.assertEqual(head.state.requested_diameter_mm, diameter)

    def test_tape_layout_and_release_are_explicit(self):
        self.assertEqual(tape_station_angles(P), tuple(range(0, 360, 20)))
        head = build_winding_head(P, 127.0)
        self.assertEqual(head.state.tape_passage_width_mm, 12.0)
        self.assertEqual(head.state.tape_station_count, 18)
        self.assertGreaterEqual(head.state.release_travel_mm, 2.0)

    def test_invalid_diameter_is_rejected(self):
        for diameter in (109.9, 145.1, float('nan')):
            with self.subTest(diameter=diameter), self.assertRaisesRegex(ValueError, 'diameter'):
                build_winding_head(P, diameter)

    def test_printable_parts_are_valid_single_solids(self):
        head = build_winding_head(P, 127.0)
        for name, shape in head.printable_parts.items():
            with self.subTest(part=name):
                self.assertTrue(shape.val().isValid())
                self.assertEqual(len(shape.val().Solids()), 1)
                self.assertGreater(shape.val().Volume(), 0)
```

- [ ] **Step 2: Run the test and confirm the missing-module failure**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_head -v`

Expected: FAIL before tests run because `windwall.winding_head` does not exist.

- [ ] **Step 3: Implement the public records and pure layout calculations first**

```python
@dataclass(frozen=True)
class WindingHeadState:
    requested_diameter_mm: float
    rib_contact_radii_mm: tuple[float, ...]
    tape_station_count: int
    tape_passage_width_mm: float
    release_travel_mm: float


@dataclass(frozen=True)
class WindingHeadParts:
    backplate: cq.Workplane
    cam: cq.Workplane
    clamp: cq.Workplane
    sliders: tuple[cq.Workplane, ...]
    ribs: tuple[cq.Workplane, ...]
    printable_parts: dict[str, cq.Workplane]
    state: WindingHeadState


def tape_station_angles(p: WindingToolParameters) -> tuple[float, ...]:
    return tuple(index * 360 / p.tape_station_count
                 for index in range(p.tape_station_count))
```

- [ ] **Step 4: Build one master slider/rib and polar-copy it six times**

Implement the backplate with six captive radial guide channels, the cam with six
identical monotonic tracks, one follower hole per slider, rounded wire-contact
ribs, 12 mm tape passages, positive travel stops, a separate lock part, and
engraved `110`, `127`, and `145` indexes. Build the master in the +X direction,
then rotate exact copies by `index * 60` degrees so radius equality is structural
rather than corrected after construction.

- [ ] **Step 5: Add geometry assertions for every public printable body**

Use a local `_valid_single_solid(shape, name)` helper that cleans the result and
raises `ValueError(f'{name} must be one valid connected solid')` unless it has
one valid solid with positive finite volume. Do not fuse moving members into the
backplate merely to satisfy this check.

- [ ] **Step 6: Run head tests at all three adjustment settings**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_head -v`

Expected: all tests report `OK`; if OCP returns a nonzero native teardown status after `OK`, record it separately and do not reinterpret it as a unittest failure.

- [ ] **Step 7: Commit the adjustable head**

```powershell
git add -- src/windwall/winding_head.py tests/test_winding_head.py
git commit -m "feat: add synchronised six-rib winding head"
```

---

### Task 3: Horizontal 608 frame, crank, and future hex interface

**Files:**
- Create: `tests/test_winding_frame.py`
- Create: `src/windwall/winding_frame.py`

**Interfaces:**
- Consumes: `WindingToolParameters`, `build_608_reference(DEFAULT_PARAMETERS)`, and `WindingHeadParts`
- Produces: `WindingFrameParts` and `build_winding_frame(tool_parameters, design_parameters=DEFAULT_PARAMETERS) -> WindingFrameParts`

- [ ] **Step 1: Write failing tests for bearing seats, coaxial drive, retention, and mounting**

```python
import unittest

from windwall.parameters import DEFAULT_PARAMETERS
from windwall.winding_frame import build_winding_frame
from windwall.winding_tool_parameters import DEFAULT_WINDING_TOOL_PARAMETERS as P


class WindingFrameTests(unittest.TestCase):
    def test_frame_uses_two_608_bearings_on_one_eight_mm_axis(self):
        frame = build_winding_frame(P, DEFAULT_PARAMETERS)
        self.assertEqual(len(frame.bearings), 2)
        self.assertEqual(frame.metadata['shaft_diameter_mm'], 8.0)
        self.assertEqual(frame.metadata['bearing_nominal_dimensions_mm'], [8.0, 22.0, 7.0])
        self.assertTrue(frame.metadata['drive_interfaces_coaxial'])

    def test_manual_drive_and_mounting_features_are_present(self):
        frame = build_winding_frame(P, DEFAULT_PARAMETERS)
        self.assertEqual(frame.metadata['hex_socket_across_flats_mm'], 6.35)
        self.assertTrue(frame.metadata['positive_head_retention'])
        self.assertGreaterEqual(frame.metadata['bench_hole_count'], 4)
        self.assertEqual(frame.metadata['clamp_land_count'], 2)

    def test_each_printable_body_is_one_valid_solid(self):
        frame = build_winding_frame(P, DEFAULT_PARAMETERS)
        for name, shape in frame.printable_parts.items():
            with self.subTest(part=name):
                self.assertTrue(shape.val().isValid())
                self.assertEqual(len(shape.val().Solids()), 1)
```

- [ ] **Step 2: Run the frame test and verify it fails on the absent module**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_frame -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement separate printable frame bodies and hardware references**

Create a flat base with four through-holes and two unobstructed clamp lands, two
bolted uprights with explicit 22.2 mm candidate 608 seats, an 8 mm shaft
reference, a removable positively retained head hub, and a crank with a freely
rotating grip reference. Reuse `build_608_reference()` for both bearing
envelopes; do not redefine the 608 dimensions.

- [ ] **Step 4: Cut and gauge the coaxial 6.35 mm female hex socket**

Construct the socket as a six-sided prism on the shaft axis, publish its across-
flats dimension in metadata, and keep enough printed wall around it for a
prototype. Add metadata `powered_operation_validated: False` and do not add a
motor mount, transmission, guard claim, or powered-speed value.

- [ ] **Step 5: Run frame and existing bearing tests**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_frame tests.test_bearings -v`

Expected: all tests report `OK`.

- [ ] **Step 6: Commit the frame and drive**

```powershell
git add -- src/windwall/winding_frame.py tests/test_winding_frame.py
git commit -m "feat: add manual winding frame and crank"
```

---

### Task 4: Separate 51105 payoff turntable and drag brake

**Files:**
- Create: `tests/test_wire_payoff.py`
- Create: `src/windwall/wire_payoff.py`

**Interfaces:**
- Consumes: `WindingToolParameters`, `build_51105_reference(DEFAULT_PARAMETERS)`, and existing 51105 fit dimensions
- Produces: `WirePayoffParts` and `build_wire_payoff(tool_parameters, design_parameters=DEFAULT_PARAMETERS, brake_setting=0.0) -> WirePayoffParts`

- [ ] **Step 1: Write failing dimensional, ownership, and brake tests**

```python
import unittest

from windwall.parameters import DEFAULT_PARAMETERS
from windwall.winding_tool_parameters import DEFAULT_WINDING_TOOL_PARAMETERS as P
from windwall.wire_payoff import build_wire_payoff


class WirePayoffTests(unittest.TestCase):
    def test_platter_pilot_and_bearing_match_design(self):
        payoff = build_wire_payoff(P, DEFAULT_PARAMETERS)
        self.assertEqual(payoff.metadata['platter_diameter_mm'], 150.0)
        self.assertEqual(payoff.metadata['spool_pilot_mm'], [15.0, 20.0])
        self.assertEqual(payoff.metadata['bearing_nominal_dimensions_mm'], [25.0, 42.0, 11.0])

    def test_51105_motion_ownership_is_explicit(self):
        payoff = build_wire_payoff(P, DEFAULT_PARAMETERS)
        self.assertEqual(set(payoff.rotating_parts), {'platter', 'shaft_washer'})
        self.assertIn('housing_washer', payoff.stationary_parts)
        self.assertIn('rolling_envelope', payoff.bearing_internal_parts)

    def test_brake_has_free_running_and_drag_states_but_no_lock_state(self):
        free = build_wire_payoff(P, DEFAULT_PARAMETERS, brake_setting=0.0)
        drag = build_wire_payoff(P, DEFAULT_PARAMETERS, brake_setting=1.0)
        self.assertEqual(free.metadata['felt_compression_mm'], 0.0)
        self.assertGreater(drag.metadata['felt_compression_mm'], 0.0)
        self.assertFalse(drag.metadata['normal_adjustment_can_lock_platter'])
        with self.assertRaisesRegex(ValueError, 'brake setting'):
            build_wire_payoff(P, DEFAULT_PARAMETERS, brake_setting=1.01)
```

- [ ] **Step 2: Run the payoff test and confirm the missing-module failure**

Run: `python scripts/run_geometry.py -m unittest tests.test_wire_payoff -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Build the base, 51105 seats, platter, and spool pilot**

Use the existing 42.2 mm housing-seat and 24.8 mm rotating-pilot candidates.
Keep the housing washer stationary, the shaft washer and platter rotating, and
the rolling envelope as bearing-internal. Chamfer the 15 x 20 mm pilot, keep the
platter removable without disturbing the stationary seat, and keep all platter
bounds at or below 150 mm in X and Y.

- [ ] **Step 4: Add a replaceable felt and spring drag mechanism**

Model printed adjuster, spring, washer, screw, and felt as separately named
assembly members. Map the validated input range `0.0 <= brake_setting <= 1.0`
to `0.0 <= felt_compression_mm <= 1.0`; retain a positive hard-stop clearance
so the normal adjustment cannot clamp the platter rigidly.

- [ ] **Step 5: Run payoff and bearing suites**

Run: `python scripts/run_geometry.py -m unittest tests.test_wire_payoff tests.test_bearings -v`

Expected: all tests report `OK`.

- [ ] **Step 6: Commit the payoff module**

```powershell
git add -- src/windwall/wire_payoff.py tests/test_wire_payoff.py
git commit -m "feat: add 51105 wire payoff turntable"
```

---

### Task 5: Assemblies, collision audits, and bill of materials

**Files:**
- Create: `tests/test_winding_tool_assembly.py`
- Create: `src/windwall/winding_tool_assembly.py`

**Interfaces:**
- Consumes: `build_winding_head`, `build_winding_frame`, and `build_wire_payoff`
- Produces: `WindingToolAssemblies`, `build_winding_tool_assemblies(...)`, `audit_winding_tool_assemblies(...) -> dict`, and `winding_tool_bom(...) -> tuple[dict, ...]`

- [ ] **Step 1: Write failing assembly-audit and BOM tests**

```python
import unittest

from windwall.winding_tool_assembly import (
    audit_winding_tool_assemblies, build_winding_tool_assemblies, winding_tool_bom)


class WindingToolAssemblyTests(unittest.TestCase):
    def test_minimum_reference_and_maximum_states_pass_clearance_audits(self):
        for diameter in (110.0, 127.0, 145.0):
            model = build_winding_tool_assemblies(diameter_mm=diameter)
            audit = audit_winding_tool_assemblies(model)
            self.assertTrue(audit['valid'])
            self.assertEqual(audit['rib_count'], 6)
            self.assertEqual(audit['tape_station_count'], 18)
            self.assertGreaterEqual(audit['minimum_tape_clearance_mm'], 12.0)
            self.assertLessEqual(audit['maximum_print_xy_mm'], 220.0)

    def test_bom_contains_exact_bearing_and_shaft_inventory(self):
        rows = winding_tool_bom(build_winding_tool_assemblies())
        quantities = {row['item']: row['quantity'] for row in rows}
        self.assertEqual(quantities['608 bearing'], 2)
        self.assertEqual(quantities['51105 thrust bearing'], 1)
        self.assertEqual(quantities['8 mm shaft'], 1)
        self.assertEqual(quantities['felt brake pad'], 1)
```

- [ ] **Step 2: Run the assembly test and confirm it fails on the absent module**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_assembly -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Position named members in two independent assemblies**

Build `winding_jig` and `wire_payoff` named part dictionaries. Preserve the
winding head's horizontal axis, keep drive members coaxial, and publish rotating,
stationary, bearing-internal, adjustable, and hardware-reference ownership sets.
Do not combine the two tools on a shared base or mechanically synchronize them.

- [ ] **Step 4: Implement fail-closed numeric audits**

At 110, 127, and 145 mm, calculate intersections between moving members and
fixed structure, tape-passage clearance, slider retention, cam lock clearance,
crank hand envelope, head-release travel, 608/shaft nesting, 51105 ownership,
brake hard-stop clearance, and each printable body's X/Y bed envelope. Return
`valid: True` only when all named checks pass; raise a clear `ValueError` from
`build_winding_tool_assemblies` when an invariant cannot be constructed.

- [ ] **Step 5: Emit a literal hardware BOM from assembly metadata**

Include exact quantities for two 608 bearings, one complete 51105 bearing, one
8 mm shaft, six metal cam followers, cam/head/crank fasteners, springs, washers,
one replaceable felt pad, and bench-fastening choices. Mark fastener lengths as
nominal CAD selections and physical fit as unverified; do not list the 51105's
three internal modeled members as three bearings.

- [ ] **Step 6: Run all tooling geometry tests together**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_parameters tests.test_winding_head tests.test_winding_frame tests.test_wire_payoff tests.test_winding_tool_assembly -v`

Expected: all tests report `OK`.

- [ ] **Step 7: Commit assembly validation and BOM**

```powershell
git add -- src/windwall/winding_tool_assembly.py tests/test_winding_tool_assembly.py
git commit -m "feat: assemble and audit winding tools"
```

---

### Task 6: Isolated tooling exports and deterministic manifest

**Files:**
- Create: `tests/test_winding_tool_export.py`
- Create: `src/windwall/winding_tool_export.py`
- Create: `scripts/build_winding_tool.py`
- Modify: `tests/test_exports.py`

**Interfaces:**
- Consumes: validated tooling assemblies, printable part dictionaries, BOM, and existing `export_part`/named-assembly patterns
- Produces: `export_winding_tool(destination: Path, ...) -> WindingToolManifest` and a fail-closed command-line release builder

- [ ] **Step 1: Write failing end-to-end export tests**

```python
import json
import unittest

from tests.support import temporary_build_directory
from windwall.export import export_all
from windwall.winding_tool_export import export_winding_tool


class WindingToolExportTests(unittest.TestCase):
    def test_tooling_export_has_valid_parts_assemblies_bom_and_manifest(self):
        with temporary_build_directory() as destination:
            manifest = export_winding_tool(destination)
            self.assertEqual({assembly['name'] for assembly in manifest.assemblies},
                             {'winding_jig', 'wire_payoff', 'winding_jig_exploded'})
            self.assertTrue(all(part.step_path.is_file() and part.stl_path.is_file()
                                for part in manifest.printable_parts))
            self.assertTrue((destination / 'bom.json').is_file())
            data = json.loads((destination / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(data['reference_diameter_mm'], 127.0)
            self.assertFalse(data['physical_fit_verified'])
            self.assertFalse(data['powered_operation_validated'])

    def test_turbine_release_inventory_does_not_absorb_tooling_parts(self):
        with temporary_build_directory() as destination:
            turbine = export_all(destination)
            self.assertNotIn('winding_head_backplate', turbine.part_names())
            self.assertNotIn('wire_payoff_platter', turbine.part_names())
```

- [ ] **Step 2: Run the export tests and verify the missing-module failure**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_export -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement deterministic printable-part and assembly export**

Reuse validation and canonical STEP-header behaviour from `windwall.export`
without adding tooling names to `PRINT_SOURCES`. Export each printable solid to
`step/` and `stl/`, three named assemblies to `assembly/`, and include source
builder, quantity, bounds, topology result, SHA-256, calculated diameter range,
tape layout, bearing ownership, physical-validation flags, and prototype limits.

- [ ] **Step 4: Write BOM and fail-closed manifest ordering**

Serialize `bom.json` and `manifest.json` with UTF-8, `indent=2`, sorted keys,
stable part ordering, and newline termination. Remove a stale manifest before
starting; write the success manifest only after all parts, round trips, topology
checks, assemblies, BOM, and audits pass.

- [ ] **Step 5: Add the command-line builder without changing `build_v5.py`**

```python
from pathlib import Path

from windwall.winding_tool_export import export_winding_tool


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    export_winding_tool(root / 'release' / 'winding-tool')
```

- [ ] **Step 6: Run tooling and regression export tests**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_export tests.test_exports -v`

Expected: all tests report `OK`, and the existing V5 production-part set remains unchanged.

- [ ] **Step 7: Commit the isolated release pipeline**

```powershell
git add -- src/windwall/winding_tool_export.py scripts/build_winding_tool.py tests/test_winding_tool_export.py tests/test_exports.py
git commit -m "feat: export serpentine winding tools"
```

---

### Task 7: Drawings, German guide, and generated release

**Files:**
- Create: `scripts/preview_winding_tool.py`
- Create: `docs/serpentine-coil-winding-tool-de.md`
- Modify: `README.md`
- Test: `tests/test_winding_tool_export.py`
- Generate: `release/winding-tool/**`

**Interfaces:**
- Consumes: tooling builders, audits, exporter, BOM, and approved prototype warnings
- Produces: overview/exploded PNGs, German instructions, synchronized release tree, and README link

- [ ] **Step 1: Extend tests to require documentation and drawing inventory**

```python
def test_release_includes_synchronised_drawings_and_german_guide(self):
    with temporary_build_directory() as destination:
        export_winding_tool(destination)
        required = {
            'drawings/winding-jig-reference.png',
            'drawings/winding-jig-range.png',
            'drawings/winding-tool-exploded.png',
            'docs/serpentine-coil-winding-tool-de.md',
        }
        self.assertTrue(all((destination / name).is_file() for name in required))
        guide = (destination / 'docs/serpentine-coil-winding-tool-de.md').read_text('utf-8')
        for phrase in ('Ø127 mm', '10-mm-Klebeband', 'Akkuschrauberbetrieb ist nicht freigegeben',
                       'Schutzbrille', 'Probespule'):
            self.assertIn(phrase, guide)
```

- [ ] **Step 2: Run the focused test and verify missing artifacts fail**

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_export.WindingToolExportTests.test_release_includes_synchronised_drawings_and_german_guide -v`

Expected: FAIL because drawings and guide copy are not emitted yet.

- [ ] **Step 3: Implement deterministic reference, range, and exploded drawings**

Render the 127 mm assembled jig, overlay the 110/145 mm rib-contact circles in
the range drawing, and render both independent exploded modules with numbered
parts. Use fixed camera, canvas size, colours, labels, and output names. Annotate
Ø110, Ø127, Ø145, six ribs, 18 x 20-degree tape positions, Ø150 platter,
Ø15 x 20 pilot, 608, 51105, rotation direction, and wire feed direction.

- [ ] **Step 4: Write the German build and operating guide**

Document print orientation, cleanup of every wire-contact surface, hardware BOM,
608 and 51105 washer ownership, assembly sequence, bench fastening, brake setup,
diameter adjustment, insertion of 18 tape strips, manual winding, rib release,
serpentine forming, lead/direction marking, 127 mm physical calibration, and
inspection after a test coil. Include wire-cut/tangle/eye hazards and state
exactly `Akkuschrauberbetrieb ist nicht freigegeben`; do not imply electrical,
strength, fit, speed, or production validation.

- [ ] **Step 5: Link the optional tooling release from the root README**

Add a short `Serpentine coil winding tool` section that links the German guide
and `release/winding-tool/manifest.json`, identifies the two independent manual
modules, and explicitly says they are workshop aids rather than V5 production
parts.

- [ ] **Step 6: Build the complete tooling release and run focused tests**

Run: `python scripts/run_geometry.py scripts/build_winding_tool.py`

Run: `python scripts/run_geometry.py -m unittest tests.test_winding_tool_export -v`

Expected: release build completes and all focused tests report `OK`.

- [ ] **Step 7: Visually inspect all three drawings and release inventory**

Open each generated PNG at full resolution. Confirm legible dimensions, no
clipped labels, correct two-module separation, visible tape access, plausible
cam/rib placements at all three diameters, correct bearing callouts, and no
hidden or duplicated parts. Compare manifest part names, BOM rows, guide wording,
and actual release files one-for-one.

- [ ] **Step 8: Commit source documentation and generated artifacts**

```powershell
git add -- README.md docs/serpentine-coil-winding-tool-de.md scripts/preview_winding_tool.py tests/test_winding_tool_export.py release/winding-tool
git commit -m "docs: publish serpentine winding tool release"
```

---

### Task 8: Full verification, cleanup, and integration review

**Files:**
- Review: all files and artifacts changed by Tasks 1--7

**Interfaces:**
- Consumes: completed tooling implementation and release
- Produces: verified, focused branch state ready for review or integration

- [ ] **Step 1: Run the complete test suite**

Run: `python scripts/run_geometry.py -m unittest discover -s tests -v`

Expected: every unittest reports `OK`. Record any native OCP teardown status separately from the unittest result.

- [ ] **Step 2: Rebuild the tooling release from a clean output directory**

Move the existing `release/winding-tool` to a temporary backup inside the
workspace, run `python scripts/run_geometry.py scripts/build_winding_tool.py`,
compare the new manifest's paths, hashes, BOM, and audit records with the
committed release, then restore nothing unless the comparison exposes a build
defect. Use explicit verified paths and PowerShell `Move-Item`/`Remove-Item` for
this destructive check.

- [ ] **Step 3: Run hygiene checks**

Run: `git diff --check`

Run: `rg -n "powered.*validated.*true|physical.*verified.*true" src/windwall/winding_* src/windwall/wire_payoff.py docs/serpentine-coil-winding-tool-de.md release/winding-tool`

Expected: no whitespace errors, no unresolved placeholders, and no false validation claims.

- [ ] **Step 4: Confirm no stale or unintended product coupling**

Run: `git status --short`

Run: `rg -n "winding_head|wire_payoff|winding-tool" src/windwall/export.py scripts/build_v5.py release/v5/manifest.json`

Expected: only intended changes are present, and the V5 turbine exporter/manifest contains no tooling production parts.

- [ ] **Step 5: Perform the engineering cleanup pass**

Remove unused imports, duplicated dimensions, dead helpers, stale comments,
obsolete generated files, and documentation claims not backed by CAD metadata or
tests. Re-run the focused test owning each corrected file.

- [ ] **Step 6: Commit only if cleanup changed tracked files**

```powershell
git add -- src tests scripts docs README.md release/winding-tool
git commit -m "test: verify serpentine winding tool release"
```

- [ ] **Step 7: Prepare the final handoff evidence**

Report implemented changes, exact files changed, commands run, unittest results,
native-process limitations, drawings visually inspected, documentation updated,
known need for physical fit/calibration testing, and the next integration choice.
