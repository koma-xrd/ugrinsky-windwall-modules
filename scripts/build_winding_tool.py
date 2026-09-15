"""Build the isolated winding-tool release; errors propagate as a nonzero exit.

Run through scripts/run_geometry.py to suppress Windows native fault dialogs.
CAD checks do not approve physical fit, printing or powered operation.
"""

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for import_root in (PROJECT_ROOT, PROJECT_ROOT / 'src'):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from windwall.winding_tool_export import export_winding_tool


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=PROJECT_ROOT / 'release/winding-tool')
    arguments = parser.parse_args()
    manifest = export_winding_tool(arguments.output_dir)
    print(f'Winding tool: {len(manifest.printable_parts)} unique print candidates, '
          f'{len(manifest.assemblies)} STEP assemblies.\nManifest: {manifest.path}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
