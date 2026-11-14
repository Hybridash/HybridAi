"""Line Pick: an original checkout-line game, made for HybridAi Day 30.

Rules:
  A shop has 4 checkout lanes. Cashiers scan at different speeds (2, 3, 3, 4 items per tick) and
  every customer also takes PAY = 8 ticks to pay. 1 customer in 25 needs a price check (+30 ticks).
  Background shoppers (1 to 30 items) arrive with chance 0.25 per tick (a busy Saturday) and join the lane with the
  fewest people (ties: lowest lane number). After WARM ticks our bot arrives with 15 items and picks
  a lane. Nobody can see cashier speed or price checks; they see people and the items in carts.
  Score = ticks from arriving to walking out. Lower is better. Each game uses one seed for the
  whole shop, so every bot faces the same shoppers on game n (until its own choices change things).

Bots:
  random    picks a random lane.
  people    picks the lane with the fewest people.
  items     picks the lane with the fewest items in carts.
  switcher  picks like 'people', then any tick another lane has fewer people in it than are ahead of it,
            it moves to the back of that lane.
  stay1     always lane 1 (the slowest cashier).

usage: python3 games/line_pick.py [games_per_bot] [seed]
"""
import random, sys

SPEED = [2, 3, 3, 4]
PAY, CHECK_P, CHECK_T, ARRIVE, WARM, MINE, CAP = 8, 1 / 25, 30, 0.25, 300, 15, 3000
BOTS = ["random", "people", "items", "switcher", "stay1"]
L = len(SPEED)

def new_customer(rng, items=None):
    it = items if items is not None else rng.randint(1, 30)
    return {"items": it, "left": it, "pay": PAY + (CHECK_T if rng.random() < CHECK_P else 0), "me": False}

def choose(bot, lanes, rng):
    if bot == "random": return rng.randrange(L)
    if bot in ("people", "switcher"): return min(range(L), key=lambda j: (len(lanes[j]), j))
    if bot == "items": return min(range(L), key=lambda j: (sum(c["left"] for c in lanes[j]), j))
    if bot == "stay1": return 0
    raise ValueError(bot)

def tick(lanes):
    for j, lane in enumerate(lanes):
        if not lane: continue
        c = lane[0]
        if c["left"] > 0: c["left"] = max(0, c["left"] - SPEED[j])
        elif c["pay"] > 0: c["pay"] -= 1
        if c["left"] == 0 and c["pay"] == 0: lane.pop(0)

def play(bot, rng, trace=False):
    lanes = [[] for _ in range(L)]
    def arrivals():
        if rng.random() < ARRIVE:
            j = min(range(L), key=lambda k: (len(lanes[k]), k))
            lanes[j].append(new_customer(rng))
    for _ in range(WARM):
        arrivals(); tick(lanes)
    me = new_customer(rng, MINE); me["me"] = True
    pick = choose(bot, lanes, rng)
    lanes[pick].append(me)
    t, switches, log = 0, 0, []
    def snap(): return [[(c["left"], c["me"]) for c in lane] for lane in lanes]
    while True:
        if trace: log.append((t, snap(), switches))
        if bot == "switcher":
            cur = next(j for j in range(L) if me in lanes[j])
            ahead = lanes[cur].index(me)
            if ahead > 0:
                best = min(range(L), key=lambda j: (len(lanes[j]), j))
                if best != cur and len(lanes[best]) < ahead:
                    lanes[cur].remove(me); lanes[best].append(me); switches += 1
        tick(lanes)
        arrivals()
        t += 1
        if not any(me in lane for lane in lanes) or t >= CAP:
            if trace: log.append((t, snap(), switches))
            return {"score": t, "lane": pick, "switches": switches, "log": log}

def summary(bot, games, seed):
    rs = [play(bot, random.Random(seed * 100003 + g)) for g in range(games)]
    sc = sorted(r["score"] for r in rs)
    return {"avg": sum(sc) / games, "median": sc[games // 2], "worst": sc[-1], "rs": rs,
            "switches": sum(r["switches"] for r in rs) / games,
            "lane_share": [sum(r["lane"] == j for r in rs) / games for j in range(L)]}

if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    res = {b: summary(b, games, seed) for b in BOTS}
    for b, s in res.items():
        print(f"{b:9s} avg {s['avg']:6.1f} med {s['median']:4d} worst {s['worst']:5d} switches {s['switches']:.2f} "
              f"lanes {' '.join(f'{x:.2f}' for x in s['lane_share'])}")
    # head to head vs 'people' on the same seeds
    base = res["people"]["rs"]
    for b in BOTS:
        if b == "people": continue
        w = sum(r["score"] < p["score"] for r, p in zip(res[b]["rs"], base))
        l = sum(r["score"] > p["score"] for r, p in zip(res[b]["rs"], base))
        print(f"{b:9s} vs people: faster {w}, slower {l}, same {games - w - l}")
