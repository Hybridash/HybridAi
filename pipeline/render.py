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
  chart     title, x: [labels], y: [numbers], unit, point_colors: [color per point] (bigger dots),
            legend: [[label, color]] drawn under the axis
  statement text, color, sub
  search    title, queries: [{q, note, line}], result: the YouTube search bar types each query
            in turn; earlier ones stack below it with their note (e.g. a % share)
  game      title, bot, seed, tps (ticks/sec, default 30), tail (only replay the last N walls),
            caption: replays a real game of games/gap_runner.py (Gap Runner), drawn live
  maze      title, bot (random|hand|memory), seed, loops, sps (steps/sec), trail, caption,
            banner, banner_at: replays a real run of games/maze_bots.py (exit = green cell)
  dice      title, bot, seed, rps (rolls/sec, default 1.2), caption: replays one real turn of
            games/bust_dice.py (Bust Dice): dice land in a row, pot counts up, repeat = BUST
  catch     title, bot (random|chaser|dodger|learner), seed, train (learner practice games, trained
            with seed 12), tps (ticks/sec, default 4), from, upto (tick window), caption: replays a
            real game of games/sky_catch.py (Sky Catch): coins and bombs fall, the player catches
  forage    title, bot ("greedy" or a genome [w_food, w_visited, w_center, w_straight]), board (seed
            for the board and the greedy bot's random moves), sps (moves/sec, default 10), caption:
            replays a real game of games/forager.py (Forager): pellets, sight diamond, trail, energy
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
            pc = sc.get("point_colors", [])
            c = col(pc[i], ACC) if i < len(pc) else ACC
            r = 16 if i < len(pc) else 10
            d.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], fill=rgba(c, a))
            d.text((p[0], p[1] - 22), f"{ys[i]:,}", font=F("bold", 32 * K), fill=rgba(c if i < len(pc) else FG, a), anchor="mb")
        if i < len(xs):
            d.text((p[0], y1 + 16), str(xs[i]), font=F("mono", 28 * K), fill=rgba(DIM, a), anchor="mt")
    for k, (lbl, cn) in enumerate(sc.get("legend", [])):
        lx = x0 + k * (x1 - x0) / max(1, len(sc["legend"]))
        d.ellipse([lx, y1 + 92 * K, lx + 28, y1 + 92 * K + 28], fill=rgba(col(cn), a))
        d.text((lx + 42, y1 + 92 * K + 14), lbl, font=F("bold", 34 * K), fill=rgba(col(cn), a), anchor="lm")
    if sc.get("unit"):
        d.text((x0 - 40, y0), sc["unit"], font=F("mono", 28 * K), fill=rgba(DIM, a), anchor="lt")

_games = {}
def game_trace(sc):
    k = (sc["bot"], sc["seed"])
    if k not in _games:
        import os, random as _r
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "games"))
        import gap_runner as G
        score, frames = G.play(sc["bot"], _r.Random(sc["seed"]), trace=True)
        _games[k] = (G, score, frames)
    return _games[k]

def s_game(d, sc, t):
    G, score, frames = game_trace(sc)
    y = head(d, sc, t, TOP)
    a = ease((t - sc["_start"] + 0.1) / 0.4)
    tail = sc.get("tail")
    i0 = max(0, len(frames) - tail * G.SPACING) if tail else 0
    tps = sc.get("tps", 30)
    i = i0 + int(max(0.0, t - sc["_start"] - 0.3) * tps)
    died = score < G.MAX_WALLS
    i = min(i, len(frames) - 1)
    py_, tw, g0, g1, sc_now = frames[i]
    x0, x1 = CX - CW / 2, CX + CW / 2
    y0, y1 = y + 60 * K, BOT - 10
    card(d, (x0, y0, x1, y1), EDGE, (13, 16, 21), a, r=18, w=2)
    fy = lambda v: y0 + 10 + (y1 - y0 - 20) * (1 - v / G.FIELD)
    px = x0 + (x1 - x0) * 0.2
    ppt = (x1 - x0) * 0.75 / G.SPACING  # pixels per tick
    ww = 34
    for ticks, gc in ((tw, g0), (tw + G.SPACING, g1)):
        wx = px + ticks * ppt
        if wx - ww / 2 > x1 - 6: continue
        lo, hi = fy(gc + G.GAP / 2), fy(gc - G.GAP / 2)
        xa, xb = max(x0 + 6, wx - ww / 2), min(x1 - 6, wx + ww / 2)
        if xb <= xa: continue
        d.rectangle([xa, y0 + 6, xb, lo], fill=rgba(COL["blue"], a))
        d.rectangle([xa, hi, xb, y1 - 6], fill=rgba(COL["blue"], a))
    end = died and i == len(frames) - 1
    rr = (y1 - y0 - 20) * G.R / G.FIELD * 1.6
    c = RED if end else ACC
    d.ellipse([px - rr, fy(py_) - rr, px + rr, fy(py_) + rr], fill=rgba(c, a))
    d.text((x0, y0 - 14), sc.get("caption", sc["bot"]).upper(), font=F("bold", 34 * K), fill=rgba(DIM, a), anchor="lb")
    d.text((x1, y0 - 14), f"WALLS {sc_now}", font=F("monob", 34 * K), fill=rgba(c, a), anchor="rb")
    if end:
        d.text((CX, (y0 + y1) / 2), "HIT", font=F("black", 120 * K), fill=rgba(RED, a), anchor="mm")

def s_search(d, sc, t):
    y = head(d, sc, t, TOP)
    a0 = ease((t - sc["_start"] + 0.1) / 0.4)
    x0, x1 = CX - CW / 2, CX + CW / 2
    bh = 120 * K
    card(d, (x0, y, x1, y + bh), FG, (16, 19, 26), a0, r=int(bh / 2), w=3)
    # magnifier icon
    mx, my, r = x0 + 70, y + bh / 2 - 6, 24 * K
    d.ellipse([mx - r, my - r, mx + r, my + r], outline=rgba(DIM, a0), width=6)
    d.line([(mx + r * 0.7, my + r * 0.7), (mx + r * 1.6, my + r * 1.6)], fill=rgba(DIM, a0), width=8)
    qs = sc.get("queries", [])
    times = reveal_times(sc, qs)
    cur = max([k for k in range(len(qs)) if t >= times[k]], default=-1)
    f = F("med", 52 * K)
    tx = x0 + 130 * K
    if cur >= 0:
        q = qs[cur]["q"]
        n = int(len(q) * min(1, (t - times[cur]) / 0.9))
        d.text((tx, y + bh / 2), q[:n], font=f, fill=rgba(FG, a0), anchor="lm")
        if int(t * 2) % 2 == 0 or n < len(q):
            cx = tx + d.textlength(q[:n], font=f) + 6
            d.line([(cx, y + bh / 2 - 32 * K), (cx, y + bh / 2 + 32 * K)], fill=rgba(ACC, a0), width=4)
    else:
        d.text((tx, y + bh / 2), "Search", font=f, fill=rgba(DIM, a0), anchor="lm")
    # finished queries stack below
    yy = y + bh + 50 * K
    rowh = 105 * K
    for k in range(len(qs)):
        done = times[k] + 1.2
        if t < done: continue
        a = ease((t - done) / 0.35)
        card(d, (x0, yy, x1, yy + rowh * 0.82), EDGE, CARD, a, w=2)
        d.text((x0 + 40, yy + rowh * 0.41), qs[k]["q"], font=F("med", 44 * K), fill=rgba(FG, a), anchor="lm")
        if qs[k].get("note"):
            d.text((x1 - 40, yy + rowh * 0.41), qs[k]["note"], font=F("monob", 38 * K), fill=rgba(ACC, a), anchor="rm")
        yy += rowh
    if sc.get("result") and len(qs) and t >= times[-1] + 1.8:
        a = ease((t - times[-1] - 1.8) / 0.4)
        text_block(d, yy + 20 * K, sc["result"], F("med", 46 * K), DIM, a)

_mazes = {}
def maze_trace(sc):
    k = (sc["bot"], sc["seed"], bool(sc.get("loops")))
    if k not in _mazes:
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "games"))
        import maze_bots as M
        _mazes[k] = (M,) + M.play(sc["bot"], sc["seed"], bool(sc.get("loops")))
    return _mazes[k]

def s_maze(d, sc, t):
    M, mz, goal, steps, path = maze_trace(sc)
    y = head(d, sc, t, TOP)
    a = ease((t - sc["_start"] + 0.1) / 0.4)
    side = min(CW, BOT - 10 - (y + 60 * K))
    x0, y0 = CX - side / 2, y + 60 * K
    cs = side / M.N
    card(d, (x0 - 14, y0 - 14, x0 + side + 14, y0 + side + 14), EDGE, (13, 16, 21), a, r=14, w=2)
    # exit cell
    gx, gy = goal
    d.rectangle([x0 + gx * cs + 6, y0 + gy * cs + 6, x0 + (gx + 1) * cs - 6, y0 + (gy + 1) * cs - 6], fill=rgba(ACC, a * 0.85))
    # trail
    sps = sc.get("sps", 10)
    i = min(len(path) - 1, int(max(0.0, t - sc["_start"] - 0.4) * sps))
    trail = sc.get("trail", 60)
    lo = max(0, i - trail)
    for j in range(lo, i):
        (ax, ay), (bx, by) = path[j], path[j + 1]
        f = (j - lo + 1) / max(1, i - lo)
        d.line([(x0 + (ax + .5) * cs, y0 + (ay + .5) * cs), (x0 + (bx + .5) * cs, y0 + (by + .5) * cs)],
               fill=rgba(COL["amb"], a * (0.15 + 0.6 * f)), width=int(cs * 0.22))
    # walls
    wc = rgba(FG, a)
    lw = max(3, int(cs * 0.08))
    for (cx, cy), op in mz.items():
        px, py = x0 + cx * cs, y0 + cy * cs
        if 0 not in op: d.line([(px, py), (px + cs, py)], fill=wc, width=lw)
        if 3 not in op: d.line([(px, py), (px, py + cs)], fill=wc, width=lw)
        if cx == M.N - 1: d.line([(px + cs, py), (px + cs, py + cs)], fill=wc, width=lw)
        if cy == M.N - 1: d.line([(px, py + cs), (px + cs, py + cs)], fill=wc, width=lw)
    done = steps is not None and i == len(path) - 1
    bx, by = path[i]
    rr = cs * 0.3
    c = ACC if done else (COL["blue"])
    d.ellipse([x0 + (bx + .5) * cs - rr, y0 + (by + .5) * cs - rr, x0 + (bx + .5) * cs + rr, y0 + (by + .5) * cs + rr], fill=rgba(c, a))
    d.text((x0 - 14, y0 - 30), sc.get("caption", sc["bot"]).upper(), font=F("bold", 34 * K), fill=rgba(DIM, a), anchor="lb")
    stuck_now = steps is None and i == len(path) - 1
    d.text((x0 + side + 14, y0 - 30), f"STEP {i:,}", font=F("monob", 34 * K), fill=rgba(RED if stuck_now else FG, a), anchor="rb")
    if done:
        f = F("black", 110 * K)
        tw = d.textlength("OUT", font=f)
        d.rounded_rectangle([CX - tw / 2 - 30, y0 + side / 2 - 80 * K, CX + tw / 2 + 30, y0 + side / 2 + 80 * K], radius=20, fill=rgba(BG, a * 0.85))
        d.text((CX, y0 + side / 2), "OUT", font=f, fill=rgba(ACC, a), anchor="mm")
    if sc.get("banner") and t >= sc["_start"] + sc.get("banner_at", 0):
        ba = ease((t - sc["_start"] - sc.get("banner_at", 0)) / 0.4)
        f = F("black", 110 * K)
        tw = d.textlength(sc["banner"], font=f)
        d.rounded_rectangle([CX - tw / 2 - 30, y0 + side / 2 - 80 * K, CX + tw / 2 + 30, y0 + side / 2 + 80 * K], radius=20, fill=rgba(BG, ba * 0.85))
        d.text((CX, y0 + side / 2), sc["banner"], font=f, fill=rgba(RED, ba), anchor="mm")

_dice = {}
def dice_trace(sc):
    k = (sc["bot"], sc["seed"])
    if k not in _dice:
        import os, random as _r
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "games"))
        import bust_dice as B
        tr = []
        v = B.turn(sc["bot"], _r.Random(sc["seed"]), trace=tr)
        _dice[k] = (tr, v)
    return _dice[k]

PIPS = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)], 4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
        5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)], 6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}
def die(d, cx, cy, size, v, c, a, fill=FG):
    h = size / 2
    d.rounded_rectangle([cx - h, cy - h, cx + h, cy + h], radius=int(size * 0.18), fill=rgba(fill, a), outline=rgba(c, a), width=8)
    pr = size * 0.09
    for px, py in PIPS[v]:
        x, y = cx + px * size * 0.27, cy + py * size * 0.27
        d.ellipse([x - pr, y - pr, x + pr, y + pr], fill=rgba(BG, a))

def s_dice(d, sc, t):
    rolls, banked = dice_trace(sc)
    y = head(d, sc, t, TOP)
    a = ease((t - sc["_start"] + 0.1) / 0.4)
    x0, x1 = CX - CW / 2, CX + CW / 2
    y0, y1 = y + 60 * K, BOT - 10
    card(d, (x0, y0, x1, y1), EDGE, (13, 16, 21), a, r=18, w=2)
    d.text((x0, y0 - 14), sc.get("caption", sc["bot"]).upper(), font=F("bold", 34 * K), fill=rgba(DIM, a), anchor="lb")
    rps = sc.get("rps", 1.2)
    el = max(0.0, t - sc["_start"] - 0.5) * rps
    n = min(len(rolls), int(el) + (1 if el > 0 else 0))
    bust = banked == 0
    done = el >= len(rolls) + 0.3
    # dice in two rows of up to 4
    size = min((x1 - x0 - 100) / 4 - 24, (y1 - y0) * 0.26)
    for k in range(n):
        v = rolls[k]
        lt = ease((el - k) / 0.35)
        row, colk = divmod(k, 4)
        cx = x0 + 50 + size / 2 + colk * (size + 24) + (x1 - x0 - 100 - 4 * size - 3 * 24) / 2
        cy = y0 + 50 + size / 2 + row * (size + 30) - (1 - lt) * 60
        rep = bust and k == len(rolls) - 1
        die(d, cx, cy, size, v, RED if rep else (EDGE if not done else (RED if bust else ACC)), a * lt, fill=(255, 210, 215) if rep else FG)
    pot = sum(rolls[:n]) if not (bust and n == len(rolls)) else sum(rolls[:n - 1])
    py = y0 + 50 + 2 * (size + 30) + 30
    ba = ease((el - len(rolls) - 0.3) / 0.4 * rps) if done else 0.0
    pa = a * (1 - ba)
    if pa > 0.02: d.text((x0 + 50, py), "POT", font=F("bold", 40 * K), fill=rgba(DIM, pa), anchor="lt")
    if pa > 0.02: d.text((x1 - 50, py), str(pot), font=F("black", 110 * K), fill=rgba(FG, pa), anchor="rt")
    if done:
        txt = "BUST: 0" if bust else f"BANK {banked}"
        f = F("black", 120 * K)
        d.text((CX, py + 60 * K), txt, font=f, fill=rgba(RED if bust else ACC, ba * a), anchor="mm")

_catch = {}
def catch_trace(sc):
    k = (sc["bot"], sc["seed"], sc.get("train", 0))
    if k not in _catch:
        import os, random as _r
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "games"))
        import sky_catch as S
        Q = None
        if sc["bot"] == "learner":
            Q = {}; S.train(Q, sc.get("train", 0), _r.Random(12))
        tr = []
        S.play(sc["bot"], _r.Random(sc["seed"]), Q, tr)
        _catch[k] = (S, tr)
    return _catch[k]

def s_catch(d, sc, t):
    S, tr = catch_trace(sc)
    y = head(d, sc, t, TOP)
    a = ease((t - sc["_start"] + 0.1) / 0.4)
    top = y + 60 * K
    hgt = BOT - 70 * K - top
    cs = min(CW / S.COLS, hgt / S.ROWS)
    gw, gh = cs * S.COLS, cs * S.ROWS
    x0, y0 = CX - gw / 2, top + (hgt - gh) / 2
    card(d, (x0 - 14, y0 - 14, x0 + gw + 14, y0 + gh + 14), EDGE, (13, 16, 21), a, r=14, w=2)
    for c in range(1, S.COLS):
        d.line([(x0 + c * cs, y0), (x0 + c * cs, y0 + gh)], fill=rgba(GRID, a), width=2)
    lo = sc.get("from", 0)
    hi = min(len(tr) - 1, sc.get("upto", len(tr) - 1))
    tps = sc.get("tps", 4)
    el = lo + max(0.0, t - sc["_start"] - 0.4) * tps
    i = min(hi, int(el))
    f = 0.0 if i >= hi else el - i
    grid, col, score, died, tick = tr[i]
    ncol = tr[min(i + 1, hi)][1] if i < hi else col
    mv = ease(min(1.0, f * 2.5))
    pc = col + (ncol - col) * mv
    fa = ease(min(1.0, f * 1.0))
    for r in range(S.ROWS):
        for c in range(S.COLS):
            v = grid[r][c]
            if v == S.EMPTY: continue
            ry = r + fa if i < hi else r
            cx, cy = x0 + (c + .5) * cs, y0 + (ry + .5) * cs
            rr = cs * 0.3
            if v == S.COIN:
                d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=rgba(COL["amb"], a), outline=rgba((140, 100, 20), a), width=5)
            else:
                d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=rgba(RED, a))
                q = rr * 0.45
                d.line([(cx - q, cy - q), (cx + q, cy + q)], fill=rgba(BG, a), width=7)
                d.line([(cx - q, cy + q), (cx + q, cy - q)], fill=rgba(BG, a), width=7)
    end = i >= hi and hi == len(tr) - 1
    boom = end and died
    px = x0 + (pc + .5) * cs
    py = y0 + (S.ROWS - 0.5) * cs
    pw, ph = cs * 0.42, cs * 0.2
    d.rounded_rectangle([px - pw, py - ph + cs * 0.15, px + pw, py + ph + cs * 0.15], radius=int(ph), fill=rgba(RED if boom else (COL["blue"]), a))
    d.text((CX, y0 - 30), sc.get("caption", sc["bot"]).upper(), font=F("bold", 34 * K), fill=rgba(DIM, a), anchor="mb")
    d.text((x0 - 14, y0 + gh + 24), f"COINS {score}", font=F("monob", 34 * K), fill=rgba(COL["amb"], a), anchor="lt")
    d.text((x0 + gw + 14, y0 + gh + 24), f"TICK {tick}", font=F("mono", 34 * K), fill=rgba(DIM, a), anchor="rt")
    if boom:
        fb = F("black", 110 * K)
        tw = d.textlength("BOOM", font=fb)
        d.rounded_rectangle([CX - tw / 2 - 30, y0 + gh / 2 - 80 * K, CX + tw / 2 + 30, y0 + gh / 2 + 80 * K], radius=20, fill=rgba(BG, a * 0.85))
        d.text((CX, y0 + gh / 2), "BOOM", font=fb, fill=rgba(RED, a), anchor="mm")

_forage = {}
def forage_trace(sc):
    k = (json.dumps(sc["bot"]), sc["board"])
    if k not in _forage:
        import os, random as _r
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "games"))
        import forager as G
        b = G.board(_r.Random(sc["board"]))
        tr = []
        bot = sc["bot"] if sc["bot"] == "greedy" else tuple(sc["bot"])
        G.play(bot, b, _r.Random(sc["board"]), tr)
        _forage[k] = (G, tr)
    return _forage[k]

def s_forage(d, sc, t):
    G, tr = forage_trace(sc)
    y = head(d, sc, t, TOP)
    a = ease((t - sc["_start"] + 0.1) / 0.4)
    side = min(CW, BOT - 80 * K - (y + 60 * K))
    x0, y0 = CX - side / 2, y + 60 * K
    cs = side / G.N
    card(d, (x0 - 14, y0 - 14, x0 + side + 14, y0 + side + 14), EDGE, (13, 16, 21), a, r=14, w=2)
    for c in range(1, G.N):
        d.line([(x0 + c * cs, y0), (x0 + c * cs, y0 + side)], fill=rgba(GRID, a), width=1)
        d.line([(x0, y0 + c * cs), (x0 + side, y0 + c * cs)], fill=rgba(GRID, a), width=1)
    sps = sc.get("sps", 10)
    i = min(len(tr) - 1, int(max(0.0, t - sc["_start"] - 0.5) * sps))
    bx, by, e, eaten, food = tr[i]
    # sight diamond
    for gx in range(G.N):
        for gy in range(G.N):
            if abs(gx - bx) + abs(gy - by) <= G.SIGHT:
                d.rectangle([x0 + gx * cs + 1, y0 + gy * cs + 1, x0 + (gx + 1) * cs - 1, y0 + (gy + 1) * cs - 1], fill=rgba(COL["blue"], a * 0.10))
    # trail
    pts = [(x0 + (p[0] + .5) * cs, y0 + (p[1] + .5) * cs) for p in tr[:i + 1]]
    if len(pts) > 1: d.line(pts, fill=rgba(COL["blue"], a * 0.45), width=max(3, int(cs * 0.16)), joint="curve")
    rr = cs * 0.24
    for fx, fy in food:
        cx, cy = x0 + (fx + .5) * cs, y0 + (fy + .5) * cs
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=rgba(COL["amb"], a))
    end = i == len(tr) - 1
    cleared = end and not food
    starved = end and food and e <= 0
    c = ACC if cleared else (RED if starved else FG)
    br = cs * 0.36
    cx, cy = x0 + (bx + .5) * cs, y0 + (by + .5) * cs
    d.ellipse([cx - br, cy - br, cx + br, cy + br], fill=rgba(c, a))
    d.text((x0 - 14, y0 - 30), sc.get("caption", "").upper(), font=F("bold", 34 * K), fill=rgba(DIM, a), anchor="lb")
    d.text((x0 + side + 14, y0 - 30), f"MOVE {i}", font=F("mono", 34 * K), fill=rgba(DIM, a), anchor="rb")
    d.text((x0 - 14, y0 + side + 30), f"FOOD {eaten}/{G.FOOD}", font=F("monob", 38 * K), fill=rgba(COL["amb"], a), anchor="lt")
    d.text((x0 + side + 14, y0 + side + 30), f"ENERGY {e}", font=F("monob", 38 * K), fill=rgba(RED if e <= 5 else ACC, a), anchor="rt")
    if cleared or starved:
        txt = "CLEARED" if cleared else "STARVED"
        fb = F("black", 110 * K)
        tw = d.textlength(txt, font=fb)
        d.rounded_rectangle([CX - tw / 2 - 30, y0 + side / 2 - 80 * K, CX + tw / 2 + 30, y0 + side / 2 + 80 * K], radius=20, fill=rgba(BG, a * 0.85))
        d.text((CX, y0 + side / 2), txt, font=fb, fill=rgba(c, a), anchor="mm")

DRAW = {"forage": s_forage, "catch": s_catch, "dice": s_dice, "maze": s_maze, "search": s_search, "game": s_game, "title": s_title, "statement": s_statement, "bignum": s_bignum, "list": s_list,
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
