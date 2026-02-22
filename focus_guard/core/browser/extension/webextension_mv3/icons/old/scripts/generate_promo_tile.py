"""
Generate Chrome Web Store promotional tile from logo.
Creates the small promo tile (440x280) for store listing.
"""

from PIL import Image, ImageDraw, ImageFont
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "icons")
SOURCE_LOGO = os.path.join(ICONS_DIR, "ChatGPT_FocusGuard_v1.png")
OUTPUT_DIR = SCRIPT_DIR

# Promo tile sizes
SMALL_TILE = (440, 280)
LARGE_TILE = (920, 680)
MARQUEE = (1400, 560)

def create_promo_tile(size, name, tagline="Stay Focused. Stay Productive."):
    """Create a promotional tile with logo and tagline.
    Layout: Title on top, logo centered, taglines below.
    """
    width, height = size
    
    # Create background with gradient-like effect (dark blue)
    img = Image.new('RGB', size, color=(20, 30, 60))
    draw = ImageDraw.Draw(img)
    
    # Add subtle gradient effect
    for y in range(height):
        # Gradient from darker top to slightly lighter bottom
        r = int(20 + (y / height) * 15)
        g = int(30 + (y / height) * 20)
        b = int(60 + (y / height) * 30)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    # Load logo
    logo = Image.open(SOURCE_LOGO)
    if logo.mode != 'RGBA':
        logo = logo.convert('RGBA')
    
    # Try to use fonts
    try:
        title_font = ImageFont.truetype("arial.ttf", int(height * 0.14))
        tagline_font = ImageFont.truetype("arial.ttf", int(height * 0.065))
    except:
        title_font = ImageFont.load_default()
        tagline_font = ImageFont.load_default()
    
    # Draw title at top center
    title = "FocusGuard"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    title_x = (width - title_width) // 2
    title_y = int(height * 0.06)
    draw.text((title_x, title_y), title, fill=(255, 255, 255), font=title_font)
    
    # Calculate logo size - fit in middle section
    # Smaller logo for wide banners with more taglines
    tagline_count = len(tagline.split(". "))
    if tagline_count > 2:
        logo_size = int(height * 0.38)
    else:
        logo_size = int(height * 0.50)
    logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    
    # Position logo centered horizontally, below title
    logo_x = (width - logo_size) // 2
    logo_y = title_y + title_height + int(height * 0.04)
    
    # Paste logo with transparency
    img.paste(logo, (logo_x, logo_y), logo)
    
    # Taglines below logo - split and center each line
    tagline_lines = tagline.split(". ")
    tagline_start_y = logo_y + logo_size + int(height * 0.04)
    line_spacing = int(height * 0.09)
    
    for i, line in enumerate(tagline_lines):
        # Add period back if needed
        if i < len(tagline_lines) - 1 or tagline.endswith("."):
            line = line.rstrip(".") + "."
        
        # Center each tagline
        line_bbox = draw.textbbox((0, 0), line, font=tagline_font)
        line_width = line_bbox[2] - line_bbox[0]
        line_x = (width - line_width) // 2
        line_y = tagline_start_y + i * line_spacing
        draw.text((line_x, line_y), line, fill=(150, 180, 220), font=tagline_font)
    
    # Save
    output_path = os.path.join(OUTPUT_DIR, f"promo_{name}.png")
    img.save(output_path, "PNG")
    print(f"Created: promo_{name}.png ({width}x{height})")
    return output_path

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"Using logo: {SOURCE_LOGO}")
    print(f"Output directory: {OUTPUT_DIR}\n")
    
    # Create small promo tile (required for good visibility)
    create_promo_tile(SMALL_TILE, "small_440x280")
    
    # Create large promo tile (optional)
    create_promo_tile(LARGE_TILE, "large_920x680")
    
    # Create marquee (optional, for featured placement)
    create_promo_tile(MARQUEE, "marquee_1400x560", "Track time. Block distractions. Stay productive.")
    
    print("\n✅ Promo tiles generated!")
    print("\nFor screenshots, you'll need to manually capture:")
    print("  1. Extension popup showing 'Connected' status")
    print("  2. A blocked page (visit a blocked site)")
    print("  3. (Optional) FocusGuard dashboard")
    print("\nRecommended screenshot size: 1280x800 or 640x400")

if __name__ == "__main__":
    main()
