"""Lift Rush: an original one-elevator game, made for HybridAi Day 24.

Rules:
  A 10-floor building (floors 0-9), one elevator holding up to 6 people. Each tick a new person
  shows up with chance RATE: half start in the lobby (floor 0) going up, the rest start on a
  random floor going to a different random floor. Each tick the elevator does one thing:
  if anyone inside wants this floor, or anyone waiting here fits, the doors open (everyone for
  this floor gets off, then waiting people get on until it's full); otherwise it moves one floor
  the way the bot says (or waits). A person's time = ticks from showing up to getting off.
  A game is 1,000 ticks; people still unfinished at the end count with their time so far.

Bots (they only choose which way to go; the door rule is the same for all):
  random   picks a random floor, goes there, picks another.
  nearest  goes to the closest floor where someone waits or wants off.
  sweep    keeps going the same way while there is any call or drop-off ahead, then turns
           around (the classic elevator algorithm).
  oldest   goes to the floor of whoever has waited longest (riders first, oldest first).
  lobby    like nearest, but when nobody needs it, it goes back down to the lobby and waits.
  nearest2 (the fix, added after the first run) like nearest, but when it's full it ignores
           people waiting and only heads for riders' floors.

usage: python3 games/lift_rush.py [games_per_bot] [seed] [rate]
"""
import random, sys

FLOORS, CAP, TICKS, RATE = 10, 6, 1000, 0.25
BOTS = ["random", "nearest", "sweep", "oldest", "lobby", "nearest2"]

def new_person(rng, t):
    if rng.random() < 0.5: a, b = 0, rng.randint(1, FLOORS - 1)
    else:
        a = rng.randrange(FLOORS); b = rng.randrange(FLOORS - 1); b += b >= a
    return {"from": a, "to": b, "t0": t}

def choose(bot, floor, dirn, waiting, riders, state, rng):
    """returns -1, 0 or +1"""
    full = len(riders) >= CAP and bot == "nearest2"
    calls = (set() if full else {p["from"] for w in waiting for p in w}) | {p["to"] for p in riders}
    if bot == "random":
        if state.get("goal") in (None, floor): state["goal"] = rng.randrange(FLOORS)
        g = state["goal"]
        return (g > floor) - (g < floor)
    if bot in ("nearest", "lobby", "nearest2"):
        if not calls: return -1 if (bot == "lobby" and floor > 0) else 0
        g = min(calls, key=lambda f: (abs(f - floor), f))
        return (g > floor) - (g < floor)
    if bot == "sweep":
        if not calls: return 0
        if dirn == 0: dirn = 1
        ahead = [f for f in calls if (f - floor) * dirn > 0]
        return dirn if ahead else -dirn
    if bot == "oldest":
        pool = riders if riders else [p for w in waiting for p in w]
        if not pool: return 0
        g = min(pool, key=lambda p: p["t0"])
        g = g["to"] if riders else g["from"]
        return (g > floor) - (g < floor)
    raise ValueError(bot)

def play(bot, rng, rate=RATE, ticks=TICKS, trace=False):
    waiting = [[] for _ in range(FLOORS)]
    riders, done, floor, dirn, state, log = [], [], 0, 0, {}, []
    for t in range(ticks):
        if rng.random() < rate:
            p = new_person(rng, t); waiting[p["from"]].append(p)
        off = [p for p in riders if p["to"] == floor]
        if off or (waiting[floor] and len(riders) < CAP):
            for p in off: p["t1"] = t; done.append(p)
            riders = [p for p in riders if p["to"] != floor]
            while waiting[floor] and len(riders) < CAP: riders.append(waiting[floor].pop(0)); riders[-1]["ton"] = t
            act = "door"
        else:
            m = choose(bot, floor, dirn, waiting, riders, state, rng)
            floor = max(0, min(FLOORS - 1, floor + m))
            if m: dirn = m
            act = m
        if trace:
            log.append((floor, act, len(riders), [len(w) for w in waiting], len(done),
                        [t - p["t0"] for w in waiting for p in w]))
    times = [p["t1"] - p["t0"] for p in done]
    left = [ticks - p["t0"] for w in waiting for p in w] + [ticks - p["t0"] for p in riders]
    return {"times": times, "left": left, "log": log, "done": done}

def summary(bot, games, seed, rate=RATE):
    rng = random.Random(seed)
    allt, worst, unfinished, served = [], [], 0, 0
    for _ in range(games):
        r = play(bot, rng, rate)
        ts = r["times"] + r["left"]
        allt += ts; worst.append(max(ts)); unfinished += len(r["left"]); served += len(r["times"])
    allt.sort()
    return {"avg": sum(allt) / len(allt), "p95": allt[int(0.95 * len(allt))], "worst": max(worst),
            "worst_avg": sum(worst) / len(worst), "unfinished": unfinished / games, "served": served / games}

if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    rate = float(sys.argv[3]) if len(sys.argv) > 3 else RATE
    for b in BOTS:
        s = summary(b, games, seed, rate)
        print(f"{b:8s} avg {s['avg']:7.1f}  p95 {s['p95']:5d}  worst-per-game avg {s['worst_avg']:7.1f}"
              f"  worst {s['worst']:5d}  served {s['served']:6.1f}  stuck at end {s['unfinished']:5.1f}")
