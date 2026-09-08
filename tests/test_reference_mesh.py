import struct
import tempfile
import unittest
from pathlib import Path

from windwall.reference_mesh import analyze_binary_stl


FIXTURE_PATH = Path("tests/fixtures/tetrahedron_binary.stl")


def temporary_fixture_directory():
    build_directory = Path("build")
    build_directory.mkdir(exist_ok=True)
    return tempfile.TemporaryDirectory(dir=build_directory)


class ReferenceMeshTests(unittest.TestCase):
    def test_closed_tetrahedron_is_one_manifold_component(self):
        report = analyze_binary_stl(FIXTURE_PATH)

        self.assertEqual(report.filename, "tetrahedron_binary.stl")
        self.assertEqual(report.triangle_count, 4)
        self.assertEqual(report.unique_vertex_count, 4)
        self.assertEqual(report.component_count, 1)
        self.assertEqual(report.minimum_xyz, (0.0, 0.0, 0.0))
        self.assertEqual(report.maximum_xyz, (1.0, 1.0, 1.0))
        self.assertEqual(report.size_xyz, (1.0, 1.0, 1.0))
        self.assertEqual(report.boundary_edge_count, 0)
        self.assertEqual(report.nonmanifold_edge_count, 0)
        self.assertEqual(report.degenerate_face_count, 0)
        self.assertAlmostEqual(report.signed_volume, 1.0 / 6.0)
        self.assertEqual(report.as_dict()["triangle_count"], 4)

    def test_rejects_a_file_with_a_triangle_count_length_mismatch(self):
        with temporary_fixture_directory() as directory:
            path = Path(directory) / "truncated.stl"
            path.write_bytes(b" ".ljust(80, b" ") + struct.pack("<I", 1))
            with self.assertRaisesRegex(ValueError, "does not match triangle count"):
                analyze_binary_stl(path)


if __name__ == "__main__":
    unittest.main()
