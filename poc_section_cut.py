#!/usr/bin/env python3
"""
POC: Section Cut approach for precise contour extraction from STEP files.

Instead of classifying individual B-rep faces (error-prone), we:
1. Load STEP → get solid shape
2. Detect rotation axis (from principal inertia)
3. For ROTATIONAL parts: cut with half-plane through axis → 2D profile
4. For PRISMATIC parts: cut with XY, XZ, YZ planes → 3 orthogonal views
5. Extract (r,z) or (x,y) points from section edges

This replaces 608 LOC contour_builder.py with ~150 LOC of direct OCCT geometry.
"""

import json
import math
import sys
from pathlib import Path

# OCCT imports
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCC.Core.gp import gp_Pln, gp_Ax3, gp_Pnt, gp_Dir, gp_Ax1, gp_Ax2
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_SOLID, TopAbs_FACE, TopAbs_VERTEX
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCC.Core.GeomAbs import (
    GeomAbs_Line, GeomAbs_Circle, GeomAbs_Ellipse,
    GeomAbs_BSplineCurve, GeomAbs_Cylinder, GeomAbs_Cone,
    GeomAbs_Torus, GeomAbs_Plane, GeomAbs_Sphere
)
from OCC.Core.GCPnts import GCPnts_UniformAbscissa
from OCC.Core.TopoDS import topods
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRep import BRep_Tool


def load_step(path: str):
    """Load STEP file, return shape."""
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(path))
    if status != IFSelect_RetDone:
        raise ValueError(f"Failed to read STEP file: {path}")
    reader.TransferRoots()
    shape = reader.OneShape()
    if shape.IsNull():
        raise ValueError(f"No shape in STEP file: {path}")
    return shape


def get_bounding_box(shape):
    """Get bounding box of shape."""
    bbox = Bnd_Box()
    brepbndlib.Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    return {
        'x_min': round(xmin, 3), 'x_max': round(xmax, 3),
        'y_min': round(ymin, 3), 'y_max': round(ymax, 3),
        'z_min': round(zmin, 3), 'z_max': round(zmax, 3),
        'dx': round(xmax - xmin, 3),
        'dy': round(ymax - ymin, 3),
        'dz': round(zmax - zmin, 3),
    }


def get_volume(shape):
    """Get volume in mm³."""
    props = GProp_GProps()
    brepgprop.VolumeProperties(shape, props)
    return round(props.Mass(), 2)


def detect_part_type_and_axis(shape):
    """
    Detect if part is rotational or prismatic + rotation axis.

    Uses surface type analysis + finds actual axis POSITION (not just direction).
    This is critical - the axis of rotation may not pass through origin!
    """
    surf_types = {'cylinder': [], 'cone': [], 'torus': [], 'plane': [], 'other': []}
    # Store full axis info: direction + position + radius
    axis_entries = []

    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        adaptor = BRepAdaptor_Surface(face)
        stype = adaptor.GetType()

        if stype == GeomAbs_Cylinder:
            cyl = adaptor.Cylinder()
            ax = cyl.Axis()
            r = cyl.Radius()
            loc = ax.Location()
            d = ax.Direction()
            surf_types['cylinder'].append({
                'radius': r,
                'axis_dir': (d.X(), d.Y(), d.Z()),
                'axis_pos': (loc.X(), loc.Y(), loc.Z()),
            })
            axis_entries.append({
                'dir': (d.X(), d.Y(), d.Z()),
                'pos': (loc.X(), loc.Y(), loc.Z()),
                'radius': r,
            })
        elif stype == GeomAbs_Cone:
            cone = adaptor.Cone()
            ax = cone.Axis()
            loc = ax.Location()
            d = ax.Direction()
            surf_types['cone'].append({
                'axis_dir': (d.X(), d.Y(), d.Z()),
                'axis_pos': (loc.X(), loc.Y(), loc.Z()),
            })
            axis_entries.append({
                'dir': (d.X(), d.Y(), d.Z()),
                'pos': (loc.X(), loc.Y(), loc.Z()),
                'radius': 0,
            })
        elif stype == GeomAbs_Torus:
            torus = adaptor.Torus()
            ax = torus.Axis()
            loc = ax.Location()
            d = ax.Direction()
            surf_types['torus'].append({
                'axis_dir': (d.X(), d.Y(), d.Z()),
                'axis_pos': (loc.X(), loc.Y(), loc.Z()),
            })
            axis_entries.append({
                'dir': (d.X(), d.Y(), d.Z()),
                'pos': (loc.X(), loc.Y(), loc.Z()),
                'radius': 0,
            })
        elif stype == GeomAbs_Plane:
            surf_types['plane'].append({})
        else:
            surf_types['other'].append({})

        explorer.Next()

    total_faces = sum(len(v) for v in surf_types.values())
    rotational_faces = len(surf_types['cylinder']) + len(surf_types['cone']) + len(surf_types['torus'])

    # Classify main axis direction
    def classify_dir(d):
        dx, dy, dz = d
        if abs(dz) > 0.9: return 'z'
        if abs(dx) > 0.9: return 'x'
        if abs(dy) > 0.9: return 'y'
        return None

    axis_counts = {'x': 0, 'y': 0, 'z': 0}
    axis_max_r = {'x': 0.0, 'y': 0.0, 'z': 0.0}  # MAX radius per axis (not sum!)
    for entry in axis_entries:
        label = classify_dir(entry['dir'])
        if label:
            axis_counts[label] += 1
            axis_max_r[label] = max(axis_max_r[label], entry['radius'])

    # Determine main axis: LARGEST CYLINDER wins (not count or sum!)
    # One Ø45 cylinder on Z-axis is more important than 8× Ø30.5 on Y-axis
    main_axis = None
    if axis_entries:
        main_axis = max(axis_max_r.items(), key=lambda x: x[1])[0]
        if axis_max_r[main_axis] == 0:
            main_axis = max(axis_counts.items(), key=lambda x: x[1])[0]

    # Find axis POSITION from the largest cylinder on main axis
    axis_position = (0.0, 0.0, 0.0)
    if main_axis and axis_entries:
        main_cylinders = [
            e for e in axis_entries
            if classify_dir(e['dir']) == main_axis and e['radius'] > 0
        ]
        if main_cylinders:
            largest = max(main_cylinders, key=lambda e: e['radius'])
            axis_position = largest['pos']

    rotational_ratio = rotational_faces / total_faces if total_faces > 0 else 0

    # Prismatic detection: if cylinders are on MULTIPLE distinct axes (>2 axis positions),
    # it's likely prismatic with holes/bores, not a rotational part.
    # Rotational parts have all main cylinders on ONE axis line.
    n_distinct_axes = sum(1 for c in axis_counts.values() if c > 0)
    axis_positions_on_main = set()
    if main_axis:
        for entry in axis_entries:
            if classify_dir(entry['dir']) == main_axis and entry['radius'] > 0:
                # Group by perpendicular position (round to 1mm)
                if main_axis == 'z':
                    key = (round(entry['pos'][0], 0), round(entry['pos'][1], 0))
                elif main_axis == 'y':
                    key = (round(entry['pos'][0], 0), round(entry['pos'][2], 0))
                else:
                    key = (round(entry['pos'][1], 0), round(entry['pos'][2], 0))
                axis_positions_on_main.add(key)

    n_axis_positions = len(axis_positions_on_main)

    # Heuristic: rotational if:
    # 1. High rotational ratio (>40%) AND
    # 2. Main cylinders share 1-2 axis positions (concentric = same axis line)
    # Prismatic if: many distinct axis positions (bolt circles, multiple bores)
    is_rotational = rotational_ratio > 0.40 and n_axis_positions <= 3

    return {
        'type': 'rotational' if is_rotational else 'prismatic',
        'main_axis': main_axis,
        'axis_position': axis_position,
        'rotational_ratio': round(rotational_ratio, 2),
        'face_counts': {k: len(v) for k, v in surf_types.items()},
        'total_faces': total_faces,
        'largest_cylinder_r': max([c['radius'] for c in surf_types['cylinder']], default=0),
        'n_distinct_axis_positions': n_axis_positions,
        'axis_max_r': {k: round(v, 2) for k, v in axis_max_r.items()},
    }


def section_cut_rotational(shape, main_axis='z', axis_position=(0, 0, 0)):
    """
    Section cut for rotational parts.

    Cuts the solid with a plane through the ACTUAL rotation axis.
    The plane passes through axis_position (not necessarily origin!).

    Returns raw edges + derived outer/inner contour as (r, z) points.

    Coordinate mapping (r = radial distance from axis, z = along axis):
      axis='z': plane normal=Y at axis_pos, r=distance from axis in X, z=Z
      axis='y': plane normal=Z at axis_pos, r=distance from axis in X/Z, z=Y
      axis='x': plane normal=Y at axis_pos, r=distance from axis in Y/Z, z=X
    """
    # STRATEGY: The rotation axis is a LINE, not a point.
    # axis_position is a point on this line (from the largest cylinder).
    # The line goes: axis_position + t * axis_direction.
    #
    # For the section cut, we need planes that CONTAIN this line.
    # A plane containing a line has its normal perpendicular to the line direction.
    # The plane must also pass through a point on the line.
    #
    # axis_position might be outside the solid (it's the cylinder base center).
    # But any point on the axis line that's inside the bbox works.
    # We project the bbox center onto the axis line to get a point inside the solid.

    bbox = Bnd_Box()
    brepbndlib.Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    cx, cy, cz = (xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2

    ax, ay, az = axis_position

    # Build a point on the rotation axis that's at the bbox center along the axis direction.
    # For axis='y': axis line is (ax, t, az). Place cut at t = cy (bbox center Y).
    # The point on axis is (ax, cy, az) — uses axis X,Z from cylinder, Y from bbox center.
    if main_axis == 'z':
        axis_point = gp_Pnt(ax, ay, cz)  # axis X,Y from cylinder, Z from bbox
    elif main_axis == 'y':
        axis_point = gp_Pnt(ax, cy, az)  # axis X,Z from cylinder, Y from bbox
    else:  # x
        axis_point = gp_Pnt(cx, ay, az)  # axis Y,Z from cylinder, X from bbox

    # Two perpendicular planes, both containing the rotation axis
    planes = []

    if main_axis == 'z':
        # Axis along Z through (ax, ay, z). Two planes containing this line:
        planes.append(('XZ', gp_Pln(gp_Ax3(axis_point, gp_Dir(0, 1, 0)))))  # normal Y
        planes.append(('YZ', gp_Pln(gp_Ax3(axis_point, gp_Dir(1, 0, 0)))))  # normal X
    elif main_axis == 'y':
        # Axis along Y through (ax, y, az). Two planes containing this line:
        planes.append(('XY', gp_Pln(gp_Ax3(axis_point, gp_Dir(0, 0, 1)))))  # normal Z → plane at z=az
        planes.append(('XZ', gp_Pln(gp_Ax3(axis_point, gp_Dir(1, 0, 0)))))  # normal X → plane at x=ax
    else:  # x
        # Axis along X through (x, ay, az). Two planes containing this line:
        planes.append(('XY', gp_Pln(gp_Ax3(axis_point, gp_Dir(0, 0, 1)))))  # normal Z
        planes.append(('XZ', gp_Pln(gp_Ax3(axis_point, gp_Dir(0, 1, 0)))))  # normal Y

    print(f"  Rotation axis point: ({axis_point.X():.2f}, {axis_point.Y():.2f}, {axis_point.Z():.2f})")
    print(f"  BBox center: ({cx:.2f}, {cy:.2f}, {cz:.2f})")
    print(f"  Axis position (from cyl): ({ax:.2f}, {ay:.2f}, {az:.2f})")

    all_results = {}

    for plane_name, plane in planes:
        section = BRepAlgoAPI_Section(shape, plane)
        section.Build()

        if not section.IsDone():
            all_results[plane_name] = {'edges': [], 'all_points': []}
            continue

        section_shape = section.Shape()
        all_points = []
        edge_data = []

        explorer = TopExp_Explorer(section_shape, TopAbs_EDGE)
        edge_idx = 0
        while explorer.More():
            edge = topods.Edge(explorer.Current())
            adaptor = BRepAdaptor_Curve(edge)
            curve_type = adaptor.GetType()

            u_first = adaptor.FirstParameter()
            u_last = adaptor.LastParameter()

            if curve_type == GeomAbs_Line:
                n_pts = 2
            elif curve_type == GeomAbs_Circle:
                n_pts = 20
            else:
                n_pts = 15

            edge_points = []
            for i in range(n_pts):
                u = u_first + (u_last - u_first) * i / (n_pts - 1)
                pt = adaptor.Value(u)

                # Convert to (r, z) relative to rotation axis
                # r = perpendicular distance from the rotation axis LINE
                # z = position along the rotation axis
                # axis_position is a point ON the axis line
                px, py, pz = pt.X(), pt.Y(), pt.Z()
                ax, ay, az = axis_position

                if main_axis == 'z':
                    r = math.sqrt((px - ax)**2 + (py - ay)**2)
                    z = pz
                elif main_axis == 'y':
                    r = math.sqrt((px - ax)**2 + (pz - az)**2)
                    z = py
                else:  # x
                    r = math.sqrt((py - ay)**2 + (pz - az)**2)
                    z = px

                edge_points.append({'r': round(r, 4), 'z': round(z, 4)})
                all_points.append({'r': round(r, 4), 'z': round(z, 4)})

            type_names = {
                GeomAbs_Line: 'line', GeomAbs_Circle: 'arc',
                GeomAbs_Ellipse: 'ellipse', GeomAbs_BSplineCurve: 'bspline',
            }

            edge_data.append({
                'index': edge_idx,
                'type': type_names.get(curve_type, f'other({curve_type})'),
                'points': edge_points,
                'n_points': len(edge_points),
            })

            edge_idx += 1
            explorer.Next()

        all_results[plane_name] = {'edges': edge_data, 'all_points': all_points}

    # Merge points from all planes
    merged_points = []
    all_edges = []
    for plane_name, data in all_results.items():
        merged_points.extend(data['all_points'])
        for e in data['edges']:
            e['plane'] = plane_name
            all_edges.append(e)

    if not merged_points:
        return {
            'outer_contour': [], 'inner_contour': [],
            'edges': all_edges, 'total_points': 0,
            'z_range': [], 'max_radius': 0,
            'planes_used': list(all_results.keys()),
            'edges_per_plane': {k: len(v['edges']) for k, v in all_results.items()},
        }

    # Build contours from merged points
    # r is always positive (it's a distance from axis)
    sorted_pts = sorted(merged_points, key=lambda p: p['z'])
    z_min = sorted_pts[0]['z']
    z_max = sorted_pts[-1]['z']

    # Group by z with tolerance, extract max_r (outer) and min_r (inner)
    z_tolerance = 0.05
    z_values = sorted(set(round(p['z'], 3) for p in merged_points))

    outer_contour = []
    inner_contour = []

    for z_val in z_values:
        nearby = [p for p in merged_points if abs(p['z'] - z_val) < z_tolerance]
        if nearby:
            r_values = [p['r'] for p in nearby]
            max_r = max(r_values)
            min_r = min(r_values)

            outer_contour.append({'r': round(max_r, 4), 'z': round(z_val, 4)})
            if min_r < max_r - 0.1:  # Inner contour exists
                inner_contour.append({'r': round(min_r, 4), 'z': round(z_val, 4)})

    return {
        'outer_contour': outer_contour,
        'inner_contour': inner_contour,
        'edges': all_edges,
        'total_points': len(merged_points),
        'z_range': [round(z_min, 3), round(z_max, 3)],
        'max_radius': round(max(p['r'] for p in merged_points), 3),
        'planes_used': list(all_results.keys()),
        'edges_per_plane': {k: len(v['edges']) for k, v in all_results.items()},
    }


def section_cut_prismatic(shape):
    """
    Section cuts for prismatic parts.

    Cuts with 3 orthogonal planes through center of mass:
    - XY plane (top view)
    - XZ plane (front view)
    - YZ plane (side view)

    Returns edges for each view.
    """
    # Get center of mass for plane placement
    props = GProp_GProps()
    brepgprop.VolumeProperties(shape, props)
    com = props.CentreOfMass()

    views = {}

    plane_configs = {
        'top_XY': gp_Pln(gp_Ax3(gp_Pnt(com.X(), com.Y(), com.Z()), gp_Dir(0, 0, 1))),
        'front_XZ': gp_Pln(gp_Ax3(gp_Pnt(com.X(), com.Y(), com.Z()), gp_Dir(0, 1, 0))),
        'side_YZ': gp_Pln(gp_Ax3(gp_Pnt(com.X(), com.Y(), com.Z()), gp_Dir(1, 0, 0))),
    }

    for view_name, plane in plane_configs.items():
        section = BRepAlgoAPI_Section(shape, plane)
        section.Build()

        if not section.IsDone():
            views[view_name] = {'edges': [], 'points': []}
            continue

        section_shape = section.Shape()
        edges = []
        all_points = []

        explorer = TopExp_Explorer(section_shape, TopAbs_EDGE)
        while explorer.More():
            edge = topods.Edge(explorer.Current())
            adaptor = BRepAdaptor_Curve(edge)
            curve_type = adaptor.GetType()

            u_first = adaptor.FirstParameter()
            u_last = adaptor.LastParameter()

            n_pts = 2 if curve_type == GeomAbs_Line else 15

            edge_points = []
            for i in range(n_pts):
                u = u_first + (u_last - u_first) * i / (n_pts - 1)
                pt = adaptor.Value(u)
                p = {'x': round(pt.X(), 4), 'y': round(pt.Y(), 4), 'z': round(pt.Z(), 4)}
                edge_points.append(p)
                all_points.append(p)

            type_names = {
                GeomAbs_Line: 'line', GeomAbs_Circle: 'arc',
                GeomAbs_Ellipse: 'ellipse', GeomAbs_BSplineCurve: 'bspline',
            }

            edges.append({
                'type': type_names.get(curve_type, 'other'),
                'points': edge_points,
            })

            explorer.Next()

        views[view_name] = {
            'n_edges': len(edges),
            'n_points': len(all_points),
            'edges': edges,
        }

    return views


def analyze_surfaces(shape):
    """
    Analyze all surfaces in the shape for feature classification.
    Returns summary of surface types with their geometric parameters.
    """
    surfaces = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)

    while explorer.More():
        face = topods.Face(explorer.Current())
        adaptor = BRepAdaptor_Surface(face)
        stype = adaptor.GetType()

        info = {'type': str(stype)}

        if stype == GeomAbs_Cylinder:
            cyl = adaptor.Cylinder()
            ax = cyl.Axis()
            info = {
                'type': 'cylinder',
                'radius': round(cyl.Radius(), 4),
                'axis': (round(ax.Direction().X(), 3), round(ax.Direction().Y(), 3), round(ax.Direction().Z(), 3)),
                'position': (round(ax.Location().X(), 3), round(ax.Location().Y(), 3), round(ax.Location().Z(), 3)),
            }
        elif stype == GeomAbs_Cone:
            cone = adaptor.Cone()
            ax = cone.Axis()
            info = {
                'type': 'cone',
                'semi_angle_deg': round(math.degrees(cone.SemiAngle()), 2),
                'ref_radius': round(cone.RefRadius(), 4),
                'axis': (round(ax.Direction().X(), 3), round(ax.Direction().Y(), 3), round(ax.Direction().Z(), 3)),
            }
        elif stype == GeomAbs_Torus:
            torus = adaptor.Torus()
            info = {
                'type': 'torus',
                'major_radius': round(torus.MajorRadius(), 4),
                'minor_radius': round(torus.MinorRadius(), 4),
            }
        elif stype == GeomAbs_Plane:
            pln = adaptor.Plane()
            ax = pln.Axis()
            info = {
                'type': 'plane',
                'normal': (round(ax.Direction().X(), 3), round(ax.Direction().Y(), 3), round(ax.Direction().Z(), 3)),
            }
        elif stype == GeomAbs_Sphere:
            sph = adaptor.Sphere()
            info = {
                'type': 'sphere',
                'radius': round(sph.Radius(), 4),
            }
        else:
            info = {'type': f'other({stype})'}

        surfaces.append(info)
        explorer.Next()

    return surfaces


def process_step_file(step_path: str):
    """Main processing function for a single STEP file."""
    print(f"\n{'='*70}")
    print(f"PROCESSING: {Path(step_path).name}")
    print(f"{'='*70}")

    # 1. Load STEP
    shape = load_step(step_path)

    # 2. Basic info
    bbox = get_bounding_box(shape)
    volume = get_volume(shape)
    print(f"\nBounding box: {bbox['dx']}×{bbox['dy']}×{bbox['dz']} mm")
    print(f"Volume: {volume} mm³ ({round(volume/1000, 2)} cm³)")

    # 3. Detect part type
    part_info = detect_part_type_and_axis(shape)
    print(f"\nPart type: {part_info['type']}")
    print(f"Main axis: {part_info['main_axis']}")
    print(f"Rotational ratio: {part_info['rotational_ratio']}")
    print(f"Face counts: {part_info['face_counts']}")
    print(f"Largest cylinder R: {part_info['largest_cylinder_r']} mm")

    # 4. Surface analysis (detailed)
    surfaces = analyze_surfaces(shape)
    print(f"\nSurface analysis ({len(surfaces)} faces):")
    type_summary = {}
    for s in surfaces:
        t = s['type']
        type_summary[t] = type_summary.get(t, 0) + 1
    for t, c in sorted(type_summary.items()):
        print(f"  {t}: {c}")

    # Print cylinder details
    cylinders = [s for s in surfaces if s['type'] == 'cylinder']
    if cylinders:
        print(f"\n  Cylinders (Ø mm):")
        # Group by diameter
        diameters = {}
        for c in cylinders:
            d = round(c['radius'] * 2, 2)
            if d not in diameters:
                diameters[d] = 0
            diameters[d] += 1
        for d in sorted(diameters.keys()):
            print(f"    Ø{d} mm × {diameters[d]} surfaces")

    # Print cone details
    cones = [s for s in surfaces if s['type'] == 'cone']
    if cones:
        print(f"\n  Cones:")
        for c in cones:
            print(f"    semi_angle={c['semi_angle_deg']}° ref_r={c['ref_radius']} mm")

    # 5. Section cut
    result = {'bbox': bbox, 'volume': volume, 'part_info': part_info}

    if part_info['type'] == 'rotational':
        print(f"\n--- SECTION CUT (rotational, axis={part_info['main_axis']}, pos={part_info['axis_position']}) ---")
        cut = section_cut_rotational(shape, part_info['main_axis'], part_info['axis_position'])
        if cut:
            print(f"Planes used: {cut['planes_used']}")
            print(f"Edges per plane: {cut['edges_per_plane']}")
            print(f"Total edges: {len(cut['edges'])}")
            print(f"Total points: {cut['total_points']}")
            print(f"Z range: {cut['z_range']}")
            print(f"Max radius: {cut['max_radius']} mm (Ø{round(cut['max_radius']*2, 2)} mm)")

            print(f"\nOuter contour ({len(cut['outer_contour'])} points):")
            for p in cut['outer_contour']:
                print(f"  z={p['z']:8.3f}  r={p['r']:8.3f}  (Ø{round(p['r']*2, 2)})")

            if cut['inner_contour']:
                print(f"\nInner contour ({len(cut['inner_contour'])} points):")
                for p in cut['inner_contour']:
                    print(f"  z={p['z']:8.3f}  r={p['r']:8.3f}  (Ø{round(p['r']*2, 2)})")
            else:
                print("\nNo inner contour (solid part)")

            print(f"\nEdge details:")
            for e in cut['edges']:
                p0 = e['points'][0]
                p1 = e['points'][-1]
                plane_tag = f"[{e.get('plane', '?')}]"
                print(f"  Edge {e['index']:2d}: {e['type']:8s} {plane_tag:5s} | "
                      f"r=({p0['r']:7.3f} → {p1['r']:7.3f}), z=({p0['z']:7.3f} → {p1['z']:7.3f})")

            result['section_cut'] = cut
        else:
            print("Section cut FAILED")
    else:
        print(f"\n--- SECTION CUT (prismatic, 3 views) ---")
        views = section_cut_prismatic(shape)
        for view_name, view_data in views.items():
            print(f"\n  {view_name}: {view_data['n_edges']} edges, {view_data['n_points']} points")
        result['section_cuts'] = views

    # Always also do a rotational cut for comparison (even for prismatic)
    if part_info['type'] == 'prismatic' and part_info['main_axis']:
        print(f"\n--- BONUS: Rotational cut on prismatic (axis={part_info['main_axis']}) ---")
        cut = section_cut_rotational(shape, part_info['main_axis'], part_info['axis_position'])
        if cut:
            print(f"  Edges: {len(cut['edges'])}, Max R: {cut['max_radius']} mm")
            result['rotational_cut_bonus'] = cut

    return result


if __name__ == '__main__':
    base = Path(__file__).parent / 'uploads' / 'drawings'

    files = [
        base / 'JR 810666.ipt.step',
        base / '3DM_90057637_000_00.stp',
        base / 'JR 808404.ipt.step',
    ]

    results = {}
    for f in files:
        if f.exists():
            try:
                result = process_step_file(str(f))
                results[f.name] = result
            except Exception as e:
                print(f"\nERROR processing {f.name}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"\nFILE NOT FOUND: {f}")

    # Save raw results
    output_path = base / 'poc_section_cut_results.json'

    # Serialize (remove edge detail for JSON)
    json_results = {}
    for name, res in results.items():
        jr = dict(res)
        if 'section_cut' in jr:
            # Keep contours, summarize edges
            jr['section_cut'] = {
                'outer_contour': jr['section_cut']['outer_contour'],
                'inner_contour': jr['section_cut']['inner_contour'],
                'n_edges': len(jr['section_cut']['edges']),
                'z_range': jr['section_cut']['z_range'],
                'max_radius': jr['section_cut']['max_radius'],
            }
        json_results[name] = jr

    with open(output_path, 'w') as fp:
        json.dump(json_results, fp, indent=2, default=str)

    print(f"\n\nResults saved to: {output_path}")
