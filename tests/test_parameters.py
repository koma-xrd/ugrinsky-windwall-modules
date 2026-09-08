import unittest

from windwall.parameters import DEFAULT_PARAMETERS


class ParameterContractTests(unittest.TestCase):
    def test_stack_and_rotation_contract(self):
        p = DEFAULT_PARAMETERS
        self.assertEqual(p.rotor.stage_count, 7)
        self.assertEqual(p.rotor.standard_stage_count, 5)
        self.assertEqual(p.rotor.rotation_direction, "counterclockwise_from_top")
        self.assertAlmostEqual(p.rotor.stage_height_mm, 70.0)
        self.assertAlmostEqual(p.rotor.nominal_stack_height_mm, 490.0)

    def test_prototype_fit_contract(self):
        p = DEFAULT_PARAMETERS
        self.assertEqual(p.shaft.nominal_diameter_mm, 8.0)
        self.assertGreater(p.shaft.clearance_hole_diameter_mm, 8.0)
        self.assertEqual(p.bayonet.lug_count, 3)
        self.assertGreaterEqual(p.manufacturing.minimum_loaded_wall_mm, 3.0)
        self.assertGreater(p.manufacturing.nut_pocket_across_flats_mm, 13.0)


if __name__ == "__main__":
    unittest.main()
