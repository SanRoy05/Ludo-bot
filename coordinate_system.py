# Constants
GRID_SIZE = 15
UNIT_SIZE = 1000 // GRID_SIZE
OFFSET = UNIT_SIZE // 2

def grid_to_px(grid_pos):
    x, y = grid_pos
    return (int(x * UNIT_SIZE + OFFSET), int(y * UNIT_SIZE + OFFSET))

def get_path_coords():
    """Clockwise perimeter of 52 steps, starting from (6, 0)."""
    path = []
    for y in range(6): path.append((6, y))          # Top arm down (left side)
    for x in range(5, -1, -1): path.append((x, 6))  # Left arm left (top side)
    path.append((0, 7))                             # Left bridge
    for x in range(6): path.append((x, 8))           # Left arm right (bottom side)
    for y in range(9, 15): path.append((6, y))       # Bottom arm down (left side)
    path.append((7, 14))                            # Bottom bridge
    for y in range(14, 8, -1): path.append((8, y))  # Bottom arm up (right side)
    for x in range(9, 15): path.append((x, 8))       # Right arm right (bottom side)
    path.append((14, 7))                            # Right bridge
    for x in range(14, 8, -1): path.append((x, 6))  # Right arm left (top side)
    for y in range(5, -1, -1): path.append((8, y))  # Top arm up (right side)
    path.append((7, 0))                             # Top bridge
    return path

MAIN_PATH_GRID = get_path_coords()
MAIN_PATH_COORDS = [grid_to_px(pos) for pos in MAIN_PATH_GRID]

# HOME PATHS (6 per color)
# Home entries are from (0,7), (7,14), (14,7), (7,0)
HOME_PATH_COORDS = {
    0: [grid_to_px((7, y)) for y in range(13, 7, -1)], # Red (BL) -> Up
    1: [grid_to_px((x, 7)) for x in range(13, 7, -1)], # Green (BR) -> Left
    2: [grid_to_px((7, y)) for y in range(1, 7)],      # Yellow (TR) -> Down
    3: [grid_to_px((x, 7)) for x in range(1, 7)],      # Blue (TL) -> Right
}

# Base Slot Pixels (re-aligned to centers of white squares)
HOME_BASE_COORDS = {
    0: [grid_to_px(p) for p in [(1.5, 10.5), (1.5, 12.5), (3.5, 10.5), (3.5, 12.5)]], # Red (BL)
    1: [grid_to_px(p) for p in [(10.5, 10.5), (10.5, 12.5), (12.5, 10.5), (12.5, 12.5)]], # Green (BR)
    2: [grid_to_px(p) for p in [(10.5, 1.5), (10.5, 3.5), (12.5, 1.5), (12.5, 3.5)]], # Yellow (TR)
    3: [grid_to_px(p) for p in [(1.5, 1.5), (1.5, 3.5), (3.5, 1.5), (3.5, 3.5)]], # Blue (TL)
}

# Safe zone indices in the 52-step path (indices matching stars in user image)
# Blue:10, Blue+5:15, Red:23, Red+5:28, Green:36, Green+5:41, Yellow:49, Yellow+5:2
SAFE_ZONE_INDICES = {10, 15, 23, 28, 36, 41, 49, 2}

def get_token_pixel_position(color, logical_position, token_index=0):
    if logical_position == -1:
        return HOME_BASE_COORDS[color][token_index]
    if logical_position == 99:
        # Slightly offset center finish for multiple tokens
        cx, cy = grid_to_px((7, 7))
        if token_index == 0: return (cx-20, cy-20)
        if token_index == 1: return (cx+20, cy-20)
        if token_index == 2: return (cx-20, cy+20)
        return (cx+20, cy+20)
        
    if 0 <= logical_position <= 51:
        return MAIN_PATH_COORDS[logical_position]
    if 52 <= logical_position <= 57:
        stretch_idx = logical_position - 52
        return HOME_PATH_COORDS[color][stretch_idx]
    return (0, 0)
