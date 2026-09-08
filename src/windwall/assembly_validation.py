"""Deterministic solid-envelope audit for the locked seven-stage rotor.

This measures the three unique module pairings, all placed hardware and service
corridors. Tangential stops/washer seating are zero-volume contacts. Only named
screw/pilot thread-forming volumes may overlap; every other overlap is reported.
Motion samples are CAD evidence, not a continuous proof or physical fit test.
"""

from itertools import combinations
from math import ceil

import cadquery as cq

from windwall.assembly import RotorAssembly, place
from windwall.bayonet import build_bayonet_coupon, build_male_bayonet
from windwall.drivers import build_drivers
from windwall.rotor_modules import module_joint_depth_mm


def _can_overlap(first, second) -> bool:
    a,b = first.val().BoundingBox(),second.val().BoundingBox()
    return all(min(getattr(a,f'{axis}max'),getattr(b,f'{axis}max'))-
               max(getattr(a,f'{axis}min'),getattr(b,f'{axis}min')) > 1e-7 for axis in 'xyz')


def require_valid_assembly_audit(report: dict) -> None:
    """Fail export on collision, blocked service paths or missing retention."""
    clear = ['unplanned_intersection_mm3', 'closure_removal_intersection_mm3',
             'top_wrench_access_intersection_mm3', 'top_washer_removal_intersection_mm3',
             'generator_rotating_stationary_intersection_mm3', 'driver_cw_release_intersection_mm3']
    if any(report[key] >= 0.01 for key in clear):
        raise ValueError('Full assembly collision or service audit failed')
    for result in report['joint_paths'].values():
        if (max(result['maximum_insertion_intersection_mm3'], result['maximum_locking_intersection_mm3'],
                result['cw_release_intersection_mm3']) >= 0.01
                or min(result['ccw_overtravel_intersection_mm3'], result['locked_pull_intersection_mm3']) <= 0.05):
            raise ValueError('Integrated module insertion, lock stop or axial retention check failed')
    for item in report['radial_retainer_access'] + report['closure_retainer_access']:
        if max(item[key] for key in ('head_intersection_mm3', 'tool_intersection_mm3', 'unplanned_shank_intersection_mm3')) >= 0.01:
            raise ValueError('Fastener shank, head or driver access is obstructed')
    if min(report['driver_ccw_stop_intersection_mm3'], report['bayonet_ccw_stop_intersection_mm3']) <= 0.05:
        raise ValueError('Both drivers and bayonet lugs must meet CCW stops')
    if len(report['thread_forming_contacts']) != 14 or min(report['thread_forming_contacts'].values()) <= 0:
        raise ValueError('All fourteen retainers must engage their designated blind pilots')
    if (report['maximum_seated_joint_intersection_mm3'] >= 0.01
            or report['maximum_preseat_retainer_intersection_mm3'] >= 0.01
            or report['maximum_seated_retainer_intersection_mm3'] >= 0.01
            or report['minimum_pilot_thread_engagement_mm3'] <= 0.05):
        raise ValueError('Loaded joint must seat on printed geometry before radial retainers carry axial load')


def _volume(first, second) -> float:
    return first.intersect(second).val().Volume() if _can_overlap(first,second) else 0.0


def intersection_report(a: RotorAssembly) -> tuple[float,dict]:
    """All part pairs; allowances are bounded thread envelopes for named bodies."""
    if a.exploded:
        raise ValueError('Thread-contact audit requires the locked assembly')
    masks = {frozenset((r.name,r.body_name)):r for r in a.retainers}
    unexpected,contacts = 0.0,{}
    for (name,first),(other,second) in combinations(a.parts.items(),2):
        if not _can_overlap(first,second):
            continue
        overlap = first.intersect(second)
        retainer = masks.get(frozenset((name,other)))
        if retainer is not None:
            contacts[retainer.name] = _volume(overlap,retainer.thread_envelope)
            unexpected += overlap.cut(retainer.thread_envelope).val().Volume()
        else:
            unexpected += overlap.val().Volume()
    return unexpected,contacts


def _obstruction(a, envelope, exclude=()) -> float:
    return sum(_volume(envelope,shape) for name,shape in a.parts.items() if name not in exclude)


def _joint_paths(a: RotorAssembly) -> dict:
    p = a.parameters
    height,depth = p.rotor.stage_height_mm,module_joint_depth_mm(p)
    travel,rise = p.bayonet.insertion_offset_deg,p.bayonet.ramp_rise_mm
    reports = {}
    for lower_name,upper_name in (('base','standard'),('standard','standard'),('standard','top')):
        lower,upper = a.local_modules[lower_name],a.local_modules[upper_name]
        insertion = [_volume(lower,place(upper,-travel,height-rise+lift)) for lift in range(ceil(depth)+2)]
        lock = []
        for index in range(ceil(travel*2)+1):
            angle = min(index/2,travel)
            lock.append(_volume(lower,place(upper,angle-travel,height+rise*(angle/travel-1))))
        reports[f'{lower_name}/{upper_name}'] = {
            'insertion_sample_count':len(insertion),'locking_sample_count':len(lock),
            'maximum_insertion_intersection_mm3':max(insertion),
            'maximum_locking_intersection_mm3':max(lock),
            'ccw_overtravel_intersection_mm3':_volume(lower,place(upper,0.5,height)),
            'cw_release_intersection_mm3':_volume(lower,place(upper,-0.5,height)),
            'locked_pull_intersection_mm3':_volume(lower,place(upper,z=height+2))}
    return reports


def audit_rotor_assembly(a: RotorAssembly) -> dict:
    """Complete audit; returned numeric failures remain visible to callers."""
    if a.exploded:
        raise ValueError('Audit the locked assembly before generating the exploded view')
    p,m = a.parameters,a.parameters.manufacturing
    unexpected,contacts = intersection_report(a)
    radial,closure_access = [],[]
    for retainer in a.retainers:
        head = _obstruction(a,retainer.head,(retainer.name,))
        tool = _obstruction(a,retainer.tool,(retainer.name,))
        shank = a.parts[retainer.name].cut(retainer.head)
        unplanned = sum(_volume(shank.cut(retainer.thread_envelope) if name == retainer.body_name else shank,shape)
                        for name,shape in a.parts.items() if name != retainer.name)
        item = {'name':retainer.name,'head_intersection_mm3':head,
                'tool_intersection_mm3':tool,'unplanned_shank_intersection_mm3':unplanned}
        if retainer.angle_deg is not None:
            radial.append(dict(item,angle_deg=retainer.angle_deg))
        else:
            closure_access.append(dict(item,pilot_engagement_mm=m.screw_length_mm-p.closure.plate_thickness_mm))
    paths = _joint_paths(a)
    seat = p.modules.locked_seating_travel_mm
    seated_joints = []
    preseat_retainers = []
    seated_retainers = []
    pilot_engagement = []
    radial_retainers = [retainer for retainer in a.retainers if retainer.angle_deg is not None]
    for index, (lower_stage, upper_stage) in enumerate(zip(a.stages, a.stages[1:])):
        lower = a.parts[lower_stage.name]
        upper = a.parts[upper_stage.name]
        seated_joints.append(_volume(lower, upper))
        for retainer in radial_retainers[2*index:2*index+2]:
            shank = a.parts[retainer.name].cut(retainer.head)
            seated_retainers.append(_volume(lower, shank))
            for lift_index in range(8):
                lift = seat*lift_index/7
                preseat_retainers.append(_volume(lower, shank.translate((0,0,lift))))
            pilot_engagement.append(_volume(upper, shank))
    depth,height = module_joint_depth_mm(p),p.rotor.stage_height_mm
    lower = a.local_modules['standard']
    upper = place(a.local_modules['top'],z=height)
    joint_z = height-depth
    drivers = place(build_drivers(p),p.modules.joint_phase_deg,joint_z).intersect(upper)
    bayonet = place(build_male_bayonet(p),p.modules.joint_phase_deg,joint_z).intersect(upper)
    # Test each independent torque element against the actual integrated lower.
    semantics = {'driver_ccw_stop_intersection_mm3':_volume(place(drivers,0.5),lower),
                 'driver_cw_release_intersection_mm3':_volume(place(drivers,-0.5),lower),
                 'bayonet_ccw_stop_intersection_mm3':_volume(place(bayonet,0.5),lower),
                 'bayonet_running_clearance_mm':build_bayonet_coupon(p).minimum_locked_clearance_mm()}
    top_z = a.stages[-1].z_mm+p.rotor.stage_height_mm
    removed = ('top_closure','closure_retainer_1','closure_retainer_2')
    closure = a.parts['top_closure']
    removal = max(_obstruction(a,closure.translate((0,0,lift)),removed)
                  for lift in (0,0.25,1,3,6,12,18,30))
    nut_bottom = a.parts['top_nut'].val().BoundingBox().zmin
    wrench = cq.Workplane('XY').circle(11.5).extrude(30).translate((0,0,nut_bottom))
    wrench_volume = _obstruction(a,wrench,(*removed,'shaft','top_nut'))
    washer_volume = max(_obstruction(a,a.parts['top_washer'].translate((0,0,lift)),
                                   (*removed,'top_nut','top_washer'))
                        for lift in (0,0.5,2,5,10,20,30))
    clearance = min(closure.val().distance(a.parts[name].val()) for name in ('shaft','top_nut','top_washer'))
    return {'stage_count':a.aerodynamic_stage_count,'base_count':a.base_count,
            'standard_count':a.standard_count,'top_count':a.top_count,
            'part_count':len(a.parts),'nominal_stage_z_mm':[s.z_mm for s in a.stages],
            'aerodynamic_height_mm':a.aerodynamic_height_mm(),
            'joint_seating_travel_mm':seat,
            'maximum_seated_joint_intersection_mm3':max(seated_joints),
            'maximum_preseat_retainer_intersection_mm3':max(preseat_retainers),
            'maximum_seated_retainer_intersection_mm3':max(seated_retainers),
            'minimum_pilot_thread_engagement_mm3':min(pilot_engagement),
            'maximum_stage_angle_error_deg':a.maximum_stage_angle_error_deg(),
            'internal_blade_twist_deg':p.blade.twist_deg,'seam_phase_jump_deg':-p.blade.twist_deg,
            'aerodynamic_seam_continuous':False,
            'unplanned_intersection_mm3':unexpected,'thread_forming_contacts':contacts,
            'joint_paths':paths,**semantics,'radial_retainer_access':radial,
            'closure_retainer_access':closure_access,
            'closure_removal_intersection_mm3':removal,
            'closure_hardware_clearance_mm':clearance,
            'top_wrench_access_intersection_mm3':wrench_volume,
            'top_washer_removal_intersection_mm3':washer_volume,
            'top_blade_end_z_mm':top_z,
            'shaft_z_bounds_mm':[a.parts['shaft'].val().BoundingBox().zmin,a.parts['shaft'].val().BoundingBox().zmax],
            'upper_generator_air_gap_mm':a.generator.upper_air_gap_mm(),
            'lower_generator_air_gap_mm':a.generator.lower_air_gap_mm(),
            'generator_rotating_stationary_intersection_mm3':a.generator.rotor_stator_intersection_volume_mm3(),
            'physical_fit_verified':False,'interactive_qa_verified':False,'print_ready':False,
            'physical_magnet_fit_verified':False,'physical_bearing_fit_verified':False,
            'magnet_retention_verified':False,'bearing_axial_retention_verified':False,
            'electrical_design_finalized':False,
            'motion_sampling':{'locking_step_deg':0.5,'insertion_step_mm':1,
                               'continuous_collision_proof':False},
            'contact_semantics':'Zero-volume stops and washer/closure seats; named M3 pilot thread-forming masks only',
            'hardware_envelopes':{'nut_height_mm':m.nut_pocket_depth_mm,
                'washer_diameter_mm':m.washer_outer_diameter_mm,
                'washer_thickness_mm':p.generator.clamp_washer_thickness_mm,
                'screw_diameter_mm':m.screw_nominal_diameter_mm,'screw_length_mm':m.screw_length_mm,
                'head_diameter_mm':m.screw_head_diameter_mm,'head_height_mm':m.screw_head_height_mm,
                'closure_screw_radius_mm':p.modules.closure_screw_radius_mm,
                'basis':'Nominal hardware envelopes; actual dimensions and fit require measurement'}}
