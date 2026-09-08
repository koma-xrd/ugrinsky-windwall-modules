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
