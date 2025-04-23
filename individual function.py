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
                   fill="none", stroke=color,
                   stroke_dasharray="4", stroke_width=1
                ))


        if any(color == "blue" for _, color in overlaps):

            minx, _, maxx, _ = ring_shape.bounds
            axis_x = (minx + maxx) / 2

            mirrored = scale(ring_shape, xfact=-1, yfact=1, origin=(axis_x, 0))
            mirrored = translate(mirrored, xoff=0, yoff=row2_offset)
            dwg.add(dwg.path(d=shapely_to_svg_path(mirrored),
                             fill="none", stroke="black"))

            for region, color in overlaps:
                if color == "blue":
                   mir_reg = scale(region, xfact=-1, yfact=1, origin=(axis_x, 0))
                   mir_reg = translate(mir_reg, xoff=0, yoff=row2_offset)
                   dwg.add(dwg.path(
                    d=shapely_to_svg_path(mir_reg),
                    fill="none", stroke=color ,
                    stroke_dasharray="4", stroke_width=1
                    ))

    dwg.save()
    print("Saved:", filename)
