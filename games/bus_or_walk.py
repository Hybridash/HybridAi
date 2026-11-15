"""Bus or Walk: an original commute game, made for HybridAi Day 32.

Rules:
  A straight road. Home is a bus stop at block 0, work is at block END = 32. There is a stop every
  GAP = 4 blocks. Buses leave the depot at block -DEPOT and drive 1 block per tick, stopping DWELL
  ticks at every stop. A new bus leaves the depot with chance 1/MEAN each tick, so buses come
  every MEAN ticks on average but at random (sometimes two close together, sometimes a long gap).
  Our bot walks 1 block every WALK ticks. It can board a bus only while standing at a stop and the
  bus is stopped there. Score = ticks from leaving home to reaching work. Lower is better.
  Each game uses one seed, so every bot faces the same buses on game n.

Bots:
  wait     waits at home for the bus, however long it takes.
  walk     walks the whole way.
  give10   waits up to 10 ticks, then walks the whole way.
  give30   waits up to 30 ticks, then walks the whole way.
  hopper   walks stop to stop; at each stop it looks back down the road and waits only if a bus
           is within SIGHT blocks; otherwise it keeps walking (a bus can pass it between stops).

usage: python3 games/bus_or_walk.py [games_per_bot] [seed]
"""
import random, sys

END, GAP, DEPOT, DWELL, MEAN, WALK, SIGHT, WARM, CAP = 32, 4, 12, 2, 30, 3, 10, 200, 3000
BOTS = ["wait", "walk", "give10", "give30", "hopper"]
PATIENCE = {"wait": CAP, "walk": 0, "give10": 10, "give30": 30}

def step_buses(buses, rng):
    if rng.random() < 1 / MEAN: buses.append({"pos": -DEPOT, "dwell": 0})
    for b in buses:
        if b["dwell"] > 0: b["dwell"] -= 1
        else:
            b["pos"] += 1
            if 0 <= b["pos"] < END and b["pos"] % GAP == 0: b["dwell"] = DWELL
    buses[:] = [b for b in buses if b["pos"] <= END]

def play(bot, rng, trace=False):
    buses = []
    for _ in range(WARM): step_buses(buses, rng)
    me = {"pos": 0, "on": None, "walked": 0, "waited": 0, "mode": "stop"}  # mode: stop | walking | bus
    passed, t, log, gave_up = 0, 0, [], False
    def snap(): return (t, [b["pos"] for b in buses], me["pos"], me["mode"], passed)
    while True:
        if trace: log.append(snap())
        if me["mode"] == "bus":
            if me["on"]["pos"] >= END: break
        elif me["pos"] >= END: break
        # decide
        if me["mode"] == "stop" and bot == "walk": me["mode"] = "walking"
        if me["mode"] == "stop":
            here = [b for b in buses if b["pos"] == me["pos"] and b["dwell"] > 0]
            if here:
                me["mode"], me["on"] = "bus", here[0]
            elif bot == "hopper":
                if not any(me["pos"] - SIGHT <= b["pos"] < me["pos"] for b in buses):
                    me["mode"] = "walking"
            elif me["waited"] >= PATIENCE[bot]:
                me["mode"], gave_up = "walking", True
        before = {id(b): b["pos"] for b in buses}
        step_buses(buses, rng)
        t += 1
        if me["mode"] == "stop": me["waited"] += 1
        elif me["mode"] == "walking":
            me["walked"] += 1
            if me["walked"] % WALK == 0:
                me["pos"] += 1
                if bot == "hopper" and me["pos"] % GAP == 0 and me["pos"] < END: me["mode"] = "stop"
            # a bus went past me while I was walking
            passed += sum(1 for b in buses if id(b) in before and before[id(b)] < me["pos"] <= b["pos"] and before[id(b)] >= 0)
        elif me["mode"] == "bus":
            me["pos"] = me["on"]["pos"]
        if t >= CAP: break
    if trace: log.append(snap())
    return {"score": t, "passed": passed, "rode": me["on"] is not None, "waited": me["waited"],
            "gave_up": gave_up, "log": log}

def summary(bot, games, seed):
    rs = [play(bot, random.Random(seed * 100003 + g)) for g in range(games)]
    sc = sorted(r["score"] for r in rs)
    return {"avg": sum(sc) / games, "median": sc[games // 2], "worst": sc[-1], "rs": rs,
            "rode": sum(r["rode"] for r in rs) / games, "passed": sum(r["passed"] > 0 for r in rs),
            "gave_up": sum(r["gave_up"] for r in rs),
            "passed_after_giving_up": sum(r["gave_up"] and r["passed"] > 0 for r in rs)}

if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 32
    res = {b: summary(b, games, seed) for b in BOTS}
    for b, s in res.items():
        print(f"{b:7s} avg {s['avg']:6.1f} med {s['median']:4d} worst {s['worst']:4d} rode {s['rode']:.3f} "
              f"bus passed me in {s['passed']} games, gave up {s['gave_up']} (passed after {s['passed_after_giving_up']})")
    w = res["wait"]["rs"]
    waits = sorted(r["waited"] for r in w)
    print(f"wait bot: avg wait at home {sum(waits) / games:.1f}, median {waits[games // 2]}, worst {waits[-1]}, "
          f"waited 60+ in {sum(x >= 60 for x in waits)}")
    for b in BOTS:
        if b == "wait": continue
        f = sum(r["score"] < p["score"] for r, p in zip(res[b]["rs"], w))
        sl = sum(r["score"] > p["score"] for r, p in zip(res[b]["rs"], w))
        print(f"{b:7s} vs wait: faster {f}, slower {sl}, same {games - f - sl}")
    # self-check: walking the whole way always takes END * WALK ticks
    assert all(r["score"] == END * WALK for r in res["walk"]["rs"])
