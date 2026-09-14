"""Stationary V5 cup, removable winding cassette, and 51105-bearing cover.

All bodies use cup-bottom Z=0; the later generator assembly translates this
package as a unit. The cassette provides open rounded islands for an
experimental serpentine winding; the winding solid is not individual wires.
The thin cover diaphragm occupies part of the upper magnetic gap; callers must
measure magnet-to-coil gaps independently. Fits, strength, and the open side
cable outlet remain unvalidated, non-waterproof prototype features.
"""

from dataclasses import dataclass
from math import cos, isfinite, pi, sin, sqrt

import cadquery as cq

from windwall.bearings import build_51105_reference
from windwall.parameters import DesignParameters


@dataclass(frozen=True)
class HousingDimensions:
    """V5-only structure; legacy V4.3 generator parameters remain unchanged."""

    shell_radius_mm: float = 65.0
    cavity_radius_mm: float = 60.5
    floor_mm: float = 3.0
    cassette_bottom_mm: float = 27.0
    shoulder_height_mm: float = 3.0
    radial_clearance_mm: float = 0.35
    cover_clearance_mm: float = 0.15
    diaphragm_mm: float = 1.0
    cover_rim_mm: float = 3.0
    fastener_radius_mm: float = 69.0
    fastener_boss_radius_mm: float = 6.0
    m4_clearance_diameter_mm: float = 4.4
    m4_nut_pocket_flats_mm: float = 7.3
    m4_nut_pocket_depth_mm: float = 3.4
    cable_center_above_cassette_bottom_mm: float = 6.0
    cable_boss_radius_mm: float = 6.0


@dataclass(frozen=True)
class CoverFastener:
    """Installed M4 hardware and a top-access driver clearance reference."""

    axis_xy_mm: tuple[float, float]
    screw: cq.Workplane
    nut: cq.Workplane
    driver_access: cq.Workplane


@dataclass(frozen=True)
class BottomMountTab:
    """A fused bottom tab and its vertical wood-screw access envelope."""

    axis_xy_mm: tuple[float, float]
    shape: cq.Workplane
    screw_access: cq.Workplane


@dataclass(frozen=True)
class CoilFitCoupon:
    """Three curved female pilot segments and a matching male arc on one plate.

    Cut the male arc free flush with the support plate before trial fitting.
    """

    shape: cq.Workplane
    radial_clearances_mm: tuple[float, float, float]
    cassette_diameter_mm: float
    release_instruction: str


@dataclass(frozen=True)
class GeneratorHousingParts:
    housing: cq.Workplane
    coil_cassette: cq.Workplane
    cover: cq.Workplane
    housing_washer: cq.Workplane
    bottom_mount_tabs: tuple[BottomMountTab, ...]
    cover_fasteners: tuple[CoverFastener, ...]
    winding_volume: cq.Workplane
    cable_passage: cq.Workplane
    rotating_keepout: cq.Workplane
    metadata: dict


def _ring(outer: float, inner: float, bottom: float, height: float) -> cq.Workplane:
    return (cq.Workplane('XY').circle(outer).circle(inner).extrude(height)
            .translate((0, 0, bottom)))


def _cylinder(radius: float, bottom: float, height: float) -> cq.Workplane:
    return cq.Workplane('XY').circle(radius).extrude(height).translate((0, 0, bottom))


def _hex(flats: float, bottom: float, height: float) -> cq.Workplane:
    return (cq.Workplane('XY').polygon(6, 2 * flats / sqrt(3)).extrude(height)
            .translate((0, 0, bottom)))


def _valid(shape: cq.Workplane, name: str) -> cq.Workplane:
    shape = shape.clean()
    if not shape.val().isValid() or len(shape.val().Solids()) != 1:
        raise ValueError(f'{name} must be one valid connected solid')
    return shape


def _layout(p: DesignParameters) -> tuple[HousingDimensions, float, float, float]:
    d = HousingDimensions()
    g = p.generator
    if not all(isfinite(v) and v > 0 for v in (
            g.coil_former_diameter_mm, g.coil_former_height_mm,
            p.bearings.thrust_housing_seat_diameter_mm,
            p.bearings.thrust_housing_seat_depth_mm)):
        raise ValueError('Housing and cassette dimensions must be positive and finite')
    radius = g.coil_former_diameter_mm / 2
    if radius + d.radial_clearance_mm >= d.cavity_radius_mm or radius < 55:
        raise ValueError('The cassette must fit the 130 mm shell and its support shoulder')
    minimum_cassette_height = (d.cable_center_above_cassette_bottom_mm
                              + d.cable_boss_radius_mm - d.cover_clearance_mm)
    if g.coil_former_height_mm < minimum_cassette_height:
        raise ValueError(f'The cassette height must be at least {minimum_cassette_height:g} mm '
                         'to keep the cable boss below the cover')
    if p.bearings.thrust_housing_seat_diameter_mm / 2 + 3 >= 25:
        raise ValueError('The bearing boss must clear the cassette central bore')
    top = d.cassette_bottom_mm + g.coil_former_height_mm
    return d, radius, top, top + d.cover_clearance_mm


def _fastener_axes(d: HousingDimensions) -> tuple[tuple[float, float], ...]:
    return tuple((d.fastener_radius_mm * cos(i * pi / 2),
                  d.fastener_radius_mm * sin(i * pi / 2)) for i in range(4))


def _cable_passage(d: HousingDimensions) -> cq.Workplane:
    return (cq.Workplane('YZ').circle(3).extrude(24)
            .translate((54, 0, d.cassette_bottom_mm + d.cable_center_above_cassette_bottom_mm))
            .rotate((0, 0, 0), (0, 0, 1), 45))


def _key(d: HousingDimensions, radius: float, height: float) -> cq.Workplane:
    return (cq.Workplane('XY').box(2, 6, height - 2, centered=(False, True, False))
            .translate((-radius - 1, 0, d.cassette_bottom_mm + 1)))


def _serpentine_guides(d: HousingDimensions, top: float) -> cq.Workplane:
    """Return 18 radial capsules matching the reference former's guide layout."""
    pitch_radius = 44.5
    half_straight = 3.5
    guide_radius = 4.0
    height = top - d.cassette_bottom_mm
    capsule = _cylinder(guide_radius, d.cassette_bottom_mm, height).translate(
        (pitch_radius - half_straight, 0, 0))
    capsule = capsule.union(
        _cylinder(guide_radius, d.cassette_bottom_mm, height).translate(
            (pitch_radius + half_straight, 0, 0)))
    capsule = capsule.union(
        cq.Workplane('XY').box(2 * half_straight, 2 * guide_radius, height,
                               centered=(True, True, False))
        .translate((pitch_radius, 0, d.cassette_bottom_mm)))
    guides = capsule
    for index in range(1, 18):
        guides = guides.union(capsule.rotate((0, 0, 0), (0, 0, 1), 20 * index))
    return guides


def build_coil_cassette(p: DesignParameters) -> cq.Workplane:
    """Open-top 18-island serpentine former with key and cable passage."""
    d, radius, top, _ = _layout(p)
    bottom = d.cassette_bottom_mm
    body = _ring(radius, 25, bottom, 1)
    body = body.union(_ring(radius, radius - 3, bottom, top - bottom))
    body = body.union(_ring(28, 25, bottom, top - bottom))
    body = body.union(_serpentine_guides(d, top))
    body = body.union(_key(d, radius, top - bottom)).cut(_cable_passage(d))
    return _valid(body, 'Coil cassette')


def build_generator_cover(p: DesignParameters) -> cq.Workplane:
    """M4-secured flat-bottom diaphragm, rim, and top-open 51105 load seat."""
    d, radius, _, bottom = _layout(p)
    b = p.bearings
    body = _ring(d.shell_radius_mm, 12.5, bottom, d.diaphragm_mm)
    body = body.union(_ring(d.shell_radius_mm, radius, bottom, d.cover_rim_mm))
    seat_floor = bottom + d.diaphragm_mm
    boss_radius = b.thrust_housing_seat_diameter_mm / 2 + 3
    body = body.union(_ring(boss_radius, b.thrust_housing_seat_diameter_mm / 2,
                            seat_floor, b.thrust_housing_seat_depth_mm))
    for x, y in _fastener_axes(d):
        boss = _cylinder(d.fastener_boss_radius_mm, bottom, d.cover_rim_mm)
        bore = _cylinder(d.m4_clearance_diameter_mm / 2, bottom - 1, d.cover_rim_mm + 2)
        body = body.union(boss.translate((x, y, 0))).cut(bore.translate((x, y, 0)))
    return _valid(body, 'Generator cover')


def build_generator_housing(p: DesignParameters) -> GeneratorHousingParts:
    """Return placed stationary print bodies, hardware, and auditable keep-outs."""
    d, radius, top, cover_bottom = _layout(p)
    body = _cylinder(d.shell_radius_mm, 0, d.floor_mm)
    body = body.union(_ring(d.shell_radius_mm, d.cavity_radius_mm,
                            d.floor_mm, cover_bottom - d.floor_mm))
    body = body.union(_ring(d.shell_radius_mm, radius - 2.5,
                            d.cassette_bottom_mm - d.shoulder_height_mm,
                            d.shoulder_height_mm))
    body = body.union(_ring(d.shell_radius_mm, radius + d.radial_clearance_mm,
                            d.cassette_bottom_mm, cover_bottom - d.cassette_bottom_mm))
    key_slot = (cq.Workplane('XY').box(3, 6.7, cover_bottom - d.cassette_bottom_mm + 1,
                                     centered=(False, True, False))
                .translate((-radius - 1.35, 0, d.cassette_bottom_mm)))
    body = body.cut(key_slot)
    tabs = []
    for angle in (0, 90, 180, 270):
        tab = (cq.Workplane('XY').box(28, 18, 5, centered=(False, True, False))
               .translate((62, 0, 0)))
        # The larger driver envelope starts above the tab, preserving its head seat.
        bore = _cylinder(2.5, -1, 7).translate((83, 0, 0))
        tab = tab.cut(bore)
        access = bore.union(_cylinder(5, 5, cover_bottom + 20).translate((83, 0, 0)))
        tab = tab.rotate((0, 0, 0), (0, 0, 1), angle)
        access = access.rotate((0, 0, 0), (0, 0, 1), angle)
        axis = (83 * cos(angle * pi / 180), 83 * sin(angle * pi / 180))
        tabs.append(BottomMountTab(axis, tab, access))
        body = body.union(tab)
    fasteners = []
    for x, y in _fastener_axes(d):
        body = body.union(_cylinder(d.fastener_boss_radius_mm, 0, cover_bottom)
                          .translate((x, y, 0)))
        body = body.cut(_cylinder(d.m4_clearance_diameter_mm / 2, -1, cover_bottom + 2)
                        .translate((x, y, 0)))
        body = body.cut(_hex(d.m4_nut_pocket_flats_mm, -1,
                             d.m4_nut_pocket_depth_mm + 1).translate((x, y, 0)))
        head_bottom = cover_bottom + d.cover_rim_mm
        screw = _cylinder(2, 0.2, head_bottom - 0.2)
        screw = screw.union(_cylinder(3.5, head_bottom, 4)).translate((x, y, 0))
        # Nut reference has a through bore; screw and nut do not occupy the same volume.
        nut = _hex(7, 0.1, 3.2).cut(_cylinder(2.1, 0, 3.4)).translate((x, y, 0))
        driver = _cylinder(4.3, head_bottom + 4, 20).translate((x, y, 0))
        fasteners.append(CoverFastener((x, y), screw, nut, driver))
    cable_z = d.cassette_bottom_mm + d.cable_center_above_cassette_bottom_mm
    boss = (cq.Workplane('YZ').circle(d.cable_boss_radius_mm).extrude(12).translate((63, 0, cable_z))
            .rotate((0, 0, 0), (0, 0, 1), 45))
    passage = _cable_passage(d)
    body = _valid(body.union(boss).cut(passage), 'Generator housing')
    seat_floor = cover_bottom + d.diaphragm_mm
    washer = build_51105_reference(p).parts['housing_washer'].translate((0, 0, seat_floor))
    winding = (_ring(radius - 3, 28, d.cassette_bottom_mm + 1,
                     top - d.cassette_bottom_mm - 1)
               .cut(_serpentine_guides(d, top)))
    metadata = {
        'role': 'stationary', 'waterproof': False, 'physically_calibrated': False,
        'cable_outlet': 'Open side cable passage; prototype, non-waterproof',
        'shell_outer_diameter_mm': 130.0, 'cavity_diameter_mm': 121.0,
        'floor_top_z_mm': d.floor_mm, 'cassette_bottom_z_mm': d.cassette_bottom_mm,
        'cassette_top_z_mm': top, 'coil_active_bottom_z_mm': d.cassette_bottom_mm + 1,
        'coil_active_top_z_mm': top, 'cover_bottom_z_mm': cover_bottom,
        'cover_diaphragm_top_z_mm': seat_floor,
        'bearing_seat_floor_z_mm': seat_floor,
        'bearing_seat_diameter_mm': p.bearings.thrust_housing_seat_diameter_mm,
        'bearing_seat_depth_mm': p.bearings.thrust_housing_seat_depth_mm,
        'rotating_keepout_diameter_mm': 120.0,
        'rotating_keepout_bottom_z_mm': 4.0, 'rotating_keepout_top_z_mm': 24.0,
        'cassette_radius_mm': radius, 'pilot_radius_mm': radius + d.radial_clearance_mm,
        'cover_fastener_nominal_diameter_mm': 4.0,
        'cover_fastener_clearance_diameter_mm': d.m4_clearance_diameter_mm,
        'nut_insertion': 'From underside before attaching cup to frame',
        'air_gap_reference': 'Magnet face to coil active face; diaphragm consumes part of upper gap',
        'serpentine_guide_count': 18,
        'serpentine_guide_pitch_radius_mm': 44.5,
        'serpentine_guide_size_mm': [15.0, 8.0],
        'serpentine_winding': 'Open experimental path around rounded guide islands',
    }
    return GeneratorHousingParts(body, build_coil_cassette(p), build_generator_cover(p),
                                 washer, tuple(tabs), tuple(fasteners), winding, passage,
                                 _cylinder(60, 4, 20), metadata)


def audit_coil_retention(parts: GeneratorHousingParts) -> dict:
    """Measure interference after small prohibited motions, never at nominal fit.

    Positive contact volumes are 0.1 mm downward and 1 degree twist probes.
    Radial clearance and upward travel describe the as-designed pilot and cover;
    neither the probes nor nominal CAD clearances certify a physical printed fit.
    """
    cassette = parts.coil_cassette
    downward = cassette.translate((0, 0, -0.1))
    twisted = cassette.rotate((0, 0, 0), (0, 0, 1), 1)
    return {
        'downward_support_contact_mm3': parts.housing.intersect(downward).val().Volume(),
        'radial_clearance_mm': round(parts.metadata['pilot_radius_mm'] -
                                     parts.metadata['cassette_radius_mm'], 6),
        'anti_rotation_contact_mm3': parts.housing.intersect(twisted).val().Volume(),
        'upward_cover_clearance_mm': round(parts.metadata['cover_bottom_z_mm'] -
                                           cassette.val().BoundingBox().zmax, 6),
        'upward_stop_contact_mm3': parts.cover.intersect(
            cassette.translate((0, 0, 0.25))).val().Volume(),
        'nominal_interference_mm3': parts.housing.intersect(cassette).val().Volume(),
    }


def build_coil_fit_coupon(p: DesignParameters) -> CoilFitCoupon:
    """Print three pilot arcs and a releasable cassette arc at full curvature."""
    _, radius, _, _ = _layout(p)
    clearances = (0.30, 0.35, 0.40)
    plate = cq.Workplane('XY').box(94, 22, 2, centered=(True, True, False))
    clip = (cq.Workplane('XY').box(18, 8, 6, centered=(True, True, False))
            .translate((0, radius + 2, 2)))
    for x, clearance in zip((-34, -11, 12), clearances, strict=True):
        arc = _ring(radius + clearance + 3, radius + clearance, 2, 5).intersect(clip)
        plate = plate.union(arc.translate((x, -radius - 2, 0)))
    male = _ring(radius, radius - 3, 2, 5).intersect(
        cq.Workplane('XY').box(18, 8, 6, centered=(True, True, False))
        .translate((0, radius - 2, 2)))
    plate = plate.union(male.translate((35, -radius + 2, 0)))
    return CoilFitCoupon(_valid(plate, 'Coil fit coupon'), clearances, 2 * radius,
                         'Cut the male arc free flush with the plate before fitting')
