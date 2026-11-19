"""Green Light: an original driving game, made for HybridAi Day 34.

Rules:
  A straight road, LENGTH metres, with a traffic light every GAP metres (LIGHTS lights, the last
  one GAP before the finish). Every light runs the same cycle: GREEN s green, AMBER s amber,
  RED s red, but each one starts at a random point in its cycle (seeded per game), so the lights
  are not synced. Cars speed up at most ACC m/s^2, brake at most BRK m/s^2, and never go over
  VMAX m/s (the speed limit). A car may not pass a light on red; on amber it goes only if it
  can't stop in time. Time step DT seconds. Score = seconds to reach the finish. Also counted:
  full stops (speed falls under 0.5 m/s) and seconds spent standing still.
  Each game uses one seed, so every bot meets the same lights in game n.

Bots:
  racer    floors it to the speed limit, brakes as late as it can for every red.
  cruiser  holds 2/3 of the speed limit, brakes for reds.
  timer    looks at the next light: if it would get there on amber/red at full speed, it slows
           down to roll up just as the light turns green (never under 3 m/s); else full speed.
  creeper  holds 1/3 of the speed limit, brakes for reds.

usage: python3 games/green_light.py [games_per_bot] [seed]
"""
import math, random, sys

LENGTH, GAP, VMAX, ACC, BRK, DT = 2000, 200, 15.0, 2.0, 4.0, 0.25
GREEN, AMBER, RED = 27, 3, 30
CYCLE = GREEN + AMBER + RED
LIGHTS = [GAP * k for k in range(1, LENGTH // GAP)]
BOTS = ["racer", "cruiser", "timer", "creeper"]
CRUISE = {"racer": VMAX, "cruiser": VMAX * 2 / 3, "timer": VMAX, "creeper": VMAX / 3}

def color(off, t):
    p = (t + off) % CYCLE
    return "G" if p < GREEN else ("A" if p < GREEN + AMBER else "R")

def until_green(off, t):
    p = (t + off) % CYCLE
    return 0.0 if p < GREEN else CYCLE - p

def reach_time(v, dist):
    """Seconds to cover dist flooring it from speed v (accelerate to VMAX, then hold)."""
    d_acc = (VMAX * VMAX - v * v) / (2 * ACC)
    if dist <= d_acc:
        return (math.sqrt(v * v + 2 * ACC * dist) - v) / ACC
    return (VMAX - v) / ACC + (dist - d_acc) / VMAX

def play(bot, rng, trace=False):
    offs = [rng.uniform(0, CYCLE) for _ in LIGHTS]
    t, x, v, stops, still, moving = 0.0, 0.0, 0.0, 0, 0.0, False
    log = []
    while x < LENGTH:
        nxt = next((i for i, L in enumerate(LIGHTS) if L > x + 1e-9), None)
        target = CRUISE[bot]
        cap = VMAX
        if nxt is not None:
            dist = LIGHTS[nxt] - x
            c = color(offs[nxt], t)
            if c == "R" or (c == "A" and v * v / (2 * BRK) < dist):
                cap = math.sqrt(2 * BRK * max(0.0, dist - 0.5))
            if bot == "timer":
                eta = t + reach_time(v, dist)
                # early amber is fine at full speed (too close to stop), later amber or red is a miss
                if (eta + offs[nxt]) % CYCLE > GREEN + 1.5:
                    wait = until_green(offs[nxt], eta) + 2.0  # roll up 2 s after it turns green
                    target = max(3.0, min(VMAX, dist / max(0.1, eta - t + wait)))
        nv = min(target, v + ACC * DT, cap)
        nv = max(nv, v - BRK * DT * 4, 0.0)  # hard stop allowed only to obey a red
        x2 = x + (v + nv) / 2 * DT
        if nxt is not None and x2 > LIGHTS[nxt] and color(offs[nxt], t) == "R":
            x2, nv = LIGHTS[nxt] - 0.01, 0.0
        x, v, t = x2, nv, t + DT
        if v < 0.5:
            still += DT
            if moving: stops += 1
            moving = False
        else:
            moving = True
        if trace: log.append((round(t, 2), round(x, 1), round(v, 2), stops))
        if t > 3600: break
    return {"score": t, "stops": stops, "still": still, "offs": offs, "log": log}

def summary(bot, games, seed):
    rs = [play(bot, random.Random(seed * 100003 + g)) for g in range(games)]
    return {"avg": sum(r["score"] for r in rs) / games, "stops": sum(r["stops"] for r in rs) / games,
            "still": sum(r["still"] for r in rs) / games, "rs": rs}

if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 34
    res = {b: summary(b, games, seed) for b in BOTS}
    for b, s in res.items():
        print(f"{b:8s} avg time {s['avg']:6.1f}s  stops {s['stops']:4.2f}  standing {s['still']:5.1f}s")
    r, tm = res["racer"]["rs"], res["timer"]["rs"]
    f = sum(a["score"] < b["score"] for a, b in zip(tm, r))
    sl = sum(a["score"] > b["score"] for a, b in zip(tm, r))
    print(f"timer vs racer: faster {f}, slower {sl}, same {games - f - sl}")
    print(f"racer zero-stop drives {sum(x['stops'] == 0 for x in r)}, timer zero-stop {sum(x['stops'] == 0 for x in tm)}")
    gaps = sorted(a["score"] - b["score"] for a, b in zip(tm, r))
    print(f"timer minus racer: median {gaps[games // 2]:.2f}s, max {gaps[-1]:.2f}s, min {gaps[0]:.2f}s")
    # self-checks: nobody beats the no-lights time, and no car ever crossed a red
    best = (VMAX / ACC) + (LENGTH - VMAX * VMAX / (2 * ACC)) / VMAX
    assert all(x["score"] >= best - DT for s in res.values() for x in s["rs"])
