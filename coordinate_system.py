def get_path_coords():
    """Generates the 52 main path coordinates for a 15x15 grid ludo board."""
    # Each unit on a 1000x1000 board is ~66.67px
    # Grid coordinates (0-14, 0-14)
    path = []
    
    # Starting from (6, 0) and going clockwise
    # Top column (Middle)
    for y in range(6): path.append((6, y))
    # Top-Left path
    for x in range(5, -1, -1): path.append((x, 6))
    path.append((0, 7))
    for x in range(6): path.append((x, 8))
    # Bottom-Left path
    for y in range(9, 15): path.append((6, y))
    path.append((7, 14))
    for y in range(14, 8, -1): path.append((8, y))
    # Bottom-Right path
    for x in range(9, 15): path.append((x, 8))
    path.append((14, 7))
    for x in range(14, 8, -1): path.append((x, 6))
    # Top-Right path
    for y in range(5, -1, -1): path.append((8, y))
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
# P0 (Red): Entrance at path[0] (6,0) -> NO, entrance is from path[51] (7,0)? 
# Let's re-align to standard:
# Red Start is (6,1). Exit to home is (7,0)? 
# Actually, if we use the list above:
# Red (Top-Left Base) starts at path[1] (6,1).
# Red turns into home stretch from path[51] (7,0) into (7,1)-(7,6).
# Blue (Top-Right Base) starts at path[40] (13,6).
# Blue turns into home stretch from path[39] (14,7) into (13-8, 7).
# Yellow (Bottom-Right Base) starts at path[27] (8,13).
# Yellow turns into home stretch from path[26] (7,14) into (7, 13-8).
# Green (Bottom-Left Base) starts at path[14] (1,8).
# Green turns into home stretch from path[13] (0,7) into (1-6, 7).

HOME_PATH_COORDS = {
    0: [grid_to_px((7, y)) for y in range(1, 7)],      # Red (P0) Down
    1: [grid_to_px((x, 7)) for x in range(13, 7, -1)], # Blue (P1) Left
    2: [grid_to_px((7, y)) for y in range(13, 7, -1)], # Yellow (P2) Up
    3: [grid_to_px((x, 7)) for x in range(1, 7)],      # Green (P3) Right
}

HOME_BASE_COORDS = {
    0: [grid_to_px((x, y)) for x in [(1,1), (1,4), (4,1), (4,4)]], # Red
    1: [grid_to_px((x, y)) for x in [(10,1), (10,4), (13,1), (13,4)]], # Blue
    2: [grid_to_px((x, y)) for x in [(10,10), (10,13), (13,10), (13,13)]], # Yellow
    3: [grid_to_px((x, y)) for x in [(1,10), (1,13), (4,10), (4,13)]], # Green
}

SAFE_ZONE_COORDS = {1, 9, 14, 22, 27, 35, 40, 48}

def get_token_pixel_position(color, logical_position, token_index=0):
    """
    logical_position:
    -1: Home Base
    0-51: Main Path
    52-57: Home Stretch
    99: Finished
    """
    if logical_position == -1:
        return HOME_BASE_COORDS[color][token_index]
    
    if logical_position == 99:
        # Center of the board (Finished)
        return grid_to_px((7, 7))
    
    if 0 <= logical_position <= 51:
        # The main path is fixed for all. 
        # But each color has a relative start.
        # However, the DB stores absolute positions 0-51 based on our clockwise map.
        return MAIN_PATH_COORDS[logical_position]
    
    if 52 <= logical_position <= 57:
        # Home stretch is relative to color
        stretch_idx = logical_position - 52
        return HOME_PATH_COORDS[color][stretch_idx]
    
    return (0, 0)
