from team_logic import can_kill, is_teammate, check_team_victory

def get_start_position(color):
    """
    Returns the starting position for each color when exiting base with a 6.
    Based on standard Ludo board layout with clockwise movement.
    
    Color mapping based on visual board positions:
    - Blue (3): Top-left quadrant → starts at position 1 (arrow pointing right, enters from left)
    - Yellow (2): Top-right quadrant → starts at position 40 (arrow pointing down, enters from top-right)
    - Red (0): Bottom-left quadrant → starts at position 14 (arrow pointing up, enters from bottom-left)
    - Green (1): Bottom-right quadrant → starts at position 27 (arrow pointing left, enters from bottom-right)
    
    Path starts at (6,0) and goes clockwise around the 52-position main path.
    """
    return {0: 14, 1: 27, 2: 40, 3: 1}[color]

def get_entrance_position(color):
    """
    Returns the position where a token enters its home stretch.
    This is exactly 50 steps from the starting position.
    """
    start = get_start_position(color)
    return (start + 50) % 52

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
        # Calculate steps to home entrance
        entrance = get_entrance_position(color)
        
        # We need to know how many steps the token has already taken to avoid infinite loops
        # Since we don't store steps_taken, we calculate distance from start
        start = get_start_position(color)
        dist_from_start = (current_pos - start) % 52
        
        remaining_main = 51 - dist_from_start
        
        if dice_value <= remaining_main:
            return (current_pos + dice_value) % 52, False
        else:
            # Entering home stretch
            steps_into_home = dice_value - remaining_main
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
