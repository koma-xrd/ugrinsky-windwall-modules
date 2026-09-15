"""Stationary overhead 608 plate in the locked rotor's global shaft frame.

The plate is screwed upward into an existing wood frame; that frame closes
the top-open seat. All shapes use the Task-3 frame (Base blade bottom z=0).
Only ``shape`` is printable. The bearing, screws, wood and longer M8 rod are
nominal references, not verified purchased hardware or structural approvals.
The sealed 608 envelope represents radial guidance without an axial clamp;
the lower 51105 remains the intended primary axial support. No guide sleeve
is added. The main rotor assembly must adopt the exposed longer shaft before
this support can be integrated; this module does not change its ownership.
"""

from dataclasses import dataclass
from math import isfinite

import cadquery as cq

from windwall.bearings import build_608_reference
from windwall.generator import intersection_volume, lower_magnet_face_z_mm
from windwall.parameters import DesignParameters


@dataclass(frozen=True)
class TopSupport:
    """Installed plate and separate hardware envelopes, all in millimetres.

    Axial float is a clearance budget of +/-1 mm, not permission to lift the
    lower thrust bearing off its seat. Bearing seat play is a separate 0.2 mm.
    The required shaft reference preserves any already longer configured rod.
    """

    shape: cq.Workplane
    bearing: cq.Workplane
    wood_frame_reference: cq.Workplane
    required_shaft_reference: cq.Workplane
    wood_screws: tuple[cq.Workplane, ...]
    wood_screw_axes: tuple[tuple[float, float], ...]
    plate_size_mm: tuple[float, float, float]
    bearing_seat_diameter_mm: float
    bearing_seat_depth_mm: float
    bottom_shoulder_mm: float
    plate_bottom_z_mm: float
    required_shaft_tip_z_mm: float
    required_shaft_extension_mm: float
    axial_float_mm: float = 1.0


def _cylinder(radius: float, bottom: float, height: float) -> cq.Workplane:
    return cq.Workplane('XY').circle(radius).extrude(height).translate((0, 0, bottom))


def build_top_support(p: DesignParameters) -> TopSupport:
    """Build an 80x50x12 plate 2 mm above the highest Top or clamp face.

    Top's face is the nominal stack height; the washer sits on its flat upper
    plate and the nut sits on the washer, as in assembly.py. A recessed clamp
    can end below Top, so all three upper faces determine the safe height.
    The screws have 4 mm shanks, 40 mm overall envelopes and provisional
    8 mm/90-degree heads.
    Plate holes are 4.5 mm with 8.5 mm/90-degree bottom countersinks. Actual
    screw heads and wood pilot/engagement requirements must be checked on site.
    The 100x70x30 wood block is only a local existing-frame closure reference.
    """
    reference = build_608_reference(p)
    b, m = p.bearings, p.manufacturing
    required_positive = (p.rotor.stage_height_mm,
                         p.generator.clamp_washer_thickness_mm, m.nut_pocket_depth_mm,
                         p.closure.rod_projection_mm, p.closure.shaft_bottom_projection_mm,
                         m.minimum_loaded_wall_mm)
    if any(not isfinite(value) or value <= 0 for value in required_positive):
        raise ValueError('Top support interface dimensions must be positive and finite')
    if (not isfinite(p.modules.washer_seat_depth_mm)
            or p.modules.washer_seat_depth_mm < 0):
        raise ValueError('Top washer seat depth must be finite and nonnegative')
    if (type(p.rotor.stage_count) is not int or type(p.rotor.standard_stage_count) is not int
            or (p.rotor.stage_count, p.rotor.standard_stage_count) != (7, 5)):
        raise ValueError('Top support requires the seven-stage rotor interface')
    if p.shaft.nominal_diameter_mm != b.radial_bore_diameter_mm:
        raise ValueError('Radial guide requires the nominal M8 shaft to match the 608 bore')
    if not p.shaft.clearance_hole_diameter_mm < b.radial_outer_diameter_mm:
        raise ValueError('Shaft passage must retain a bearing shoulder')
    shoulder = 12.0 - b.radial_housing_seat_depth_mm
    if shoulder < max(3.0, m.minimum_loaded_wall_mm):
        raise ValueError('608 seat must retain at least 3 mm of bottom shoulder')
    if b.radial_housing_seat_depth_mm <= b.radial_height_mm:
        raise ValueError('608 seat must provide positive axial play below the wood frame')
    if b.radial_housing_seat_diameter_mm / 2 + m.minimum_loaded_wall_mm >= 25:
        raise ValueError('608 seat must retain the side wall of the support plate')

    module_top = p.rotor.nominal_stack_height_mm
    washer_top = (module_top - p.modules.washer_seat_depth_mm
                  + p.generator.clamp_washer_thickness_mm)
    nut_top = washer_top + m.nut_pocket_depth_mm
    bottom = max(module_top, washer_top, nut_top) + 2.0
    floor = bottom + shoulder
    frame_bottom = bottom + 12.0
    # Retain full engagement even with the bearing against the wood closure
    # and the shaft at the downward end of its independent float budget.
    required_tip = frame_bottom + 1.0
    existing_tip = nut_top + p.closure.rod_projection_mm
    shaft_bottom = (lower_magnet_face_z_mm(p) - p.generator.carrier_height_mm
                    - p.closure.shaft_bottom_projection_mm)
    shaft_tip = max(required_tip, existing_tip)
    if not isfinite(shaft_bottom) or shaft_bottom >= bottom:
        raise ValueError('Generator shaft bottom must be finite and below the top support')

    plate = (cq.Workplane('XY').box(80, 50, 12, centered=(True, True, False))
             .translate((0, 0, bottom)))
    plate = plate.cut(_cylinder(b.radial_housing_seat_diameter_mm / 2,
                                floor, b.radial_housing_seat_depth_mm + 1))
    plate = plate.cut(_cylinder(p.shaft.clearance_hole_diameter_mm / 2, bottom - 1, 14))
    axes = ((-30.0, -15.0), (-30.0, 15.0), (30.0, -15.0), (30.0, 15.0))
    screws = []
    for x, y in axes:
        passage = _cylinder(2.25, bottom - 1, 14).translate((x, y, 0))
        sink = cq.Workplane(obj=cq.Solid.makeCone(4.25, 2.25, 2.0,
                                                 cq.Vector(x, y, bottom)))
        plate = plate.cut(passage).cut(sink)
        head = cq.Workplane(obj=cq.Solid.makeCone(4.0, 2.0, 2.0,
                                                 cq.Vector(x, y, bottom)))
        shank = _cylinder(2.0, bottom + 2, 38).translate((x, y, 0))
        screws.append(head.union(shank).clean())
    plate = plate.clean()
    if not plate.val().isValid() or len(plate.val().Solids()) != 1:
        raise ValueError('Top support plate must be one valid connected solid')
    frame = (cq.Workplane('XY').box(100, 70, 30, centered=(True, True, False))
             .translate((0, 0, frame_bottom)))
    frame = frame.cut(_cylinder(p.shaft.clearance_hole_diameter_mm / 2, frame_bottom - 1, 32))
    return TopSupport(
        shape=plate, bearing=reference.parts['sealed_envelope'].translate((0, 0, floor)),
        wood_frame_reference=frame,
        required_shaft_reference=_cylinder(p.shaft.nominal_diameter_mm / 2,
                                            shaft_bottom, shaft_tip - shaft_bottom),
        wood_screws=tuple(screws), wood_screw_axes=axes, plate_size_mm=(80.0, 50.0, 12.0),
        bearing_seat_diameter_mm=b.radial_housing_seat_diameter_mm,
        bearing_seat_depth_mm=b.radial_housing_seat_depth_mm, bottom_shoulder_mm=shoulder,
        plate_bottom_z_mm=bottom, required_shaft_tip_z_mm=required_tip,
        required_shaft_extension_mm=max(0.0, required_tip - existing_tip))


def build_top_support_assembly(p: DesignParameters) -> cq.Assembly:
    """Expose separate named components for later STEP/manifest integration.

    ``required_extended_m8_reference`` replaces, rather than accompanies, the
    total rotor's old shaft. Wood/screw overlap depicts intended engagement,
    not a validated pilot hole, thread model, screw capacity or mounting load.
    """
    s = build_top_support(p)
    result = cq.Assembly(name='upper_608_support')
    for name, shape, color in (
            ('top_support_plate', s.shape, (0.50, 0.54, 0.58)),
            ('bearing_608', s.bearing, (0.7, 0.7, 0.72)),
            ('upper_wood_frame_reference', s.wood_frame_reference, (0.65, 0.45, 0.25)),
            ('required_extended_m8_reference', s.required_shaft_reference, (0.38, 0.64, 0.81))):
        result.add(shape, name=name, color=cq.Color(*color))
    for index, screw in enumerate(s.wood_screws, 1):
        result.add(screw, name=f'wood_screw_{index}_reference', color=cq.Color(0.7, 0.7, 0.72))
    return result


def audit_top_support(p: DesignParameters) -> dict:
    """Measure capture and clearance against actual Task-3 placed rotor solids.

    A nominal 8 mm shaft touches the 8 mm bearing bore without volume overlap;
    this is a radial guidance envelope, not a verified sliding fit on M8 thread.
    The annular reference does not resolve individual inner/outer bearing races.
    """
    from windwall.assembly import build_locked_rotor_assembly

    s = build_top_support(p)
    rotor = build_locked_rotor_assembly(p)
    stationary = (s.shape, s.bearing, s.wood_frame_reference)
    moving = {name: rotor.parts[name] for name in ('top', 'top_washer', 'top_nut')}
    moving['required_extended_m8_reference'] = s.required_shaft_reference
    gaps = [s.shape.val().distance(shape.val()) for name, shape in moving.items()
            if name != 'required_extended_m8_reference']
    intersections = {f'{name}/axial_shift_{shift:g}': sum(
        intersection_volume(fixed, shape.translate((0, 0, shift))) for fixed in stationary)
        for name, shape in moving.items() for shift in (-s.axial_float_mm, 0, s.axial_float_mm)}
    bearing_box = s.bearing.val().BoundingBox()
    frame_bottom = s.wood_frame_reference.val().BoundingBox().zmin
    play = frame_bottom - bearing_box.zmax
    return {
        'coordinate_frame': 'Locked rotor: Base nominal blade bottom z=0, M8 axis x=y=0',
        'role': 'stationary_radial_guide', 'primary_axial_support': False,
        'physically_calibrated': False, 'physical_load_verified': False,
        'plate_size_mm': list(s.plate_size_mm),
        'plate_bottom_z_mm': s.plate_bottom_z_mm,
        'bearing_floor_z_mm': bearing_box.zmin,
        'wood_frame_bottom_z_mm': frame_bottom,
        'bearing_axial_play_mm': play,
        'bearing_seat_radial_clearance_mm': (s.bearing_seat_diameter_mm - p.bearings.radial_outer_diameter_mm) / 2,
        'shaft_to_printed_passage_radial_clearance_mm': (p.shaft.clearance_hole_diameter_mm - p.shaft.nominal_diameter_mm) / 2,
        'shaft_to_bearing_nominal_radial_clearance_mm': (p.bearings.radial_bore_diameter_mm - p.shaft.nominal_diameter_mm) / 2,
        'top_module_gap_mm': s.shape.val().BoundingBox().zmin - rotor.parts['top'].val().BoundingBox().zmax,
        'minimum_hardware_gap_mm': min(gaps),
        'axial_float_each_direction_mm': s.axial_float_mm,
        'minimum_gap_at_axial_float_mm': min(gaps) - s.axial_float_mm,
        'downward_capture_contact_mm3': intersection_volume(s.shape, s.bearing.translate((0, 0, -0.1))),
        'upward_capture_contact_mm3': intersection_volume(s.wood_frame_reference,
                                                        s.bearing.translate((0, 0, play + 0.1))),
        'stationary_rotating_interference_mm3': sum(intersections.values()),
        'interference_by_moving_part_and_axial_shift_mm3': intersections,
        'existing_rotor_shaft_tip_z_mm': rotor.parts['shaft'].val().BoundingBox().zmax,
        'existing_rotor_shaft_reaches_bearing': rotor.parts['shaft'].val().BoundingBox().zmax >= bearing_box.zmax,
        'required_shaft_tip_z_mm': s.required_shaft_tip_z_mm,
        'required_shaft_extension_mm': s.required_shaft_extension_mm,
        'shaft_extension_integration_required': s.required_shaft_extension_mm > 1e-6,
        'wood_screw_nominal_dimensions_mm': [4.0, 40.0],
        'wood_screw_axes_xy_mm': [list(axis) for axis in s.wood_screw_axes],
        'wood_screw_provisional_head_diameter_mm': 8.0,
        'wood_screw_passage_diameter_mm': 4.5,
        'bottom_countersink_diameter_mm': 8.5,
        'bottom_countersink_angle_deg': 90.0,
        'wood_screw_nominal_engagement_mm': 28.0,
        'assembly_integration': 'Replace main rotor shaft with required_shaft_reference; add plate, 608 and frame reference separately',
    }
