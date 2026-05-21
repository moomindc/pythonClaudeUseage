# make_icon.py — run once: py make_icon.py  →  ClaudeUsageBar.ico
# Reuses the tray icon design from ClaudeUsageBar/tray.py (navy circle + white "C" arc),
# drawn at 256px and saved as a multi-resolution Windows .ico.

from PIL import Image, ImageDraw

S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

m = S * 2 // 64
d.ellipse([m, m, S - m, S - m], fill=(0, 31, 91, 255))

am = S * 12 // 64
d.arc([am, am, S - am, S - am], start=50, end=310,
      fill=(255, 255, 255, 255), width=S * 6 // 64)

img.save(
    "ClaudeUsageBar.ico",
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print("Wrote ClaudeUsageBar.ico")
