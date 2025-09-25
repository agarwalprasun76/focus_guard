#!/usr/bin/env python
"""
Create Icons for FocusGuard Extension

This script creates simple icons for the FocusGuard browser extension.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, output_path):
    """Create a simple icon with the given size."""
    # Detect offline icon by filename
    is_offline = 'offline' in os.path.basename(output_path).lower()

    # Set colors
    circle_color = (76, 175, 80, 255) if not is_offline else (180, 180, 180, 255)  # Green or gray
    text_color = (255, 255, 255, 255)

    # Create a new image with transparent background
    img = Image.new('RGBA', (size, size), color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Draw main circle
    margin = int(size * 0.1)
    draw.ellipse(
        [(margin, margin), (size - margin, size - margin)],
        fill=circle_color
    )

    # Draw "FG" text in the center
    try:
        font_size = int(size * 0.5)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()
        text = "FG"
        text_width, text_height = draw.textsize(text, font=font)
        position = ((size - text_width) / 2, (size - text_height) / 2)
        draw.text(position, text, fill=text_color, font=font)
    except Exception:
        # Fallback: draw a simple "F" shape
        line_width = int(size * 0.1)
        center = size // 2
        draw.rectangle(
            [(center - line_width, center - line_width * 2),
             (center + line_width, center + line_width * 2)],
            fill=text_color
        )
        draw.rectangle(
            [(center - line_width * 2, center - line_width),
             (center + line_width * 2, center)],
            fill=text_color
        )

    # If offline, draw a red "X" over the icon
    if is_offline:
        x_margin = int(size * 0.22)
        x_width = int(size * 0.13)
        draw.line(
            [(x_margin, x_margin), (size - x_margin, size - x_margin)],
            fill=(220, 0, 0, 255), width=x_width
        )
        draw.line(
            [(size - x_margin, x_margin), (x_margin, size - x_margin)],
            fill=(220, 0, 0, 255), width=x_width
        )

    img.save(output_path, "PNG")
    print(f"Created icon: {output_path}")

def main():
    """Create icons of different sizes."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create icons of different sizes
    sizes = {
        "icon16.png": 16,
        "icon48.png": 48,
        "icon128.png": 128,
        "icon16_offline.png": 16,
        "icon48_offline.png": 48,
        "icon128_offline.png": 128
    }
    
    for filename, size in sizes.items():
        output_path = os.path.join(script_dir, filename)
        create_icon(size, output_path)

if __name__ == "__main__":
    main()

