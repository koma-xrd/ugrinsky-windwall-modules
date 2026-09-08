"""Export and inspect the complete rotor through scripts/run_geometry.py.

The coupon is generated first, followed by unique print candidates and named
locked/exploded STEP assemblies. PNG sections use the exported STEP solids.
These artifacts establish CAD geometry only; this script never prints a part.
"""

import argparse
import json
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for import_root in (PROJECT_ROOT,PROJECT_ROOT/'src'):
    if str(import_root) not in sys.path:
        sys.path.insert(0,str(import_root))

import cadquery as cq

from scripts.preview_generator import _export_print_candidate, export_magnet_pocket_coupon
from windwall.assembly import (audit_rotor_assembly, build_exploded_rotor_assembly,
                               build_locked_rotor_assembly)
from windwall.assembly_validation import require_valid_assembly_audit
from windwall.parameters import DEFAULT_PARAMETERS, DesignParameters


def _static_inspection(destination: Path, report: dict) -> None:
    # Keep the default plotting cache inside the authorized workspace. Respect
    # an explicit caller setting; Matplotlib otherwise uses the profile folder.
    cache = PROJECT_ROOT/'build/matplotlib'
    cache.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR',str(cache))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import to_rgb

    locked = cq.importers.importStep(str(destination/'rotor_locked.step')).val()
    exploded = cq.importers.importStep(str(destination/'rotor_exploded.step')).val()
    fig = plt.figure(figsize=(17,12))
    grid = fig.add_gridspec(2,3,width_ratios=(1,1,1.35))
    for column,shape,title in ((0,locked,'Locked | seven stages, 490 mm'),
                               (1,exploded,'Exploded | entry poses at -18 degrees')):
        ax = fig.add_subplot(grid[:,column])
        view = np.array([1.,-2.,0.3]); view /= np.linalg.norm(view)
        right = np.array([2.,1.,0.]); right /= np.linalg.norm(right)
        up = np.cross(view,right)
        polygons,depths,colors = [],[],[]
        for solid in shape.Solids():
            box = solid.BoundingBox()
            color = '#dda345' if box.zmin > 480 and box.xlen > 100 and box.zlen < 20 else '#68a0bf' if box.zmax > 0 and 75 < box.zlen < 100 else '#8c949c'
            vertices,triangles = solid.tessellate(0.25,0.3)
            points = np.array([v.toTuple() for v in vertices])
            triangles_xyz = points[np.array(triangles)]
            normals = np.cross(triangles_xyz[:,1]-triangles_xyz[:,0],triangles_xyz[:,2]-triangles_xyz[:,0])
            normals /= np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
            light = .45+.55*np.abs(normals@view)
            polygons.append(np.stack((triangles_xyz@right,triangles_xyz@up),axis=2))
            depths.append((triangles_xyz@view).mean(axis=1))
            colors.append(light[:,None]*np.array(to_rgb(color)))
        order = np.argsort(np.concatenate(depths))
        ax.add_collection(PolyCollection(np.concatenate(polygons)[order],
                         facecolors=np.concatenate(colors)[order],edgecolors='none'))
        ax.autoscale_view(); ax.set_aspect('equal'); ax.margins(.06)
        ax.set_title(title,pad=14); ax.set_ylabel('Projected height / mm')
        ax.set_xlabel('Projected width / mm'); ax.grid(alpha=.15)
    top_z = report['top_blade_end_z_mm']
    for row,limits,title in ((0,(top_z-5,locked.BoundingBox().zmax+6),'Top section | cap clear of M8 clamp'),
                             (1,(locked.BoundingBox().zmin-1,2),'Generator section | common shaft')):
        ax = fig.add_subplot(grid[row,2])
        for solid in locked.Solids():
            box = solid.BoundingBox()
            if box.zmax < limits[0] or box.zmin > limits[1]:
                continue
            color = '#cc9029' if box.zmin > top_z-0.1 and box.xlen > 100 else '#317ca4' if box.xlen > 30 else '#655076'
            section = cq.Workplane(obj=solid).rotate((0,0,0),(1,0,0),90).section(0)
            for edge in section.val().Edges():
                points = edge.positions(np.linspace(0,1,max(2,int(edge.Length()/0.2))))
                ax.plot([v.x for v in points],[-v.y for v in points],color=color,lw=1.1)
        ax.set_xlim(-63,63); ax.set_ylim(*limits); ax.set_aspect('equal'); ax.grid(alpha=.2)
        ax.set_title(title,pad=22 if row == 0 else 8); ax.set_xlabel('X / mm'); ax.set_ylabel('Z / mm')
        if row == 0:
            ax.text(0,limits[1]-2,f"Minimum cap/hardware gap: {report['closure_hardware_clearance_mm']:.2f} mm",
                    ha='center',fontsize=8)
    fig.suptitle('Actual exported STEP solids | Task 8 rotor assembly\n'
                 '+60 degree internal twist retained; -60 degree blade phase jump at every seam. Physical fit unverified.',fontsize=14)
    fig.subplots_adjust(top=.91,bottom=.07,wspace=.23,hspace=.35)
    fig.savefig(destination/'assembly_inspection.png',dpi=140)
    plt.close(fig)


def export_assembly(parameters: DesignParameters, output_dir: Path) -> dict:
    """Audit, export and round-trip all solids without hiding validation failures."""
    output_dir.mkdir(parents=True,exist_ok=True)
    exports = {'magnet_pocket_coupon':export_magnet_pocket_coupon(parameters,output_dir)}
    locked = build_locked_rotor_assembly(parameters)
    report = audit_rotor_assembly(locked)
    require_valid_assembly_audit(report)
    exploded = build_exploded_rotor_assembly(parameters,locked=locked)
    unique = {f'{name}_module':shape for name,shape in locked.local_modules.items()}
    unique.update(top_closure=locked.parts['top_closure'].translate((0,0,-locked.stages[-1].z_mm)),
                  lower_magnet_rotor=locked.parts['lower_magnet_rotor'])
    for name,shape in unique.items():
        exports[name] = _export_print_candidate(name,shape,parameters,output_dir)
    for name,model in (('rotor_locked',locked),('rotor_exploded',exploded)):
        model.as_cq_assembly().export(str(output_dir/f'{name}.step'))
        imported = cq.importers.importStep(str(output_dir/f'{name}.step')).val()
        if not imported.isValid() or len(imported.Solids()) != len(model.parts):
            raise ValueError(f'{name} STEP round trip lost valid assembly components')
    section_bottom = report['top_blade_end_z_mm']-5
    section_height = locked.parts['top_closure'].val().BoundingBox().zmax-section_bottom+1
    slab = cq.Workplane('XY').box(parameters.blade.rotor_radius_mm*2+5,0.2,section_height,
                                centered=(True,True,False)).translate((0,0,section_bottom))
    sections = [shape.intersect(slab).val() for shape in locked.parts.values()
                if shape.val().BoundingBox().zmax >= section_bottom]
    cq.exporters.export(cq.Compound.makeCompound(sections),str(output_dir/'top_closure_section.svg'),opt={
        'projectionDir':(0,-1,0),'showHidden':False,'width':1100,'height':450})
    _static_inspection(output_dir,report)
    report.update(export_order=list(exports),exports=exports,
                  exploded_stage_poses=[{'name':s.name,'z_mm':s.z_mm,'angle_deg':s.angle_deg} for s in exploded.stages],
                  exploded_pose_basis={'lift_from_entry_mm':parameters.closure.exploded_joint_lift_mm,
                      'cumulative_increment_above_lock_mm':parameters.closure.exploded_joint_lift_mm-parameters.bayonet.ramp_rise_mm,
                      'upper_frame_angle_deg':-parameters.bayonet.insertion_offset_deg,
                      'frame_reference':'Each upper pose refers to its own locked lower frame'},
                  static_qa_artifact='assembly_inspection.png')
    (output_dir/'assembly_fit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=PROJECT_ROOT/'build/assembly')
    args = parser.parse_args()
    print(json.dumps(export_assembly(DEFAULT_PARAMETERS,args.output_dir),indent=2),flush=True)
    return 0


if 'show_object' in globals():
    model = build_locked_rotor_assembly(DEFAULT_PARAMETERS)
    show_object(model.as_cq_assembly(),name='Locked rotor | seven stages | +60 degree twist per stage')
    exploded = build_exploded_rotor_assembly(DEFAULT_PARAMETERS,locked=model)
    for name,shape in exploded.parts.items():
        show_object(shape.translate((180,0,0)),name=f'Exploded: {name}')
    section_box = cq.Workplane('XY').box(125,0.2,580,centered=(True,True,False)).translate((0,0,-65))
    for name,shape in model.parts.items():
        show_object(shape.intersect(section_box).translate((-180,0,0)),name=f'Section: {name}')
elif __name__ == '__main__':
    raise SystemExit(main())
