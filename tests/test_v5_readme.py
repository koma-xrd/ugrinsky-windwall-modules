"""Keep the public V5 BOM and illustrated entry points aligned with the release."""

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class V5ReadmeTests(unittest.TestCase):
    def test_print_bom_matches_release_quantities_and_filenames(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "release/v5/manifest.json").read_bytes())
        rows = re.findall(r"^\| (\d+) \| `([a-z_]+\.stl)` \|", readme, flags=re.MULTILINE)
        expected = {Path(p["stl_path"]).name: str(p["quantity"]) for p in manifest["production_parts"]}
        self.assertEqual({filename: quantity for quantity, filename in rows}, expected)

    def test_required_release_images_are_embedded_with_portable_paths(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        paths = re.findall(r"!\[[^\]]+\]\(([^)]+)\)", readme)
        for filename in ("E06-generator-explosion.png", "E07-generator-schnitt.png",
                         "E14-zaunmontage.png", "E15-gesamtbaugruppe.png"):
            self.assertIn("release/v5/drawings/" + filename, paths)
        for relative in paths:
            self.assertFalse(Path(relative).is_absolute())
            self.assertTrue((ROOT / relative).is_file())


if __name__ == "__main__":
    unittest.main()
