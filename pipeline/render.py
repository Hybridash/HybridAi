"""Draws every frame of a video from a spec + timeline, in the HybridAi style.

usage:
  python3 render.py <spec.json> <workdir> part <i> <n>     render frames part i of n -> part{i}.mp4
  python3 render.py <spec.json> <workdir> still <t> [<t>...] save still_<t>.png for checking

Scene types (each scene also has "lines": the narration):
  title     kicker, title, sub
  bignum    label, value, sub, color, count (true = count up to a number)
  list      title, items: [str | {text, mark: x|check, color}]
  bars      title, bars: [{label, frac (0-1), display}]
  terminal  title, log: [[text, color]]
  chart     title, x: [labels], y: [numbers], unit
  statement text, color, sub
Items/bars/log rows reveal one by one across the scene, or at {"line": i} if given.
"""
import json, sys, math, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SPEC = json.load(open(sys.argv[1]))
WD = sys.argv[2]
TL = json.load(open(f"{WD}/timeline.json"))
SHORT = SPEC.get("format", "long") == "short"
W, H = (1080, 1920) if SHORT else (1920, 1080)
FPS = 30
DUR = TL["duration"]
NFRAMES = int(DUR * FPS)
SC = SPEC["scenes"]
for i, s in enumerate(SC):
    s["_start"], s["_end"] = TL["scenes"][i]["start"], TL["scenes"][i]["end"]
    s["_lines"] = [l for l in TL["lines"] if l["scene"] == i]
LINES = TL["lines"]

BG, FG, DIM, GRID = (10, 12, 16), (236, 240, 245), (120, 130, 145), (22, 26, 34)
COL = {"acc": (61, 255, 162), "red": (255, 77, 94), "amb": (255, 196, 61), "fg": FG, "dim": DIM, "blue": (90, 170, 255)}
ACC, RED = COL["acc"], COL["red"]
CARD, EDGE = (20, 24, 32), (48, 54, 68)

GF = "/usr/share/fonts/truetype/google-fonts/"
IF = "/usr/share/fonts/opentype/inter/"
DJ = "/usr/share/fonts/truetype/dejavu/"
_fc = {}
def F(name, size):
    k = (name, int(size))
    if k not in _fc:
        _fc[k] = ImageFont.truetype({"head": GF + "Poppins-Bold.ttf", "med": GF + "Poppins-Medium.ttf",
                                    "body": IF + "Inter-Medium.otf", "bold": IF + "Inter-Bold.otf",
                                    "black": IF + "Inter-Black.otf", "mono": DJ + "DejaVuSansMono.ttf",
                                    "monob": DJ + "DejaVuSansMono-Bold.ttf", "sym": DJ + "DejaVuSans-Bold.ttf"}[name], int(size))
    return _fc[k]

def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def rgba(c, a): return tuple(c[:3]) + (int(255 * max(0, min(1, a))),)
def col(name, default=FG): return COL.get(name, default) if isinstance(name, str) else (tuple(name) if name else default)

# layout
CX = W // 2
CW = int(W * (0.84 if SHORT else 0.72))
TOP = 300 if SHORT else 150
BOT = int(H * 0.66) if SHORT else H - 210
K = 1.15 if SHORT else 1.0   # text scale

base = Image.new("RGB", (W, H), BG)
d0 = ImageDraw.Draw(base)
for x in range(0, W, 60): d0.line([(x, 0), (x, H)], fill=GRID)
for y in range(0, H, 60): d0.line([(0, y), (W, y)], fill=GRID)
vig = Image.new("L", (W, H), 0)
ImageDraw.Draw(vig).ellipse([-300, -250, W + 300, H + 250], fill=255)
vig = vig.filter(ImageFilter.GaussianBlur(220))
base = Image.composite(base, Image.new("RGB", (W, H), (4, 5, 7)), vig)

def wrap(d, s, font, maxw):
    out = []
    for para in str(s).split("\n"):
        cur = ""
        for w in para.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=font) <= maxw: cur = t
            else:
                if cur: out.append(cur)
                cur = w
        out.append(cur)
    return out

def text_block(d, y, s, font, color, a, maxw=None, lh=1.18):
    lines = wrap(d, s, font, maxw or CW)
    step = font.size * lh
    for i, ln in enumerate(lines):
        d.text((CX, y + i * step), ln, font=font, fill=rgba(color, a), anchor="mt")
    return y + len(lines) * step

def fit_font(d, s, name, size, maxw, maxlines):
    while size > 24:
        f = F(name, size)
        ls = wrap(d, s, f, maxw)
        if len(ls) <= maxlines and max(d.textlength(l, font=f) for l in ls) <= maxw: return f
        size -= 4
    return F(name, size)

def card(d, box, outline, fill, a, r=20, w=3):
    d.rounded_rectangle(box, radius=r, fill=rgba(fill, a), outline=rgba(outline, a) if outline else None, width=w)

def reveal_times(sc, items):
    n = len(items)
    st, en = sc["_start"], sc["_end"]
    ls = [l["start"] for l in sc["_lines"]]
    out = []
    for k, it in enumerate(items):
        if isinstance(it, dict) and "line" in it and it["line"] < len(ls):
            out.append(ls[it["line"]])
        else:
            out.append(st + 0.3 + (en - st - 1.0) * 0.8 * k / max(1, n))
    return out

def head(d, sc, t, y):
    a = ease((t - sc["_start"] + 0.1) / 0.4)
    if sc.get("kicker"):
        d.text((CX, y), sc["kicker"].upper(), font=F("bold", 38 * K), fill=rgba(ACC, a), anchor="mt")
        y += 60 * K
    if sc.get("title"):
        f = fit_font(d, sc["title"], "head", 92 * K, CW, 2)
        y = text_block(d, y, sc["title"], f, FG, a) + 30 * K
    return y

# ---------- scene drawers ----------
def s_title(d, sc, t):
    y = TOP + (BOT - TOP) * 0.18
    a = ease((t - sc["_start"] + 0.1) / 0.45)
    if sc.get("kicker"):
        d.text((CX, y), sc["kicker"].upper(), font=F("bold", 42 * K), fill=rgba(ACC, a), anchor="mt"); y += 80 * K
    f = fit_font(d, sc.get("title", ""), "head", 130 * K, CW, 3)
    y = text_block(d, y, sc.get("title", ""), f, col(sc.get("color"), FG), a) + 40 * K
    if sc.get("sub"):
        ls = sc["_lines"]
        ta = ls[1]["start"] if len(ls) > 1 else sc["_start"] + 1.2
        text_block(d, y, sc["sub"], F("med", 50 * K), DIM, ease((t - ta) / 0.4))

def s_statement(d, sc, t):
    a = ease((t - sc["_start"] + 0.1) / 0.45)
    f = fit_font(d, sc["text"], "head", 120 * K, CW, 4)
    n = len(wrap(d, sc["text"], f, CW))
    y = (TOP + BOT) / 2 - n * f.size * 1.18 / 2 - (40 * K if sc.get("sub") else 0)
    y = text_block(d, y, sc["text"], f, col(sc.get("color"), FG), a) + 30 * K
    if sc.get("sub"):
        ls = sc["_lines"]
        ta = ls[1]["start"] if len(ls) > 1 else sc["_start"] + 1.0
        text_block(d, y, sc["sub"], F("med", 48 * K), DIM, ease((t - ta) / 0.4))

def s_bignum(d, sc, t):
    a = ease((t - sc["_start"] + 0.1) / 0.45)
    y = TOP + (BOT - TOP) * 0.12
    if sc.get("label"):
        d.text((CX, y), sc["label"].upper(), font=F("bold", 44 * K), fill=rgba(col(sc.get("label_color"), COL["amb"]), a), anchor="mt")
        y += 90 * K
    v = str(sc["value"])
    if sc.get("count"):
        try:
            target = float(v.replace(",", ""))
            frac = ease((t - sc["_start"]) / max(0.8, min(2.5, (sc["_end"] - sc["_start"]) * 0.4)))
            cur = target * frac
            v = f"{cur:,.0f}" if target == int(target) else f"{cur:,.1f}"
        except ValueError:
            pass
    f = fit_font(d, str(sc["value"]), "black", 300 * K, CW * 0.9, 1)
    d.text((CX, y), v, font=f, fill=rgba(col(sc.get("color"), FG), a), anchor="mt")
    y += f.size * 1.15
    if sc.get("sub"):
        ls = sc["_lines"]
        ta = ls[1]["start"] if len(ls) > 1 else sc["_start"] + 0.8
        text_block(d, y, sc["sub"], F("med", 54 * K), DIM, ease((t - ta) / 0.4))

def s_list(d, sc, t):
    y = head(d, sc, t, TOP)
    items = sc.get("items", [])
    times = reveal_times(sc, items)
    n = len(items)
    room = BOT - y
    rowh = min(130 * K, room / max(1, n))
    fsz = min(48 * K, rowh * 0.42)
    for k, it in enumerate(items):
        a = ease((t - times[k]) / 0.35)
        if a <= 0: continue
        it = it if isinstance(it, dict) else {"text": it}
        c = col(it.get("color"), EDGE)
        yy = y + k * rowh + (1 - a) * 20
        x0, x1 = CX - CW / 2, CX + CW / 2
        card(d, (x0, yy, x1, yy + rowh * 0.84), c if it.get("color") else EDGE, CARD, a, w=2)
        mark = it.get("mark")
        tx = x0 + 40
        if mark:
            sym = {"x": "✗", "check": "✓"}.get(mark, mark)
            mc = RED if mark == "x" else ACC
            d.text((tx, yy + rowh * 0.42), sym, font=F("sym", fsz * 1.1), fill=rgba(mc, a), anchor="lm")
            tx += fsz * 1.5
        f = F("med", fsz)
        s = it["text"]
        while d.textlength(s, font=f) > (x1 - tx - 30) and len(s) > 4: s = s[:-2]
        if s != it["text"]: s = s.rstrip() + "…"
        d.text((tx, yy + rowh * 0.42), s, font=f, fill=rgba(FG, a), anchor="lm")
        if it.get("strike"):
            sa = ease((t - times[k] - 0.4) / 0.3)
            if sa > 0:
                tw = d.textlength(s, font=f)
                d.line([(tx, yy + rowh * 0.42), (tx + tw * sa, yy + rowh * 0.42)], fill=rgba(RED, a), width=5)

def s_bars(d, sc, t):
    y = head(d, sc, t, TOP)
    bars = sc.get("bars", [])
    times = reveal_times(sc, bars)
    rowh = min(150 * K, (BOT - y) / max(1, len(bars)))
    x0, x1 = CX - CW / 2, CX + CW / 2
    for k, b in enumerate(bars):
        a = ease((t - times[k]) / 0.4)
        if a <= 0: continue
        yy = y + k * rowh
        d.text((x0, yy), b["label"], font=F("bold", 40 * K), fill=rgba(FG, a), anchor="lt")
        d.text((x1, yy), b.get("display", ""), font=F("mono", 36 * K), fill=rgba(DIM, a), anchor="rt")
        by = yy + 58 * K
        card(d, (x0, by, x1, by + 38 * K), None, (30, 35, 45), a, r=18, w=0)
        frac = max(0.0, min(1.0, float(b.get("frac", 0)))) * ease((t - times[k] - 0.2) / 0.8)
        c = col(b.get("color"), ACC)
        card(d, (x0, by, x0 + max(10, (x1 - x0) * frac), by + 38 * K), None, c, a, r=18, w=0)

def s_terminal(d, sc, t):
    y = head(d, sc, t, TOP)
    a0 = ease((t - sc["_start"] + 0.1) / 0.4)
    x0, x1 = CX - CW / 2 - 20, CX + CW / 2 + 20
    y1 = BOT
    card(d, (x0, y, x1, y1), EDGE, (13, 16, 21), a0, r=18, w=2)
    for k, c in enumerate([RED, COL["amb"], ACC]):
        d.ellipse([x0 + 30 + k * 40, y + 25, x0 + 52 + k * 40, y + 47], fill=rgba(c, a0))
    log = sc.get("log", [])
    times = reveal_times(sc, log)
    fs = 34 * K if not SHORT else 34
    yy = y + 80
    for k, row in enumerate(log):
        txt, c = (row[0], row[1]) if isinstance(row, list) else (row, "fg")
        tt = t - times[k]
        if tt <= 0: break
        for ln in wrap(d, txt, F("mono", fs), x1 - x0 - 80):
            n = int(len(ln) * min(1, tt / 0.45))
            d.text((x0 + 40, yy), ln[:n], font=F("mono", fs), fill=rgba(col(c), 1))
            yy += fs * 1.45
        if yy > y1 - 40: break

def s_chart(d, sc, t):
    y = head(d, sc, t, TOP)
    xs, ys = sc.get("x", []), sc.get("y", [])
    if not ys: return
    a = ease((t - sc["_start"]) / 0.5)
    x0, x1 = CX - CW / 2 + 60, CX + CW / 2
    y0, y1 = y + 20, BOT - 60
    top = max(ys) * 1.15 or 1
    d.line([(x0, y1), (x1, y1)], fill=rgba(EDGE, a), width=3)
    pts = [(x0 + (x1 - x0) * i / max(1, len(ys) - 1), y1 - (y1 - y0) * v / top) for i, v in enumerate(ys)]
    prog = ease((t - sc["_start"] - 0.3) / max(1.0, (sc["_end"] - sc["_start"]) * 0.6))
    upto = prog * (len(pts) - 1)
    drawn = [pts[0]]
    for i in range(1, len(pts)):
        if i <= upto: drawn.append(pts[i])
        else:
            f = upto - (i - 1)
            if f > 0: drawn.append((pts[i-1][0] + (pts[i][0]-pts[i-1][0]) * f, pts[i-1][1] + (pts[i][1]-pts[i-1][1]) * f))
            break
    if len(drawn) > 1: d.line(drawn, fill=rgba(ACC, a), width=8, joint="curve")
    for i, p in enumerate(pts):
        if i <= upto + 0.01:
            d.ellipse([p[0]-10, p[1]-10, p[0]+10, p[1]+10], fill=rgba(ACC, a))
            d.text((p[0], p[1] - 22), f"{ys[i]:,}", font=F("bold", 32 * K), fill=rgba(FG, a), anchor="mb")
        if i < len(xs):
            d.text((p[0], y1 + 16), str(xs[i]), font=F("mono", 28 * K), fill=rgba(DIM, a), anchor="mt")
    if sc.get("unit"):
        d.text((x0 - 40, y0), sc["unit"], font=F("mono", 28 * K), fill=rgba(DIM, a), anchor="lt")

DRAW = {"title": s_title, "statement": s_statement, "bignum": s_bignum, "list": s_list,
        "bars": s_bars, "terminal": s_terminal, "chart": s_chart}

def hud(img, t):
    d = ImageDraw.Draw(img)
    pulse = 0.5 + 0.5 * math.sin(t * 4)
    y = 120 if SHORT else 61
    x = 60
    d.ellipse([x, y - 11, x + 22, y + 11], fill=tuple(int((120 + (255-120)*pulse, 30 + 47*pulse, 40 + 54*pulse)[i]) for i in range(3)))
    d.text((x + 38, y), "HybridAi", font=F("head", 40 if SHORT else 34), fill=FG, anchor="lm")
    d.text((x + (270 if SHORT else 230), y), SPEC.get("label", ""), font=F("mono", 28 if SHORT else 26), fill=DIM, anchor="lm")
    st = SPEC.get("hud_stats")
    if st:
        s = "   ".join(f"{k.upper()} {v}" for k, v in st.items())
        if SHORT: d.text((60, y + 56), s, font=F("mono", 28), fill=DIM, anchor="lm")
        else: d.text((W - 60, y), s, font=F("mono", 26), fill=DIM, anchor="rm")
    if SHORT: d.rectangle([0, 0, int(W * t / DUR), 8], fill=ACC)
    else: d.rectangle([0, H - 6, int(W * t / DUR), H], fill=ACC)

def captions(img, t):
    cur = next((l for l in LINES if l["start"] - 0.05 <= t <= l["end"] + 0.2), None)
    if not cur: return
    d = ImageDraw.Draw(img, "RGBA")
    f = F("bold", 56 if SHORT else 44)
    maxw = W * (0.86 if SHORT else 0.78)
    lines = wrap(d, cur["text"], f, maxw)
    lh = f.size * 1.3
    total = lh * len(lines)
    y0 = (H * 0.72) if SHORT else (H - 70 - total)
    mw = max(d.textlength(s, font=f) for s in lines)
    d.rounded_rectangle([W/2 - mw/2 - 30, y0 - 18, W/2 + mw/2 + 30, y0 + total + 8], radius=16, fill=(0, 0, 0, 175))
    for i, s in enumerate(lines):
        d.text((W / 2, y0 + i * lh), s, font=f, fill=FG, anchor="mt")

def frame(t):
    img = base.copy().convert("RGBA")
    i = next((k for k, s in enumerate(SC) if t < s["_end"]), len(SC) - 1)
    sc = SC[i]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    DRAW[sc["type"]](ImageDraw.Draw(layer), sc, t)
    fo = 1 - ease((t - (sc["_end"] - 0.3)) / 0.3) if i < len(SC) - 1 else 1.0
    if fo < 1:
        r, g, b, al = layer.split()
        layer = Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * fo))))
    img.alpha_composite(layer)
    hud(img, t)
    captions(img, t)
    return img.convert("RGB")

if __name__ == "__main__":
    mode = sys.argv[3]
    if mode == "still":
        for tt in sys.argv[4:]:
            frame(float(tt)).save(f"{WD}/still_{tt}.png")
        sys.exit()
    part, n = int(sys.argv[4]), int(sys.argv[5])
    a, b = NFRAMES * part // n, NFRAMES * (part + 1) // n
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "19", "-pix_fmt", "yuv420p", f"{WD}/part{part}.mp4"], stdin=subprocess.PIPE)
    for fi in range(a, b):
        p.stdin.write(frame(fi / FPS).tobytes())
    p.stdin.close(); p.wait()
    print("done part", part)
