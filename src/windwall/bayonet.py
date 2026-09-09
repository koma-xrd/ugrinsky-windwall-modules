"""Three-lug CCW bayonet and isolated fit coupon, in millimetres.

The female stays fixed. Male builders return the locked orientation (0 degrees);
insertion starts at -18 degrees viewed from +Z. A common z_plane_mm translates
the interface without changing its frame. Tracks rise along CCW travel and have
solid terminal faces. Their finite-lug envelope leaves axial/radial running
clearance; stop contact intentionally has zero tangential clearance. Blade-end
drivers, relieved retainer guides and module shoulders are integrated by the
module builders; this file remains the reusable central bayonet primitive.
"""

from dataclasses import dataclass
from math import atan2, cos, degrees, hypot, isfinite, radians, sin

import cadquery as cq

from windwall.parameters import DesignParameters


def _validate(parameters: DesignParameters, z_plane_mm: float = 0) -> None:
    b, m = parameters.bayonet, parameters.manufacturing
    positive = (b.hub_outer_diameter_mm, b.lug_radial_depth_mm,
                b.lug_tangential_width_mm, b.lug_axial_thickness_mm,
                b.root_fillet_mm, m.radial_clearance_mm, m.axial_clearance_mm,
                m.minimum_loaded_wall_mm, parameters.shaft.clearance_hole_diameter_mm)
    if any(not isfinite(value) or value <= 0 for value in positive):
        raise ValueError("Bayonet dimensions and running clearances must be positive and finite")
    if b.lug_count != 3:
        raise ValueError("This interface requires exactly three lugs")
    if not isfinite(b.insertion_offset_deg) or not 15 <= b.insertion_offset_deg <= 20:
        raise ValueError("Counterclockwise locking travel must be between 15 and 20 degrees")
    if not isfinite(b.ramp_rise_mm) or not 0 <= b.ramp_rise_mm <= m.axial_clearance_mm * 2:
        raise ValueError("Ramp rise must be finite, nonnegative and no more than two axial clearances")
    if not isfinite(z_plane_mm):
        raise ValueError("Bayonet Z plane must be finite")
    if b.root_fillet_mm * 2 >= min(b.lug_tangential_width_mm, b.lug_radial_depth_mm):
        raise ValueError("Lug width and depth must leave room for the root fillet and stop face")
    if parameters.shaft.clearance_hole_diameter_mm + 2*m.minimum_loaded_wall_mm >= b.hub_outer_diameter_mm:
        raise ValueError("Bayonet hub must retain a loaded wall outside the shaft hole")


def locked_angle_deg(parameters: DesignParameters) -> float:
    """Positive CCW travel from insertion to the zero-orientation final stop."""
    _validate(parameters)
    return parameters.bayonet.insertion_offset_deg


def _lug_outer_radius(parameters: DesignParameters) -> float:
    b = parameters.bayonet
    return hypot(b.hub_outer_diameter_mm/2 + b.lug_radial_depth_mm - b.root_fillet_mm,
                 b.lug_tangential_width_mm/2 - b.root_fillet_mm) + b.root_fillet_mm


def _track_half_span_deg(parameters: DesignParameters) -> float:
    b = parameters.bayonet
    # Includes the enlarged concave root fillet at the cylinder junction.
    return degrees(atan2(b.lug_tangential_width_mm/2 + b.root_fillet_mm
                        + parameters.manufacturing.radial_clearance_mm,
                        b.hub_outer_diameter_mm/2))


def _receiver_height(parameters: DesignParameters) -> float:
    b, m = parameters.bayonet, parameters.manufacturing
    slope = b.ramp_rise_mm / b.insertion_offset_deg
    return (_insertion_height(parameters) + m.minimum_loaded_wall_mm
            + b.lug_axial_thickness_mm + b.ramp_rise_mm
            + 2*slope*_track_half_span_deg(parameters) + m.axial_clearance_mm)


def _insertion_height(parameters: DesignParameters) -> float:
    b, m = parameters.bayonet, parameters.manufacturing
    # The finite-lug envelope extends below the nominal center path. Lift the
    # entire path so its lowest ramp surface still has a full loaded wall.
    return (m.minimum_loaded_wall_mm + m.axial_clearance_mm
            + 2*b.ramp_rise_mm/b.insertion_offset_deg*_track_half_span_deg(parameters))


def build_male_bayonet(parameters: DesignParameters, z_plane_mm: float = 0) -> cq.Workplane:
    """Build the locked male hub with three rounded, root-filleted lugs."""
    _validate(parameters, z_plane_mm)
    b, m = parameters.bayonet, parameters.manufacturing
    radius, wall = b.hub_outer_diameter_mm/2, m.minimum_loaded_wall_mm
    bottom = _insertion_height(parameters) + b.ramp_rise_mm
    body = (cq.Workplane("XY").workplane(offset=bottom).circle(radius)
            .circle(radius-m.minimum_loaded_wall_mm)
            .extrude(_receiver_height(parameters) + wall - bottom))
    guide = (cq.Workplane("XY").workplane(offset=bottom).circle(6.0)
             .circle(parameters.shaft.clearance_hole_diameter_mm/2)
             .extrude(_receiver_height(parameters)+wall-bottom))
    spoke = (cq.Workplane("XY").box(radius-5,3,
             _receiver_height(parameters)+wall-bottom,centered=(False,True,False))
             .translate((5,0,bottom)))
    body = body.union(guide)
    for angle in (0,120,240):
        body = body.union(spoke.rotate((0,0,0),(0,0,1),angle))
    lug = (cq.Workplane("XY").box(b.lug_radial_depth_mm + wall,
           b.lug_tangential_width_mm, b.lug_axial_thickness_mm,
           centered=(False, True, False)).translate((radius-wall, 0, bottom))
           .edges("|Z").fillet(b.root_fillet_mm))
    for angle in (0, 120, 240):
        body = body.union(lug.rotate((0,0,0), (0,0,1), angle))
    tooth_radius = _lug_outer_radius(parameters)
    tooth_wire = cq.Wire.makePolygon([
        cq.Vector(tooth_radius-0.7,-1,0),cq.Vector(tooth_radius+0.30,0,0),
        cq.Vector(tooth_radius-0.7,1,0)],close=True)
    tooth = cq.Workplane(obj=cq.Solid.extrudeLinear(tooth_wire,[],cq.Vector(0,0,1.6)))
    tooth = tooth.translate((0,0,bottom+0.8))
    for angle in (0,120,240):
        body = body.union(tooth.rotate((0,0,0),(0,0,1),angle))
    root_edges = [edge for edge in body.val().Edges()
                  if edge.geomType() == "LINE"
                  and abs(edge.Length() - b.lug_axial_thickness_mm) < 1e-6
                  and abs(hypot(edge.Center().x, edge.Center().y) - radius) < 1e-6]
    if len(root_edges) != 6:
        raise ValueError("Expected six lug-root edges for the configured bayonet")
    body = body.newObject(root_edges).fillet(b.root_fillet_mm)
    pawl_wire = cq.Wire.makePolygon([
        cq.Vector(tooth_radius+0.20,-3.85,0),cq.Vector(tooth_radius-0.55,-3.20,0),
        cq.Vector(tooth_radius+0.20,-2.55,0)],close=True)
    pawl_notch = cq.Workplane(obj=cq.Solid.extrudeLinear(pawl_wire,[],cq.Vector(0,0,2.0)))
    pawl_notch = pawl_notch.translate((0,0,bottom+0.6))
    for angle in (0,120,240):
        body = body.cut(pawl_notch.rotate((0,0,0),(0,0,1),angle))
    return body.translate((0, 0, z_plane_mm))


def _track(parameters: DesignParameters) -> cq.Workplane:
    """Loft radial rectangles into a rising channel with a finite-lug envelope.

    One-degree ruled spans approximate a helicoid. At the inner bore they are
    overlapped; at the outer radius they are extended by the chord sag so the
    running clearance is not consumed by the polygonal interpolation.
    """
    b, m = parameters.bayonet, parameters.manufacturing
    radius = b.hub_outer_diameter_mm/2
    half_span = _track_half_span_deg(parameters)
    slope = b.ramp_rise_mm / b.insertion_offset_deg
    start, end = -b.insertion_offset_deg-half_span, half_span
    count = int(end-start) + 1
    step = (end-start)/count
    outer = (_lug_outer_radius(parameters) + m.radial_clearance_mm)/cos(radians(step/2))
    inner = radius - b.root_fillet_mm
    sections = []
    for index in range(count+1):
        angle = start + index*step
        phi = radians(angle)
        lower = (_insertion_height(parameters) + slope*(angle+b.insertion_offset_deg-half_span)
                 - m.axial_clearance_mm)
        upper = (_insertion_height(parameters) + b.lug_axial_thickness_mm
                 + slope*(angle+b.insertion_offset_deg+half_span) + m.axial_clearance_mm)
        sections.append(cq.Wire.makePolygon([
            cq.Vector(r*cos(phi), r*sin(phi), z)
            for r, z in ((inner, lower), (outer, lower), (outer, upper), (inner, upper))
        ], close=True))
    channel = cq.Workplane(obj=cq.Solid.makeLoft(sections, ruled=True))
    # Preserve a flat terminal stop beyond the root blend. Its face is tangent
    # to the leading flat of the final lug, with no angular play at final zero.
    stop = (cq.Workplane("XY").box(outer*2, outer*2, _receiver_height(parameters)*3,
                                  centered=False)
            .translate((radius+b.root_fillet_mm+m.radial_clearance_mm,
                        b.lug_tangential_width_mm/2, -_receiver_height(parameters))))
    return channel.cut(stop)


def build_female_bayonet(parameters: DesignParameters, z_plane_mm: float = 0) -> cq.Workplane:
    """Build a receiver ring with top insertion windows and three rising tracks."""
    _validate(parameters, z_plane_mm)
    b, m = parameters.bayonet, parameters.manufacturing
    radius = b.hub_outer_diameter_mm/2
    height = _receiver_height(parameters)
    body = (cq.Workplane("XY").circle(_lug_outer_radius(parameters)
            + m.radial_clearance_mm + m.minimum_loaded_wall_mm)
            .circle(radius + m.radial_clearance_mm).extrude(height))
    track = _track(parameters)
    # A vertical angular window includes all lug/root surfaces at insertion.
    # Follow the actual rounded male profile, offset in XY, to keep the window
    # small enough that a locked lug remains captured beneath the roof.
    male = build_male_bayonet(parameters)
    section_z = _insertion_height(parameters) + b.ramp_rise_mm + b.lug_axial_thickness_mm/2
    section = cq.Workplane(obj=male.val()).section(section_z)
    wires = section.val().Wires()
    outline = max(wires, key=lambda item: item.Length())
    offset = outline.offset2D(m.radial_clearance_mm)[0]
    rail_top = _insertion_height(parameters)-m.axial_clearance_mm
    window = (cq.Workplane(obj=cq.Solid.extrudeLinear(
              offset, [], cq.Vector(0,0,height-rail_top+0.1)))
              .translate((0,0,rail_top-section_z))
              .rotate((0,0,0), (0,0,1), -b.insertion_offset_deg))
    for angle in (0, 120, 240):
        body = body.cut(track.rotate((0,0,0), (0,0,1), angle))
    body = body.cut(window)
    tooth_radius = _lug_outer_radius(parameters)
    notch_wire = cq.Wire.makePolygon([
        cq.Vector(tooth_radius-0.78,-1.08,0),cq.Vector(tooth_radius+0.40,0,0),
        cq.Vector(tooth_radius-0.78,1.08,0)],close=True)
    notch = cq.Workplane(obj=cq.Solid.extrudeLinear(notch_wire,[],cq.Vector(0,0,1.8)))
    notch = notch.translate((0,0,_insertion_height(parameters)+parameters.bayonet.ramp_rise_mm+0.7))
    for angle in (0,120,240):
        body = body.cut(notch.rotate((0,0,0),(0,0,1),angle))
    pawl_wire = cq.Wire.makePolygon([
        cq.Vector(tooth_radius+0.15,-3.78,0),cq.Vector(tooth_radius-0.45,-3.20,0),
        cq.Vector(tooth_radius+0.15,-2.62,0)],close=True)
    pawl = cq.Workplane(obj=cq.Solid.extrudeLinear(pawl_wire,[],cq.Vector(0,0,1.8)))
    pawl = pawl.translate((0,0,_insertion_height(parameters)+parameters.bayonet.ramp_rise_mm+0.7))
    for angle in (0,120,240):
        body = body.union(pawl.rotate((0,0,0),(0,0,1),angle))
    return body.translate((0,0,z_plane_mm))


@dataclass(frozen=True)
class BayonetCoupon:
    """Printable pair and assembly placement/fit diagnostics for export reports."""

    parameters: DesignParameters
    male: cq.Workplane
    female: cq.Workplane
    z_plane_mm: float = 0
    lug_centers_deg: tuple[float, float, float] = (0.0, 120.0, 240.0)

    def male_at_travel(self, travel_deg: float) -> cq.Workplane:
        """Place the male along its finite, positive CCW insertion-to-lock path."""
        b = self.parameters.bayonet
        if not isfinite(travel_deg) or not 0 <= travel_deg <= b.insertion_offset_deg:
            raise ValueError("Bayonet travel must lie between insertion and the locked stop")
        return (self.male.rotate((0,0,0), (0,0,1), travel_deg-b.insertion_offset_deg)
                .translate((0,0,b.ramp_rise_mm*(travel_deg/b.insertion_offset_deg-1))))

    def locked_intersection_volume_mm3(self) -> float:
        return self.male.intersect(self.female).val().Volume()

    def minimum_locked_clearance_mm(self) -> float:
        """Measured running gap; intentional tangential stop faces are omitted.

        Measure cylindrical radial and sloped axial running faces only. Stop
        and insertion-window walls are intentional tangential boundaries.
        """
        b = self.parameters.bayonet
        body = self.male.val()
        # Female cylindrical bore and the ruled track roof/floor are identified
        # by their surface normals, excluding vertical stop/window side walls.
        distances = []
        for face in self.female.val().Faces():
            normal = face.normalAt()
            center = face.Center()
            bore = face.geomType() == "CYLINDER" and hypot(center.x, center.y) < b.hub_outer_diameter_mm/2+1
            ramp = (abs(normal.z) > 0.90
                    and self.z_plane_mm + 1e-6 < center.z
                    < self.z_plane_mm + _receiver_height(self.parameters) - 1e-6)
            if bore or ramp:
                distances.append(body.distance(face))
        if not distances:
            raise ValueError("No bayonet running faces found for clearance measurement")
        return min(distances)


def build_bayonet_coupon(parameters: DesignParameters, z_plane_mm: float = 0) -> BayonetCoupon:
    """Return independent male and female print parts in their locked assembly."""
    return BayonetCoupon(parameters, build_male_bayonet(parameters, z_plane_mm),
                         build_female_bayonet(parameters, z_plane_mm), z_plane_mm)
