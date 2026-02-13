from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
from coordinate_system import get_token_pixel_position, SAFE_ZONE_INDICES, UNIT_SIZE, MAIN_PATH_COORDS, HOME_BASE_COORDS

def draw_star(draw, x, y, size, fill):
    """Draws a star shape."""
    points = []
    for i in range(10):
        radius = size if i % 2 == 0 else size / 2.5
        import math
        angle = math.radians(i * 36 - 90)
        points.append((x + radius * math.cos(angle), y + radius * math.sin(angle)))
    draw.polygon(points, fill=fill, outline=(100, 100, 100))

def draw_arrow(draw, x, y, direction, color):
    """Draws an entrance arrow."""
    u = UNIT_SIZE
    if direction == 'right': # Red
        points = [(x-u/3, y-u/4), (x, y-u/4), (x, y-u/2), (x+u/2, y), (x, y+u/2), (x, y+u/4), (x-u/3, y+u/4)]
    elif direction == 'down': # Green
        points = [(x-u/4, y-u/3), (x-u/4, y), (x-u/2, y), (x, y+u/2), (x+u/2, y), (x+u/4, y), (x+u/4, y-u/3)]
    elif direction == 'left': # Yellow
        points = [(x+u/3, y-u/4), (x, y-u/4), (x, y-u/2), (x-u/2, y), (x, y+u/2), (x, y+u/4), (x+u/3, y+u/4)]
    elif direction == 'up': # Blue
        points = [(x-u/4, y+u/3), (x-u/4, y), (x-u/2, y), (x, y-u/2), (x+u/2, y), (x+u/4, y), (x+u/4, y+u/3)]
    draw.polygon(points, fill=color)

def generate_base_board():
    """Generates the enhanced Ludo board matching the image."""
    img = Image.new('RGB', (1000, 1000), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    u = UNIT_SIZE
    
    # Red, Green, Yellow, Blue (TL, TR, BR, BL)
    colors = {
        0: (231, 76, 60),  # Red
        1: (46, 204, 113), # Green
        2: (241, 196, 15), # Yellow
        3: (52, 152, 219)  # Blue
    }
    
    # Bases
    draw.rectangle([0, 0, 6*u, 6*u], fill=colors[0])
    draw.rectangle([9*u, 0, 15*u, 6*u], fill=colors[1])
    draw.rectangle([9*u, 9*u, 15*u, 15*u], fill=colors[2])
    draw.rectangle([0, 9*u, 6*u, 15*u], fill=colors[3])
    
    # White base centers with circular slots
    for b_idx, base in enumerate([(u,u), (10*u,u), (10*u,10*u), (u,10*u)]):
        draw.rectangle([base[0], base[1], base[0]+4*u, base[1]+4*u], fill=(255,255,255))
        # Draw 4 circular slots
        for px, py in HOME_BASE_COORDS[b_idx]:
            draw.ellipse([px-35, py-35, px+35, py+35], outline=colors[b_idx], width=3)

    # Path Grid
    for x in range(15):
        for y in range(15):
            if (6 <= x <= 8) or (6 <= y <= 8):
                if not (6 <= x <= 8 and 6 <= y <= 8):
                    draw.rectangle([x*u, y*u, (x+1)*u, (y+1)*u], outline=(220, 220, 220))

    # Home Stretches
    for i in range(1, 7):
        draw.rectangle([i*u, 7*u, (i+1)*u, 8*u], fill=colors[0]) # Red (Left arm)
        draw.rectangle([7*u, i*u, 8*u, (i+1)*u], fill=colors[1]) # Green (Top arm)
        draw.rectangle([(14-i)*u, 7*u, (15-i)*u, 8*u], fill=colors[2]) # Yellow (Right arm)
        draw.rectangle([7*u, (14-i)*u, 8*u, (15-i)*u], fill=colors[3]) # Blue (Bottom arm)

    # Safe Zone Stars
    for idx in SAFE_ZONE_INDICES:
        px, py = MAIN_PATH_COORDS[idx]
        draw_star(draw, px, py, 20, (255, 255, 255))

    # Entry Arrows
    draw_arrow(draw, 0.5*u, 7.5*u, 'right', colors[0])
    draw_arrow(draw, 7.5*u, 0.5*u, 'down', colors[1])
    draw_arrow(draw, 14.5*u, 7.5*u, 'left', colors[2])
    draw_arrow(draw, 7.5*u, 14.5*u, 'up', colors[3])

    # Center Finish
    draw.rectangle([6*u, 6*u, 9*u, 9*u], fill=(255, 255, 255))
    draw.polygon([(7.5*u, 7.5*u), (6*u, 6*u), (6*u, 9*u)], fill=colors[0]) # Left
    draw.polygon([(7.5*u, 7.5*u), (6*u, 6*u), (9*u, 6*u)], fill=colors[1]) # Top
    draw.polygon([(7.5*u, 7.5*u), (9*u, 6*u), (9*u, 9*u)], fill=colors[2]) # Right
    draw.polygon([(7.5*u, 7.5*u), (6*u, 9*u), (9*u, 9*u)], fill=colors[3]) # Bottom

    return img

BASE_BOARD_IMG = generate_base_board()

def draw_glow(draw, x, y, color):
    for i in range(10, 40, 5):
        alpha = int(100 * (1 - i/40))
        glow_color = (*color[:3], alpha)
        draw.ellipse([x-i, y-i, x+i, y+i], fill=glow_color)

def render_board(game_state):
    img = BASE_BOARD_IMG.copy()
    overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    player_colors = {
        0: (231, 76, 60, 255),  # Red
        1: (46, 204, 113, 255), # Green
        2: (241, 196, 15, 255), # Yellow
        3: (52, 152, 219, 255)  # Blue
    }
    
    occupations = {}
    for p_idx, player in enumerate(game_state['players']):
        for t_idx, token in enumerate(player['tokens']):
            if token['position'] == 99: continue
            pos_key = (player['color'], token['position'])
            if pos_key not in occupations: occupations[pos_key] = []
            occupations[pos_key].append((p_idx, t_idx))

    # Glow
    curr_turn = game_state.get('current_turn_index', 0)
    if curr_turn < len(game_state['players']):
        curr_player = game_state['players'][curr_turn]
        glow_c = player_colors[curr_player['color']]
        for t in curr_player['tokens']:
            if -1 <= t['position'] < 99:
                px, py = get_token_pixel_position(curr_player['color'], t['position'], t['token_index'])
                draw_glow(draw, px, py, glow_c)

    # Tokens
    for pos_key, occupants in occupations.items():
        color, pos = pos_key
        count = len(occupants)
        
        for i, (p_idx, t_idx) in enumerate(occupants):
            p_color = game_state['players'][p_idx]['color']
            if pos == -1:
                px, py = get_token_pixel_position(p_color, pos, t_idx)
            else:
                base_px, base_py = get_token_pixel_position(p_color, pos)
                off_x = (i - (count-1)/2) * 15 if count > 1 else 0
                off_y = (i - (count-1)/2) * 5 if count > 1 else 0
                px, py = base_px + off_x, base_py + off_y
            
            # Shadow
            draw.ellipse([px-22, py-22+4, px+22, py+22+4], fill=(0, 0, 0, 60))
            # Border
            draw.ellipse([px-24, py-24, px+24, py+24], fill=(255, 255, 255))
            # Token
            draw.ellipse([px-22, py-22, px+22, py+22], fill=player_colors[p_color])
            # Inner gloss
            draw.ellipse([px-10, py-10, px+5, py+5], fill=(255, 255, 255, 100))

    img.paste(overlay, (0, 0), overlay)
    draw_final = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("arial.ttf", 30)
    except: font = ImageFont.load_default()
    
    if curr_turn < len(game_state['players']):
        curr_p = game_state['players'][curr_turn]
        draw_final.text((20, 20), f"Turn: @{curr_p['username']}", fill=(50, 50, 50), font=font)
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf
