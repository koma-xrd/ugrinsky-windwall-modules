"""Build the tracked V5 geometry release, with repository-relative manifest paths.

Run through scripts/run_geometry.py to suppress native Windows fault dialogs.
All CAD/topology checks must pass before the manifest is published. The output
does not approve physical fit or operation and never starts a physical print.
"""

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for import_root in (PROJECT_ROOT, PROJECT_ROOT / 'src'):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from windwall.export import export_all
from windwall.parameters import DEFAULT_PARAMETERS


def build_v5(output_dir: Path, p=DEFAULT_PARAMETERS) -> dict:
    """Create eight print candidates, nine coupon solids and three assemblies.

    Paths describe the canonical repository location release/v5 even when a
    fresh temporary directory is used to verify reproducibility.
    """
    manifest = export_all(Path(output_dir), p, repository_prefix=Path('release/v5'))
    return json.loads(manifest.path.read_text(encoding='utf-8'))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=PROJECT_ROOT / 'release/v5')
    args = parser.parse_args()
    manifest = build_v5(args.output_dir)
    print(f"V5: {len(manifest['production_parts'])} unique print candidates, "
          f"{len(manifest['coupons'])} coupon solids, {len(manifest['assemblies'])} STEP assemblies.\n"
          f"Manifest: {args.output_dir / 'manifest.json'}\n"
          'Physical validation remains false. Record the process exit separately.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
