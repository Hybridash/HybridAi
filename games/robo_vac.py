"""Robo Vac: an original cleaning game, made for HybridAi Day 36.

Rules:
  A room of COLS x ROWS floor cells with furniture (a few random blocks) and the dock in the top-left
  corner. The robot starts on the dock and cleans every cell it stands on. Each turn it tries to move one
  cell (up/down/left/right); if a wall or furniture is there it bumps and stays put (the turn is still
  used). It has no camera: the only thing it ever learns about the room is where it bumped. The battery
  lasts BATTERY turns. Score = share of the reachable floor that got cleaned. Each room uses one seed, so
  every bot cleans the same room in game n.

Bots:
  bounce   drives a straight line at a random angle; after a bump it picks a new random angle.
  mower    back-and-forth rows: drives across until it bumps, steps one row down (or up), turns around.
           If the row step is blocked it picks a random direction for one move and carries on.
  hugger   follows the wall on its right hand all the way round.
  mapper   remembers every cell it cleaned and every bump. It drives the shortest known path to the
           nearest cell it hasn't cleaned yet (unknown cells count as open until it bumps into them).

usage: python3 games/robo_vac.py [rooms_per_bot] [seed]
"""
import random, sys
from collections import deque

COLS, ROWS, BATTERY = 16, 12, 400
DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1)]  # E S W N
BOTS = ["bounce", "mower", "hugger", "mapper"]

def make_room(rng):
    while True:
        block = set()
        for _ in range(rng.randint(3, 5)):  # sofas, tables, beds
            w, h = rng.randint(2, 4), rng.randint(2, 3)
            x, y = rng.randint(1, COLS - w - 1), rng.randint(1, ROWS - h - 1)
            block |= {(x + i, y + j) for i in range(w) for j in range(h)}
        for _ in range(rng.randint(4, 8)):  # chair legs, plant pots
            block.add((rng.randint(1, COLS - 2), rng.randint(1, ROWS - 2)))
        block.discard((0, 0))
        seen, q = {(0, 0)}, deque([(0, 0)])
        while q:
            x, y = q.popleft()
            for dx, dy in DIRS:
                n = (x + dx, y + dy)
                if 0 <= n[0] < COLS and 0 <= n[1] < ROWS and n not in block and n not in seen:
                    seen.add(n); q.append(n)
        if len(seen) >= COLS * ROWS * 0.6:
            # cells the robot can't reach count as furniture
            return {(x, y) for x in range(COLS) for y in range(ROWS)} - seen, seen

def free(block, c):
    return 0 <= c[0] < COLS and 0 <= c[1] < ROWS and c not in block

def play(bot, rng, trace=False, battery=BATTERY):
    block, floor = make_room(rng)
    pos, d = (0, 0), 0
    clean = {pos}
    walls = set()      # mapper: cells it bumped into
    vdir = 1           # mower: going down (1) or up (-1)
    turn_back = False  # mower: just stepped a row, now reverse
    path = []
    bumps = 0
    log = [(pos, 0)]
    curve = []
    import math
    ang = rng.uniform(0, math.pi / 2)  # bounce: heading angle; first heading points into the room
    found = False                       # hugger: touched a wall yet
    for step in range(1, battery + 1):
        if bot == "bounce":
            cx, cy = math.cos(ang), math.sin(ang)
            # step along the heading: x or y, in proportion, so it drives straight lines at any angle
            if rng.random() < abs(cx) / (abs(cx) + abs(cy)):
                d = 0 if cx > 0 else 2
            else:
                d = 1 if cy > 0 else 3
        elif bot == "hugger" and found:
            r = (d + 1) % 4
            if free(block, (pos[0] + DIRS[r][0], pos[1] + DIRS[r][1])):
                d = r
        if bot == "mapper":
            if not path or path[0] in walls:
                path = route(pos, clean, walls)
            want = path.pop(0) if path else pos
            d = DIRS.index((want[0] - pos[0], want[1] - pos[1])) if want != pos else d
        nxt = (pos[0] + DIRS[d][0], pos[1] + DIRS[d][1])
        if free(block, nxt):
            pos = nxt
            clean.add(pos)
            if bot == "mower" and turn_back:
                d, turn_back = (2 if d_prev == 0 else 0), False
        else:
            bumps += 1
            walls.add(nxt)
            path = []
            if bot == "bounce":
                ang = rng.uniform(0, 2 * math.pi)
            elif bot == "mower":
                if d in (0, 2):
                    if not free(block, (pos[0], pos[1] + vdir)):
                        vdir = -vdir
                    d_prev, d, turn_back = d, (1 if vdir == 1 else 3), True
                else:  # the row step was blocked
                    d, turn_back = rng.choice([0, 2]), False
            elif bot == "hugger":
                found = True
                d = (d + 3) % 4  # turn left: the wall is now on its right
        if trace: log.append((pos, bumps))
        curve.append(len(clean))
    return {"score": len(clean) / len(floor), "clean": len(clean), "floor": len(floor), "bumps": bumps,
            "block": block, "log": log, "curve": curve}

def route(pos, clean, walls):
    """BFS over cells not known to be walls (inside the room) to the nearest uncleaned one."""
    prev, q = {pos: None}, deque([pos])
    while q:
        c = q.popleft()
        if c not in clean:
            out = []
            while c != pos:
                out.append(c); c = prev[c]
            return out[::-1]
        for dx, dy in DIRS:
            n = (c[0] + dx, c[1] + dy)
            if 0 <= n[0] < COLS and 0 <= n[1] < ROWS and n not in walls and n not in prev:
                prev[n] = c; q.append(n)
    return []

def summary(bot, games, seed):
    return [play(bot, random.Random(seed * 100003 + g)) for g in range(games)]

if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 36
    res = {b: summary(b, games, seed) for b in BOTS}
    fl = sum(r["floor"] for r in res["bounce"]) / games
    print(f"avg floor cells {fl:.1f}, battery {BATTERY}")
    for b, rs in res.items():
        avg = sum(r["score"] for r in rs) / games
        full = sum(r["clean"] == r["floor"] for r in rs)
        bmp = sum(r["bumps"] for r in rs) / games
        at = {k: sum(r["curve"][k - 1] / r["floor"] for r in rs) / games for k in (100, 200, 400)}
        print(f"{b:7s} cleaned {avg*100:5.1f}%  whole room {full:5d}  bumps {bmp:6.1f}  "
              f"at 100/200/400 turns {at[100]*100:4.1f}/{at[200]*100:4.1f}/{at[400]*100:4.1f}%")
    m, bo = res["mower"], res["bounce"]
    print("mower vs bounce: more", sum(a["clean"] > b["clean"] for a, b in zip(m, bo)),
          "less", sum(a["clean"] < b["clean"] for a, b in zip(m, bo)))
    # self-checks: nobody cleans more than the floor, and cleaned cells are all floor
    assert all(r["clean"] <= r["floor"] for rs in res.values() for r in rs)
