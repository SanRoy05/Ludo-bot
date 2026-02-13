def get_path_coords():
    """
    Generates the 52 main path coordinates for a 15x15 grid ludo board.
    Starting from (6, 0) and going clockwise.
    """
    path = []
    
    # top arm, left side (down)
    for y in range(6): path.append((6, y))
    # left arm, top side (left)
    for x in range(5, -1, -1): path.append((x, 6))
    # left end bridge
    path.append((0, 7))
    # left arm, bottom side (right)
    for x in range(6): path.append((x, 8))
    # bottom arm, left side (down)
    for y in range(9, 15): path.append((6, y))
    # bottom end bridge
    path.append((7, 14))
    # bottom arm, right side (up)
    for y in range(14, 8, -1): path.append((8, y))
    # right arm, bottom side (right)
    for x in range(9, 15): path.append((x, 8))
    # right end bridge
    path.append((14, 7))
    # right arm, top side (left)
    for x in range(14, 8, -1): path.append((x, 6))
    # top arm, right side (up)
    for y in range(5, -1, -1): path.append((8, y))
    # top end bridge
    path.append((7, 0))
    
    return path

# Constants
GRID_SIZE = 15
UNIT_SIZE = 1000 // GRID_SIZE
OFFSET = UNIT_SIZE // 2

def grid_to_px(grid_pos):
    x, y = grid_pos
    return (x * UNIT_SIZE + OFFSET, y * UNIT_SIZE + OFFSET)

MAIN_PATH_GRID = get_path_coords()
MAIN_PATH_COORDS = [grid_to_px(pos) for pos in MAIN_PATH_GRID]

# HOME PATHS (6 per color)
# Indices for Home entries (where they turn in)
# 0: Red (TL) - Turns at (6,7) from (0,7)? No.
# Looking at image:
# Red (TL) Home is (1..6, 7) - Left to Right
# Green (TR) Home is (7, 1..6) - Top to Bottom
# Yellow (BR) Home is (13..8, 7) - Right to Left
# Blue (BL) Home is (7, 13..8) - Bottom to Top

HOME_PATH_COORDS = {
    0: [grid_to_px((x, 7)) for x in range(1, 7)],      # Red (TL) Right
    1: [grid_to_px((7, y)) for y in range(1, 7)],      # Green (TR) Down
    2: [grid_to_px((x, 7)) for x in range(13, 7, -1)], # Yellow (BR) Left
    3: [grid_to_px((7, y)) for y in range(13, 7, -1)], # Blue (BL) Up
}

HOME_BASE_COORDS = {
    0: [grid_to_px((x, y)) for x, y in [(1.5, 1.5), (1.5, 3.5), (3.5, 1.5), (3.5, 3.5)]], # Red (TL)
    1: [grid_to_px((x, y)) for x, y in [(10.5, 1.5), (10.5, 3.5), (12.5, 1.5), (12.5, 3.5)]], # Green (TR)
    2: [grid_to_px((x, y)) for x, y in [(10.5, 10.5), (10.5, 12.5), (12.5, 10.5), (12.5, 12.5)]], # Yellow (BR)
    3: [grid_to_px((x, y)) for x, y in [(1.5, 10.5), (1.5, 12.5), (3.5, 10.5), (3.5, 12.5)]], # Blue (BL)
}

# Adjusted Safe Zones based on image stars:
# Indices in MAIN_PATH_GRID:
# Red Start: (1, 6) -> idx 10
# Green Start: (8, 1) -> idx 49
# Yellow Start: (13, 8) -> idx 36
# Blue Start: (6, 13) -> idx 23
# Additional Stars:
# (2, 8) -> idx 13
# (6, 2) -> idx 2
# (12, 6) -> idx 41
# (8, 12) -> idx 30

SAFE_ZONE_INDICES = {10, 49, 36, 23, 13, 2, 41, 30}

def get_token_pixel_position(color, logical_position, token_index=0):
    if logical_position == -1:
        return HOME_BASE_COORDS[color][token_index]
    if logical_position == 99:
        return grid_to_px((7, 7))
    if 0 <= logical_position <= 51:
        return MAIN_PATH_COORDS[logical_position]
    if 52 <= logical_position <= 57:
        stretch_idx = logical_position - 52
        return HOME_PATH_COORDS[color][stretch_idx]
    return (0, 0)
