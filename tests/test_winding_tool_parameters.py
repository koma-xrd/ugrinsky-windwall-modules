import unittest
from dataclasses import replace
from math import inf, nan

from windwall.winding_tool_parameters import (
    DEFAULT_WINDING_TOOL_PARAMETERS,
    diameter_settings_mm,
    validate_winding_tool_parameters,
)


class WindingToolParameterTests(unittest.TestCase):
    def test_defaults_expose_the_approved_simple_coil_wheel_contract(self):
        """Catches restoring the superseded cam/rib winder contract."""
        p = DEFAULT_WINDING_TOOL_PARAMETERS

        self.assertEqual(
            diameter_settings_mm(p),
            (100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0,
             180.0, 190.0, 200.0),
        )
        self.assertEqual(
            (p.minimum_diameter_mm, p.maximum_diameter_mm, p.diameter_step_mm),
            (100.0, 200.0, 10.0),
        )
        self.assertEqual((p.spoke_count, p.shoe_tongue_count, p.tape_station_count), (6, 2, 18))
        self.assertEqual((p.tape_clearance_mm, p.release_clearance_mm), (12.0, 2.0))
        self.assertEqual(
            (p.platter_diameter_mm, p.spool_pilot_diameter_mm, p.spool_pilot_height_mm,
             p.print_bed_mm),
            (150.0, 15.0, 20.0, 220.0),
        )
        self.assertFalse(hasattr(p, 'cam_track_eccentricity_mm'))
        self.assertFalse(hasattr(p, 'brake_max_travel_mm'))
        self.assertIsNone(validate_winding_tool_parameters(p))

    def test_validation_rejects_invalid_dimension_values(self):
        """Catches accepting invalid dimensions into the CAD contract."""
        p = DEFAULT_WINDING_TOOL_PARAMETERS
        invalid_values = ('100', None, True, 0, -1, nan, inf)

        for field in vars(p):
            if field.endswith('_mm'):
                for value in invalid_values:
                    with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                        validate_winding_tool_parameters(replace(p, **{field: value}))

    def test_validation_rejects_float_valued_counts(self):
        """Catches counts silently accepting numeric values that cannot be array sizes."""
        p = DEFAULT_WINDING_TOOL_PARAMETERS

        for field, value in (('spoke_count', 6.0), ('shoe_tongue_count', 2.0),
                             ('tape_station_count', 18.0), ('spoke_count', True),
                             ('shoe_tongue_count', None), ('tape_station_count', '18')):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate_winding_tool_parameters(replace(p, **{field: value}))

    def test_validation_rejects_non_divisible_ranges_and_wrong_fixed_counts(self):
        """Catches settings that cannot produce the approved matched shoe positions."""
        p = DEFAULT_WINDING_TOOL_PARAMETERS
        invalid_parameters = (
            replace(p, maximum_diameter_mm=195.0),
            replace(p, spoke_count=5),
            replace(p, shoe_tongue_count=1),
            replace(p, tape_station_count=17),
        )

        for candidate in invalid_parameters:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                validate_winding_tool_parameters(candidate)

    def test_validation_rejects_an_oversized_winding_even_if_the_parameter_bed_is_larger(self):
        """Catches treating a user value as permission to exceed the 220 mm printer bed."""
        p = DEFAULT_WINDING_TOOL_PARAMETERS

        with self.assertRaises(ValueError):
            validate_winding_tool_parameters(replace(
                p, maximum_diameter_mm=230.0, print_bed_mm=230.0))
