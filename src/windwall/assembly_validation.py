"""Solid-envelope audit of the phased stack and generator bearing load path.

Installed solids must not overlap. Named bearing contacts and joint compression
probes are measured separately. Permanent bayonet
joint interference during the lifted lock path is reported as an unverified elastic fit;
neither rigid motion samples nor this audit establish print readiness.
"""

from itertools import combinations
from math import ceil

import cadquery as cq

from windwall.assembly import RotorAssembly, place
from windwall.generator import intersection_volume
from windwall.rotor_modules import module_joint_depth_mm


def require_valid_assembly_audit(report: dict) -> None:
    """Require collision-free installed geometry and the named support contacts."""
    for key in ('unplanned_intersection_mm3', 'top_wrench_access_intersection_mm3',
                'top_washer_removal_intersection_mm3', 'generator_rotating_stationary_intersection_mm3',
                'maximum_installed_joint_intersection_mm3'):
        if report[key] >= 0.01:
            raise ValueError('Full assembly collision or service audit failed')
    if report['maximum_stage_angle_error_deg'] >= 0.01:
        raise ValueError('Installed stages must preserve the helical blade registration')
    for result in report['joint_paths'].values():
        if min(result[key] for key in ('ccw_overtravel_intersection_mm3',
                                       'cw_reverse_intersection_mm3', 'locked_pull_intersection_mm3')) <= 0.05:
            raise ValueError('Permanent bayonet must resist overtravel, reversal and axial pull')
    for contact in report['generator_collision_report']['intended_bearing_contacts'].values():
        if contact['distance_mm'] > 0.0001 or contact['intersection_mm3'] >= 0.01:
            raise ValueError('51105 load path requires seated, non-interpenetrating support surfaces')


def intersection_report(a: RotorAssembly) -> tuple[float, dict]:
    """All installed part pairs; no blanket or thread-forming overlap allowances."""
    if a.exploded:
        raise ValueError('Installed-contact audit requires the locked assembly')
    pairs = {f'{name}/{other}': intersection_volume(first, second)
             for (name, first), (other, second) in combinations(a.parts.items(), 2)}
    return sum(pairs.values()), pairs


def _obstruction(a: RotorAssembly, envelope: cq.Workplane, exclude=()) -> float:
    return sum(intersection_volume(envelope, shape) for name, shape in a.parts.items() if name not in exclude)


def _joint_paths(a: RotorAssembly) -> dict:
    p = a.parameters
    height, depth = p.rotor.stage_height_mm, module_joint_depth_mm(p)
    travel = p.bayonet.insertion_offset_deg
    reports = {}
    for lower_name, upper_name in (('base', 'standard'), ('standard', 'standard'), ('standard', 'top')):
        lower, upper = a.local_modules[lower_name], a.local_modules[upper_name]
        phase = p.blade.twist_deg
        # Tongues are lowered into their matching groove only at final phase.
        # Added receiver headroom clears the rigid lug roof; snap-pawl contact
        # remains an unverified elastic fit.
        lift = p.bayonet.seating_headroom_mm
        insertion = [intersection_volume(lower, place(upper, phase-travel, height+step))
                     for step in range(1, ceil(depth)+3)]
        lock = [intersection_volume(lower, place(upper, phase-travel+min(index/2, travel), height+lift))
                for index in range(ceil(travel*2)+1)]
        reports[f'{lower_name}/{upper_name}'] = {
            'insertion_sample_count': len(insertion), 'locking_sample_count': len(lock),
            'locking_lift_mm': lift,
            'maximum_insertion_intersection_mm3': max(insertion),
            'maximum_locking_intersection_mm3': max(lock),
            'ccw_overtravel_intersection_mm3': intersection_volume(lower, place(upper, phase+0.5, height)),
            'cw_reverse_intersection_mm3': intersection_volume(lower, place(upper, phase-0.5, height)),
            'locked_pull_intersection_mm3': intersection_volume(lower, place(upper, phase, height+2)),
            'elastic_snap_fit_verified': False,
            'disassembly_supported': False}
    return reports


def audit_rotor_assembly(a: RotorAssembly) -> dict:
    """Return measured failures as data; export validation is an explicit gate."""
    if a.exploded:
        raise ValueError('Audit the locked assembly before generating the preassembly view')
    p, m = a.parameters, a.parameters.manufacturing
    unexpected, pairs = intersection_report(a)
    installed, axial_float = [], []
    for lower_stage, upper_stage in zip(a.stages, a.stages[1:]):
        lower, upper = a.parts[lower_stage.name], a.parts[upper_stage.name]
        installed.append(intersection_volume(lower, upper))
        small_probe = intersection_volume(lower, upper.translate((0, 0, -0.1)))
        large_probe = intersection_volume(lower, upper.translate((0, 0, -0.2)))
        axial_float.append({'joint': f'{lower_stage.name}/{upper_stage.name}',
                            'compression_0_10_mm_intersection_mm3': small_probe,
                            'compression_0_20_mm_intersection_mm3': large_probe,
                            'contact_probe_bracket_mm': [0.1, 0.2]
                            if small_probe < 0.01 and large_probe >= 0.01 else None,
                            'physical_load_capacity_verified': False})
    nut_bottom = a.parts['top_nut'].val().BoundingBox().zmin
    wrench = cq.Workplane('XY').circle(11.5).extrude(30).translate((0, 0, nut_bottom))
    wrench_volume = _obstruction(a, wrench, ('shaft', 'top_nut'))
    washer_volume = max(_obstruction(a, a.parts['top_washer'].translate((0, 0, lift)),
                                    ('top_nut', 'top_washer')) for lift in (0, 0.5, 2, 5, 10, 20, 30))
    collisions = a.generator.collision_report(a.rotating_parts)
    gaps = a.generator.air_gap_report()
    sleeve_height = (a.generator.clamp_hardware['upper_nut'].val().BoundingBox().zmin
                     - gaps['lower_magnet_face_z_mm'])
    return {'stage_count': a.aerodynamic_stage_count, 'base_count': a.base_count,
            'standard_count': a.standard_count, 'top_count': a.top_count,
            'part_count': len(a.parts), 'nominal_stage_z_mm': [s.z_mm for s in a.stages],
            'aerodynamic_height_mm': a.aerodynamic_height_mm(),
            'nominal_stage_pitch_mm': p.rotor.stage_height_mm,
            'maximum_installed_joint_intersection_mm3': max(installed),
            'joint_axial_float': axial_float,
            'axial_float_note': 'Blade skins meet at nominal pitch; compression probes do not establish physical load capacity',
            'maximum_stage_angle_error_deg': a.maximum_stage_angle_error_deg(),
            'internal_blade_twist_deg': p.blade.twist_deg, 'seam_phase_jump_deg': 0,
            'aerodynamic_seam_continuous': a.maximum_stage_angle_error_deg() < 0.01,
            'unplanned_intersection_mm3': unexpected, 'part_pair_intersections_mm3': pairs,
            'joint_paths': _joint_paths(a),
            'top_wrench_access_intersection_mm3': wrench_volume,
            'top_washer_removal_intersection_mm3': washer_volume,
            'top_blade_end_z_mm': a.stages[-1].z_mm+p.rotor.stage_height_mm,
            'shaft_z_bounds_mm': [a.parts['shaft'].val().BoundingBox().zmin, a.parts['shaft'].val().BoundingBox().zmax],
            'upper_generator_air_gap_mm': gaps['upper_air_gap_mm'],
            'lower_generator_air_gap_mm': gaps['lower_air_gap_mm'],
            'generator_air_gap_report': gaps, 'generator_collision_report': collisions,
            'integral_lower_rotor_sleeve': {
                'outer_diameter_mm': p.generator.spacer_outer_diameter_mm,
                'inner_diameter_mm': p.shaft.clearance_hole_diameter_mm,
                'height_mm': round(sleeve_height, 6),
                'separate_part_required': False,
            },
            'generator_rotating_stationary_intersection_mm3': collisions['unintended_intersection_mm3'],
            'physical_fit_verified': False, 'interactive_qa_verified': False, 'print_ready': False,
            'physical_magnet_fit_verified': False, 'physical_bearing_fit_verified': False,
            'magnet_retention_verified': False, 'bearing_axial_retention_verified': False,
            'electrical_design_finalized': False,
            'motion_sampling': {'locking_step_deg': 0.5, 'insertion_step_mm': 1,
                                'continuous_collision_proof': False, 'elastic_snap_fit_verified': False},
            'contact_semantics': 'Named 51105 washer/support contacts; permanent bayonet stops; flush blade skins and inset seams',
            'hardware_envelopes': {'nut_height_mm': m.nut_pocket_depth_mm,
                'washer_diameter_mm': m.washer_outer_diameter_mm,
                'washer_thickness_mm': p.generator.clamp_washer_thickness_mm,
                'basis': 'Nominal hardware envelopes; dimensions and fit require measurement'}}
