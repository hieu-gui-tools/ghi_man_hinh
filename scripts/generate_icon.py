import os
from PIL import Image, ImageDraw

def create_app_icon():
    os.makedirs("assets", exist_ok=True)
    size = 512
    # Create RGBA canvas
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer dark modern card
    margin = 32
    radius = 96
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=(15, 23, 42, 255),  # Slate 900
        outline=(99, 102, 241, 230),  # Indigo 500
        width=8
    )

    # Subtle inner border for depth
    draw.rounded_rectangle(
        [margin + 12, margin + 12, size - margin - 12, size - margin - 12],
        radius=radius - 8,
        outline=(51, 65, 85, 180),  # Slate 700
        width=3
    )

    # Draw a stylized screen / monitor frame
    mon_l = margin + 50
    mon_t = margin + 55
    mon_r = size - margin - 50
    mon_b = size - margin - 120
    
    # Screen inner background
    draw.rounded_rectangle(
        [mon_l, mon_t, mon_r, mon_b],
        radius=28,
        fill=(30, 41, 59, 255),  # Slate 800
        outline=(71, 85, 105, 255),
        width=4
    )

    # Monitor stand
    stand_w = 40
    stand_h = 30
    stand_l = size // 2 - stand_w // 2
    stand_r = size // 2 + stand_w // 2
    draw.rectangle([stand_l, mon_b + 4, stand_r, mon_b + 4 + stand_h], fill=(71, 85, 105, 255))
    draw.rounded_rectangle(
        [size // 2 - 65, mon_b + 4 + stand_h - 4, size // 2 + 65, mon_b + 4 + stand_h + 10],
        radius=5,
        fill=(100, 116, 139, 255)
    )

    # Inside screen: Camera / Recording aperture and glowing record dot
    center_x = size // 2
    center_y = (mon_t + mon_b) // 2

    # Outer glowing ring (Cyan)
    ring_radius = 80
    draw.ellipse(
        [center_x - ring_radius, center_y - ring_radius, center_x + ring_radius, center_y + ring_radius],
        outline=(6, 182, 212, 240),  # Cyan 500
        width=6
    )

    # Inner glowing recording circle (Vibrant Red)
    rec_radius = 48
    draw.ellipse(
        [center_x - rec_radius, center_y - rec_radius, center_x + rec_radius, center_y + rec_radius],
        fill=(239, 68, 68, 255),  # Red 500
        outline=(254, 202, 202, 255),  # Red 200
        width=4
    )

    # Center white shine
    shine_r = 16
    draw.ellipse(
        [center_x - 18, center_y - 20, center_x - 18 + shine_r, center_y - 20 + shine_r],
        fill=(255, 255, 255, 220)
    )

    # Corner indicator dot (live recording status pulse)
    dot_x = mon_r - 28
    dot_y = mon_t + 28
    draw.ellipse([dot_x - 10, dot_y - 10, dot_x + 10, dot_y + 10], fill=(239, 68, 68, 255))
    draw.ellipse([dot_x - 4, dot_y - 4, dot_x + 4, dot_y + 4], fill=(255, 255, 255, 220))

    # Save high resolution PNG
    png_path = os.path.join("assets", "icon.png")
    img.save(png_path, "PNG")
    print(f"Saved PNG icon to {png_path}")

    # Save Windows multi-resolution ICO
    ico_path = os.path.join("assets", "icon.ico")
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=icon_sizes)
    print(f"Saved Windows ICO icon to {ico_path}")

if __name__ == "__main__":
    create_app_icon()
