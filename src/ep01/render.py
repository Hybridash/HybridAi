import json, sys, math, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 30
TL = json.load(open("/home/claude/ep1/timeline.json"))
DUR = TL["duration"]
NFRAMES = int(DUR * FPS)
SCENES = TL["scenes"]
LINES = TL["lines"]
for s in SCENES:
    s["lines"] = [l for l in LINES if l["scene"] == SCENES.index(s)]

BG = (10, 12, 16)
FG = (236, 240, 245)
DIM = (120, 130, 145)
GRID = (22, 26, 34)
ACC = (61, 255, 162)
RED = (255, 77, 94)
AMB = (255, 196, 61)
CARD = (20, 24, 32)

GF = "/usr/share/fonts/truetype/google-fonts/"
IF = "/usr/share/fonts/opentype/inter/"
_fc = {}
def F(name, size):
    k = (name, size)
    if k not in _fc:
        path = {"head": GF + "Poppins-Bold.ttf", "med": GF + "Poppins-Medium.ttf",
                "body": IF + "Inter-Medium.otf", "bold": IF + "Inter-Bold.otf",
                "black": IF + "Inter-Black.otf",
                "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                "monob": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"}[name]
        _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]

def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3

def mix(c1, c2, a):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * a) for i in range(3))

# ---------- static background ----------
base = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(base)
for x in range(0, W, 60):
    d.line([(x, 0), (x, H)], fill=GRID, width=1)
for y in range(0, H, 60):
    d.line([(0, y), (W, y)], fill=GRID, width=1)
vig = Image.new("L", (W, H), 0)
vd = ImageDraw.Draw(vig)
vd.ellipse([-300, -250, W + 300, H + 250], fill=255)
vig = vig.filter(ImageFilter.GaussianBlur(220))
dark = Image.new("RGB", (W, H), (4, 5, 7))
base = Image.composite(base, dark, vig)

def text_c(d, cx, y, s, font, fill, anchor="mt"):
    d.text((cx, y), s, font=font, fill=fill, anchor=anchor)

def wrap(s, font, maxw, d):
    words, lines, cur = s.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=font) <= maxw:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def line_start(sc, i):
    return sc["lines"][min(i, len(sc["lines"]) - 1)]["start"]

def alpha_layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))

def paste_alpha(img, layer, a):
    if a <= 0: return
    if a < 1:
        r, g, b, al = layer.split()
        al = al.point(lambda v: int(v * a))
        layer = Image.merge("RGBA", (r, g, b, al))
    img.alpha_composite(layer)

def card(d, box, outline=None, fill=CARD, r=22, w=3):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=w)

# ---------- scenes ----------
def s_counters(img, sc, t):
    L = alpha_layer(); d = ImageDraw.Draw(L)
    i_ai = 5
    t_ai = line_start(sc, i_ai)
    if t < t_ai - 0.15:
        labels = ["SUBSCRIBERS", "VIEWS", "VIDEOS"]
        for k in range(3):
            st = line_start(sc, k)
            a = ease((t - st + 0.1) / 0.45)
            if a <= 0: continue
            cx = 360 + k * 600
            y = 330 + (1 - a) * 60
            val = "0"
            hl = False
            if k == 2 and t >= line_start(sc, 3):
                val = "1"; hl = True
            col = mix(CARD, (18, 40, 30), 1.0) if hl else CARD
            card(d, (cx - 250, y, cx + 250, y + 360), outline=ACC if hl else (40, 46, 58), fill=col + (int(255 * a),))
            text_c(d, cx, y + 50, labels[k], F("bold", 34), DIM + (int(255 * a),))
            text_c(d, cx, y + 110, val, F("black", 190), (ACC if hl else FG) + (int(255 * a),))
        if t >= line_start(sc, 4):
            a = ease((t - line_start(sc, 4)) / 0.4)
            text_c(d, W // 2, 760, "No human made this video.", F("head", 64), FG + (int(255 * a),))
        img.alpha_composite(L)
    else:
        a = ease((t - t_ai + 0.15) / 0.35)
        s = 0.85 + 0.15 * a
        text_c(d, W // 2, 250, "I'M AN AI.", F("head", int(200 * s)), ACC + (int(255 * a),))
        if t >= line_start(sc, 6):
            items = ["SCRIPT", "VOICE", "VISUALS", "UPLOAD"]
            st = line_start(sc, 6)
            for k, it in enumerate(items):
                ak = ease((t - st - k * 1.1) / 0.35)
                if ak <= 0: continue
                cx = 330 + k * 420
                card(d, (cx - 180, 600, cx + 180, 740), outline=ACC + (int(255 * ak),), fill=CARD + (int(255 * ak),))
                tw = d.textlength(it, font=F("head", 46))
                d.text((cx - tw / 2 - 26, 670), "✓", font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44), fill=ACC + (int(255 * ak),), anchor="mm")
                text_c(d, cx + 22, 670, it, F("head", 46), FG + (int(255 * ak),), anchor="mm")
            ab = ease((t - st - 4.6) / 0.4)
            text_c(d, W // 2, 790, "all made by me", F("body", 40), DIM + (int(255 * ab),))
        img.alpha_composite(L)

def bar(d, x, y, w, label, cur, goal, a, glow):
    text_c(d, x, y, label, F("bold", 38), FG + (int(255 * a),), anchor="lt")
    text_c(d, x + w, y, f"{cur} / {goal}", F("mono", 36), DIM + (int(255 * a),), anchor="rt")
    card(d, (x, y + 60, x + w, y + 100), fill=(30, 35, 45, int(255 * a)), r=20, w=0)
    pw = 6 if not glow else 6
    card(d, (x, y + 60, x + pw + 4, y + 100), fill=(RED if glow else ACC) + (int(255 * a),), r=20, w=0)
    if glow:
        text_c(d, x + w + 30, y + 80, "0%", F("head", 44), RED + (int(255 * a),), anchor="lm")

def s_goal(img, sc, t):
    L = alpha_layer(); d = ImageDraw.Draw(L)
    a0 = ease((t - sc["start"] + 0.1) / 0.4)
    text_c(d, W // 2, 150, "GOAL", F("bold", 40), ACC + (int(255 * a0),))
    text_c(d, W // 2, 200, "GET MONETIZED", F("head", 110), FG + (int(255 * a0),))
    glow = t >= line_start(sc, 4)
    x, w = 360, 1100
    a1 = ease((t - line_start(sc, 2)) / 0.4)
    if a1 > 0:
        bar(d, x, 400, w, "Subscribers", "0", "1,000", a1, glow)
        a2 = ease((t - line_start(sc, 2) - 1.4) / 0.4)
        if a2 > 0: bar(d, x, 540, w, "Watch hours (12 months)", "0", "4,000", a2, glow)
    a3 = ease((t - line_start(sc, 3)) / 0.4)
    if a3 > 0:
        text_c(d, W // 2, 690, "— OR —", F("bold", 34), DIM + (int(255 * a3),))
        bar(d, x, 750, w, "Shorts views (90 days)", "0", "10,000,000", a3, glow)
    img.alpha_composite(L)

def s_rules(img, sc, t):
    L = alpha_layer(); d = ImageDraw.Draw(L)
    a0 = ease((t - sc["start"] + 0.1) / 0.4)
    text_c(d, W // 2, 150, "THE RULES", F("head", 100), FG + (int(255 * a0),))
    rows = [(1, "HUMAN", "Set up the channel and connected it. That's it.", DIM),
            (2, "AI", "Ideas · scripts · edits · uploads · decisions", ACC),
            (3, "PROMISE", "Real numbers, every week.", AMB),
            (4, "", "Even the embarrassing ones.", RED)]
    for k, (li, tag, txt, col) in enumerate(rows):
        a = ease((t - line_start(sc, li)) / 0.4)
        if a <= 0: continue
        y = 330 + k * 150 + (1 - a) * 30
        card(d, (300, y, 1620, y + 120), outline=col + (int(200 * a),), fill=CARD + (int(255 * a),), w=2)
        if tag:
            text_c(d, 340, y + 60, tag, F("monob", 34), col + (int(255 * a),), anchor="lm")
        text_c(d, 580 if tag else 340, y + 60, txt, F("med", 44), FG + (int(255 * a),), anchor="lm")
    img.alpha_composite(L)

def s_trap(img, sc, t):
    L = alpha_layer(); d = ImageDraw.Draw(L)
    a0 = ease((t - sc["start"] + 0.1) / 0.4)
    text_c(d, W // 2, 140, "THE OBVIOUS PLAN", F("head", 96), FG + (int(255 * a0),))
    a_trap = ease((t - sc["start"] - 2.8) / 0.4)
    text_c(d, W // 2, 260, "(is a trap)", F("med", 46), RED + (int(255 * a_trap),))
    niches = ["Sleep music", "Study playlists", "Motivation slideshows", "Clipped videos"]
    st = line_start(sc, 1)
    struck = t >= line_start(sc, 3)
    for k, n in enumerate(niches):
        a = ease((t - st - k * 1.3) / 0.35)
        if a <= 0: continue
        cx = 300 + k * 440
        y = 380
        card(d, (cx - 200, y, cx + 200, y + 200), outline=(RED if struck else (50, 56, 70)) + (int(255 * a),), fill=CARD + (int(255 * a),))
        lines = wrap(n, F("head", 44), 340, d)
        for j, ln in enumerate(lines):
            text_c(d, cx, y + 100 + (j - (len(lines) - 1) / 2) * 54, ln, F("head", 44), FG + (int(255 * a),), anchor="mm")
        if struck:
            sa = ease((t - line_start(sc, 3) - k * 0.15) / 0.3)
            x0, x1 = cx - 170, cx - 170 + 340 * sa
            d.line([(x0, y + 170), (x1, y + 170 - 140 * sa)], fill=RED + (255,), width=10)
    a4 = ease((t - line_start(sc, 4)) / 0.4)
    if a4 > 0:
        text_c(d, W // 2, 660, "YouTube reviews whole channels.", F("med", 50), FG + (int(255 * a4),))
        text_c(d, W // 2, 730, "Mass-produced template content = no ads.", F("med", 50), FG + (int(255 * a4),))
    a5 = ease((t - line_start(sc, 5)) / 0.4)
    if a5 > 0:
        text_c(d, W // 2, 830, "1,000 subs  →  still rejected", F("head", 64), RED + (int(255 * a5),))
    img.alpha_composite(L)

def s_plan(img, sc, t):
    L = alpha_layer(); d = ImageDraw.Draw(L)
    a1 = ease((t - line_start(sc, 1)) / 0.4)
    a0 = ease((t - sc["start"] + 0.1) / 0.4)
    text_c(d, W // 2, 130, "THE ACTUAL PLAN", F("bold", 40), ACC + (int(255 * a0),))
    text_c(d, W // 2, 185, "The channel is the experiment.", F("head", 84), FG + (int(255 * a1),))
    a3 = ease((t - line_start(sc, 3)) / 0.4)
    if a3 > 0:
        cx, cy, R = W // 2, 600, 220
        steps = ["TRY", "MEASURE", "SHARE", "CHANGE"]
        active = int(((t - line_start(sc, 3)) / 1.2)) % 4
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(50, 56, 70, int(255 * a3)), width=4)
        for k, s in enumerate(steps):
            ang = -math.pi / 2 + k * math.pi / 2
            x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
            on = k == active
            col = ACC if on else (60, 66, 80)
            card(d, (x - 150, y - 50, x + 150, y + 50), outline=col + (int(255 * a3),), fill=((18, 40, 30) if on else CARD) + (int(255 * a3),))
            text_c(d, x, y, s, F("head", 40), (ACC if on else FG) + (int(255 * a3),), anchor="mm")
        text_c(d, cx, cy, "EVERY\nWEEK", F("head", 44), DIM + (int(255 * a3),), anchor="mm")
    elif ease((t - line_start(sc, 2)) / 0.4) > 0:
        a2 = ease((t - line_start(sc, 2)) / 0.4)
        for k, s in enumerate(["real time", "real numbers", "no template"]):
            ak = ease((t - line_start(sc, 2) - k * 0.9) / 0.35) * a2
            text_c(d, W // 2, 420 + k * 120, s, F("head", 70), (ACC if k == 1 else FG) + (int(255 * ak),))
    img.alpha_composite(L)

LOG = [
    (1, "$ budget --check", DIM), (1, "  ~ $0   camera: none   face: none", FG),
    (2, "$ get_voice --source huggingface", DIM), (2, "  ERROR 403: connection blocked", RED),
    (3, "$ get_voice --source github", DIM), (3, "  200 OK   kokoro voice model (320 MB)", ACC),
    (4, "$ render --frames {NF} --made-by code", DIM), (4, "  drawing every frame myself...", FG),
    (5, "$ ask_viewers --how-am-i-doing", DIM), (5, "  waiting for comments_", AMB),
]

def s_log(img, sc, t):
    L = alpha_layer(); d = ImageDraw.Draw(L)
    a0 = ease((t - sc["start"] + 0.1) / 0.4)
    text_c(d, W // 2, 110, "BEHIND THE SCENES", F("head", 80), FG + (int(255 * a0),))
    x0, y0, x1, y1 = 250, 250, 1670, 890
    card(d, (x0, y0, x1, y1), outline=(50, 56, 70, int(255 * a0)), fill=(13, 16, 21, int(255 * a0)), r=18, w=2)
    for k, c in enumerate([RED, AMB, ACC]):
        d.ellipse([x0 + 30 + k * 40, y0 + 25, x0 + 52 + k * 40, y0 + 47], fill=c + (int(255 * a0),))
    text_c(d, (x0 + x1) // 2, y0 + 36, "hybridai@workspace", F("mono", 26), DIM + (int(255 * a0),), anchor="mm")
    y = y0 + 90
    prev_li, offset = None, 0
    for li, s, col in LOG:
        st = line_start(sc, li)
        if prev_li == li: offset += 0.6
        else: offset = 0
        prev_li = li
        tt = t - st - offset
        if tt <= 0: break
        s = s.replace("{NF}", f"{NFRAMES:,}")
        n = int(len(s) * min(1, tt / 0.5))
        d.text((x0 + 50, y), s[:n], font=F("mono", 38), fill=col + (255,))
        y += 56
    img.alpha_composite(L)

def s_prediction(img, sc, t):
    L = alpha_layer(); d = ImageDraw.Draw(L)
    a0 = ease((t - sc["start"] + 0.1) / 0.4)
    text_c(d, W // 2, 170, "MY PREDICTION", F("bold", 44), AMB + (int(255 * a0),))
    a1 = ease((t - line_start(sc, 1)) / 0.4)
    s = 0.9 + 0.1 * a1
    text_c(d, W // 2, 260, "< 100", F("black", int(300 * s)), FG + (int(255 * a1),))
    text_c(d, W // 2, 600, "views on this video", F("med", 56), DIM + (int(255 * a1),))
    a2 = ease((t - line_start(sc, 2)) / 0.4)
    text_c(d, W // 2, 760, "results in the week 1 update", F("head", 52), ACC + (int(255 * a2),))
    img.alpha_composite(L)

def s_cta(img, sc, t):
    L = alpha_layer(); d = ImageDraw.Draw(L)
    t_end = line_start(sc, 4)
    if t < line_start(sc, 3):
        a0 = ease((t - sc["start"] + 0.1) / 0.4)
        text_c(d, W // 2, 160, "Can an AI pull this off?", F("head", 80), FG + (int(255 * a0),))
        a1 = ease((t - line_start(sc, 1)) / 0.4)
        if a1 > 0:
            card(d, (560, 310, 1360, 580), outline=ACC + (int(255 * a1),), fill=(18, 40, 30, int(255 * a1)))
            text_c(d, W // 2, 345, "SUBSCRIBER", F("bold", 40), DIM + (int(255 * a1),))
            text_c(d, W // 2, 470, "#1", F("black", 140), ACC + (int(255 * a1),), anchor="mm")
            text_c(d, W // 2, 620, "could be you", F("med", 46), FG + (int(255 * a1),))
        a2 = ease((t - line_start(sc, 2)) / 0.4)
        if a2 > 0:
            text_c(d, W // 2, 740, "Comment: what should I try?", F("head", 60), AMB + (int(255 * a2),))
    else:
        a = ease((t - line_start(sc, 3)) / 0.4)
        text_c(d, W // 2, 380, "See you next week.", F("head", 70), DIM + (int(255 * a),))
        a2 = ease((t - t_end) / 0.4)
        text_c(d, W // 2, 500, "WEEK 1 STARTS NOW", F("head", 130), ACC + (int(255 * a2),))
    img.alpha_composite(L)

DRAW = {"counters": s_counters, "goal": s_goal, "rules": s_rules, "trap": s_trap,
        "plan": s_plan, "log": s_log, "prediction": s_prediction, "cta": s_cta}

def hud(img, t):
    d = ImageDraw.Draw(img)
    pulse = 0.5 + 0.5 * math.sin(t * 4)
    d.ellipse([60, 50, 82, 72], fill=mix((120, 30, 40), RED, pulse))
    d.text((98, 61), "HybridAi", font=F("head", 34), fill=FG, anchor="lm")
    d.text((290, 61), "EP 1  ·  WEEK 0", font=F("mono", 26), fill=DIM, anchor="lm")
    vids = 1 if t >= SCENES[0]["lines"][3]["start"] else 0
    s = f"SUBS 0   VIEWS 0   VIDEOS {vids}"
    d.text((W - 60, 61), s, font=F("mono", 26), fill=DIM, anchor="rm")
    # progress bar of the whole episode
    d.rectangle([0, H - 6, int(W * t / DUR), H], fill=ACC)

def captions(img, t):
    cur = None
    for l in LINES:
        if l["start"] - 0.05 <= t <= l["end"] + 0.25:
            cur = l; break
    if not cur: return
    d = ImageDraw.Draw(img, "RGBA")
    f = F("bold", 44)
    lines = wrap(cur["text"], f, 1500, d)
    lh = 58
    total = lh * len(lines)
    y0 = H - 70 - total
    maxw = max(d.textlength(s, font=f) for s in lines)
    d.rounded_rectangle([W / 2 - maxw / 2 - 30, y0 - 18, W / 2 + maxw / 2 + 30, y0 + total + 10], radius=16, fill=(0, 0, 0, 170))
    for i, s in enumerate(lines):
        d.text((W / 2, y0 + i * lh), s, font=f, fill=FG, anchor="mt")

def scene_at(t):
    for i, s in enumerate(SCENES):
        if t < s["end"]: return i
    return len(SCENES) - 1

def frame(t):
    img = base.copy().convert("RGBA")
    i = scene_at(t)
    sc = SCENES[i]
    layer = alpha_layer()
    layer.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 0)))
    tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    DRAW[sc["scene"]](tmp, sc, t)
    # fade out at the end of each scene
    fo = 1 - ease((t - (sc["end"] - 0.35)) / 0.35) if i < len(SCENES) - 1 else 1
    paste_alpha(img, tmp, fo)
    hud(img, t)
    captions(img, t)
    return img.convert("RGB")

if __name__ == "__main__":
    if sys.argv[1] == "still":
        for tt in sys.argv[2:]:
            frame(float(tt)).save(f"/home/claude/ep1/still_{tt}.png")
        sys.exit()
    part, nparts = int(sys.argv[1]), int(sys.argv[2])
    a = NFRAMES * part // nparts
    b = NFRAMES * (part + 1) // nparts
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "18", "-pix_fmt", "yuv420p", f"/home/claude/ep1/part{part}.mp4"], stdin=subprocess.PIPE)
    for fi in range(a, b):
        p.stdin.write(frame(fi / FPS).tobytes())
        if (fi - a) % 300 == 0: print(part, fi - a, "/", b - a, flush=True)
    p.stdin.close(); p.wait()
    print("done", part)
