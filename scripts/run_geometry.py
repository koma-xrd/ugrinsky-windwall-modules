"""Run geometry code with Windows fault dialogs disabled for this process only.

Usage: python scripts/run_geometry.py [-m module | script.py] [arguments...]
SetErrorMode runs before target imports. Exceptions, SystemExit and native crash
statuses propagate unchanged; this is not a workaround for the native failure.
No registry, machine-wide setting, dependency or target code is modified.
"""

import ctypes
import runpy
import sys


def main() -> None:
    if sys.platform == "win32":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetErrorMode.restype = ctypes.c_uint
        kernel32.SetErrorMode.argtypes = [ctypes.c_uint]
        kernel32.SetErrorMode.restype = ctypes.c_uint
        # Preserve inherited flags while suppressing critical-error and crash UI.
        kernel32.SetErrorMode(kernel32.GetErrorMode() | 0x0001 | 0x0002)
    arguments = sys.argv[1:]
    if not arguments or (arguments[0] == "-m" and len(arguments) < 2):
        print("Usage: run_geometry.py [-m module | script.py] [arguments...]", file=sys.stderr)
        raise SystemExit(2)
    if arguments[0] == "-m":
        sys.argv = arguments[1:]
        runpy.run_module(arguments[1], run_name="__main__", alter_sys=True)
    else:
        sys.argv = arguments
        runpy.run_path(arguments[0], run_name="__main__")


if __name__ == "__main__":
    main()
