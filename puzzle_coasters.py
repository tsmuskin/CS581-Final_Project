import svgwrite


def opposite_edge(e):
    if e == 'out':
        return 'in'
    elif e == 'in':
        return 'out'
    else:
        return 'none'


def define_edges(rows, cols):
    """
       If not the rightmost column, right='out' in this block and left='in' in the next block.
       If not the lowest line, the bottom='out this block is' out' and the top of the next block is' in'.
       The uppermost and leftmost columns are set to' none'
    """
    edges_map = [[{"top": "none", "right": "none", "bottom": "none", "left": "none"}
                  for _ in range(cols)] for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):

            if r > 0:
                edges_map[r][c]["top"] = opposite_edge(edges_map[r - 1][c]["bottom"])
            else:
                edges_map[r][c]["top"] = "none"

            if c > 0:
                edges_map[r][c]["left"] = opposite_edge(edges_map[r][c - 1]["right"])
            else:
                edges_map[r][c]["left"] = "none"

            if c < cols - 1:
                edges_map[r][c]["right"] = "out"
            else:
                edges_map[r][c]["right"] = "none"

            if r < rows - 1:
                edges_map[r][c]["bottom"] = "out"
            else:
                edges_map[r][c]["bottom"] = "none"

    return edges_map


def piece_path(r, c, edge_dict, piece_w, piece_h, tab_size, x_off, y_off):
    """
    'piece_w' and 'piece_h' : the base width and height.
    'tab_size' : protrusion or indentation size.
    (x_off, y_off) :entire layout.
    """
    sx = x_off + c * piece_w
    sy = y_off + r * piece_h

    cmds = []
    cmds.append(f"M {sx} {sy}")

    #top
    top_type = edge_dict["top"]
    if top_type == "none":
        cmds.append(f"L {sx + piece_w} {sy}")
    else:
        half = (piece_w - tab_size) / 2.0
        mid_left = sx + half
        mid_right = mid_left + tab_size
        if top_type == "out":
            # Protrude upwards
            cmds.append(f"L {mid_left} {sy}")
            cmds.append(f"L {mid_left} {sy - tab_size}")
            cmds.append(f"L {mid_right} {sy - tab_size}")
            cmds.append(f"L {mid_right} {sy}")
            cmds.append(f"L {sx + piece_w} {sy}")
        else:
            # Indent downwards
            cmds.append(f"L {mid_left} {sy}")
            cmds.append(f"L {mid_left} {sy + tab_size}")
            cmds.append(f"L {mid_right} {sy + tab_size}")
            cmds.append(f"L {mid_right} {sy}")
            cmds.append(f"L {sx + piece_w} {sy}")

    # right
    right_type = edge_dict["right"]
    if right_type == "none":
        cmds.append(f"L {sx + piece_w} {sy + piece_h}")
    else:
        half = (piece_h - tab_size) / 2.0
        mid_top = sy + half
        mid_bottom = mid_top + tab_size
        if right_type == "out":
            # Protrude to the right
            cmds.append(f"L {sx + piece_w} {mid_top}")
            cmds.append(f"L {sx + piece_w + tab_size} {mid_top}")
            cmds.append(f"L {sx + piece_w + tab_size} {mid_bottom}")
            cmds.append(f"L {sx + piece_w} {mid_bottom}")
            cmds.append(f"L {sx + piece_w} {sy + piece_h}")
        else:
            # Indent to the left
            cmds.append(f"L {sx + piece_w} {mid_top}")
            cmds.append(f"L {sx + piece_w - tab_size} {mid_top}")
            cmds.append(f"L {sx + piece_w - tab_size} {mid_bottom}")
            cmds.append(f"L {sx + piece_w} {mid_bottom}")
            cmds.append(f"L {sx + piece_w} {sy + piece_h}")

    # bottom
    bottom_type = edge_dict["bottom"]
    if bottom_type == "none":
        cmds.append(f"L {sx} {sy + piece_h}")
    else:
        half = (piece_w - tab_size) / 2.0
        mid_right = sx + piece_w - half
        mid_left = mid_right - tab_size
        if bottom_type == "out":
            # Protrude downwards
            cmds.append(f"L {mid_right} {sy + piece_h}")
            cmds.append(f"L {mid_right} {sy + piece_h + tab_size}")
            cmds.append(f"L {mid_left} {sy + piece_h + tab_size}")
            cmds.append(f"L {mid_left} {sy + piece_h}")
            cmds.append(f"L {sx} {sy + piece_h}")
        else:
            # Indent upwards
            cmds.append(f"L {mid_right} {sy + piece_h}")
            cmds.append(f"L {mid_right} {sy + piece_h - tab_size}")
            cmds.append(f"L {mid_left} {sy + piece_h - tab_size}")
            cmds.append(f"L {mid_left} {sy + piece_h}")
            cmds.append(f"L {sx} {sy + piece_h}")

    # left
    left_type = edge_dict["left"]
    if left_type == "none":
        cmds.append(f"L {sx} {sy}")
    else:
        half = (piece_h - tab_size) / 2.0
        mid_bottom = sy + piece_h - half
        mid_top = mid_bottom - tab_size
        if left_type == "out":
            # Protrude to the left
            cmds.append(f"L {sx} {mid_bottom}")
            cmds.append(f"L {sx - tab_size} {mid_bottom}")
            cmds.append(f"L {sx - tab_size} {mid_top}")
            cmds.append(f"L {sx} {mid_top}")
            cmds.append(f"L {sx} {sy}")
        else:
            # Indent to the right
            cmds.append(f"L {sx} {mid_bottom}")
            cmds.append(f"L {sx + tab_size} {mid_bottom}")
            cmds.append(f"L {sx + tab_size} {mid_top}")
            cmds.append(f"L {sx} {mid_top}")
            cmds.append(f"L {sx} {sy}")

    cmds.append("Z")
    return " ".join(cmds)


def generate_puzzle_coasters(
        filename="puzzle_coasters_final.svg",
        rows=2,
        cols=2,
        piece_w=80,
        piece_h=80,
        tab_size=10
):
    """
        rows, cols: Number of rows and columns in the puzzle layout
    """
    edges_map = define_edges(rows, cols)


    dwg_width = cols * piece_w + 200
    dwg_height = rows * piece_h + 200
    dwg = svgwrite.Drawing(filename, size=(f"{dwg_width}px", f"{dwg_height}px"))


    x_offset = 50
    y_offset = 50


    for r in range(rows):
        for c in range(cols):
            # (r,c) 对应的四边
            edict = edges_map[r][c]
            d_str = piece_path(r, c, edict, piece_w, piece_h, tab_size, x_offset, y_offset)
            dwg.add(dwg.path(d=d_str, fill="none", stroke="black", stroke_width=1))

    dwg.save()
    print(f"print: {filename}")


if __name__ == "__main__":

    generate_puzzle_coasters(
        filename="puzzle_coasters.svg",
        rows=3,
        cols=3,
        piece_w=80,
        piece_h=80,
        tab_size=20
    )
