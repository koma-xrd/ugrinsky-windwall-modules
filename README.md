# Windwall

Parametric CadQuery source for a seven-stage Ugrinsky wind-wall rotor. The
source files are authoritative; generated STEP and STL output belongs in the
local `build/` directory.

## CadQuery environment

Open `C:\Users\fi87roy\Downloads\CQ-editor-windows-x86_64.exe\CQ-editor.exe`
to use CQ-editor. In an unpacked CQ-editor distribution, locate its bundled
Python executable before running CadQuery commands from a terminal:

```powershell
$cqPython = Get-ChildItem -Path "C:\path\to\CQ-editor" -Recurse -Filter python.exe |
    Select-Object -First 1 -ExpandProperty FullName
& $cqPython -c "import cadquery; print(cadquery.__version__)"
```

The currently downloaded portable CQ-editor 0.7 package contains only
`CQ-editor.exe`; it does not expose a discoverable `python.exe`, so the command
above cannot select a standalone CQ-editor interpreter from that package. Do
not install or modify a system-wide Python to work around this. Its embedded
interpreter is available through the CQ-editor UI; open `scripts/build_all.py`
there once that script is introduced in the later export task.

The parameter contract has no CadQuery dependency. It was verified with the
existing system Python 3.14 without creating a virtual environment. CadQuery
geometry tests introduced later must run in a compatible CQ-editor or
project-local CadQuery environment; create a project-local `.venv/` only after
checking the selected CadQuery release supports that Python version.

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

Run the read-only binary-STL audit against a directory of reference meshes:

```powershell
$env:PYTHONPATH = "$PWD;$PWD\src"
python scripts/analyze_references.py "C:\path\to\reference-files"
```

The command writes `build/reference-report.json`, containing mesh envelopes,
signed volumes, connected-component counts, and boundary, non-manifold, and
degenerate-face counts. The input meshes are never copied into this project.
