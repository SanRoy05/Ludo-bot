def get_team_id(color):
    """
    Red (0) + Yellow (2) = Team 1
    Blue (1) + Green (3) = Team 2
    """
    if color in [0, 2]: return 1
    if color in [1, 3]: return 2
    return None

def is_teammate(color1, color2):
    return get_team_id(color1) == get_team_id(color2)

def check_team_victory(game_state):
    """
    Team wins when BOTH teammates finish all tokens.
    """
    team_finished = {1: True, 2: True}
    
    for player in game_state['players']:
        team_id = player['team_id']
        # If any player in the team hasn't finished all tokens, the team isn't finished
        all_tokens_finished = all(t['position'] == 99 for t in player['tokens'])
        if not all_tokens_finished:
            team_finished[team_id] = False
            
    # Check if either team has won
    if team_finished[1]: return 1
    if team_finished[2]: return 2
    return None

def can_kill(attacker_color, victim_color, is_safe_zone):
    if is_safe_zone: return False
    # In team mode, teammates do not kill each other
    if is_teammate(attacker_color, victim_color):
        return False
    return True
