from dataclasses import dataclass
from math import isfinite
from numbers import Integral, Real


_PRINT_BED_ENVELOPE_MM = 220.0


@dataclass(frozen=True)
class WindingToolParameters:
    minimum_diameter_mm: float = 100.0
    maximum_diameter_mm: float = 200.0
    diameter_step_mm: float = 10.0
    spoke_count: int = 6
    shoe_pin_count: int = 2
    tape_station_count: int = 18
    tape_clearance_mm: float = 12.0
    release_clearance_mm: float = 2.0
    platter_diameter_mm: float = 150.0
    spool_pilot_diameter_mm: float = 15.0
    spool_pilot_height_mm: float = 20.0
    print_bed_mm: float = _PRINT_BED_ENVELOPE_MM


def validate_winding_tool_parameters(p: WindingToolParameters) -> None:
    for name, value in vars(p).items():
        if name.endswith('_mm'):
            if isinstance(value, bool) or not isinstance(value, Real):
                raise ValueError(f'{name} must be a numeric dimension, not {type(value).__name__}')
            if not isfinite(value) or value <= 0:
                raise ValueError(f'{name} must be positive and finite')
        elif name.endswith('_count'):
            if isinstance(value, bool) or not isinstance(value, Integral):
                raise ValueError(f'{name} must be an integer count')
    if p.maximum_diameter_mm < p.minimum_diameter_mm:
        raise ValueError('Maximum diameter must not be smaller than minimum diameter')
    diameter_steps = (p.maximum_diameter_mm - p.minimum_diameter_mm) / p.diameter_step_mm
    if diameter_steps != round(diameter_steps):
        raise ValueError('Diameter range must be exactly divisible by the diameter step')
    if (p.spoke_count, p.shoe_pin_count, p.tape_station_count) != (6, 2, 18):
        raise ValueError('The coil wheel requires six spokes, two shoe pins, and 18 tape stations')
    bed_limit_mm = min(p.print_bed_mm, _PRINT_BED_ENVELOPE_MM)
    if p.maximum_diameter_mm > bed_limit_mm:
        raise ValueError('The maximum winding diameter must fit the 220 mm print-bed envelope')
    if p.platter_diameter_mm > bed_limit_mm:
        raise ValueError('The payoff platter must fit the 220 mm print-bed envelope')


def diameter_settings_mm(p: WindingToolParameters) -> tuple[float, ...]:
    validate_winding_tool_parameters(p)
    setting_count = round((p.maximum_diameter_mm - p.minimum_diameter_mm) / p.diameter_step_mm)
    return tuple(float(p.minimum_diameter_mm + index * p.diameter_step_mm)
                 for index in range(setting_count + 1))


DEFAULT_WINDING_TOOL_PARAMETERS = WindingToolParameters()
validate_winding_tool_parameters(DEFAULT_WINDING_TOOL_PARAMETERS)
