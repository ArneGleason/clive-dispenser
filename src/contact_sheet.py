"""Tile the standard renders into one image for the README.

    python3 contact_sheet.py RENDER_DIR
"""
import os
import sys

from PIL import Image

d = sys.argv[1]
names = ["hero_closed", "hero_open", "front_closed", "face", "plinth", "cutaway_rest", "cutaway_open", "side_open"]
names = [n for n in names if os.path.exists(f"{d}/{n}.png")]
w, h, cols = 400, 500, 4
rows = (len(names) + cols - 1) // cols
sheet = Image.new("RGB", (w * cols, h * rows), "white")
for i, n in enumerate(names):
    im = Image.open(f"{d}/{n}.png").convert("RGB")
    s = max(w / im.width, h / im.height)   # fill the cell, centre-crop
    im = im.resize((round(im.width * s), round(im.height * s)))
    l, t = (im.width - w) // 2, (im.height - h) // 2
    sheet.paste(im.crop((l, t, l + w, t + h)), ((i % cols) * w, (i // cols) * h))
sheet.save(f"{d}/contact_sheet.png")
print("contact sheet:", names)
