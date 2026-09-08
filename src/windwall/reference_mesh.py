"""Read binary STL meshes for measurement and topology reporting.

This module inspects external references and generated release STL topology.
It does not construct, modify, or import meshes into production CAD geometry.
"""

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
import struct

import numpy as np


_STL_HEADER_SIZE = 80
_STL_COUNT_SIZE = 4
_STL_RECORD_SIZE = 50
_DEGENERATE_FACE_AREA_MM2 = 1e-10
_TRIANGLE_DTYPE = np.dtype(
    [
        ("normal", "<f4", (3,)),
        ("vertices", "<f4", (3, 3)),
        ("attribute", "<u2"),
    ]
)


@dataclass(frozen=True)
class MeshReport:
    """Measured geometry and topology information for one binary STL file."""

    filename: str
    triangle_count: int
    unique_vertex_count: int
    component_count: int
    minimum_xyz: tuple[float, float, float]
    maximum_xyz: tuple[float, float, float]
    size_xyz: tuple[float, float, float]
    boundary_edge_count: int
    nonmanifold_edge_count: int
    degenerate_face_count: int
    signed_volume: float

    def as_dict(self) -> dict[str, object]:
        """Return native Python values suitable for ``json.dumps``."""
        report = asdict(self)
        for key in ("minimum_xyz", "maximum_xyz", "size_xyz"):
            report[key] = list(report[key])
        return report


class _DisjointSet:
    def __init__(self, size: int) -> None:
        self._parents = list(range(size))

    def find(self, item: int) -> int:
        while self._parents[item] != item:
            self._parents[item] = self._parents[self._parents[item]]
            item = self._parents[item]
        return item

    def union(self, first: int, second: int) -> None:
        first_root = self.find(first)
        second_root = self.find(second)
        if first_root != second_root:
            self._parents[second_root] = first_root

    def component_count(self) -> int:
        return len({self.find(index) for index in range(len(self._parents))})


def analyze_binary_stl(path: Path) -> MeshReport:
    """Analyze a binary STL at *path* and reject malformed record lengths."""
    data = path.read_bytes()
    minimum_length = _STL_HEADER_SIZE + _STL_COUNT_SIZE
    if len(data) < minimum_length:
        raise ValueError(f"{path} is shorter than a binary STL header and triangle count")

    triangle_count = struct.unpack_from("<I", data, _STL_HEADER_SIZE)[0]
    expected_length = minimum_length + triangle_count * _STL_RECORD_SIZE
    if len(data) != expected_length:
        raise ValueError(
            f"{path} length {len(data)} does not match triangle count {triangle_count} "
            f"(expected {expected_length} bytes)"
        )

    triangles = np.frombuffer(data, dtype=_TRIANGLE_DTYPE, count=triangle_count, offset=minimum_length)
    vertices = triangles["vertices"].reshape((-1, 3))
    if not len(vertices):
        return MeshReport(
            filename=path.name,
            triangle_count=0,
            unique_vertex_count=0,
            component_count=0,
            minimum_xyz=(0.0, 0.0, 0.0),
            maximum_xyz=(0.0, 0.0, 0.0),
            size_xyz=(0.0, 0.0, 0.0),
            boundary_edge_count=0,
            nonmanifold_edge_count=0,
            degenerate_face_count=0,
            signed_volume=0.0,
        )

    unique_vertices, inverse_indices = np.unique(vertices, axis=0, return_inverse=True)
    face_indices = inverse_indices.reshape((-1, 3))
    edge_counts = _edge_incidence_counts(face_indices)
    components = _component_count(face_indices, len(unique_vertices))
    triangle_vertices = vertices.astype(np.float64).reshape((-1, 3, 3))
    cross_products = np.cross(
        triangle_vertices[:, 1] - triangle_vertices[:, 0],
        triangle_vertices[:, 2] - triangle_vertices[:, 0],
    )
    face_areas = np.linalg.norm(cross_products, axis=1) / 2.0
    signed_volume = float(
        np.sum(np.einsum("ij,ij->i", triangle_vertices[:, 0], cross_products)) / 6.0
    )
    minimum_xyz = tuple(float(value) for value in unique_vertices.min(axis=0))
    maximum_xyz = tuple(float(value) for value in unique_vertices.max(axis=0))

    return MeshReport(
        filename=path.name,
        triangle_count=triangle_count,
        unique_vertex_count=len(unique_vertices),
        component_count=components,
        minimum_xyz=minimum_xyz,
        maximum_xyz=maximum_xyz,
        size_xyz=tuple(maximum - minimum for minimum, maximum in zip(minimum_xyz, maximum_xyz)),
        boundary_edge_count=sum(count == 1 for count in edge_counts.values()),
        nonmanifold_edge_count=sum(count > 2 for count in edge_counts.values()),
        degenerate_face_count=int(np.count_nonzero(face_areas < _DEGENERATE_FACE_AREA_MM2)),
        signed_volume=signed_volume,
    )


def _edge_incidence_counts(face_indices: np.ndarray) -> Counter[tuple[int, int]]:
    counts: Counter[tuple[int, int]] = Counter()
    for first, second, third in face_indices:
        counts[tuple(sorted((int(first), int(second))))] += 1
        counts[tuple(sorted((int(second), int(third))))] += 1
        counts[tuple(sorted((int(third), int(first))))] += 1
    return counts


def _component_count(face_indices: np.ndarray, vertex_count: int) -> int:
    components = _DisjointSet(vertex_count)
    for first, second, third in face_indices:
        components.union(int(first), int(second))
        components.union(int(second), int(third))
    return components.component_count()
