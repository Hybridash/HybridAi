"""Lane Drop: an original merge game, made for HybridAi Day 42.

Rules:
  A two-lane road, cells of 7.5 m (one car each). The left lane ends at cell DROP (a work zone); the right
  lane goes on to the exit at cell END. Each game second every car speeds up by 1 (max VMAX cells/s),
  slows to the free cells ahead, sometimes brakes by 1 for no reason (chance SLOW), then moves
  (a simple Nagel-Schreckenberg traffic model). During the rush (RUSH seconds) cars arrive at the start of
  each lane with chance ARRIVE per second; a car that can't get on yet waits at the entrance, and that
  wait counts in its trip time. A car in the left lane must change into the right lane before DROP.
  It may change into an empty cell beside it if the car behind in the right lane is far enough back
  not to hit it (gap > that car's speed), or, in the zipper merge zone (last ZONE cells), if the
  right-lane driver lets it in (the cell beside it is free; the car behind brakes).
  Every bot drives every car on the road, and each game uses one seed, so every bot gets the same
  arrivals and the same random braking chances per car and second.

Bots (merge rules, used by every driver):
  early    change lanes as soon as there is a safe gap after the "lane ends" sign (cell SIGN).
  random   each driver picks a random spot between the sign and the zone and changes from there on (safe gap only).
  zipper   stay in your lane to the zone, then take turns: right-lane drivers let one car in.
  rude     like zipper, but right-lane drivers never let anyone in: safe gaps only, even at the end.

usage: python3 games/lane_drop.py [games_per_bot] [seed]
"""
import random, sys

DROP, END, VMAX, SLOW, ARRIVE, RUSH, ZONE = 200, 230, 4, 0.15, 0.32, 600, 4
CELL = 7.5
SIGN = 40                            # "left lane ends" sign: 1.2 km before the work zone
BOTS = ["early", "random", "zipper", "rude"]

def arrivals(rng):
    return [(t, ln) for t in range(RUSH) for ln in (0, 1) if rng.random() < ARRIVE]

def play(bot, rng, trace=False):
    arr = arrivals(rng)
    bseed = rng.random()             # same braking draws for every bot (each car has its own stream)
    pick = random.Random(rng.random())
    cars = []                        # dict: id, lane (0 left/1 right), x, v, t0, go (cell to start merging)
    wait = {0: [], 1: []}            # entrance queues
    done, trips, frames, ai, t, jam = 0, [], [], 0, 0, 0
    merge_wait = {}                  # id -> seconds stopped at the end of the left lane
    while done < len(arr):
        while ai < len(arr) and arr[ai][0] == t:
            i = ai
            wait[arr[ai][1]].append({"id": i, "lane": arr[ai][1], "x": 0, "v": 2, "t0": t,
                                     "go": pick.randint(SIGN, DROP - ZONE - 1) if bot == "random" else 0,
                                     "rng": random.Random(bseed + i)})
            ai += 1
        occ = {(c["lane"], c["x"]): c for c in cars}
        for ln in (0, 1):
            if wait[ln] and (ln, 0) not in occ:
                c = wait[ln].pop(0); cars.append(c); occ[(ln, 0)] = c
                c["v"] = 0 if (ln, 1) in occ else 1
        # lane changes, front to back
        for c in sorted([c for c in cars if c["lane"] == 0], key=lambda c: -c["x"]):
            x = c["x"]
            start = {"early": SIGN, "random": c["go"], "zipper": DROP - ZONE, "rude": DROP - ZONE}[bot]
            if x < start or (1, x) in occ:
                continue
            back = next((occ[(1, b)] for b in range(x - 1, max(-1, x - VMAX - 2), -1) if (1, b) in occ), None)
            safe = back is None or x - back["x"] > back["v"]
            letin = bot == "zipper" and x >= DROP - ZONE and (back is None or not back.get("let"))
            if safe or letin:
                del occ[(0, x)]; c["lane"] = 1; occ[(1, x)] = c
                if back is not None and not safe:
                    back["v"] = min(back["v"], max(0, x - back["x"] - 1)); back["let"] = True
        for c in cars:
            if c["lane"] == 1 and c["x"] > DROP:
                c["let"] = False      # a driver lets one car in, then the next one gets a turn
        # move, front to back in each lane
        moved = []
        for ln in (0, 1):
            ahead = END + VMAX + 1 if ln == 1 else DROP
            for c in sorted([c for c in cars if c["lane"] == ln], key=lambda c: -c["x"]):
                v = min(c["v"] + 1, VMAX, ahead - c["x"] - 1)
                if c["rng"].random() < SLOW and v > 0:
                    v -= 1
                ahead = c["x"]                # parallel update: the car behind sees this car's old cell
                c["v"] = max(0, v); c["x"] += c["v"]
                if ln == 0 and c["x"] == DROP - 1 and c["v"] == 0:
                    merge_wait[c["id"]] = merge_wait.get(c["id"], 0) + 1
                if c["x"] >= END:
                    trips.append(t + 1 - c["t0"]); done += 1
                else:
                    moved.append(c)
        cars = moved
        q = 0                         # jam = the longest packed line of slow cars, in cells (+ cars waiting to get on)
        for ln in (0, 1):
            xs = sorted(((c["x"], c["v"]) for c in cars if c["lane"] == ln), reverse=True)
            k = 0
            while k < len(xs):
                if xs[k][1] > 2:
                    k += 1; continue
                front = back = xs[k][0]; k += 1
                while k < len(xs) and back - xs[k][0] <= 3 and xs[k][1] <= 2:
                    back = xs[k][0]; k += 1
                q = max(q, front - back + 1 + (len(wait[ln]) if back <= 2 else 0))
        jam = max(jam, q)
        if trace:
            frames.append((t, [(c["lane"], c["x"], c["v"]) for c in cars], done, q))
        t += 1
        assert t < 20000, "stuck"
    return {"time": t, "trips": trips, "n": len(arr), "jam": jam, "frames": frames,
            "worst_merge": max(merge_wait.values()) if merge_wait else 0}

def summary(bot, games, seed):
    return [play(bot, random.Random(seed * 100003 + g)) for g in range(games)]

if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    res = {b: summary(b, games, seed) for b in BOTS}
    for b, gs in res.items():
        trip = sum(sum(g["trips"]) / g["n"] for g in gs) / games
        print(f"{b:7s} avg trip {trip/60:5.2f} min  jam avg {sum(g['jam'] for g in gs)/games*CELL:6.0f} m  "
              f"clear {sum(g['time'] for g in gs)/games/60:5.2f} min  worst wait {max(g['worst_merge'] for g in gs)} s")
    for a, b in (("zipper", "early"), ("zipper", "rude"), ("early", "random")):
        print(f"{a} shorter jam than {b} in {sum(x['jam'] < y['jam'] for x, y in zip(res[a], res[b]))} of {games}")
    # self-check: every car finishes exactly once
    g = play("zipper", random.Random(1), trace=True)
    assert len(g["trips"]) == g["n"]
