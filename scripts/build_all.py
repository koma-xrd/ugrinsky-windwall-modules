"""Export and validate every release artifact through scripts/run_geometry.py."""

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for import_root in (PROJECT_ROOT, PROJECT_ROOT / 'src'):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from windwall.export import export_all


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=PROJECT_ROOT / 'build')
    parser.add_argument('--inspect', action='store_true', help='Render actual STEP/STL inspection sheets')
    args = parser.parse_args()
    manifest = export_all(args.output_dir)
    if args.inspect:
        from scripts.inspect_exports import inspect_exports
        inspect_exports(manifest.path)
    print(f'Exported and validated {len(manifest.production_parts)} unique production candidates, '
          f'{len(manifest.coupons)} coupon solids and {len(manifest.assemblies)} assemblies.\n'
          f'Manifest: {manifest.path}\nPhysical fit and operation remain unvalidated. '
          'Record the process exit separately.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
