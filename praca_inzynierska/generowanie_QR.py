import qrcode
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import random
import os

# Define a folder to save the generated images
output_dir = "/mnt/data/qr_code_images_with_random_shadow"
os.makedirs(output_dir, exist_ok=True)

# Generate 100 images
image_count = 100
qr_per_image_range = (5, 15)
image_size = (1024, 1024)  # Default image size
natural_backgrounds = ["wood", "paper", "solid"]


# Generate a background with the specified type
def generate_background(size, bg_type):
    if bg_type == "solid":
        color = tuple(random.randint(200, 255) for _ in range(3))  # Light neutral colors
        bg = Image.new("RGBA", size, color + (255,))
    elif bg_type == "wood":
        bg = Image.new("RGBA", size)
        draw = ImageDraw.Draw(bg)
        for i in range(size[0]):
            color = (
                random.randint(100, 140),
                random.randint(70, 90),
                random.randint(40, 60),
            )
            draw.line([(i, 0), (i, size[1])], fill=color)
    else:  # Paper-like background
        bg = Image.new("RGBA", size, (240, 240, 230, 255))
        draw = ImageDraw.Draw(bg)
        for i in range(0, size[0], 10):
            draw.line([(i, 0), (i, size[1])], fill=(200, 200, 200, 255), width=1)
    return bg


# Apply lighting effect to the image
def apply_lighting_effect(image, lighting_type):
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    gradient_size = max(image.size)
    for i in range(gradient_size):
        if lighting_type == "bright":
            color = (255, 255, 255)
            alpha = int(255 * (1 - (i / gradient_size) ** 2))
        elif lighting_type == "dark":
            color = (50, 50, 50)
            alpha = int(255 * (i / gradient_size))
        else:  # Balanced lighting
            color = (200, 200, 200)
            alpha = int(255 * (1 - abs((i / gradient_size) - 0.5)))

        draw.ellipse(
            [(-i, -i), (image.size[0] + i, image.size[1] + i)],
            fill=color + (alpha,),
        )
    return Image.alpha_composite(image, overlay)


# Add shadow to the background with larger random offset
def add_background_shadow(image, qr_boxes, shadow_offset_range=(50, 150), blur_radius=20):
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)

    for x, y, w, h in qr_boxes:
        # Increase the offset range for a larger shadow effect
        shadow_offset_x = random.randint(*shadow_offset_range)
        shadow_offset_y = random.randint(*shadow_offset_range)

        # Add shadow with offset
        shadow_draw.rectangle(
            [x + shadow_offset_x, y + shadow_offset_y, w + shadow_offset_x, h + shadow_offset_y],
            fill=(0, 0, 0, 180),  # Darker and more opaque shadow
        )

    shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))
    return Image.alpha_composite(image, shadow)


# Generate QR codes
def generate_qr_code(data, size):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    return img.resize(size, Image.Resampling.LANCZOS)


# Crop excess transparency from rotated QR codes
def crop_to_content(img):
    bbox = img.getbbox()
    return img.crop(bbox)


# Rotate QR code with transparency
def rotate_qr_code(qr_code, angle):
    rotated = qr_code.rotate(angle, expand=True)
    return crop_to_content(rotated)


# Check if a QR code overlaps with others
def is_overlapping(new_box, existing_boxes):
    for box in existing_boxes:
        if (
                new_box[0] < box[2]
                and new_box[2] > box[0]
                and new_box[1] < box[3]
                and new_box[3] > box[1]
        ):
            return True
    return False


# Generate and save images
for img_index in range(image_count):
    # Randomly choose a background type
    bg_type = random.choice(natural_backgrounds)
    background = generate_background(image_size, bg_type)

    # Decide on lighting type
    lighting_type = random.choice(["bright", "dark", "balanced"])

    # Determine number of QR codes
    num_qr_codes = random.randint(*qr_per_image_range)
    placed_boxes = []  # Track placed QR codes

    for _ in range(num_qr_codes):
        for attempt in range(100):  # Retry placement up to 100 times
            # Generate QR code
            data = f"Data-{random.randint(1000, 9999)}"
            qr_size = random.randint(100, 300)
            qr_code = generate_qr_code(data, (qr_size, qr_size))

            # Apply random rotation
            rotation_angle = random.randint(0, 359)
            qr_code = rotate_qr_code(qr_code, rotation_angle)
            qr_width, qr_height = qr_code.size

            # Random position
            x = random.randint(0, image_size[0] - qr_width)
            y = random.randint(0, image_size[1] - qr_height)
            new_box = (x, y, x + qr_width, y + qr_height)

            if not is_overlapping(new_box, placed_boxes):
                background.alpha_composite(qr_code, (x, y))
                placed_boxes.append(new_box)
                break

    # Add lighting effect
    background = apply_lighting_effect(background, lighting_type)

    # Add shadow on the background with random offset
    background_with_shadow = add_background_shadow(background.copy(), placed_boxes)

    # Save image
    output_path = os.path.join(output_dir, f"qr_image_{img_index + 1}.png")
    background_with_shadow.save(output_path, "PNG")

print(f"Images saved to {output_dir}")
