# Task 1 execution report: parameter contract

## TDD evidence

- **RED command:** `$env:PYTHONPATH = "$PWD;$PWD/src"; python -m unittest tests.test_winding_tool_parameters`
- **RED result:** failed as expected before implementation with `ImportError: cannot import name 'diameter_settings_mm'`. The focused default-contract test named the new public API and eleven required settings.
- **GREEN command:** `$env:PYTHONPATH = "$PWD;$PWD/src"; python scripts/run_geometry.py -m unittest tests.test_winding_tool_parameters -v`
- **GREEN result:** 5 tests ran, all passed; unittest exit status was 0 and launcher process exit status was 0.
- **OCP native teardown status:** not encountered (the parameter-only test command exited 0; no status-1 teardown occurred).

## Changed files

- `src/windwall/winding_tool_parameters.py`: replaced the superseded cam/rib contract with the simple pin-adjustable wheel parameters, strict validation, and derived diameter settings.
- `tests/test_winding_tool_parameters.py`: replaced legacy-contract coverage with simplified default and invalid-input regressions.
- `.superpowers/sdd/2026-09-16-simple-pin-adjustable-coil-winder/task-1-report.md`: this evidence report.

## Self-review

- Removed obsolete cam/rib, slider, fastener, shaft, and brake-related parameter fields; no compatibility aliases remain.
- Retained only the approved simple-wheel, tape, payoff, and print-bed dimensions.
- The diameter sequence derives from range fields and stores no duplicate settings tuple.
- A single private 220 mm envelope constant supplies the default and fixed printer-limit check.
- No unused imports, duplicate parameter constants, or unclear validation messages found.

## Downstream temporary breakage

Existing winding-head, frame, assembly, export, preview, and service builders still refer to intentionally removed legacy fields. They are expected to be updated by downstream tasks and were not edited here.

## Commit

Implementation, tests, and this report are committed with `refactor: define simple coil wheel parameters`. The commit hash is supplied in the task handoff because including a commit's own hash in its tracked contents would change that hash.
