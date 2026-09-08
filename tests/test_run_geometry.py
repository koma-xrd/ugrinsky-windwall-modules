"""The launcher must set process-local error flags without hiding target exits."""

import json
from pathlib import Path
import subprocess
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = PROJECT_ROOT / "scripts/run_geometry.py"


class GeometryLauncherTests(unittest.TestCase):
    def run_launcher(self, *arguments):
        return subprocess.run([sys.executable, str(LAUNCHER), *arguments],
                              cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)

    def test_script_arguments_output_and_nonzero_exit_are_preserved(self):
        result = self.run_launcher("tests/fixtures/launcher_probe.py", "first", "two words")
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(json.loads(result.stdout)["arguments"], ["first", "two words"])

    def test_module_execution_preserves_nonzero_exit(self):
        result = self.run_launcher("-m", "tests.fixtures.launcher_probe", "module argument")
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(json.loads(result.stdout)["arguments"], ["module argument"])

    @unittest.skipUnless(sys.platform == "win32", "Windows process error-mode check")
    def test_windows_fault_dialog_flags_are_set_before_the_target_runs(self):
        result = self.run_launcher("tests/fixtures/launcher_probe.py")
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(json.loads(result.stdout)["error_mode"] & 0x0003, 0x0003)

    def test_missing_target_is_a_usage_error(self):
        for arguments in ((), ("-m",)):
            with self.subTest(arguments=arguments):
                result = self.run_launcher(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertIn("Usage:", result.stderr)


if __name__ == "__main__":
    unittest.main()
