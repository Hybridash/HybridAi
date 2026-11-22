"""Pizza Rush: an original delivery game, made for HybridAi Day 38.

Rules:
  A town of SIZE x SIZE blocks with the pizza shop in the middle. During a SHIFT-minute evening, orders
  come in at random houses (each minute an order arrives with chance RATE). One driver moves one block
  per minute (city blocks: no diagonals). At the shop it can load up to BAG pizzas from the orders that
  are waiting, drives them out in the order the bot picks, then drives back to the shop. Every order must
  be delivered; the game ends when the last one is. Wait = minutes from order to doorstep. A pizza that
  waits more than COLD minutes arrives cold. Each evening uses one seed, so every bot gets the same orders.

Bots:
  oldest    loads the oldest waiting orders and delivers them oldest first.
  nearest   loads the orders closest to the shop and always drives to the closest house next.
  single    one pizza per trip, oldest order first.
  planner   loads the oldest waiting orders, then tries every drop order and drives the shortest route.

usage: python3 games/pizza_rush.py [evenings_per_bot] [seed]
"""
import random, sys
from itertools import permutations

SIZE, SHOP, SHIFT, RATE, BAG, COLD = 9, (4, 4), 240, 0.15, 3, 30
BOTS = ["oldest", "nearest", "single", "planner"]

def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def orders(rng):
    out = []
    for m in range(SHIFT):
        if rng.random() < RATE:
            while True:
                h = (rng.randrange(SIZE), rng.randrange(SIZE))
                if h != SHOP:
                    break
            out.append({"id": len(out), "t": m, "house": h})
    return out

def path(a, b):
    """Block-by-block cells from a to b (x first, then y), not including a."""
    out, (x, y) = [], a
    while x != b[0]:
        x += 1 if b[0] > x else -1; out.append((x, y))
    while y != b[1]:
        y += 1 if b[1] > y else -1; out.append((x, y))
    return out

def length(start, stops):
    tot, p = 0, start
    for s in stops:
        tot += dist(p, s["house"]); p = s["house"]
    return tot + dist(p, SHOP)

def pick(bot, waiting):
    if bot == "single":
        return waiting[:1]
    if bot == "oldest":
        return waiting[:BAG]
    if bot == "planner":
        load = waiting[:BAG]
        return list(min(permutations(load), key=lambda p: length(SHOP, p)))
    # nearest: closest to the shop, then always the closest house next
    load = sorted(waiting, key=lambda o: (dist(SHOP, o["house"]), o["t"]))[:BAG]
    route, p = [], SHOP
    while load:
        nx = min(load, key=lambda o: (dist(p, o["house"]), o["t"]))
        route.append(nx); load.remove(nx); p = nx["house"]
    return route

def play(bot, rng, trace=False):
    od = orders(rng)
    t, pos, i = 0, SHOP, 0
    waiting, done, frames = [], [], []
    def tick(p, bag):
        nonlocal t, i
        t += 1
        while i < len(od) and od[i]["t"] < t:
            waiting.append(od[i]); i += 1
        if trace:
            frames.append((t, p, [o["id"] for o in waiting], [o["id"] for o in bag], len(done)))
    while i < len(od) or waiting:
        if not waiting:
            tick(pos, []); continue
        route = pick(bot, waiting)
        for o in route:
            waiting.remove(o)
        bag = list(route)
        for o in route:
            for c in path(pos, o["house"]):
                pos = c; tick(pos, bag)
            o["wait"] = t - o["t"]; done.append(o); bag.remove(o)
        for c in path(pos, SHOP):
            pos = c; tick(pos, bag)
    waits = [o["wait"] for o in done]
    return {"orders": len(od), "avg": sum(waits) / len(waits), "max": max(waits),
            "cold": sum(w > COLD for w in waits), "end": t, "od": od, "frames": frames,
            "worst": max(done, key=lambda o: o["wait"])}

def summary(bot, games, seed):
    return [play(bot, random.Random(seed * 100003 + g)) for g in range(games)]

if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 38
    res = {b: summary(b, games, seed) for b in BOTS}
    print(f"avg orders per evening {sum(r['orders'] for r in res['oldest']) / games:.1f}")
    for b, rs in res.items():
        avg = sum(r["avg"] * r["orders"] for r in rs) / sum(r["orders"] for r in rs)
        cold = sum(r["cold"] for r in rs) / sum(r["orders"] for r in rs)
        mx = max(r["max"] for r in rs)
        amx = sum(r["max"] for r in rs) / games
        end = sum(r["end"] for r in rs) / games
        print(f"{b:8s} avg wait {avg:5.1f} min  cold {cold*100:5.1f}%  worst wait per evening {amx:6.1f}  "
              f"worst ever {mx:4d}  last drop min {end:6.1f}")
    for a, b in (("nearest", "planner"), ("nearest", "oldest")):
        x, y = res[a], res[b]
        print(f"{a} vs {b}: lower avg in {sum(p['avg'] < q['avg'] for p, q in zip(x, y))}, "
              f"higher worst in {sum(p['max'] > q['max'] for p, q in zip(x, y))}")
    # self-checks: every order delivered exactly once, waits are never negative
    for rs in res.values():
        for r in rs:
            assert all("wait" in o and o["wait"] >= 0 for o in r["od"])
