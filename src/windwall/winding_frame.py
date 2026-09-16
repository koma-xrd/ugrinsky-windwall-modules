"""Screwless PLA stand, serviceable printed spindle and manual crank.

Construction coordinates match the head: Z is the shaft axis and Y is up.
Returned parts are installed upright: rotate +90 degrees about X and raise
the axis above the bench. The wheel uses the same transform from metadata.
Only the front 608 locates the shaft axially; the rear outer ring can float.
Bearing solids are catalog envelopes, not rolling-element or fit simulation.
"""

from dataclasses import dataclass

import cadquery as cq

from windwall.bearings import build_608_reference
from windwall.parameters import DesignParameters
from windwall.winding_head import build_winding_head
from windwall.winding_tool_parameters import WindingToolParameters, diameter_settings_mm


@dataclass(frozen=True)
class WindingFrameParts:
    base: cq.Workplane
    tower: cq.Workplane
    bearing_retainers: tuple[cq.Workplane, ...]
    bearings: tuple[cq.Workplane, ...]
    shaft: cq.Workplane
    snap_collars: tuple[cq.Workplane, ...]
    crank: cq.Workplane
    grip: cq.Workplane
    metadata: dict


def _box(x, y, z, dx, dy, dz):
    return cq.Workplane('XY').box(dx, dy, dz, centered=False).translate((x, y, z))


def _cylinder(radius, z, length):
    return cq.Workplane('XY').circle(radius).extrude(length).translate((0, 0, z))


def _ring(outer, inner, z, length):
    return (cq.Workplane('XY').circle(outer).circle(inner).extrude(length)
            .translate((0, 0, z)))


def _polygon(diameter, z, length):
    return cq.Workplane('XY').polygon(6, diameter).extrude(length).translate((0, 0, z))


def _base_and_tower(height, seat_radius):
    floor = -height
    base = _box(-80, floor, -80, 160, 8, 110)
    pocket = _box(-14.2, floor + 1.8, -38.2, 28.4, 6.3, 20.4)
    base = base.cut(pocket)
    tongue = _box(-14, floor + 2, -38, 28, 6, 20)
    foot = _box(-15, floor + 8, -39, 30, 8, 22)
    tower = tongue.union(foot).union(_box(-11, floor + 16, -42, 22, height - 27, 24))
    # Upright keys carry shear; the two small hooks only prevent lift-out.
    for mirrored in (False, True):
        pier = _box(17.2, floor + 8, -34, 7, 9, 12)
        pier = pier.cut(_box(17.1, floor + 11.2, -32.2, 1.1, 3, 8.4))
        beam = _box(16, floor + 8, -32, 1, 20, 8)
        root = _box(14, floor + 8, -32, 3, 3, 8)
        hook = (cq.Workplane('XY').polyline([
            (16.8, floor + 11), (17.4, floor + 13),
            (17.4, floor + 14), (16.8, floor + 14)])
            .close().extrude(8).translate((0, 0, -32)))
        tab = beam.union(root).union(hook)
        edges = [e for e in tab.edges('|Z').vals()
                 if abs(e.Center().x - 16) < 1e-6 and abs(e.Center().y - (floor + 11)) < 1e-6]
        if edges:
            tab = tab.newObject(edges).fillet(.6)
        if mirrored:
            pier, tab = pier.mirror('YZ'), tab.mirror('YZ')
        base, tower = base.union(pier), tower.union(tab)
    for x in (-68, 68):
        for z in (-64, 12):
            # Optional bench-clamp holes are not product assembly hardware.
            hole = _cylinder(3.5, 0, 12).rotate((0, 0, 0), (1, 0, 0), 90)
            base = base.cut(hole.translate((x, floor + 10, z)))
    rear = _ring(16, 9.8, -44, 13)
    rear = rear.cut(_cylinder(seat_radius, -44.1, 11.7))
    front = _ring(16, 9.8, -29.3, 10.8)
    front = front.cut(_cylinder(seat_radius, -28.1, 9.8))
    tower = tower.union(rear).union(front)
    for z in (-42.2, -21.0):
        tower = tower.cut(_cylinder(12.1, z, 1.7))
        # Open squeeze-ear access; the opening remains narrower than a bearing.
        tower = tower.cut(_box(-5, 10, z - .1, 10, 15, 1.9))
    # The central service gap exposes the rear locating collar completely.
    tower = tower.cut(_box(-18, -10, -31, 36, 35, 2.7))
    for z in (-30.3, -20.8):
        tower = tower.cut(_box(-8, 5.2, z, 16, 20, 2.2))
    return base.clean(), tower.clean()


def _bearing_retainer():
    clip = _ring(11.9, 9.8, 0, 1.5).cut(_box(-2.5, 8, -.1, 5, 12, 1.7))
    for x in (-4.5, 2.5):
        clip = clip.union(_box(x, 9.4, 0, 2, 5, 1.5))
    return clip.clean()


def _snap_collar():
    # Open throat 6.8 mm springs over the 7 mm groove, not the 8 mm journal.
    return _ring(5.1, 3.6, 0, 1.8).cut(_box(-3.4, 0, -.1, 6.8, 8, 2)).clean()


def _shaft(drive_diameter):
    shaft = _cylinder(4, -54, 35.5).union(_polygon(8, -68, 14))
    for z in (-30.2, -20.8):
        shaft = shaft.cut(_ring(4.2, 3.5, z, 2))
    # A small rear polygon passes through both bores after crank removal.
    shaft = shaft.cut(_ring(5, 3, -64.2, 2.6))
    shaft = shaft.union(_polygon(drive_diameter, -18.5, 26))
    shaft = shaft.union(_cylinder(9, -.6, .4))
    # Two long flexures release the wheel from its front face. Remaining flats
    # transmit torque even while the tips are compressed for removal.
    for side in (-1, 1):
        slot = _box(5.1, -1.8, -10, .9, 3.6, 17.6)
        isolation = (_box(5.1, -2.2, -10, 3, .4, 17.6)
                     .union(_box(5.1, 1.8, -10, 3, .4, 17.6)))
        hook = (cq.Workplane('XZ').polyline([
            (6.7, 5.2), (7.4, 5.2), (7.4, 5.8), (6.7, 6.8)])
            .close().extrude(.6).translate((0, .3, 0)))
        if side < 0:
            slot, isolation, hook = (s.mirror('YZ') for s in (slot, isolation, hook))
        shaft = shaft.cut(slot).cut(isolation).union(hook)
    roots = [edge for edge in shaft.edges('|Y').vals()
             if abs(edge.Center().z + 10) < 1e-6 and abs(abs(edge.Center().x) - 6) < 1e-6]
    shaft = shaft.newObject(sorted(roots, key=lambda e: e.Center().x)).fillet(.35)
    return shaft.clean()


def _crank_and_grip():
    # The 14 mm rear hub is removable, allowing the narrow spindle to withdraw.
    hub = _cylinder(7, -67, 12).cut(_polygon(8.4, -68, 14))
    arm = _box(0, -7, -59, 52, 14, 5).union(_cylinder(7, -59, 5).translate((52, 0, 0)))
    crank = hub.union(arm).cut(_polygon(8.4, -68, 14))
    # Axial beams snap inward into the rear groove. Lift the exposed tails
    # outward through the two hub windows to release the crank.
    for side in (-1, 1):
        window = _box(-2, 3.3, -67.1, 4, 5, 11.6)
        beam = _box(-1.5, 4, -68, 3, .8, 13)
        hook = (cq.Workplane('YZ').polyline([
            (4.1, -64), (3.2, -64), (3.2, -62), (4.1, -61)])
            .close().extrude(3).translate((-1.5, 0, 0)))
        if side < 0:
            window, beam, hook = (s.mirror('XZ') for s in (window, beam, hook))
        crank = crank.cut(window).union(beam).union(hook)
    roots = [edge for edge in crank.edges('|X').vals()
             if abs(edge.Center().z + 55.5) < 1e-6
             and abs(abs(edge.Center().y) - 4.8) < 1e-6]
    crank = crank.newObject(sorted(roots, key=lambda e: e.Center().y)).fillet(.3)
    journal = _cylinder(4, -85, 26)
    end = (cq.Workplane('XZ').polyline([
        (3.7, -85), (4.7, -84), (4.7, -82), (3.7, -82)])
        .close().extrude(2).translate((0, 1, 0)))
    journal = journal.union(end).union(end.mirror('YZ'))
    journal = journal.cut(_box(-1.25, -6, -86, 2.5, 12, 23))
    roots = [edge for edge in journal.edges('|Y').vals()
             if abs(edge.Center().z + 63) < 1e-6 and abs(abs(edge.Center().x) - 1.25) < 1e-6]
    journal = journal.newObject(sorted(roots, key=lambda e: e.Center().x)).fillet(.8)
    crank = crank.union(journal.translate((52, 0, 0)))
    grip = _ring(9, 4.3, -81.8, 22.6).translate((52, 0, 0))
    grip = grip.edges('%CIRCLE').fillet(.5)
    return crank.clean(), grip.clean()


def build_winding_frame(tool_parameters: WindingToolParameters,
                        design_parameters: DesignParameters) -> WindingFrameParts:
    """Build installed occurrences; exactly two 608s are purchased components.

    Assemble bearings/outer clips, insert shaft from the front, snap the two
    locating collars into the front-bearing grooves, fit crank then grip, and
    snap the wheel onto its front polygon. Reverse this sequence for service.
    Both bearings slide over the rear polygon; neither is trapped by a shoulder.
    """
    settings = diameter_settings_mm(tool_parameters)
    b = design_parameters.bearings
    if b.radial_nominal_dimensions_mm != (8.0, 22.0, 7.0):
        raise ValueError('The printed spindle and service clips require canonical 8 x 22 x 7 mm 608 bearings')
    if not 22 < b.radial_housing_seat_diameter_mm <= 22.4:
        raise ValueError('608 seat diameter must be above 22 and at most 22.4 mm for positive clip engagement')
    head = build_winding_head(tool_parameters, settings[0])
    socket = head.metadata['drive_socket']
    if socket['polygon_sides'] != 6 or socket['circumdiameter_mm'] != 14.4:
        raise ValueError('The printed wheel drive requires the six-sided 14.4 mm wheel socket')
    height = tool_parameters.maximum_diameter_mm / 2 + 30
    base, tower = _base_and_tower(height, b.radial_housing_seat_diameter_mm / 2)
    reference = build_608_reference(design_parameters).parts['sealed_envelope']
    bearings = tuple(reference.translate((0, 0, z)) for z in (-40, -28))
    clip = _bearing_retainer()
    clips = tuple(clip.translate((0, 0, z)) for z in (-42.1, -20.9))
    collar = _snap_collar()
    collars = tuple(collar.translate((0, 0, z)) for z in (-30.1, -20.7))
    shaft = _shaft(socket['circumdiameter_mm'] - .4)
    crank, grip = _crank_and_grip()
    rotations = {'base': (90, 0, 0), 'tower': (0, 90, 0),
                 'bearing_retainer': (0, 0, 0), 'snap_collar': (0, 0, 0),
                 'shaft': (90, 0, 0), 'crank': (90, 0, 0), 'grip': (0, 0, 0)}
    masters = dict(base=base, tower=tower, bearing_retainer=clip,
                   snap_collar=collar, shaft=shaft, crank=crank, grip=grip)
    for name, shape in masters.items():
        if not shape.val().isValid() or len(shape.val().Solids()) != 1 or shape.val().Volume() <= 0:
            raise ValueError(f'{name} must be one valid positive-volume solid')
        printed = shape
        for axis, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), rotations[name]):
            printed = printed.rotate((0, 0, 0), axis, angle)
        bounds = printed.val().BoundingBox()
        if max(bounds.xlen, bounds.ylen) > min(220, tool_parameters.print_bed_mm):
            raise ValueError(f'{name} exceeds the documented print-bed envelope')
    def installed(shape):
        return shape.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, 0, height))

    metadata = {
        'axis_height_mm': height,
        'head_rotation_x_deg': 90,
        'head_translation_mm': (0, 0, height),
        'bearing_nominal_dimensions_mm': b.radial_nominal_dimensions_mm,
        'bearing_seat_diameter_mm': b.radial_housing_seat_diameter_mm,
        'bearing_centers_local_z_mm': (-36.5, -24.5),
        'locating_bearing_index': 1,
        'rear_bearing_axial_float_mm': 1.2,
        'print_rotations_deg': rotations,
        'print_orientation_notes': {
            'shaft': 'axis parallel to bed; support lower drive faces; keep journal surfaces smooth',
            'crank': 'journal parallel to bed; support lower hub; preserve open flexure slots',
            'tower': 'side face on bed; snap beams parallel to layers',
            'bearing_retainer': 'flat face on bed; squeeze ears together before insertion or service',
            'snap_collar': 'flat face on bed; spread open throat over reduced groove',
        },
        'purchased_components': {'608': 2},
        'clamp_lands_local_x_mm': (-70, 70),
        'physical_validation_required': True,
        'service_sequence': ('remove wheel', 'release grip end', 'release crank tails',
                             'remove two shaft collars', 'withdraw shaft forward',
                             'squeeze outer-ring clips and remove bearings'),
    }
    return WindingFrameParts(installed(base), installed(tower), tuple(map(installed, clips)),
        tuple(map(installed, bearings)), installed(shaft), tuple(map(installed, collars)),
        installed(crank), installed(grip), metadata)
