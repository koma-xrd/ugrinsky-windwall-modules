import unittest
from dataclasses import replace

import cadquery as cq

from windwall.bearings import (bearing_fit_manifest, build_51105_fit_coupon,
                               build_51105_reference, build_608_fit_coupon,
                               build_608_reference)
from windwall.parameters import DEFAULT_PARAMETERS
from windwall.reference_mesh import analyze_binary_stl
from tests.support import temporary_build_directory


class BearingReferenceTests(unittest.TestCase):
    def test_normative_bearing_envelopes_and_coupon_variants(self):
        thrust = build_51105_reference(DEFAULT_PARAMETERS)
        radial = build_608_reference(DEFAULT_PARAMETERS)

        self.assertEqual(thrust.nominal_dimensions_mm, (25.0, 42.0, 11.0))
        self.assertEqual(radial.nominal_dimensions_mm, (8.0, 22.0, 7.0))
        self.assertEqual(build_51105_fit_coupon(DEFAULT_PARAMETERS).seat_diameters_mm,
                         (42.0, 42.2, 42.4))
        self.assertEqual(build_608_fit_coupon(DEFAULT_PARAMETERS).seat_diameters_mm,
                         (22.0, 22.2, 22.4))

    def test_thrust_reference_keeps_independent_washers(self):
        reference = build_51105_reference(DEFAULT_PARAMETERS)

        self.assertEqual(set(reference.parts),
                         {"housing_washer", "rolling_envelope", "shaft_washer"})
        self.assertIsNot(reference.parts["housing_washer"], reference.parts["shaft_washer"])
        for part in reference.parts.values():
            self.assertTrue(part.val().isValid())
            self.assertEqual(len(part.val().Solids()), 1)
            self.assertGreater(part.val().Volume(), 0)

    def test_fit_coupons_are_connected_printable_solids_and_publish_candidates(self):
        thrust_coupon = build_51105_fit_coupon(DEFAULT_PARAMETERS)
        radial_coupon = build_608_fit_coupon(DEFAULT_PARAMETERS)

        self.assertEqual(thrust_coupon.pilot_diameters_mm, (24.6, 24.8, 25.0))
        self.assertEqual(radial_coupon.pilot_diameters_mm, ())
        for coupon in (thrust_coupon, radial_coupon):
            self.assertTrue(coupon.shape.val().isValid())
            self.assertEqual(len(coupon.shape.val().Solids()), 1)
            self.assertGreater(coupon.shape.val().Volume(), 0)

    def test_coupon_meshes_are_closed_manifold_single_components(self):
        p = DEFAULT_PARAMETERS
        with temporary_build_directory() as destination:
            for name, coupon in (("51105", build_51105_fit_coupon(p)),
                                 ("608", build_608_fit_coupon(p))):
                path = destination / f"bearing_{name}_coupon.stl"
                cq.exporters.export(coupon.shape, str(path),
                                    tolerance=p.manufacturing.export_linear_tolerance_mm,
                                    angularTolerance=p.manufacturing.export_angular_tolerance_rad)
                mesh = analyze_binary_stl(path)
                self.assertEqual(mesh.component_count, 1)
                self.assertEqual(mesh.boundary_edge_count, 0)
                self.assertEqual(mesh.nonmanifold_edge_count, 0)
                self.assertEqual(mesh.degenerate_face_count, 0)
                self.assertGreater(mesh.signed_volume, 0)

    def test_manifest_records_prototype_status_and_literal_dimensions(self):
        manifest = bearing_fit_manifest(DEFAULT_PARAMETERS)

        self.assertFalse(manifest["physically_calibrated"])
        self.assertEqual(manifest["51105"]["seat_diameters_mm"], [42.0, 42.2, 42.4])
        self.assertEqual(manifest["51105"]["pilot_diameters_mm"], [24.6, 24.8, 25.0])
        self.assertEqual(manifest["608"]["seat_diameters_mm"], [22.0, 22.2, 22.4])

    def test_rejects_non_positive_bearing_fit_dimensions(self):
        invalid = replace(DEFAULT_PARAMETERS, bearings=replace(
            DEFAULT_PARAMETERS.bearings, thrust_rotating_pilot_diameter_mm=0.0))

        with self.assertRaisesRegex(ValueError, "positive and finite"):
            build_51105_fit_coupon(invalid)

    def test_rejects_nonfinite_dimensions_and_invalid_export_tolerances(self):
        for group, field in (('bearings', 'thrust_height_mm'),
                             ('bearings', 'radial_height_mm'),
                             ('manufacturing', 'export_linear_tolerance_mm'),
                             ('manufacturing', 'export_angular_tolerance_rad'),
                             ('shaft', 'clearance_hole_diameter_mm')):
            for value in (float('nan'), float('inf'), -float('inf'), 0.0, -0.1):
                with self.subTest(group=group, field=field, value=value):
                    p = replace(DEFAULT_PARAMETERS, **{group: replace(
                        getattr(DEFAULT_PARAMETERS, group), **{field: value})})
                    with self.assertRaisesRegex(ValueError, 'positive and finite'):
                        build_51105_reference(p)

    def test_rejects_shaft_without_clearance_and_reversed_bearing_rings(self):
        for clearance in (8.0, 7.9):
            with self.subTest(clearance=clearance):
                p = replace(DEFAULT_PARAMETERS, shaft=replace(
                    DEFAULT_PARAMETERS.shaft, clearance_hole_diameter_mm=clearance))
                with self.assertRaisesRegex(ValueError, 'exceed the nominal shaft'):
                    build_608_reference(p)
        for prefix, outer in (('thrust', 42.0), ('radial', 22.0)):
            for bore in (outer, outer + 1):
                with self.subTest(bearing=prefix, bore=bore):
                    p = replace(DEFAULT_PARAMETERS, bearings=replace(
                        DEFAULT_PARAMETERS.bearings, **{prefix + '_bore_diameter_mm': bore}))
                    with self.assertRaisesRegex(ValueError, 'outer diameter must exceed its bore'):
                        build_608_reference(p)


if __name__ == "__main__":
    unittest.main()
