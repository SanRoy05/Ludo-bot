from team_logic import can_kill, is_teammate, check_team_victory

def get_start_position(color):
    """
    Returns the starting position for each color based on the 52-step path.
    Mapping (matching user board image):
    - Red (0): Bottom-left quadrant → starts at index 23 (grid 6, 13)
    - Green (1): Bottom-right quadrant → starts at index 36 (grid 13, 8)
    - Yellow (2): Top-right quadrant → starts at index 49 (grid 8, 1)
    - Blue (3): Top-left quadrant → starts at index 10 (grid 1, 6)
    """
    return {0: 23, 1: 36, 2: 49, 3: 10}[color]

def get_entrance_position(color):
    """
    Returns the position index (on the 52-step path) where a token turns into home.
    Matches the arrow positions in the image: Blue:12, Red:25, Green:38, Yellow:51.
    """
    return {0: 25, 1: 38, 2: 51, 3: 12}[color]

def move_token(player, token_idx, dice_value):
    token = player['tokens'][token_idx]
    current_pos = token['position']
    color = player['color']
    
    if current_pos == -1:
        if dice_value == 6:
            return get_start_position(color), False
        return -1, False
    
    if current_pos == 99:
        return 99, False
    
    if 0 <= current_pos <= 51:
        # Calculate steps remaining on main path
        # In Ludo, you exit main path at the threshold.
        # Thresholds: B:11, R:24, G:37, Y:50
        threshold = get_entrance_position(color)
        
        # Steps from current to threshold (clockwise)
        if current_pos <= threshold:
            steps_to_threshold = threshold - current_pos
        else:
            steps_to_threshold = (52 - current_pos) + threshold
            
        if dice_value <= steps_to_threshold:
            return (current_pos + dice_value) % 52, False
        else:
            # Entering home stretch
            steps_into_home = dice_value - steps_to_threshold
            # Home path starts at 52 (index 0 of home stretch)
            new_pos = 51 + steps_into_home 
            if new_pos > 57:
                if new_pos == 58: return 99, True # Exactly finished
                return current_pos, False # Too high
            return new_pos, False
            
    if 52 <= current_pos <= 57:
        new_pos = current_pos + dice_value
        if new_pos > 57:
            if new_pos == 58: return 99, True
            return current_pos, False
        return new_pos, False
        
    return current_pos, False

def get_killing_impact(game, attacker_color, new_pos):
    """
    Checks if a move kills any other tokens.
    Returns list of tokens to reset: (player_idx, token_idx)
    """
    if new_pos < 0 or new_pos > 51: return [] # Home stretch/base is safe
    
    # Safe zones (stars)
    from coordinate_system import SAFE_ZONE_INDICES
    if new_pos in SAFE_ZONE_INDICES: return []
    
    to_reset = []
    for p_idx, player in enumerate(game['players']):
        if player['color'] == attacker_color: continue
        
        # Check team logic
        if game.get('team_mode') and is_teammate(attacker_color, player['color']):
            continue
            
        for t_idx, token in enumerate(player['tokens']):
            if token['position'] == new_pos:
                to_reset.append((p_idx, t_idx))
                
    return to_reset
