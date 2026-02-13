from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
from coordinate_system import get_token_pixel_position, SAFE_ZONE_COORDS, UNIT_SIZE

def draw_glow(draw, x, y, color):
    """Draws a glowing halo around a position."""
    for i in range(10, 40, 5):
        alpha = int(100 * (1 - i/40))
        glow_color = (*color[:3], alpha)
        draw.ellipse([x-i, y-i, x+i, y+i], fill=glow_color)

def generate_base_board():
    """Programmatically generates a high-quality 1000x1000 Ludo board."""
    img = Image.new('RGB', (1000, 1000), (240, 240, 240))
    draw = ImageDraw.Draw(img)
    
    colors = {
        0: (231, 76, 60),  # Red
        1: (52, 152, 219), # Blue
        2: (241, 196, 15), # Yellow
        3: (46, 204, 113)  # Green
    }
    
    u = 1000 // 15
    # Bases
    draw.rectangle([0, 0, 6*u, 6*u], fill=colors[0])
    draw.rectangle([9*u, 0, 15*u, 6*u], fill=colors[1])
    draw.rectangle([9*u, 9*u, 15*u, 15*u], fill=colors[2])
    draw.rectangle([0, 9*u, 6*u, 15*u], fill=colors[3])
    
    # White base centers
    for base in [(u,u), (10*u,u), (10*u,10*u), (u,10*u)]:
        draw.rectangle([base[0], base[1], base[0]+4*u, base[1]+4*u], fill=(255,255,255))

    # Path
    for x in range(15):
        for y in range(15):
            if (6 <= x <= 8) or (6 <= y <= 8):
                if not (6 <= x <= 8 and 6 <= y <= 8): # Not center
                    draw.rectangle([x*u, y*u, (x+1)*u, (y+1)*u], outline=(200, 200, 200))

    # Home Stretches
    for i in range(1, 7):
        draw.rectangle([7*u, i*u, 8*u, (i+1)*u], fill=colors[0]) # Red
        draw.rectangle([(14-i)*u, 7*u, (15-i)*u, 8*u], fill=colors[1]) # Blue
        draw.rectangle([7*u, (14-i)*u, 8*u, (15-i)*u], fill=colors[2]) # Yellow
        draw.rectangle([i*u, 7*u, (i+1)*u, 8*u], fill=colors[3]) # Green

    # Start tiles
    draw.rectangle([6*u, 1*u, 7*u, 2*u], fill=colors[0])
    draw.rectangle([13*u, 6*u, 14*u, 7*u], fill=colors[1])
    draw.rectangle([8*u, 13*u, 9*u, 14*u], fill=colors[2])
    draw.rectangle([1*u, 8*u, 2*u, 9*u], fill=colors[3])

    # Safe zones (stars)
    for idx in SAFE_ZONE_COORDS:
        # Drawing a small circle for safe zone
        from coordinate_system import MAIN_PATH_COORDS
        px, py = MAIN_PATH_COORDS[idx]
        draw.ellipse([px-10, py-10, px+10, py+10], fill=(200, 200, 200))

    # Center (Finish)
    draw.rectangle([6*u, 6*u, 9*u, 9*u], fill=(255, 255, 255))
    # Triangles in center
    draw.polygon([(7.5*u, 7.5*u), (6*u, 6*u), (9*u, 6*u)], fill=colors[0])
    draw.polygon([(7.5*u, 7.5*u), (9*u, 6*u), (9*u, 9*u)], fill=colors[1])
    draw.polygon([(7.5*u, 7.5*u), (9*u, 9*u), (6*u, 9*u)], fill=colors[2])
    draw.polygon([(7.5*u, 7.5*u), (6*u, 9*u), (6*u, 6*u)], fill=colors[3])

    return img

BASE_BOARD_IMG = generate_base_board()

def render_board(game_state):
    """
    game_state: dict containing 'players' and 'current_turn_index'
    """
    img = BASE_BOARD_IMG.copy()
    overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    player_colors = {
        0: (231, 76, 60, 255),  # Red
        1: (52, 152, 219, 255), # Blue
        2: (241, 196, 15, 255), # Yellow
        3: (46, 204, 113, 255)  # Green
    }
    
    # Track occupations for stacking
    occupations = {} # label -> list of (color, index)
    
    for p_idx, player in enumerate(game_state['players']):
        for t_idx, token in enumerate(player['tokens']):
            if token['position'] == 99: continue # Skip finished for simplified stacking
            
            pos_key = (player['color'], token['position'])
            if pos_key not in occupations: occupations[pos_key] = []
            occupations[pos_key].append((player['color'], t_idx))

    # Draw glow for current player
    curr_turn = game_state.get('current_turn_index', 0)
    curr_player = game_state['players'][curr_turn]
    glow_color = player_colors[curr_player['color']]
    
    for t in curr_player['tokens']:
        if -1 <= t['position'] < 99:
            px, py = get_token_pixel_position(curr_player['color'], t['position'], t['token_index'])
            draw_glow(draw, px, py, glow_color)

    # Draw tokens
    for pos_key, occupants in occupations.items():
        color, pos = pos_key
        # Base position
        # For base positions (-1), they have specific slots, so we don't stack offsets there
        if pos == -1:
            for p_color, t_idx in occupants:
                px, py = get_token_pixel_position(p_color, pos, t_idx)
                # Shadow
                draw.ellipse([px-22, py-22+4, px+22, py+22+4], fill=(0, 0, 0, 60))
                # Token
                draw.ellipse([px-22, py-22, px+22, py+22], fill=player_colors[p_color], outline=(255,255,255, 100), width=2)
        else:
            # Main path stacking
            base_px, base_py = get_token_pixel_position(color, pos)
            count = len(occupants)
            for i, (p_color, t_idx) in enumerate(occupants):
                # Offset logic
                off_x = (i - (count-1)/2) * 15 if count > 1 else 0
                off_y = (i - (count-1)/2) * 5 if count > 1 else 0
                px, py = base_px + off_x, base_py + off_y
                
                # Shadow
                draw.ellipse([px-22, py-22+4, px+22, py+22+4], fill=(0, 0, 0, 60))
                # Token
                draw.ellipse([px-22, py-22, px+22, py+22], fill=player_colors[p_color], outline=(255,255,255), width=2)
                
                # Check if finished (though 99 is filtered, home stretch end might need crown)
                if pos == 57:
                    # Draw crown placeholder or text
                    draw.text((px-5, py-10), "👑", fill=(255,255,255))

    img.paste(overlay, (0, 0), overlay)
    
    # Text overlay
    draw_final = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except:
        font = ImageFont.load_default()
        
    status_text = f"Turn: @{curr_player['username']}"
    draw_final.text((20, 20), status_text, fill=(50, 50, 50), font=font)
    
    if game_state.get('team_mode'):
        team_text = f"TEAM MODE - Team {curr_player['team_id']}"
        draw_final.text((750, 20), team_text, fill=(50, 50, 50), font=font)

    # Return as BytesIO
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf
