import math
import random
import svgwrite
from shapely.geometry import Polygon, Point
from shapely.affinity import rotate, translate


# -----------------------------------------------
# Basic Functions: Generate rectangular rings and convert to SVG path strings
# -----------------------------------------------

def create_rectangle_ring(cx, cy, outer_w, outer_h, inner_w, inner_h, angle):
    """
    Generate a rectangular ring (frame) by subtracting an inner rectangle from an outer rectangle.

    Parameters:
      cx, cy:           Center coordinates of the ring.
      outer_w, outer_h: Width and height of the outer rectangle.
      inner_w, inner_h: Width and height of the inner rectangle (should be smaller than the outer rectangle).
      angle:            Rotation angle (in degrees) about the center.

    Returns:
      A Shapely Polygon representing the ring.
    """
    # Construct the outer rectangle (starting at (0,0))
    outer_rect = Polygon([
        (0, 0),
        (outer_w, 0),
        (outer_w, outer_h),
        (0, outer_h)
    ])
    # Construct the inner rectangle (starting at (0,0))
    inner_rect = Polygon([
        (0, 0),
        (inner_w, 0),
        (inner_w, inner_h),
        (0, inner_h)
    ])
    # Translate the inner rectangle to center it within the outer rectangle
    inner_rect = translate(inner_rect, xoff=(outer_w - inner_w) / 2.0, yoff=(outer_h - inner_h) / 2.0)
    # Subtract the inner rectangle from the outer rectangle to form the ring
    ring = outer_rect.difference(inner_rect)
    # Translate the ring so that its center is at the origin
    ring = translate(ring, xoff=-outer_w / 2.0, yoff=-outer_h / 2.0)
    # Rotate the ring about the origin by the specified angle
    ring = rotate(ring, angle, origin=(0, 0), use_radians=False)
    # Translate the ring to the specified center (cx, cy)
    ring = translate(ring, xoff=cx, yoff=cy)
    return ring


def create_inner_polygon(cx, cy, outer_w, outer_h, inner_w, inner_h, angle):
    """
    Generate the inner polygon (hole) of the coaster, used for constraint detection.

    Parameters are the same as for create_rectangle_ring, but this function only generates
    the inner rectangle after translation and rotation.

    Returns:
      A Shapely Polygon representing the inner area of the coaster.
    """
    inner_rect = Polygon([
        (0, 0),
        (inner_w, 0),
        (inner_w, inner_h),
        (0, inner_h)
    ])
    inner_rect = translate(inner_rect, xoff=(outer_w - inner_w) / 2.0, yoff=(outer_h - inner_h) / 2.0)
    inner_rect = translate(inner_rect, xoff=-outer_w / 2.0, yoff=-outer_h / 2.0)
    inner_rect = rotate(inner_rect, angle, origin=(0, 0), use_radians=False)
    inner_rect = translate(inner_rect, xoff=cx, yoff=cy)
    return inner_rect


def polygon_to_path(poly):
    """
    Convert a single Shapely Polygon (including holes) to an SVG path string.
    """
    exterior_coords = list(poly.exterior.coords)
    path_str = f"M {exterior_coords[0][0]} {exterior_coords[0][1]}"
    for x, y in exterior_coords[1:]:
        path_str += f" L {x} {y}"
    path_str += " Z"
    for interior in poly.interiors:
        interior_coords = list(interior.coords)
        path_str += f" M {interior_coords[0][0]} {interior_coords[0][1]}"
        for x, y in interior_coords[1:]:
            path_str += f" L {x} {y}"
        path_str += " Z"
    return path_str


def shapely_to_svg_path(geom):
    """
    Convert a Shapely geometry object (Polygon or MultiPolygon) to an SVG path string.
    """
    if geom.is_empty:
        return ""
    if geom.geom_type == 'Polygon':
        return polygon_to_path(geom)
    elif geom.geom_type == 'MultiPolygon':
        paths = []
        for poly in geom.geoms:
            paths.append(polygon_to_path(poly))
        return " ".join(paths)
    else:
        return ""


# -----------------------------------------------
# Constraint Detection Function (with tolerance and triple overlap check)
# -----------------------------------------------

def check_coaster_constraints(candidate_spec, existing_specs,
                              outer_w, outer_h, inner_w, inner_h,
                              tol=0.5, overlap_threshold=1.0):
    """
    Parameters:
      candidate_spec: A tuple (cx, cy, angle) representing the candidate coaster's center and angle.
      existing_specs: List of specifications for the already placed coasters, each as (cx, cy, angle).
      outer_w, outer_h, inner_w, inner_h: Dimensions of the coaster.
      tol: Tolerance (in pixels).
      overlap_threshold: Area threshold for significant overlap.

    Returns:
      True if all constraints are satisfied; False otherwise.
    """
    cx, cy, angle = candidate_spec
    candidate_ring = create_rectangle_ring(cx, cy, outer_w, outer_h, inner_w, inner_h, angle)

    candidate_inner = None
    if len(candidate_ring.interiors) > 0:
        candidate_inner = Polygon(list(candidate_ring.interiors[0].coords))

    # Candidate coaster's outer vertices
    candidate_outer_pts = list(candidate_ring.exterior.coords)
    # Candidate coaster's inner vertices (if available, taking the outer ring of the inner hole)
    candidate_inner_pts = list(candidate_inner.exterior.coords) if candidate_inner is not None else []

    # Condition 1: Shared gap region detection
    cond1 = False
    for spec in existing_specs:
        ox, oy, oangle = spec
        other_inner = create_inner_polygon(ox, oy, outer_w, outer_h, inner_w, inner_h, oangle)
        for pt_out in candidate_outer_pts:
            p_out = Point(pt_out)
            if other_inner.contains(p_out) and p_out.distance(other_inner.boundary) > tol:
                for pt_in in candidate_inner_pts:
                    p_in = Point(pt_in)
                    if other_inner.contains(p_in) and p_in.distance(other_inner.boundary) > tol:
                        cond1 = True
                        break
            if cond1:
                break
        if cond1:
            break

    # Condition 2: Vertex constraint detection. No vertex of the candidate coaster (outer or inner) should lie within another coaster,
    # and each vertex must be at least tol away from its boundary.
    cond2 = True
    for spec in existing_specs:
        ox, oy, oangle = spec
        other_coaster = create_rectangle_ring(ox, oy, outer_w, outer_h, inner_w, inner_h, oangle)
        for pt in candidate_outer_pts + candidate_inner_pts:
            p = Point(pt)
            # If the point lies inside another coaster, it's not allowed
            if other_coaster.contains(p):
                cond2 = False
                break
            # If the point is closer to the other coaster's boundary than tol, it's not allowed either
            if p.distance(other_coaster.boundary) < tol:
                cond2 = False
                break
        if not cond2:
            break

    # Condition 3: Multiple overlap check. Calculate the intersection area between the candidate coaster
    # and each existing coaster. If more than one coaster has an intersection area exceeding overlap_threshold,
    # then it is considered a triple overlap which is not allowed.
    cond3 = True
    overlap_count = 0
    for spec in existing_specs:
        ox, oy, oangle = spec
        other_ring = create_rectangle_ring(ox, oy, outer_w, outer_h, inner_w, inner_h, oangle)
        inter_area = candidate_ring.intersection(other_ring).area
        if inter_area > overlap_threshold:
            overlap_count += 1
        if overlap_count >= 2:
            cond3 = False
            break

    return cond1 and cond2 and cond3



# -----------------------------------------------
# Method 1: Generate a Complex SVG showing original overlapping configuration
# -----------------------------------------------

def generate_complex_rings_svg(ring_specs, filename="complex_rings.svg", margin=50):
    """
    Parameters:
      ring_specs: A list of tuples, each tuple containing (cx, cy, outer_w, outer_h, inner_w, inner_h, angle).
      filename: The output SVG filename.
      margin: Margin (in pixels).
    """
    rings = []
    for spec in ring_specs:
        cx, cy, ow, oh, iw, ih, angle = spec
        ring = create_rectangle_ring(cx, cy, ow, oh, iw, ih, angle)
        rings.append(ring)
    red_regions = []
    n = len(rings)
    for i in range(n):
        union_others = None
        for j in range(n):
            if i == j:
                continue
            if union_others is None:
                union_others = rings[j]
            else:
                union_others = union_others.union(rings[j])
        if union_others is not None:
            red_region = rings[i].intersection(union_others)
        else:
            red_region = rings[i].buffer(0)
        red_regions.append(red_region)
    all_bounds = [ring.bounds for ring in rings]
    min_x = min(b[0] for b in all_bounds) - margin
    min_y = min(b[1] for b in all_bounds) - margin
    max_x = max(b[2] for b in all_bounds) + margin
    max_y = max(b[3] for b in all_bounds) + margin
    canvas_width = max_x - min_x
    canvas_height = max_y - min_y
    dwg = svgwrite.Drawing(filename, size=(f"{canvas_width}px", f"{canvas_height}px"))
    transform_offset = (-min_x, -min_y)
    for ring, red in zip(rings, red_regions):
        ring_trans = translate(ring, xoff=transform_offset[0], yoff=transform_offset[1])
        path_d = shapely_to_svg_path(ring_trans)
        if path_d:
            dwg.add(dwg.path(d=path_d, fill="none", stroke="black", stroke_width=1))
        if red and not red.is_empty:
            red_trans = translate(red, xoff=transform_offset[0], yoff=transform_offset[1])
            red_d = shapely_to_svg_path(red_trans)
            if red_d:
                dwg.add(dwg.path(d=red_d, fill="none", stroke="red", stroke_dasharray="4", stroke_width=1))
    dwg.save()
    print(f"Complex (overlapping) SVG generated: {filename}")


# -----------------------------------------------
# Method 2: Generate an Individual SVG showing arranged, non-overlapping rings
# -----------------------------------------------

def generate_individual_rings_svg(ring_specs, filename="individual_rings.svg", margin=50):
    """
    Normalize multiple rings (with the new center set to (outer_w/2, outer_h/2)) and arrange them horizontally.
    The SVG marks the original overlapping (thinned) red areas on each individual shape.

    Parameters:
      ring_specs: A list of tuples, each tuple containing (cx, cy, outer_w, outer_h, inner_w, inner_h, angle).
      filename: The output SVG filename.
      margin: The spacing (in pixels) between the shapes.
    """
    n = len(ring_specs)
    rings_original = []
    for spec in ring_specs:
        cx, cy, ow, oh, iw, ih, angle = spec
        ring = create_rectangle_ring(cx, cy, ow, oh, iw, ih, angle)
        rings_original.append(ring)
    red_regions_original = []
    for i in range(n):
        red_region = None
        for j in range(n):
            if i == j:
                continue
            inter = rings_original[i].intersection(rings_original[j])
            if not inter.is_empty:
                if red_region is None:
                    red_region = inter
                else:
                    red_region = red_region.union(inter)
        if red_region is None:
            red_region = rings_original[i].buffer(0)
        red_regions_original.append(red_region)
    normalized_rings = []
    normalized_reds = []
    for spec, red_orig in zip(ring_specs, red_regions_original):
        cx, cy, ow, oh, iw, ih, angle = spec
        norm_ring = create_rectangle_ring(ow / 2, oh / 2, ow, oh, iw, ih, angle)
        normalized_rings.append(norm_ring)
        dx0 = (ow / 2) - cx
        dy0 = (oh / 2) - cy
        norm_red = translate(red_orig, xoff=dx0, yoff=dy0)
        normalized_reds.append(norm_red)
    arranged_rings = []
    arranged_reds = []
    x_cursor = margin
    overall_max_height = 0
    for i, spec in enumerate(ring_specs):
        _, _, ow, oh, _, _, _ = spec
        ring = normalized_rings[i]
        minx, miny, maxx, maxy = ring.bounds
        w = maxx - minx
        h = maxy - miny
        overall_max_height = max(overall_max_height, h)
        dx = x_cursor - minx
        dy = margin - miny
        arranged_rings.append(translate(ring, xoff=dx, yoff=dy))
        arranged_reds.append(translate(normalized_reds[i], xoff=dx, yoff=dy))
        x_cursor += w + margin
    dwg_width = x_cursor + margin
    dwg_height = overall_max_height + 2 * margin
    dwg = svgwrite.Drawing(filename, size=(f"{dwg_width}px", f"{dwg_height}px"))
    for ring, red in zip(arranged_rings, arranged_reds):
        path_d = shapely_to_svg_path(ring)
        if path_d:
            dwg.add(dwg.path(d=path_d, fill="none", stroke="black", stroke_width=1))
        if red and not red.is_empty:
            red_d = shapely_to_svg_path(red)
            if red_d:
                dwg.add(dwg.path(d=red_d, fill="none", stroke="red", stroke_dasharray="4", stroke_width=1))
    dwg.save()
    print(f"Individual (separated) SVG generated: {filename}")


# -----------------------------------------------
# Main Program: Generate two SVG files simultaneously and randomly generate coaster centers and angles
# -----------------------------------------------

def calculate_coaster_centers(num_coasters, outer_w, outer_h, margin, max_retries=50):
    """
    Parameters:
      num_coasters: Number of coasters.
      outer_w, outer_h: Outer dimensions of each coaster.
      margin: Grid margin (in pixels).
      max_retries: Maximum number of retries for each candidate.

    Returns:
      A list of tuples, each tuple being.
    """
    centers = []
    cols = math.ceil(math.sqrt(num_coasters))
    rows = math.ceil(num_coasters / cols)
    cell_w = outer_w * 0.9
    cell_h = outer_h * 0.9
    max_offset_x = cell_w * 0.5
    max_offset_y = cell_h * 0.5
    start_x = margin
    start_y = margin
    allowed_angles = [0, 15, 30, 45]
    for r in range(rows):
        for c in range(cols):
            if len(centers) >= num_coasters:
                break
            cell_x = start_x + c * cell_w
            cell_y = start_y + r * cell_h
            ideal_cx = cell_x + cell_w / 2
            ideal_cy = cell_y + cell_h / 2
            valid = False
            retries = 0
            while not valid and retries < max_retries:
                offset_x = random.uniform(-max_offset_x, max_offset_x)
                offset_y = random.uniform(-max_offset_y, max_offset_y)
                cx = ideal_cx + offset_x
                cy = ideal_cy + offset_y
                angle = random.choice(allowed_angles)
                candidate_spec = (cx, cy, angle)
                if len(centers) == 0:
                    valid = True
                else:
                    # Generate candidate coaster
                    candidate_ring = create_rectangle_ring(cx, cy, outer_w, outer_h, inner_w, inner_h, angle)
                    # First check the existing constraints
                    if check_coaster_constraints(candidate_spec, centers, outer_w, outer_h, inner_w, inner_h):
                        # Additional check: count the number of overlaps between the candidate coaster and the existing coasters
                        overlap_count = 0
                        for spec_exist in centers:
                            ox, oy, oangle = spec_exist
                            other_ring = create_rectangle_ring(ox, oy, outer_w, outer_h, inner_w, inner_h, oangle)
                            if candidate_ring.intersection(other_ring).area > 1.0:  # Adjust threshold as needed
                                overlap_count += 1
                            if overlap_count >= 2:
                                break
                        if overlap_count < 2:
                            valid = True
                retries += 1
            if valid:
                centers.append(candidate_spec)
            else:
                centers.append((ideal_cx, ideal_cy, random.choice(allowed_angles)))
    return centers


if __name__ == "__main__":
    num_coasters = int(input("Please enter the number of coasters: "))
    DPI = 192  # pixels per inch
    outer_w = outer_h = 2.5 * DPI  # e.g., 240 pixels
    inner_w = inner_h = 2.0 * DPI  # e.g., 192 pixels
    margin_between = 50

    # Calculate coaster centers and angles (that meet the constraints)
    centers = calculate_coaster_centers(num_coasters, outer_w, outer_h, margin_between)

    # Build the specifications list, each tuple is (cx, cy, outer_w, outer_h, inner_w, inner_h, angle)
    specs = []
    for center in centers:
        cx, cy, angle = center
        specs.append((cx, cy, outer_w, outer_h, inner_w, inner_h, angle))

    # Generate the SVG file showing the original overlapping configuration
    generate_complex_rings_svg(specs, filename="complex_rings.svg", margin=margin_between)
    # Generate the SVG file with the arranged, separated coasters
    generate_individual_rings_svg(specs, filename="individual_rings.svg", margin=margin_between)

