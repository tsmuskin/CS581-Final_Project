import math
import random
import svgwrite
from shapely.geometry import Polygon, Point
from shapely.affinity import rotate, translate, scale


def regular_polygon_vertices(n_sides, radius):
    """
    Returns the vertices of a regular n-sided polygon with the origin at (0, 0),
    and the first vertex at (radius, 0).
    """
    return [
        (
            radius * math.cos(2 * math.pi * i / n_sides),
            radius * math.sin(2 * math.pi * i / n_sides)
        )
        for i in range(n_sides)
    ]

def create_polygon_ring(cx, cy, n_sides, outer_r, inner_r, angle):
    """
    Generates a regular polygon ring (outer polygon minus inner polygon),
    and aligns the 0° edge to be horizontal.

    Parameters:
      cx, cy     -- center of the ring
      n_sides    -- number of sides
      outer_r    -- outer radius
      inner_r    -- inner radius
      angle      -- additional rotation angle (degrees)

    Returns:
      Shapely Polygon representing the polygon ring
    """
    outer_pts = regular_polygon_vertices(n_sides, outer_r)
    inner_pts = regular_polygon_vertices(n_sides, inner_r)

    outer = Polygon(outer_pts)
    inner = Polygon(inner_pts)
    ring = outer.difference(inner)

    # Align 0° edge to be horizontal by applying an initial offset
    initial_offset = 180.0 / n_sides
    total_angle = angle + initial_offset

    ring = rotate(ring,
                  total_angle,
                  origin=(0, 0),
                  use_radians=False)
    ring = translate(ring, xoff=cx, yoff=cy)
    return ring

def create_inner_polygon(cx, cy, n_sides, outer_r, inner_r, angle):
    """
    Generates only the inner polygon, with the initial offset to align the 0° edge horizontally.
    """
    pts = regular_polygon_vertices(n_sides, inner_r)
    poly = Polygon(pts)

    initial_offset = 180.0 / n_sides
    total_angle = angle + initial_offset

    poly = rotate(poly,
                  total_angle,
                  origin=(0, 0),
                  use_radians=False)
    poly = translate(poly, xoff=cx, yoff=cy)
    return poly

def polygon_to_path(poly):
    ext = list(poly.exterior.coords)
    s = f"M {ext[0][0]} {ext[0][1]}"
    for x, y in ext[1:]:
        s += f" L {x} {y}"
    s += " Z"
    for interior in poly.interiors:
        pts = list(interior.coords)
        s += f" M {pts[0][0]} {pts[0][1]}"
        for x, y in pts[1:]:
            s += f" L {x} {y}"
        s += " Z"
    return s

def shapely_to_svg_path(g):
    if g.is_empty: return ""
    if g.geom_type == "Polygon":
        return polygon_to_path(g)
    return " ".join(polygon_to_path(p) for p in g.geoms)

def check_coaster_constraints(cand, existing, n_sides,
                              outer_r, inner_r, tol=0.5, overlap_thr=1.0):
    cx, cy, angle = cand
    ring = create_polygon_ring(cx, cy, n_sides, outer_r, inner_r, angle)
    # Inner polygon
    inner_poly = create_inner_polygon(cx, cy, n_sides, outer_r, inner_r, angle)
    outer_pts = list(ring.exterior.coords)
    inner_pts = list(inner_poly.exterior.coords)
    # cond1: common vacancy
    cond1 = False
    for ex in existing:
        ox, oy, oang = ex
        other_inner = create_inner_polygon(ox, oy, n_sides, outer_r, inner_r, oang)
        for p_out in outer_pts:
            Pout = Point(p_out)
            if other_inner.contains(Pout) and Pout.distance(other_inner.boundary) > tol:
                for p_in in inner_pts:
                    Pin = Point(p_in)
                    if other_inner.contains(Pin) and Pin.distance(other_inner.boundary) > tol:
                        cond1 = True
                        break
            if cond1: break
        if cond1: break
    # cond2: vertices must not fall inside others' rings, and distance to boundary must be >= tol
    cond2 = True
    for ex in existing:
        ox, oy, oang = ex
        other = create_polygon_ring(ox, oy, n_sides, outer_r, inner_r, oang)
        for p in outer_pts + inner_pts:
            P = Point(p)
            if other.contains(P) or P.distance(other.boundary) < tol:
                cond2 = False
                break
        if not cond2: break
    # cond3: no overlap with two or more rings
    cond3 = True
    cnt = 0
    for ex in existing:
        ox, oy, oang = ex
        other = create_polygon_ring(ox, oy, n_sides, outer_r, inner_r, oang)
        if ring.intersection(other).area > overlap_thr:
            cnt += 1
        if cnt >= 2:
            cond3 = False
            break
    return cond1 and cond2 and cond3

def calculate_coaster_centers(n_sides, num_coasters, rotation_flag, outer_w, outer_h, margin, max_retries=1000):
    """
    Place coasters so they overlap intentionally at corners (not more than 2 per overlap).

    Parameters:
        num_coasters: total number of coasters
        rotation_flag: 'y' to rotate each by 45 degrees
        outer_w, outer_h: dimensions of coasters
        margin: spacing from the edge

    Returns:
        List of (cx, cy, angle)
    """
    centers = []

    # Staggered layout setup
    overlap_ratio = .37  # How much overlap at corners
    print(n_sides)
    if n_sides < 5:
        step_x = 1.7 * outer_w * (1 - overlap_ratio)
        step_y = 1.7 * outer_h * (1 - overlap_ratio)
    if n_sides == 4:
            step_x = 1.5 * outer_w * (1 - overlap_ratio)
            step_y = 1.5 * outer_h * (1 - overlap_ratio)
    else:
        step_x = 1.8 * outer_w * (1 - overlap_ratio)
        step_y = 1.8 * outer_h * (1 - overlap_ratio)

    cols = math.ceil(math.sqrt(num_coasters))
    rows = math.ceil(num_coasters / cols)

    allowed_angles = [15, 30, 45, 60, 75]
    if rotation_flag == "y":
        angle = random.choice(allowed_angles)
    else:
        angle = 0

    idx = 0
    for r in range(rows):
        for c in range(cols):
            if idx >= num_coasters:
                break

            # Stagger every other row for corner alignment
            offset_x = (step_x / 2) if r % 2 else 0


            cx = margin + c * step_x + offset_x
            cy = margin + r * step_y

            centers.append((cx, cy, angle))
            idx += 1

    return centers

def generate_complex_svg(specs, filename="complex.svg", margin=50):
    rings = []
    for cx, cy, ow, oh, iw, ih, angle, n in specs:
        r = create_polygon_ring(cx, cy, n, ow / 2, iw / 2, angle)
        rings.append(r)
    red = []
    for i, ri in enumerate(rings):
        u = None
        for j, rj in enumerate(rings):
            if i == j: continue
            u = rj if u is None else u.union(rj)
        red.append(ri.intersection(u) if u else ri.buffer(0))
    # Canvas bounds
    bs = [r.bounds for r in rings]
    minx = min(b[0] for b in bs) - margin
    miny = min(b[1] for b in bs) - margin
    maxx = max(b[2] for b in bs) + margin
    maxy = max(b[3] for b in bs) + margin
    W, H = maxx - minx, maxy - miny
    dwg = svgwrite.Drawing(filename, size=(f"{W}px", f"{H}px"))
    offs = (-minx, -miny)
    for r, region in zip(rings, red):
        r2 = translate(r, *offs)
        dwg.add(dwg.path(d=shapely_to_svg_path(r2), fill="none", stroke="black"))
        if not region.is_empty:
            R2 = translate(region, *offs)
            dwg.add(dwg.path(d=shapely_to_svg_path(R2), fill="none", stroke="red", stroke_dasharray="4"))
    dwg.save()
    print("Saved", filename)

def generate_individual_svg(specs, filename="individual.svg", margin=50):
    """
    Normalize each coaster and arrange them horizontally.
    Draw overlap regions in blue if the current coaster’s index is greater
    than the overlapping coaster’s index, otherwise in red.
    If a coaster has any blue overlap, also draw its left–right mirror image
    in a second row below the originals.
    """

    rings = [
        create_polygon_ring(cx, cy, n_sides, ow/2, iw/2, angle)
        for cx, cy, ow, oh, iw, ih, angle, n_sides in specs
    ]


    arranged = []
    overlaps_list = []
    x_cursor = margin
    max_h = 0

    for idx, ((cx, cy, ow, oh, iw, ih, angle, n_sides), ring) in enumerate(zip(specs, rings)):

        norm = translate(ring, xoff=ow/2 - cx, yoff=oh/2 - cy)
        minx, miny, maxx, maxy = norm.bounds
        w, h = maxx - minx, maxy - miny
        max_h = max(max_h, h)


        dx, dy = x_cursor - minx, margin - miny
        placed = translate(norm, xoff=dx, yoff=dy)
        arranged.append(placed)


        overlaps = []
        for jdx, other in enumerate(rings):
            if jdx == idx: continue
            other_norm = translate(other, xoff=ow/2 - cx, yoff=oh/2 - cy)
            region = norm.intersection(other_norm)
            if region.is_empty: continue
            region = translate(region, xoff=dx, yoff=dy)
            color = "blue" if idx > jdx else "red"
            overlaps.append((region, color))

        overlaps_list.append(overlaps)
        x_cursor += w + margin


    canvas_w = x_cursor + margin
    canvas_h = margin + max_h + margin + max_h + margin
    dwg = svgwrite.Drawing(filename, size=(f"{canvas_w}px", f"{canvas_h}px"))

    row2_offset = max_h + 2 * margin

    for idx, (ring_shape, overlaps) in enumerate(zip(arranged, overlaps_list)):

        dwg.add(dwg.path(d=shapely_to_svg_path(ring_shape),
                         fill="none", stroke="black"))

        for region, color in overlaps:
            if color == "red":
                dwg.add(dwg.path(
                   d=shapely_to_svg_path(region),
                   fill=color, stroke=color,
                   stroke_dasharray="4", stroke_width=1
                ))


        if any(color == "blue" for _, color in overlaps):

            minx, miny, maxx, maxy = ring_shape.bounds
            axis_y = (miny + maxy) / 2  # Mirror across horizontal axis

            mirrored = scale(ring_shape, xfact=1, yfact=-1, origin=(0, axis_y))
            mirrored = translate(mirrored, xoff=0, yoff=row2_offset)
            dwg.add(dwg.path(d=shapely_to_svg_path(mirrored),
                             fill="none", stroke="black"))

            for region, color in overlaps:
                if color == "blue":
                    mir_reg = scale(region, xfact=1, yfact=-1, origin=(0, axis_y))
                    mir_reg = translate(mir_reg, xoff=0, yoff=row2_offset)
                    dwg.add(dwg.path(
                        d=shapely_to_svg_path(mir_reg),
                        fill=color, stroke=color,
                        stroke_dasharray="4", stroke_width=1
                    ))

    dwg.save()
    print("Saved:", filename)


if __name__ == "__main__":
    num = int(input("Enter number of coasters: "))
    n_sides = int(input("Enter the number of sides for each coaster (>=3): "))
    rotation_flag = str(input("Would you like to rotate the coasters (y/n): "))
    DPI = 96
    outer_w = outer_h = 3.0 * DPI  # Outer diameter
    inner_w = inner_h = 2.25 * DPI  # Inner diameter
    margin = 50

    centers = calculate_coaster_centers(n_sides, num, rotation_flag,
                                        outer_w / 2, inner_w / 2, margin)
    specs = []
    for (cx, cy, ang) in centers:
        specs.append((cx, cy, outer_w, outer_h, inner_w, inner_h, ang, n_sides))

    generate_complex_svg(specs, filename="complex.svg", margin=margin)
    generate_individual_svg(specs, filename="individual.svg", margin=margin)
