"""
Generate extension icons from source logo.
Creates all required sizes for Chrome Web Store submission.
"""

from PIL import Image
import os

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_IMAGE = os.path.join(SCRIPT_DIR, "ChatGPT_FocusGuard_v1.png")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "experiment")

# Required sizes for Chrome extension
SIZES = [16, 32, 48, 128]

def generate_icons():
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Open source image
    print(f"Loading source image: {SOURCE_IMAGE}")
    img = Image.open(SOURCE_IMAGE)
    print(f"Source size: {img.size}")
    
    # Convert to RGBA if needed
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Generate each size
    for size in SIZES:
        # Resize with high-quality resampling
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Save color version
        output_path = os.path.join(OUTPUT_DIR, f"icon{size}.png")
        resized.save(output_path, "PNG")
        print(f"Created: icon{size}.png ({size}x{size})")
        
        # Create grayscale version for disconnected state
        gray = resized.convert('LA').convert('RGBA')
        gray_path = os.path.join(OUTPUT_DIR, f"icon{size}_gray.png")
        gray.save(gray_path, "PNG")
        print(f"Created: icon{size}_gray.png ({size}x{size})")
    
    print(f"\nAll icons generated in: {OUTPUT_DIR}")
    print("\nGenerated files:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.endswith('.png'):
            print(f"  - {f}")

if __name__ == "__main__":
    generate_icons()
