from typing import List, Tuple
from .state import GameState, Player, Token
import logging

logger = logging.getLogger(__name__)

# Starting positions on the shared 0-51 track
START_POSITIONS = {
    0: 0,   # Red
    1: 13,  # Yellow
    2: 26,  # Green
    3: 39   # Blue
}

def get_track_pos(color_index: int, relative_pos: int) -> int:
    """
    Converts relative position (0-50) to shared track position (0-51).
    relative_pos 0 is the starting square for that color.
    """
    start = START_POSITIONS[color_index]
    return (start + relative_pos) % 52

def can_move_token(player: Player, token_index: int, dice: int) -> bool:
    token = player.tokens[token_index]
    
    if token.state == "home":
        return dice == 6
    
    if token.state == "finished":
        return False
    
    if token.state == "active":
        # Check if the move would overshoot the finish (56)
        if (token.pos + dice) > 56:
            return False
        return True
    
    return False

def move_token(state: GameState, player_index: int, token_index: int, dice: int) -> bool:
    """
    Moves a token and handles collisions.
    Returns True if an opponent token was killed.
    """
    player = state.players[player_index]
    if token_index < 0 or token_index >= len(player.tokens):
        return False
        
    token = player.tokens[token_index]
    killed = False
    
    if token.state == "home":
        if dice == 6:
            token.state = "active"
            token.pos = 0 # Just entered track
        else:
            return False # Should not happen if get_valid_moves is used
    elif token.state == "active":
        if (token.pos + dice) <= 56:
            token.pos += dice
            # Check if finished
            if token.pos == 56:
                token.state = "finished"
        else:
            return False
            
    # Collision detection (only if on main track 0-50)
    if token.state == "active" and token.pos <= 50:
        global_pos = get_track_pos(player.color_index, token.pos)
        
        # Safe zones
        from config import SAFE_POSITIONS
        safe_spots = [p - 1 for p in SAFE_POSITIONS]
        
        if global_pos not in safe_spots:
            for other_idx, other_player in enumerate(state.players):
                if other_idx == player_index: continue
                
                for other_token in other_player.tokens:
                    if other_token.state == "active" and other_token.pos <= 50:
                        other_global = get_track_pos(other_player.color_index, other_token.pos)
                        if other_global == global_pos:
                            # Kill it!
                            other_token.state = "home"
                            other_token.pos = 0
                            killed = True
    
    return killed

def is_game_over(player: Player) -> bool:
    return all(token.state == "finished" for token in player.tokens)

def get_valid_moves(player: Player, dice: int) -> List[int]:
    valid = []
    for i in range(4):
        if can_move_token(player, i, dice):
            valid.append(i)
    logger.info(f"get_valid_moves for {player.first_name} (dice={dice}): {valid}")
    return valid
