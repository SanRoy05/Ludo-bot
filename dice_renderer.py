from PIL import Image, ImageDraw
import io

def generate_dice_frame(value):
    """Generates a high-quality dice face image."""
    size = 200
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Shadow
    draw.rounded_rectangle([10, 15, 190, 195], radius=30, fill=(0, 0, 0, 40))
    # Base
    draw.rounded_rectangle([10, 10, 190, 190], radius=30, fill=(255, 255, 255), outline=(200, 200, 200))
    
    dot_radius = 15
    dots = {
        1: [(100, 100)],
        2: [(60, 60), (140, 140)],
        3: [(60, 60), (100, 100), (140, 140)],
        4: [(60, 60), (140, 60), (60, 140), (140, 140)],
        5: [(60, 60), (140, 60), (100, 100), (60, 140), (140, 140)],
        6: [(60, 60), (140, 60), (60, 100), (140, 100), (60, 140), (140, 140)]
    }
    
    for dot_pos in dots.get(value, []):
        x, y = dot_pos
        draw.ellipse([x-dot_radius, y-dot_radius, x+dot_radius, y+dot_radius], fill=(0, 0, 0))
        
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf
