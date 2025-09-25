from PIL import Image, ImageOps
import os

def create_grayscale_icon(icon_path):
    # Open the original image
    img = Image.open(icon_path)
    
    # Convert to grayscale
    gray_img = ImageOps.grayscale(img)
    
    # Create output path
    base, ext = os.path.splitext(icon_path)
    output_path = f"{base}_gray{ext}"
    
    # Save the grayscale image
    gray_img.save(output_path)
    print(f"Created: {output_path}")

# Create grayscale versions of all icons
icons = ['icon16.png', 'icon48.png', 'icon128.png']
for icon in icons:
    if os.path.exists(icon):
        create_grayscale_icon(icon)
    else:
        print(f"Warning: {icon} not found")
