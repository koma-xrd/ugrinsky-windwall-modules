"""Child-process fixture: report the inherited launcher policy and fail normally."""

import ctypes
import json
import sys

mode = ctypes.windll.kernel32.GetErrorMode() if sys.platform == "win32" else None
print(json.dumps({"error_mode": mode, "arguments": sys.argv[1:]}), flush=True)
raise SystemExit(7)
