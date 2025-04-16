import math
import svgwrite
from shapely.geometry import Polygon
from shapely.affinity import rotate, translate
import random

def create_rectangle_ring(cx, cy, outer_w, outer_h, inner_w, inner_h, angle=0):
    """
    Create a rectangular ring (frame) by subtracting an inner rectangle from an outer rectangle.

    Parameters:
      cx, cy:           Center coordinates of the ring.
      outer_w, outer_h: Width and height of the outer rectangle.
      inner_w, inner_h: Width and height of the inner rectangle.
      angle:            Rotation angle around the center.
    """
    outer_rect = Polygon([
        (0, 0),
        (outer_w, 0),
        (outer_w, outer_h),
        (0, outer_h)
    ])

    inner_rect = Polygon([
        (0, 0),
        (inner_w, 0),
        (inner_w, inner_h),
        (0, inner_h)
    ])

    inner_rect = translate(inner_rect, xoff=(outer_w - inner_w) / 2.0, yoff=(outer_h - inner_h) / 2.0)
    ring = outer_rect.difference(inner_rect)
    ring = translate(ring, xoff=-outer_w / 2.0, yoff=-outer_h / 2.0)
    ring = rotate(ring, angle, origin=(0, 0), use_radians=False)
    ring = translate(ring, xoff=cx, yoff=cy)
    return ring


def polygon_to_path(poly):
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


def generate_complex_rings_svg(ring_specs, filename="complex_rings.svg", margin=50):
    """
    Generate an SVG of overlapping rings and highlight overlapping regions.

    Parameters:
      ring_specs: A list of tuples, each as (cx, cy, outer_w, outer_h, inner_w, inner_h, angle),
                  representing the parameters for each ring.
      margin:     Margin around the SVG content.
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


def generate_individual_rings_svg(ring_specs, filename="individual_rings.svg", margin=50):
    """
    Generate an SVG of individual (non-overlapping) rings with their overlap regions highlighted.
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
        if h > overall_max_height:
            overall_max_height = h
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


def calculate_coaster_centers(num_coasters, outer_w, outer_h, margin):
    """

    Parameters:
      num_coasters: Number of coasters.
      outer_w, outer_h: Outer dimensions of each coaster.
      margin: Margin between coasters (in pixels).

    Returns:
      A list of tuples, each as (cx, cy, angle).
    """
    centers = []
    cols = math.ceil(math.sqrt(num_coasters))
    rows = math.ceil(num_coasters / cols)
    cell_w = outer_w * 0.9  # Cell size = 90% of outer dimensions
    cell_h = outer_h * 0.9
    max_offset_x = cell_w * 0.2  # Max random offset = 20% of cell size
    max_offset_y = cell_h * 0.2
    start_x = margin
    start_y = margin
    allowed_angles = [0, 30, 45]
    for r in range(rows):
        for c in range(cols):
            if len(centers) < num_coasters:
                cell_x = start_x + c * cell_w
                cell_y = start_y + r * cell_h
                ideal_cx = cell_x + cell_w / 2
                ideal_cy = cell_y + cell_h / 2
                offset_x = random.uniform(-max_offset_x, max_offset_x)
                offset_y = random.uniform(-max_offset_y, max_offset_y)
                cx = ideal_cx + offset_x
                cy = ideal_cy + offset_y
                angle = random.choice(allowed_angles)
                centers.append((cx, cy, angle))
    return centers


if __name__ == "__main__":
    num_coasters = int(input("Enter number of coasters: "))
    DPI = 96
    outer_w = outer_h = 2.5 * DPI
    inner_w = inner_h = 2.0 * DPI
    margin_between = 50
    centers = calculate_coaster_centers(num_coasters, outer_w, outer_h, margin_between)
    specs = []
    for center in centers:
        cx, cy, angle = center
        specs.append((cx, cy, outer_w, outer_h, inner_w, inner_h, angle))

    generate_complex_rings_svg(specs, filename="complex_rings.svg", margin=50)
    generate_individual_rings_svg(specs, filename="individual_rings.svg", margin=50)
