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
    
    # Updated Colors mapping to match standard layout and image:
    # 0: Red (BL), 1: Green (BR), 2: Yellow (TR), 3: Blue (TL)
    colors = {
        0: (231, 76, 60),  # Red
        1: (46, 204, 113), # Green
        2: (241, 196, 15), # Yellow
        3: (52, 152, 219)  # Blue
    }
    
    # Bases - Re-positioned to match the image:
    # Blue: Top-Left, Yellow: Top-Right, Green: Bottom-Right, Red: Bottom-Left
    draw.rectangle([0, 0, 6*u, 6*u], fill=colors[3])      # Blue (TL)
    draw.rectangle([9*u, 0, 15*u, 6*u], fill=colors[2])   # Yellow (TR)
    draw.rectangle([9*u, 9*u, 15*u, 15*u], fill=colors[1]) # Green (BR)
    draw.rectangle([0, 9*u, 6*u, 15*u], fill=colors[0])    # Red (BL)
    
    # White base centers with circular slots
    # Base positions: TL(3), TR(2), BR(1), BL(0)
    for b_idx, base in enumerate([(0,0), (9*u,0), (9*u,9*u), (0,9*u)]):
        # b_idx mapping: 0:Blue(TL), 1:Yellow(TR), 2:Green(BR), 3:Red(BL)? No.
        # Let's use explicit color mapping for base slots:
        color_order = [3, 2, 1, 0] # TL, TR, BR, BL
        c_idx = color_order[b_idx]
        draw.rectangle([base[0]+u, base[1]+u, base[0]+5*u, base[1]+5*u], fill=(255,255,255))
        # Draw 4 circular slots
        for px, py in HOME_BASE_COORDS[c_idx]:
            draw.ellipse([px-35, py-35, px+35, py+35], outline=colors[c_idx], width=3)

    # Path Grid
    for x in range(15):
        for y in range(15):
            if (6 <= x <= 8) or (6 <= y <= 8):
                if not (6 <= x <= 8 and 6 <= y <= 8):
                    draw.rectangle([x*u, y*u, (x+1)*u, (y+1)*u], outline=(220, 220, 220))

    # Home Stretches - Updated to match new layout:
    for i in range(1, 7):
        draw.rectangle([7*u, (14-i)*u, 8*u, (15-i)*u], fill=colors[0]) # Red (Bottom arm)
        draw.rectangle([(14-i)*u, 7*u, (15-i)*u, 8*u], fill=colors[1]) # Green (Right arm)
        draw.rectangle([7*u, i*u, 8*u, (i+1)*u], fill=colors[2])       # Yellow (Top arm)
        draw.rectangle([i*u, 7*u, (i+1)*u, 8*u], fill=colors[3])       # Blue (Left arm)

    # Safe Zone Stars
    for idx in SAFE_ZONE_INDICES:
        px, py = MAIN_PATH_COORDS[idx]
        draw_star(draw, px, py, 20, (255, 255, 255))

    # Entry Arrows - Updated directions for new color positions:
    draw_arrow(draw, 7.5*u, 14.5*u, 'up', colors[0])    # Red (Bottom)
    draw_arrow(draw, 14.5*u, 7.5*u, 'left', colors[1])  # Green (Right)
    draw_arrow(draw, 7.5*u, 0.5*u, 'down', colors[2])   # Yellow (Top)
    draw_arrow(draw, 0.5*u, 7.5*u, 'right', colors[3])  # Blue (Left)

    # Center Finish - Updated colors for triangles to match the arm colors:
    draw.rectangle([6*u, 6*u, 9*u, 9*u], fill=(255, 255, 255))
    draw.polygon([(7.5*u, 7.5*u), (6*u, 9*u), (9*u, 9*u)], fill=colors[0]) # Bottom (Red)
    draw.polygon([(7.5*u, 7.5*u), (9*u, 6*u), (9*u, 9*u)], fill=colors[1]) # Right (Green)
    draw.polygon([(7.5*u, 7.5*u), (6*u, 6*u), (9*u, 6*u)], fill=colors[2]) # Top (Yellow)
    draw.polygon([(7.5*u, 7.5*u), (6*u, 6*u), (6*u, 9*u)], fill=colors[3]) # Left (Blue)

    return img

import os

def load_base_board():
    """Loads a custom board image if exists, otherwise generates one."""
    if os.path.exists("playing_board.png"):
        try:
            img = Image.open("playing_board.png").convert('RGB')
            # Ensure it's 1000x1000 to match coordinate system
            if img.size != (1000, 1000):
                img = img.resize((1000, 1000), Image.LANCZOS)
            return img
        except:
            pass
    return generate_base_board()

BASE_BOARD_IMG = load_base_board()

def draw_glow(draw, x, y, color):
    # Simplified glow: 3 ellipses instead of 6
    for i in range(15, 36, 10):
        alpha = int(80 * (1 - i/40))
        glow_color = (*color[:3], alpha)
        draw.ellipse([x-i, y-i, x+i, y+i], fill=glow_color)

def render_board(game_state):
    # Performance: Only check board file logic if not already loaded once
    global BASE_BOARD_IMG
    if not hasattr(render_board, "bg_loaded") or not render_board.bg_loaded:
        if os.path.exists("playing_board.png"):
            BASE_BOARD_IMG = load_base_board()
        render_board.bg_loaded = True

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

    # Glow for current player's tokens
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
            base_px, base_py = get_token_pixel_position(p_color, pos, t_idx)
            
            px, py = base_px, base_py
            if pos != -1 and count > 1:
                off_x = (i - (count-1)/2) * 15
                off_y = (i - (count-1)/2) * 15
                px, py = px + off_x, py + off_y
            
            # Simplified shadow (one ellipse)
            draw.ellipse([px-22, py-18, px+22, py+26], fill=(0, 0, 0, 40))
            # Border
            draw.ellipse([px-24, py-24, px+24, py+24], fill=(255, 255, 255))
            # Token
            draw.ellipse([px-22, py-22, px+22, py+22], fill=player_colors[p_color])
            # Inner gloss (Simplified)
            draw.ellipse([px-10, py-10, px+5, py+5], fill=(255, 255, 255, 80))

    img.paste(overlay, (0, 0), overlay)
    draw_final = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("arial.ttf", 35)
    except: font = ImageFont.load_default()
    
    if curr_turn < len(game_state['players']):
        curr_p = game_state['players'][curr_turn]
        draw_final.rectangle([10, 10, 400, 60], fill=(255, 255, 255, 200))
        draw_final.text((20, 15), f"Turn: @{curr_p['username']}", fill=(0, 0, 0), font=font)
    
    buf = io.BytesIO()
    # Optimized: Save as JPEG with 85% quality instead of PNG
    # This significantly reduces file size (e.g. 200KB -> 40KB) and improves speed
    img.save(buf, format='JPEG', quality=85)
    buf.seek(0)
    return buf
