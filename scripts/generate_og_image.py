#!/usr/bin/env python3
"""USAGE: uv run python scripts/generate_og_image.py

Renders the site's Open Graph card (1200x630) to content/extra/og-image.png.
Style mirrors the theme: warm charcoal, hairline frame, serif name, brass period.
"""

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = "#0c0b09"
FRAME = "#2c2921"
BONE = "#eae5d9"
GOLD = "#D4AF37"
MUTED = "#98917f"
ITALIC = "#b6af9e"

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
SERIF_BOLD = f"{FONT_DIR}/DejaVuSerif-Bold.ttf"
SERIF_ITALIC = f"{FONT_DIR}/DejaVuSerif-Italic.ttf"
MONO = f"{FONT_DIR}/DejaVuSansMono.ttf"

OUT = "content/extra/og-image.png"


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # hairline ledger frame
    draw.rectangle([24, 24, W - 24, H - 24], outline=FRAME, width=1)

    f_mono = ImageFont.truetype(MONO, 26)
    f_name = ImageFont.truetype(SERIF_BOLD, 150)
    f_sub = ImageFont.truetype(SERIF_ITALIC, 38)

    # kicker: gold leader + ~/whoami
    draw.line([(96, 130), (144, 130)], fill=GOLD, width=2)
    draw.text((160, 116), "~/whoami", font=f_mono, fill=MUTED)

    # name with brass period
    draw.text((96, 210), "secemp", font=f_name, fill=BONE)
    name_w = draw.textlength("secemp", font=f_name)
    draw.text((96 + name_w, 210), ".", font=f_name, fill=GOLD)

    # subtitle
    draw.text((96, 440), "Reverse engineering, ML, and systems notes", font=f_sub, fill=ITALIC)
    draw.text((96, 498), "from an independent researcher.", font=f_sub, fill=ITALIC)

    # domain, bottom right
    domain = "secemp.blog"
    domain_w = draw.textlength(domain, font=f_mono)
    draw.text((W - 96 - domain_w, H - 78), domain, font=f_mono, fill=MUTED)

    img.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
