"""Thumbnail (1280x720) in the channel style.

usage: python3 thumb.py <spec.json> <out.jpg>
spec["thumbnail"] = {"headline": "...", "lines": ["...", "..."], "tag": "...",
                     "card_label": "...", "card_value": "...", "card_sub": "..."}
"""
import json, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

th = json.load(open(sys.argv[1]))["thumbnail"]
W, H = 1280, 720
BG, FG, ACC, RED, DIM = (10, 12, 16), (240, 244, 248), (61, 255, 162), (255, 77, 94), (130, 140, 155)
GF = "/usr/share/fonts/truetype/google-fonts/"
IF = "/usr/share/fonts/opentype/inter/"
def fnt(p, s): return ImageFont.truetype(p, s)
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
for x in range(0, W, 48): d.line([(x, 0), (x, H)], fill=(20, 24, 31))
for y in range(0, H, 48): d.line([(0, y), (W, y)], fill=(20, 24, 31))
glow = Image.new("RGB", (W, H), 0)
ImageDraw.Draw(glow).ellipse([700, 120, 1240, 660], fill=(20, 110, 70))
glow = glow.filter(ImageFilter.GaussianBlur(120))
img = Image.blend(img, Image.composite(glow, img, glow.convert("L")), 0.9)
d = ImageDraw.Draw(img)

def fit(text, path, size, maxw):
    while size > 30 and d.textlength(text, font=fnt(path, size)) > maxw: size -= 4
    return fnt(path, size)

hl = th.get("headline", "")
d.text((70, 110), hl, font=fit(hl, GF + "Poppins-Bold.ttf", 120, 640), fill=ACC)
y = 280
for ln in th.get("lines", [])[:2]:
    d.text((72, y), ln, font=fit(ln, GF + "Poppins-Bold.ttf", 84, 640), fill=FG); y += 100
if th.get("tag"):
    f = fit(th["tag"], GF + "Poppins-Bold.ttf", 44, 440)
    tw = d.textlength(th["tag"], font=f)
    d.rounded_rectangle([72, 530, 72 + tw + 60, 610], radius=14, fill=RED)
    d.text((72 + (tw + 60) / 2, 570), th["tag"], font=f, fill=(255, 255, 255), anchor="mm")
d.rounded_rectangle([760, 150, 1200, 590], radius=28, fill=(18, 24, 30), outline=ACC, width=5)
d.text((980, 210), th.get("card_label", "").upper(), font=fit(th.get("card_label", ""), IF + "Inter-Bold.otf", 40, 380), fill=DIM, anchor="mm")
v = str(th.get("card_value", ""))
d.text((980, 375), v, font=fit(v, IF + "Inter-Black.otf", 270 if len(v) <= 2 else 200, 400), fill=FG, anchor="mm")
d.text((980, 545), th.get("card_sub", ""), font=fnt("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 40), fill=ACC, anchor="mm")
img.save(sys.argv[2], quality=92)
print("thumbnail", sys.argv[2])
