import svgwrite
import random


def opposite_edge(e):
    """
    Returns the opposite edge type:
      'out' -> 'in'
      'in'  -> 'out'
      'none' -> 'none'
    """
    if e == 'out':
        return 'in'
    elif e == 'in':
        return 'out'
    else:
        return 'none'


def define_edges(rows, cols, randomize=True):
    """
      {
        'top':    'in' | 'out' | 'none',
        'right':  'in' | 'out' | 'none',
        'bottom': 'in' | 'out' | 'none',
        'left':   'in' | 'out' | 'none'
      }

    Rules:
      1. The top row has 'top' = 'none' (outer boundary).
      2. The left column has 'left' = 'none' (outer boundary).
      3. For pieces not on the right edge, randomly choose 'in' or 'out' for 'right'
         (if randomize is False, default to 'out'). The adjacent piece's 'left'
         edge will be set to the opposite.
      4. For pieces not on the bottom, randomly choose 'in' or 'out' for 'bottom'
         (if randomize is False, default to 'out'). The piece below's 'top'
         will be set to the opposite.
    """
    edges_map = [[{"top": "none", "right": "none", "bottom": "none", "left": "none"}
                  for _ in range(cols)] for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            # Top edge: if not first row, set as opposite of the piece above's bottom.
            if r > 0:
                edges_map[r][c]["top"] = opposite_edge(edges_map[r - 1][c]["bottom"])
            else:
                edges_map[r][c]["top"] = "none"

            # Left edge: if not first column, set as opposite of the piece to the left's right.
            if c > 0:
                edges_map[r][c]["left"] = opposite_edge(edges_map[r][c - 1]["right"])
            else:
                edges_map[r][c]["left"] = "none"

            # Right edge: if not on the rightmost side, randomly choose 'in' or 'out'.
            if c < cols - 1:
                if randomize:
                    edges_map[r][c]["right"] = random.choice(["in", "out"])
                else:
                    edges_map[r][c]["right"] = "out"
            else:
                edges_map[r][c]["right"] = "none"

            # Bottom edge: if not on the bottom, randomly choose 'in' or 'out'.
            if r < rows - 1:
                if randomize:
                    edges_map[r][c]["bottom"] = random.choice(["in", "out"])
                else:
                    edges_map[r][c]["bottom"] = "out"
            else:
                edges_map[r][c]["bottom"] = "none"
    return edges_map


def piece_path(r, c, edge_dict, piece_w, piece_h, tab_size, kerf, x_off, y_off):
    """
    Build the SVG path for the puzzle piece at grid position (r, c).

    Parameters:
      edge_dict: a dictionary with the edge types for 'top', 'right', 'bottom', 'left'
                 (values: 'in' | 'out' | 'none').
      piece_w, piece_h: the base width and height of each piece (excluding the tabs).
      tab_size: the original size of the tab.
      kerf: laser cutting compensation value. For "out" edges, the tab depth is increased by kerf/2;
            for "in" edges, the tab depth is decreased by kerf/2.
      (x_off, y_off): overall offset to avoid drawing at the very edge of the canvas.

    Drawing steps:
      1. Move to the top-left corner.
      2. Draw the top edge with a bump or indent at the midpoint (with kerf compensation).
      3. Draw the right edge.
      4. Draw the bottom edge.
      5. Draw the left edge.
      6. Close the path.
    """
    sx = x_off + c * piece_w
    sy = y_off + r * piece_h

    cmds = []
    # Move to the top-left corner
    cmds.append(f"M {sx} {sy}")

    # Top Edge
    top_type = edge_dict["top"]
    if top_type == "none":
        cmds.append(f"L {sx + piece_w} {sy}")
    else:
        half = (piece_w - tab_size) / 2.0
        mid_left = sx + half
        mid_right = mid_left + tab_size
        if top_type == "out":
            # Protrude upward with added kerf compensation
            cmds.append(f"L {mid_left} {sy}")
            cmds.append(f"L {mid_left} {sy - (tab_size + kerf / 2)}")
            cmds.append(f"L {mid_right} {sy - (tab_size + kerf / 2)}")
            cmds.append(f"L {mid_right} {sy}")
            cmds.append(f"L {sx + piece_w} {sy}")
        else:
            # Indent downward with reduced tab depth
            cmds.append(f"L {mid_left} {sy}")
            cmds.append(f"L {mid_left} {sy + (tab_size - kerf / 2)}")
            cmds.append(f"L {mid_right} {sy + (tab_size - kerf / 2)}")
            cmds.append(f"L {mid_right} {sy}")
            cmds.append(f"L {sx + piece_w} {sy}")

    # Right Edge
    right_type = edge_dict["right"]
    if right_type == "none":
        cmds.append(f"L {sx + piece_w} {sy + piece_h}")
    else:
        half = (piece_h - tab_size) / 2.0
        mid_top = sy + half
        mid_bottom = mid_top + tab_size
        if right_type == "out":
            # Protrude to the right with added kerf compensation
            cmds.append(f"L {sx + piece_w} {mid_top}")
            cmds.append(f"L {sx + piece_w + (tab_size + kerf / 2)} {mid_top}")
            cmds.append(f"L {sx + piece_w + (tab_size + kerf / 2)} {mid_bottom}")
            cmds.append(f"L {sx + piece_w} {mid_bottom}")
            cmds.append(f"L {sx + piece_w} {sy + piece_h}")
        else:
            # Indent to the left with reduced tab depth
            cmds.append(f"L {sx + piece_w} {mid_top}")
            cmds.append(f"L {sx + piece_w - (tab_size - kerf / 2)} {mid_top}")
            cmds.append(f"L {sx + piece_w - (tab_size - kerf / 2)} {mid_bottom}")
            cmds.append(f"L {sx + piece_w} {mid_bottom}")
            cmds.append(f"L {sx + piece_w} {sy + piece_h}")

    #  Bottom Edge
    bottom_type = edge_dict["bottom"]
    if bottom_type == "none":
        cmds.append(f"L {sx} {sy + piece_h}")
    else:
        half = (piece_w - tab_size) / 2.0
        mid_right = sx + piece_w - half
        mid_left = mid_right - tab_size
        if bottom_type == "out":
            # Protrude downward with added kerf compensation
            cmds.append(f"L {mid_right} {sy + piece_h}")
            cmds.append(f"L {mid_right} {sy + piece_h + (tab_size + kerf / 2)}")
            cmds.append(f"L {mid_left} {sy + piece_h + (tab_size + kerf / 2)}")
            cmds.append(f"L {mid_left} {sy + piece_h}")
            cmds.append(f"L {sx} {sy + piece_h}")
        else:
            # Indent upward with reduced tab depth
            cmds.append(f"L {mid_right} {sy + piece_h}")
            cmds.append(f"L {mid_right} {sy + piece_h - (tab_size - kerf / 2)}")
            cmds.append(f"L {mid_left} {sy + piece_h - (tab_size - kerf / 2)}")
            cmds.append(f"L {mid_left} {sy + piece_h}")
            cmds.append(f"L {sx} {sy + piece_h}")

    # --- 4) Left Edge ---
    left_type = edge_dict["left"]
    if left_type == "none":
        cmds.append(f"L {sx} {sy}")
    else:
        half = (piece_h - tab_size) / 2.0
        mid_bottom = sy + piece_h - half
        mid_top = mid_bottom - tab_size
        if left_type == "out":
            # Protrude to the left with added kerf compensation
            cmds.append(f"L {sx} {mid_bottom}")
            cmds.append(f"L {sx - (tab_size + kerf / 2)} {mid_bottom}")
            cmds.append(f"L {sx - (tab_size + kerf / 2)} {mid_top}")
            cmds.append(f"L {sx} {mid_top}")
            cmds.append(f"L {sx} {sy}")
        else:
            # Indent to the right with reduced tab depth
            cmds.append(f"L {sx} {mid_bottom}")
            cmds.append(f"L {sx + (tab_size - kerf / 2)} {mid_bottom}")
            cmds.append(f"L {sx + (tab_size - kerf / 2)} {mid_top}")
            cmds.append(f"L {sx} {mid_top}")
            cmds.append(f"L {sx} {sy}")

    # Close the path
    cmds.append("Z")
    return " ".join(cmds)


def generate_puzzle_coasters(
        filename="puzzle_coasters_final.svg",
        rows=2,
        cols=2,
        piece_w=80,
        piece_h=80,
        tab_size=10,
        kerf=0.5,  # Laser cutting compensation
        randomize=True
):
    """
    Parameters:
      rows, cols: Number of rows and columns in the puzzle layout.
      randomize: If True, the internal edge patterns are randomized (each run may produce a different pattern).
    """
    edges_map = define_edges(rows, cols, randomize=randomize)

    # Create an SVG canvas with extra margin
    dwg_width = cols * piece_w + 200
    dwg_height = rows * piece_h + 200
    dwg = svgwrite.Drawing(filename, size=(f"{dwg_width}px", f"{dwg_height}px"))

    # Set offsets so the design doesn't touch the canvas edge
    x_offset = 50
    y_offset = 50

    # Generate and add each piece's path to the SVG drawing
    for r in range(rows):
        for c in range(cols):
            e_dict = edges_map[r][c]
            d_str = piece_path(r, c, e_dict, piece_w, piece_h, tab_size, kerf, x_offset, y_offset)
            dwg.add(dwg.path(d=d_str, fill="none", stroke="black", stroke_width=1))

    dwg.save()
    print(f"SVG generated: {filename}")


if __name__ == "__main__":
    # Example: Generate a 2x2 puzzle with pieces of 80x80, a tab size of 20, and a kerf compensation of 0.5 pixels.
    # Internal edges are randomized.
    generate_puzzle_coasters(
        filename="puzzle_coasters_final.svg",
        rows=3,
        cols=3,
        piece_w=80,
        piece_h=80,
        tab_size=20,
        kerf=0.5,
        randomize=True
    )
