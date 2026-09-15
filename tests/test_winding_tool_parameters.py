import unittest
from dataclasses import replace
from math import inf, nan

from windwall.parameters import DEFAULT_PARAMETERS
from windwall.winding_tool_parameters import (
    DEFAULT_WINDING_TOOL_PARAMETERS, validate_winding_tool_parameters)


class WindingToolParameterTests(unittest.TestCase):
    def test_defaults_match_approved_design(self):
        p = DEFAULT_WINDING_TOOL_PARAMETERS
        self.assertEqual((p.minimum_diameter_mm, p.reference_diameter_mm,
                          p.maximum_diameter_mm), (110.0, 127.0, 145.0))
        self.assertEqual((p.rib_count, p.tape_station_count), (6, 18))
        self.assertEqual((p.tape_width_mm, p.tape_passage_width_mm), (10.0, 12.0))
        self.assertEqual((p.platter_diameter_mm, p.spool_pilot_diameter_mm,
                          p.spool_pilot_height_mm), (150.0, 15.0, 20.0))
        self.assertEqual((p.shaft_diameter_mm, p.hex_socket_across_flats_mm), (8.0, 6.35))
        self.assertIsNot(p, DEFAULT_PARAMETERS)

    def test_validation_rejects_bad_ranges_counts_and_clearances(self):
        p = DEFAULT_WINDING_TOOL_PARAMETERS
        invalid = (
            replace(p, minimum_diameter_mm=146),
            replace(p, reference_diameter_mm=109),
            replace(p, rib_count=5),
            replace(p, tape_station_count=17),
            replace(p, tape_passage_width_mm=9.9),
            replace(p, release_travel_mm=1.9),
            replace(p, platter_diameter_mm=221),
        )
        for candidate in invalid:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                validate_winding_tool_parameters(candidate)

    def test_validation_rejects_integer_and_non_finite_dimensions(self):
        p = DEFAULT_WINDING_TOOL_PARAMETERS
        invalid = (
            replace(p, shaft_diameter_mm=0),
            replace(p, platter_diameter_mm=-1),
            replace(p, spool_pilot_height_mm=nan),
            replace(p, tape_width_mm=inf),
        )
        for candidate in invalid:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                validate_winding_tool_parameters(candidate)
