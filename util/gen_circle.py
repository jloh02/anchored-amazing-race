import os
from PIL import Image, ImageDraw

def generate_colored_circle(hex_code, sz=15,border=2,border_color=(128,128,128)):
    # Remove hex
    hex_code = hex_code[1:]

    # Create a new image with a white background
    image = Image.new('RGBA', (sz+border,sz+border), (255, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Convert hex code to RGB tuple
    rgb_color = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

    # Draw a colored circle
    draw.ellipse((0,0,sz-1,sz-1), fill=border_color)
    draw.ellipse((border,border,sz-1-border,sz-1-border), fill=rgb_color)

    return image

def generate_images(hex_codes, save_path='output'):
    for idx,hex in enumerate(hex_codes):
        image = generate_colored_circle(hex)
        image.save(f'{save_path}/{idx}.png')

if __name__ == "__main__":
    # Replace the hex_codes list with your desired hex codes
    hex_codes = ['#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#42d4f4', '#f032e6', '#fabed4', '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000', '#aaffc3', '#000075', '#a9a9a9']

    # Create a directory to save the images
    save_directory = '../dashboard/src/assets'
    os.makedirs(save_directory, exist_ok=True)

    # Generate 20 images with different colored circles
    generate_images(hex_codes, save_path=save_directory)