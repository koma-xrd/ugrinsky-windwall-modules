from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class WindingToolParameters:
    minimum_diameter_mm: float = 110.0
    reference_diameter_mm: float = 127.0
    maximum_diameter_mm: float = 145.0
    rib_count: int = 6
    tape_station_count: int = 18
    tape_width_mm: float = 10.0
    tape_passage_width_mm: float = 12.0
    release_travel_mm: float = 2.0
    shaft_diameter_mm: float = 8.0
    hex_socket_across_flats_mm: float = 6.35
    platter_diameter_mm: float = 150.0
    spool_pilot_diameter_mm: float = 15.0
    spool_pilot_height_mm: float = 20.0
    print_bed_size_mm: float = 220.0


def validate_winding_tool_parameters(p: WindingToolParameters) -> None:
    if any(name.endswith('_mm') and isinstance(value, bool)
           for name, value in vars(p).items()):
        raise ValueError('Winding-tool dimensions must be numeric, not boolean')
    values = tuple(
        value for name, value in vars(p).items()
        if name.endswith('_mm')
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
    )
    if not all(isfinite(value) and value > 0 for value in values):
        raise ValueError('Winding-tool dimensions must be positive and finite')
    if not p.minimum_diameter_mm <= p.reference_diameter_mm <= p.maximum_diameter_mm:
        raise ValueError('Reference diameter must lie inside the winding range')
    if p.rib_count != 6 or p.tape_station_count != 18:
        raise ValueError('The winding head requires six ribs and 18 tape stations')
    if p.tape_passage_width_mm < p.tape_width_mm + 2:
        raise ValueError('Tape passages require 1 mm clearance on each side')
    if p.release_travel_mm < 2:
        raise ValueError('Coil release travel must be at least 2 mm')
    if p.platter_diameter_mm > p.print_bed_size_mm:
        raise ValueError('The payoff platter must fit the unsplit print bed')


DEFAULT_WINDING_TOOL_PARAMETERS = WindingToolParameters()
validate_winding_tool_parameters(DEFAULT_WINDING_TOOL_PARAMETERS)
