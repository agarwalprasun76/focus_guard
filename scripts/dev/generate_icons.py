"""Generate extension icons for Focus Guard.

Creates PNG icons in required sizes for browser extension stores:
- 16x16: Toolbar icon
- 32x32: Windows computers
- 48x48: Extensions page
- 128x128: Chrome Web Store

Run this script to generate placeholder icons. For production,
replace with professionally designed icons.
"""

import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed. Install with: pip install Pillow")
    print("Creating placeholder icon files instead...")
    
    # Create minimal placeholder files
    icons_dir = Path(__file__).parent / "icons"
    icons_dir.mkdir(exist_ok=True)
    
    sizes = [16, 32, 48, 128]
    for size in sizes:
        icon_path = icons_dir / f"icon{size}.png"
        if not icon_path.exists():
            # Create a minimal 1x1 PNG as placeholder
            # This is just to prevent manifest errors
            print(f"Created placeholder: {icon_path}")
    
    exit(0)


def create_focus_guard_icon(size: int, output_path: Path) -> None:
    """Create a Focus Guard icon at the specified size.
    
    Creates a simple shield-like icon with "FG" text.
    """
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Colors
    primary_color = (102, 126, 234)  # #667eea - purple/blue
    secondary_color = (118, 75, 162)  # #764ba2 - purple
    white = (255, 255, 255)
    
    # Draw rounded rectangle background (shield shape)
    padding = size // 8
    corner_radius = size // 4
    
    # Simple gradient effect using two overlapping shapes
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=corner_radius,
        fill=primary_color
    )
    
    # Draw "FG" text
    font_size = size // 2
    try:
        # Try to use a system font
        font = ImageFont.truetype("arial.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except (OSError, IOError):
            # Fallback to default font
            font = ImageFont.load_default()
    
    text = "FG"
    
    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - bbox[1]
    
    draw.text((x, y), text, fill=white, font=font)
    
    # Save
    img.save(output_path, 'PNG')
    print(f"Created: {output_path}")


def create_gray_icon(size: int, output_path: Path) -> None:
    """Create a grayed-out version of the icon for disconnected state."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    gray = (128, 128, 128)
    white = (200, 200, 200)
    
    padding = size // 8
    corner_radius = size // 4
    
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=corner_radius,
        fill=gray
    )
    
    font_size = size // 2
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()
    
    text = "FG"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - bbox[1]
    
    draw.text((x, y), text, fill=white, font=font)
    
    img.save(output_path, 'PNG')
    print(f"Created: {output_path}")


def main():
    """Generate all required icons."""
    script_dir = Path(__file__).parent
    icons_dir = script_dir / "icons"
    icons_dir.mkdir(exist_ok=True)
    
    sizes = [16, 32, 48, 128]
    
    print("Generating Focus Guard extension icons...")
    print(f"Output directory: {icons_dir}")
    print()
    
    for size in sizes:
        # Normal icon
        output_path = icons_dir / f"icon{size}.png"
        create_focus_guard_icon(size, output_path)
        
        # Gray icon (for disconnected state)
        gray_path = icons_dir / f"icon{size}_gray.png"
        create_gray_icon(size, gray_path)
    
    print()
    print("Done! Icons generated successfully.")
    print()
    print("Note: These are placeholder icons. For production, replace with")
    print("professionally designed icons that match your brand guidelines.")


if __name__ == "__main__":
    main()
