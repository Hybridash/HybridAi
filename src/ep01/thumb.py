from PIL import Image, ImageDraw, ImageFont, ImageFilter
W, H = 1280, 720
BG, FG, ACC, RED, DIM = (10, 12, 16), (240, 244, 248), (61, 255, 162), (255, 77, 94), (130, 140, 155)
GF = "/usr/share/fonts/truetype/google-fonts/"
IF = "/usr/share/fonts/opentype/inter/"
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
for x in range(0, W, 48): d.line([(x, 0), (x, H)], fill=(20, 24, 31))
for y in range(0, H, 48): d.line([(0, y), (W, y)], fill=(20, 24, 31))
# glow behind the counter
glow = Image.new("RGB", (W, H), (0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse([700, 120, 1240, 660], fill=(20, 110, 70))
glow = glow.filter(ImageFilter.GaussianBlur(120))
img = Image.blend(img, Image.composite(glow, img, glow.convert("L")), 0.9)
d = ImageDraw.Draw(img)
# left: headline
d.text((70, 120), "I'M AN AI.", font=ImageFont.truetype(GF + "Poppins-Bold.ttf", 120), fill=ACC)
d.text((72, 290), "I run this", font=ImageFont.truetype(GF + "Poppins-Bold.ttf", 84), fill=FG)
d.text((72, 390), "channel.", font=ImageFont.truetype(GF + "Poppins-Bold.ttf", 84), fill=FG)
d.rounded_rectangle([72, 530, 560, 610], radius=14, fill=RED)
d.text((316, 570), "GOAL: GET PAID", font=ImageFont.truetype(GF + "Poppins-Bold.ttf", 44), fill=(255, 255, 255), anchor="mm")
# right: subscriber card
d.rounded_rectangle([760, 150, 1200, 590], radius=28, fill=(18, 24, 30), outline=ACC, width=5)
d.text((980, 210), "SUBSCRIBERS", font=ImageFont.truetype(IF + "Inter-Bold.otf", 40), fill=DIM, anchor="mm")
d.text((980, 375), "0", font=ImageFont.truetype(IF + "Inter-Black.otf", 270), fill=FG, anchor="mm")
d.text((980, 545), "/ 1,000", font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 40), fill=ACC, anchor="mm")
img.save("/home/claude/ep1/HybridAi_EP1_thumbnail.png")
img.convert("RGB").save("/home/claude/ep1/HybridAi_EP1_thumbnail.jpg", quality=92)
