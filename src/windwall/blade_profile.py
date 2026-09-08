"""Clean Ugrinsky circular sections and a twisted shared stage.

The external STL is measurement evidence only and is never imported here.
Each blade is a tangent pair of constant-thickness circular arcs. A 180-degree
copy forms the complementary blade, and a local cylindrical hub connects them.
The 60-degree section twist preserves the reference's aerodynamic handedness;
later module-specific shaft holes, end fittings, and closures are separate.
"""

from math import cos, isfinite, radians, sin

import cadquery as cq

from windwall.parameters import BladeParameters, DesignParameters


def _validate(parameters: DesignParameters) -> None:
    blade = parameters.blade
    dimensions = (blade.rotor_radius_mm, blade.wall_thickness_mm,
                  blade.small_arc_radius_mm, blade.large_arc_radius_mm,
                  blade.hub_blend_radius_mm, parameters.rotor.stage_height_mm)
    if any(not isfinite(value) or value <= 0 for value in dimensions):
        raise ValueError("Blade radii, wall thickness, and stage height must be positive and finite")
    if blade.wall_thickness_mm >= 2 * blade.small_arc_radius_mm:
        raise ValueError("Blade wall consumes the small arc radius")
    if not 0 < blade.large_arc_sweep_deg < 180 or not isfinite(blade.twist_deg):
        raise ValueError("Blade sweep must lie between 0 and 180 degrees and twist must be finite")
    if not isinstance(blade.loft_section_count, int) or blade.loft_section_count < 3:
        raise ValueError("A twisted stage needs at least three loft sections")
    small = blade.small_arc_center_xy_mm
    large = blade.large_arc_center_xy_mm
    transition = blade.tangent_transition_xy_mm
    for point in (small, large, transition):
        if len(point) != 2 or any(not isfinite(value) for value in point):
            raise ValueError('Blade centers and transition must be finite XY pairs')
        if abs(point[1]) > 1e-7:
            raise ValueError('Blade centers and transition must use the canonical shaft-frame X axis')
    if small[0] <= 0 or large[0] >= 0 or transition[0] <= 0:
        raise ValueError('Blade centers must retain the canonical small-positive/large-negative frame')
    expected = ((small[0] - blade.small_arc_radius_mm, small[1]),
                (large[0] + blade.large_arc_radius_mm, large[1]))
    if any(abs(a-b) > 1e-7 for point in expected for a,b in zip(point, transition)):
        raise ValueError("Arc centers and radii must meet at the configured tangent transition")
    minimum_connection = abs(transition[0]) - blade.wall_thickness_mm / 2
    if not minimum_connection < blade.hub_blend_radius_mm <= 20.0:
        raise ValueError("Hub must connect both blades and stay inside the central 20 mm radius")
    if blade.hub_blend_radius_mm > minimum_connection + parameters.manufacturing.minimum_loaded_wall_mm:
        raise ValueError("Hub reinforcement exceeds one loaded-wall thickness beyond blade contact")
    if abs(small[0] + blade.small_arc_radius_mm + blade.wall_thickness_mm/2 - blade.rotor_radius_mm) > 1e-7:
        raise ValueError("Rotor radius must match the outer small-arc tip")


def _point(center: tuple[float, float], radius: float, angle_deg: float) -> tuple[float, float]:
    angle = radians(angle_deg)
    return center[0] + radius * cos(angle), center[1] + radius * sin(angle)


def _blade_wire(blade: BladeParameters) -> cq.Wire:
    small, large = blade.small_arc_center_xy_mm, blade.large_arc_center_xy_mm
    half_wall = blade.wall_thickness_mm / 2
    small_outer, small_inner = blade.small_arc_radius_mm + half_wall, blade.small_arc_radius_mm - half_wall
    large_outer, large_inner = blade.large_arc_radius_mm + half_wall, blade.large_arc_radius_mm - half_wall
    sweep = blade.large_arc_sweep_deg
    # Opposite curvature switches the outer/inner offset at the tangent junction.
    return (cq.Workplane("XY")
            .moveTo(*_point(small, small_outer, 0))
            .threePointArc(_point(small, small_outer, 90), _point(small, small_outer, 180))
            .threePointArc(_point(large, large_inner, -sweep/2), _point(large, large_inner, -sweep))
            .lineTo(*_point(large, large_outer, -sweep))
            .threePointArc(_point(large, large_outer, -sweep/2), _point(large, large_outer, 0))
            .threePointArc(_point(small, small_inner, 90), _point(small, small_inner, 0))
            .close().val())


def build_blade_profile(parameters: DesignParameters) -> cq.Wire:
    """Return the closed bottom-section outline, including the local hub."""
    _validate(parameters)
    first = cq.Face.makeFromWires(_blade_wire(parameters.blade))
    second = first.rotate((0, 0, 0), (0, 0, 1), 180)
    hub = cq.Face.makeFromWires(cq.Workplane("XY").circle(parameters.blade.hub_blend_radius_mm).val())
    face = hub.fuse(first, second).clean()
    if not face.isValid() or len(face.Faces()) != 1:
        raise ValueError('Blade profile must be one valid connected planar face')
    return face.Faces()[0].outerWire()


def build_blade_stage(parameters: DesignParameters) -> cq.Workplane:
    """Loft analytic sections through the measured twist and join a central hub."""
    _validate(parameters)
    blade = parameters.blade
    height = parameters.rotor.stage_height_mm
    profile = _blade_wire(blade)
    sections = []
    for index in range(blade.loft_section_count):
        fraction = index / (blade.loft_section_count - 1)
        section = profile.rotate((0, 0, 0), (0, 0, 1), blade.twist_deg * fraction)
        sections.append(section.translate((0, 0, height * fraction)))
    first = cq.Solid.makeLoft(sections)
    second = first.rotate((0, 0, 0), (0, 0, 1), 180)
    hub = cq.Workplane("XY").circle(blade.hub_blend_radius_mm).extrude(height).val()
    stage = hub.fuse(first, second).clean()
    if not stage.isValid() or len(stage.Solids()) != 1:
        raise ValueError('Blade stage must be one valid connected solid')
    return cq.Workplane(obj=stage)
