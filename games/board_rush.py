"""Board Rush: an original plane-boarding game, made for HybridAi Day 40.

Rules:
  A plane with ROWS rows of 6 seats (A B C | aisle | D E F), one passenger per seat, one door at the front.
  Each game second, passengers in the aisle step one row toward the back if the spot ahead is free
  (people further back move first). A passenger who reaches their row stops in the aisle: if they have a
  bag (chance BAG) they stow it for BAG_MIN..BAG_MAX seconds, plus SHUFFLE seconds for every seated
  passenger they have to squeeze past (someone already in the aisle or middle seat on their side).
  Then they sit and the aisle spot frees up. The next passenger in line steps through the door when the
  first aisle spot is free. The game ends when everyone is seated. Each game uses one seed, so every bot
  gets the same passengers and the same bags; only the boarding order changes.

Bots (boarding orders):
  front    front rows first (4 groups, random inside each group).
  back     back rows first (4 groups, random inside each group), what many airlines call back-to-front.
  random   everyone in a random order (open seating with assigned seats).
  window   window seats first, then middle, then aisle (random inside each group).
  steffen  window, then middle, then aisle; inside each, every other row from the back, one side at a time.

usage: python3 games/board_rush.py [games_per_bot] [seed]
"""
import random, sys

ROWS, BAG, BAG_MIN, BAG_MAX, SHUFFLE = 20, 0.8, 4, 10, 3
BOTS = ["front", "back", "random", "window", "steffen"]
SEATS = "ABCDEF"
DEPTH = {"A": 3, "F": 3, "B": 2, "E": 2, "C": 1, "D": 1}  # 1 = aisle seat

def passengers(rng):
    """Same passengers (and bags) for every bot in a game."""
    out = []
    for r in range(ROWS):
        for s in SEATS:
            stow = rng.randint(BAG_MIN, BAG_MAX) if rng.random() < BAG else 1
            out.append({"row": r, "seat": s, "stow": stow})
    return out

def order(bot, ps, rng):
    ps = list(ps)
    rng.shuffle(ps)
    if bot == "random":
        return ps
    if bot in ("front", "back"):
        g = lambda p: p["row"] * 4 // ROWS
        return sorted(ps, key=(lambda p: g(p)) if bot == "front" else (lambda p: -g(p)))
    if bot == "window":
        return sorted(ps, key=lambda p: -DEPTH[p["seat"]])
    # steffen: depth (window first), then row parity block, then side, then back to front
    return sorted(ps, key=lambda p: (-DEPTH[p["seat"]], (ROWS - 1 - p["row"]) % 2, p["seat"] in "DEF", -p["row"]))

def play(bot, rng, trace=False):
    ps = passengers(rng)
    line = order(bot, ps, random.Random(rng.random()))
    aisle = [None] * ROWS           # passenger index standing in each aisle spot
    left = {}                       # passenger index -> seconds left at their row
    seated = set()
    q, t, frames = 0, 0, []
    taken = {}                      # (row, seat) -> True once seated
    while len(seated) < len(line):
        t += 1
        for r in range(ROWS - 1, -1, -1):
            i = aisle[r]
            if i is None:
                continue
            p = line[i]
            if p["row"] == r:
                if i not in left:
                    side = "ABC" if p["seat"] in "ABC" else "DEF"
                    block = sum(1 for s in side if DEPTH[s] < DEPTH[p["seat"]] and taken.get((r, s)))
                    left[i] = p["stow"] + SHUFFLE * block
                left[i] -= 1
                if left[i] <= 0:
                    aisle[r] = None; seated.add(i); taken[(r, p["seat"])] = True
            elif aisle[r + 1] is None:
                aisle[r + 1], aisle[r] = i, None
        if aisle[0] is None and q < len(line):
            aisle[0] = q; q += 1
        if trace:
            frames.append((t, list(aisle), {(line[i]["row"], line[i]["seat"]) for i in seated}, len(line) - q))
        assert t < 100000
    return {"time": t, "frames": frames, "line": line, "n": len(line)}

def summary(bot, games, seed):
    return [play(bot, random.Random(seed * 100003 + g))["time"] for g in range(games)]

if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    res = {b: summary(b, games, seed) for b in BOTS}
    for b, ts in res.items():
        print(f"{b:8s} avg {sum(ts)/games/60:5.2f} min  best {min(ts)/60:5.2f}  worst {max(ts)/60:5.2f}")
    for a, b in (("random", "back"), ("window", "random"), ("steffen", "window"), ("back", "front")):
        print(f"{a} faster than {b} in {sum(x < y for x, y in zip(res[a], res[b]))} of {games}")
    # self-check: everyone seated exactly once, all seats filled
    g = play("random", random.Random(1), trace=True)
    assert len(g["frames"][-1][2]) == ROWS * 6
