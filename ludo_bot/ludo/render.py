from .state import GameState
from config import COLORS

# Pre-defined Coordinate Mapping for Tokens
# (y, x) coordinates for main track (0-51)
MAIN_TRACK_COORDS = [
    (13,6),(12,6),(11,6),(10,6),(9,6), # Red start path
    (8,5),(8,4),(8,3),(8,2),(8,1),(8,0), # To Left
    (7,0), # Left center
    (6,0),(6,1),(6,2),(6,3),(6,4),(6,5), # From Left
    (5,6),(4,6),(3,6),(2,6),(1,6),(0,6), # To Top
    (0,7), # Top center
    (0,8),(1,8),(2,8),(3,8),(4,8),(5,8), # From Top
    (6,9),(6,10),(6,11),(6,12),(6,13),(6,14), # To Right
    (7,14), # Right center
    (8,14),(8,13),(8,12),(8,11),(8,10),(8,9), # From Right
    (9,8),(10,8),(11,8),(12,8),(13,8),(14,8), # To Bottom
    (14,7), # Bottom center
    (14,6) # From Bottom (closes at 13,6)
]

# (y, x) coordinates for home paths (0-4 index maps to pos 51-55)
HOME_PATHS = {
    0: [(13,7),(12,7),(11,7),(10,7),(9,7)], # Red (Bottom)
    1: [(7,1),(7,2),(7,3),(7,4),(7,5)],     # Yellow (Left)
    2: [(1,7),(2,7),(3,7),(4,7),(5,7)],     # Green (Top)
    3: [(7,13),(7,12),(7,11),(7,10),(7,9)] # Blue (Right)
}

# (y, x) coordinates for home room squares
ROOM_COORDS = {
    0: [(11,2),(11,3),(12,2),(12,3)], # Red (BL)
    1: [(2,11),(2,12),(3,11),(3,12)], # Yellow (TR)
    2: [(2,2),(2,3),(3,2),(3,3)],     # Green (TL)
    3: [(11,11),(11,12),(12,11),(12,12)] # Blue (BR)
}

SAFE_INDEXES = [0, 8, 13, 21, 26, 34, 39, 47]

def generate_base_board():
    """Generates the static part of the Ludo board."""
    board = [["⬛" for _ in range(15)] for _ in range(15)]
    
    # Path areas
    for y in range(6):
        for x in range(6, 9): board[y][x] = "⬜"
    for y in range(9, 15):
        for x in range(6, 9): board[y][x] = "⬜"
    for y in range(6, 9):
        for x in range(6): board[y][x] = "⬜"
    for y in range(6, 9):
        for x in range(9, 15): board[y][x] = "⬜"
    
    # Static home rooms
    for y, x in ROOM_COORDS[0]: board[y][x] = "🔴"
    for y, x in ROOM_COORDS[1]: board[y][x] = "🟡"
    for y, x in ROOM_COORDS[2]: board[y][x] = "🟢"
    for y, x in ROOM_COORDS[3]: board[y][x] = "🔵"
    
    # Safe spots
    for idx in SAFE_INDEXES:
        y, x = MAIN_TRACK_COORDS[idx]
        board[y][x] = "🛡️"
        
    board[7][7] = "👑"
    return board

# Global Static Board
BASE_BOARD = generate_base_board()

def render_board(state: GameState) -> str:
    """Optimized renderer that overlays tokens on a base board template."""
    # Copy the static base board
    board = [row[:] for row in BASE_BOARD]
    
    # Overlay Tokens
    for p in state.players:
        color_char = COLORS[p.color_index]
        p_room = ROOM_COORDS[p.color_index]
        home_idx = 0
        
        for t in p.tokens:
            if t.state == "home":
                # Render inside room if space available
                if home_idx < len(p_room):
                    ry, rx = p_room[home_idx]
                    board[ry][rx] = color_char
                    home_idx += 1
            elif t.state == "active":
                if t.pos <= 50:
                    # Circular track coordinate
                    from .rules import get_track_pos
                    track_idx = get_track_pos(p.color_index, t.pos)
                    y, x = MAIN_TRACK_COORDS[track_idx]
                    board[y][x] = color_char
                elif 51 <= t.pos <= 55:
                    # Home path coordinate
                    path_idx = t.pos - 51
                    y, x = HOME_PATHS[p.color_index][path_idx]
                    board[y][x] = color_char
            # "finished" tokens are explicitly NOT rendered
            
    return "\n".join(["".join(row) for row in board])
