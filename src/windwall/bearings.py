"""Bearing reference envelopes and prototype-only printed fit coupons.

These solids record bearing catalog dimensions and candidate printed seats. They
do not certify a press fit, retain a purchased bearing, or model rolling parts.
Generator housing and top-support builders consume the references later.
"""

from dataclasses import dataclass, fields
from math import isfinite

import cadquery as cq

from windwall.parameters import DesignParameters


@dataclass(frozen=True)
class BearingReference:
    """Named, non-printable reference components for one bearing envelope."""

    designation: str
    nominal_dimensions_mm: tuple[float, float, float]
    parts: dict[str, cq.Workplane]


@dataclass(frozen=True)
class FitCoupon:
    """One printable connected body with the literal dimensions it samples."""

    bearing_designation: str
    shape: cq.Workplane
    seat_diameters_mm: tuple[float, ...]
    seat_depth_mm: float
    pilot_diameters_mm: tuple[float, ...] = ()


def _ring(outer_diameter_mm: float, inner_diameter_mm: float, height_mm: float,
          bottom_mm: float = 0.0) -> cq.Workplane:
    return (cq.Workplane("XY").circle(outer_diameter_mm / 2).circle(inner_diameter_mm / 2)
            .extrude(height_mm).translate((0, 0, bottom_mm)))


def _validate(parameters: DesignParameters) -> None:
    b, m, s = parameters.bearings, parameters.manufacturing, parameters.shaft
    if any(not isfinite(getattr(b, item.name)) or getattr(b, item.name) <= 0
           for item in fields(b)):
        raise ValueError("Bearing dimensions must be positive and finite")
    if not all(isfinite(value) and value > 0 for value in (
            s.nominal_diameter_mm, s.clearance_hole_diameter_mm,
            m.export_linear_tolerance_mm, m.export_angular_tolerance_rad)):
        raise ValueError("Shaft clearances and export tolerances must be positive and finite")
    if s.clearance_hole_diameter_mm <= s.nominal_diameter_mm:
        raise ValueError("Shaft clearance hole must exceed the nominal shaft diameter")
    if not b.thrust_bore_diameter_mm < b.thrust_outer_diameter_mm:
        raise ValueError("51105 outer diameter must exceed its bore")
    if not b.radial_bore_diameter_mm < b.radial_outer_diameter_mm:
        raise ValueError("608 outer diameter must exceed its bore")
    if b.thrust_housing_seat_diameter_mm <= b.thrust_outer_diameter_mm:
        raise ValueError("51105 printed housing seat must clear the bearing envelope")
    if b.radial_housing_seat_diameter_mm <= b.radial_outer_diameter_mm:
        raise ValueError("608 printed housing seat must clear the bearing envelope")
    if b.thrust_rotating_pilot_diameter_mm >= b.thrust_bore_diameter_mm:
        raise ValueError("51105 rotating pilot must remain below the bearing bore")


def _require_valid_part(shape: cq.Workplane, name: str) -> cq.Workplane:
    if not shape.val().isValid() or len(shape.val().Solids()) != 1:
        raise ValueError(f"{name} must be one valid connected solid")
    return shape


def build_51105_reference(parameters: DesignParameters) -> BearingReference:
    """Model the 51105 with independently placed housing and shaft washers."""
    _validate(parameters)
    b = parameters.bearings
    washer_height = 1.0
    rolling_height = b.thrust_height_mm - 2 * washer_height
    rolling_outer_diameter = b.thrust_outer_diameter_mm - 2.0
    rolling_inner_diameter = b.thrust_bore_diameter_mm + 2.0
    parts = {
        "housing_washer": _require_valid_part(
            _ring(b.thrust_outer_diameter_mm, b.thrust_bore_diameter_mm, washer_height),
            "51105 housing washer"),
        "rolling_envelope": _require_valid_part(
            _ring(rolling_outer_diameter, rolling_inner_diameter, rolling_height, washer_height),
            "51105 rolling envelope"),
        "shaft_washer": _require_valid_part(
            _ring(b.thrust_outer_diameter_mm, b.thrust_bore_diameter_mm, washer_height,
                  washer_height + rolling_height), "51105 shaft washer"),
    }
    return BearingReference("51105", b.thrust_nominal_dimensions_mm, parts)


def build_608_reference(parameters: DesignParameters) -> BearingReference:
    """Model the sealed 608 as one annular envelope, without internal components."""
    _validate(parameters)
    b = parameters.bearings
    sealed_envelope = _require_valid_part(
        _ring(b.radial_outer_diameter_mm, b.radial_bore_diameter_mm, b.radial_height_mm),
        "608 sealed envelope")
    return BearingReference("608", b.radial_nominal_dimensions_mm,
                            {"sealed_envelope": sealed_envelope})


def _candidate_diameters(nominal_diameter_mm: float, step_mm: float) -> tuple[float, float, float]:
    return (round(nominal_diameter_mm - step_mm, 4), round(nominal_diameter_mm, 4),
            round(nominal_diameter_mm + step_mm, 4))


def _stepped_coupon(seat_diameters_mm: tuple[float, float, float], seat_depth_mm: float,
                    seat_centers_mm: tuple[tuple[float, float], ...], plate_size_mm: tuple[float, float],
                    pilot_diameters_mm: tuple[float, ...] = (),
                    pilot_centers_mm: tuple[tuple[float, float], ...] = ()) -> cq.Workplane:
    plate_height_mm = seat_depth_mm + 3.0
    body = cq.Workplane("XY").box(*plate_size_mm, plate_height_mm, centered=(True, True, False))
    for center, diameter in zip(seat_centers_mm, seat_diameters_mm, strict=True):
        seat = (cq.Workplane("XY").center(*center).circle(diameter / 2).extrude(seat_depth_mm)
                .translate((0, 0, plate_height_mm - seat_depth_mm)))
        body = body.cut(seat)
    for center, diameter in zip(pilot_centers_mm, pilot_diameters_mm, strict=True):
        pilot = (cq.Workplane("XY").center(*center).circle(diameter / 2).extrude(8.0)
                 .translate((0, 0, plate_height_mm)))
        body = body.union(pilot)
    return _require_valid_part(body.clean(), "Bearing fit coupon")


def build_51105_fit_coupon(parameters: DesignParameters) -> FitCoupon:
    """Build three 51105 housing seats and three rotating-pilot gauges on one body."""
    _validate(parameters)
    b = parameters.bearings
    seat_diameters = _candidate_diameters(b.thrust_housing_seat_diameter_mm,
                                          b.coupon_diameter_step_mm)
    pilot_diameters = _candidate_diameters(b.thrust_rotating_pilot_diameter_mm,
                                           b.coupon_diameter_step_mm)
    shape = _stepped_coupon(seat_diameters, b.thrust_housing_seat_depth_mm,
                            ((-55.0, -28.0), (0.0, -28.0), (55.0, -28.0)), (170.0, 110.0),
                            pilot_diameters, ((-55.0, 28.0), (0.0, 28.0), (55.0, 28.0)))
    return FitCoupon("51105", shape, seat_diameters, b.thrust_housing_seat_depth_mm,
                     pilot_diameters)


def build_608_fit_coupon(parameters: DesignParameters) -> FitCoupon:
    """Build three 608 housing-seat diameters on one connected printable plate."""
    _validate(parameters)
    b = parameters.bearings
    seat_diameters = _candidate_diameters(b.radial_housing_seat_diameter_mm,
                                          b.coupon_diameter_step_mm)
    shape = _stepped_coupon(seat_diameters, b.radial_housing_seat_depth_mm,
                            ((-30.0, 0.0), (0.0, 0.0), (30.0, 0.0)), (100.0, 70.0))
    return FitCoupon("608", shape, seat_diameters, b.radial_housing_seat_depth_mm)


def bearing_fit_manifest(parameters: DesignParameters) -> dict:
    """Return JSON-safe V5 fit-coupon metadata; physical fit remains unapproved."""
    _validate(parameters)
    thrust = build_51105_fit_coupon(parameters)
    radial = build_608_fit_coupon(parameters)
    return {
        "physically_calibrated": False,
        "shaft_clearance_hole_diameter_mm": parameters.shaft.clearance_hole_diameter_mm,
        "export_tolerances": {
            "linear_mm": parameters.manufacturing.export_linear_tolerance_mm,
            "angular_rad": parameters.manufacturing.export_angular_tolerance_rad,
        },
        "51105": {
            "nominal_dimensions_mm": list(build_51105_reference(parameters).nominal_dimensions_mm),
            "seat_diameters_mm": list(thrust.seat_diameters_mm),
            "seat_depth_mm": thrust.seat_depth_mm,
            "pilot_diameters_mm": list(thrust.pilot_diameters_mm),
        },
        "608": {
            "nominal_dimensions_mm": list(build_608_reference(parameters).nominal_dimensions_mm),
            "seat_diameters_mm": list(radial.seat_diameters_mm),
            "seat_depth_mm": radial.seat_depth_mm,
        },
    }
