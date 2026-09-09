"""Contract tests for the reconstructed, shared aerodynamic stage."""

from dataclasses import replace
import os
from pathlib import Path
import unittest

import cadquery as cq
import numpy as np

from windwall.blade_profile import build_blade_profile, build_blade_stage
from windwall.parameters import DEFAULT_PARAMETERS


class BladeProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = build_blade_stage(DEFAULT_PARAMETERS).val()

    def test_two_mm_stage_retains_the_122_mm_diameter_and_70_mm_height(self):
        shape = self.stage
        box = shape.BoundingBox()
        self.assertAlmostEqual(box.xlen, 122.0, delta=0.1)
        self.assertAlmostEqual(box.ylen, 121.37, delta=0.1)
        self.assertAlmostEqual(box.zlen, 70.0, delta=0.1)

    def test_stage_is_single_valid_solid(self):
        shape = self.stage
        self.assertTrue(shape.isValid())
        self.assertEqual(len(shape.Solids()), 1)

    def test_profile_is_closed_and_planar(self):
        profile = build_blade_profile(DEFAULT_PARAMETERS)
        self.assertTrue(profile.IsClosed())
        self.assertAlmostEqual(profile.BoundingBox().zlen, 0.0, places=6)

    def test_top_section_retains_reference_sixty_degree_twist(self):
        top = cq.Workplane(obj=self.stage).section(69.9).val().BoundingBox()
        bottom = cq.Workplane(obj=self.stage).section(0.1).val().BoundingBox()
        self.assertAlmostEqual(bottom.xlen, 122.0, delta=0.1)
        self.assertAlmostEqual(top.xlen, 73.603, delta=0.6)
        self.assertGreater(bottom.xlen - top.xlen, 45)

    def test_reinforcement_is_confined_to_central_twenty_mm_radius(self):
        # Two 2 mm-wide 24/60 mm arc pairs, clipped outside radius 20 mm.
        # V4.3 leaves two separate section wires in the open middle.
        # Independent annular-sector minus circle-overlap calculation: 455.19897 mm2.
        section = cq.Workplane(obj=self.stage).section(35).val()
        self.assertEqual(len(section.Wires()), 2)
        exclusion = cq.Face.makeFromWires(cq.Workplane("XY").circle(20).val()).translate((0, 0, 35))
        area = sum(cq.Face.makeFromWires(wire).cut(exclusion).Area() for wire in section.Wires())
        self.assertAlmostEqual(area, 455.20, delta=0.5)

    def test_invalid_hub_cannot_encroach_on_active_blade(self):
        oversized_hub = replace(DEFAULT_PARAMETERS.blade, hub_blend_radius_mm=21)
        with self.assertRaises(ValueError):
            build_blade_stage(replace(DEFAULT_PARAMETERS, blade=oversized_hub))

    def test_noncanonical_or_nonfinite_coordinates_are_rejected(self):
        p = DEFAULT_PARAMETERS
        for blade in (
            replace(p.blade, small_arc_center_xy_mm=(36,1), large_arc_center_xy_mm=(-48,1),
                    tangent_transition_xy_mm=(12,1)),
            replace(p.blade, small_arc_center_xy_mm=(float('nan'),0)),
            replace(p.blade, tangent_transition_xy_mm=(12,)),
        ):
            for builder in (build_blade_profile, build_blade_stage):
                with self.subTest(blade=blade, builder=builder.__name__):
                    with self.assertRaises(ValueError):
                        builder(replace(p, blade=blade))

    @unittest.skipUnless(os.environ.get("WINDWALL_REFERENCE_BLADE"), "External reference path not configured")
    def test_active_sections_match_external_reference_in_both_directions(self):
        from scripts.preview_blade import load_reference_triangles, slice_triangles
        triangles = load_reference_triangles(Path(os.environ["WINDWALL_REFERENCE_BLADE"]))
        # Original end fastener bosses alter the section at z > 60 mm; those
        # fittings are replaced by later module tasks, not the shared skin.
        for z in (5.0, 17.5, 35.0, 52.5, 60.0):
            with self.subTest(z=z):
                reference_segments = slice_triangles(triangles, z) - [6.25, 122.634]
                reference = reference_segments.reshape(-1, 2)
                section = cq.Workplane(obj=self.stage).section(z).val()
                samples = []
                for edge in section.Edges():
                    count = max(2, int(edge.Length() / 0.15) + 1)
                    samples.extend([(p.x, p.y) for p in edge.positions(np.linspace(0, 1, count))])
                production = np.asarray(samples)
                reference_samples = []
                for start, end in reference_segments:
                    count = max(2, int(np.linalg.norm(end - start) / 0.1) + 1)
                    fractions = np.linspace(0, 1, count)[:, None]
                    reference_samples.extend(start + (end - start) * fractions)
                reference_dense = np.asarray(reference_samples)
                for source, target in ((reference, production), (production, reference_dense)):
                    source = source[np.linalg.norm(source, axis=1) > 20.0]
                    deviations = [np.min(np.linalg.norm(target - point, axis=1)) for point in source]
                    self.assertLess(max(deviations), 0.60)


if __name__ == "__main__":
    unittest.main()
