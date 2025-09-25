from PIL import Image, ImageOps, ImageDraw
import os

# Source icon (should be high-res, e.g., 128x128)
SOURCE_ICON = 'icons/icon128.png'
SIZES = [16, 32, 48, 128]

def create_resized_icons(source_icon, sizes):
    img = Image.open(source_icon).convert("RGBA")
    for size in sizes:
        resized = img.resize((size, size), Image.LANCZOS)
        out_path = f'icons/icon{size}.png'
        resized.save(out_path)
        print(f"Created: {out_path}")

def create_grayscale_icons(sizes):
    for size in sizes:
        icon_path = f'icons/icon{size}.png'
        if os.path.exists(icon_path):
            img = Image.open(icon_path)
            gray_img = ImageOps.grayscale(img).convert("RGBA")
            out_path = f'icons/icon{size}_gray.png'
            gray_img.save(out_path)
            print(f"Created: {out_path}")
        else:
            print(f"Warning: {icon_path} not found")

def create_arrow_icon(output_path, color):
    """Create a 16x16 icon with a colored arrow (green or red)."""
    size = 32
    img = Image.new('RGBA', (size, size), color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    # Draw a simple arrow (triangle)
    arrow = [
        (size // 2, 3),      # Tip
        (size - 3, size - 4), # Bottom right
        (3, size - 4)        # Bottom left
    ]
    draw.polygon(arrow, fill=color)
    img.save(output_path)
    print(f"Created: {output_path}")

if __name__ == "__main__":
    if not os.path.exists(SOURCE_ICON):
        print(f"Source icon {SOURCE_ICON} not found!")
    else:
        create_resized_icons(SOURCE_ICON, SIZES)
        create_grayscale_icons(SIZES)
        # Generate arrow icons for extension connection status
        GREEN = (76, 175, 80, 255)
        RED = (220, 0, 0, 255)
        create_arrow_icon("icons/empty16_connected.png", GREEN)
        create_arrow_icon("icons/empty16_disconnected.png", RED)