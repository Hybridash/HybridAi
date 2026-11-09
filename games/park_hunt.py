"""Park Hunt: an original parking game, made for HybridAi Day 26.

Rules:
  One lane of 40 spots. The door is at spot 0; the car enters at spot 39 and drives toward the door,
  one spot per tick. Spots near the door are usually taken: spot i starts taken with chance
  0.97 - 0.6 * i / 39. While the car drives, other drivers come and go: each tick a taken spot frees
  up with chance 1/150 and a free spot gets taken with chance FILL(i) (higher near the door).
  The car only sees the spot it is passing. If it reaches the door without parking it must drive
  around the block (LOOP = 40 ticks) and enter at spot 39 again.
  Score = ticks driving + 2 ticks per spot walked to the door (walking is slower than driving).
  Lower is better. A hunt that hasn't parked after 2,000 ticks stops and counts as 2,000 + walk 80.

Bots (they only decide: park in this free spot, or keep going):
  first   parks in the first free spot it sees.
  half    ignores free spots until it is past halfway (spot < 20), then takes the first free one.
  close   only parks within 10 spots of the door; otherwise loops.
  front   only parks in the 3 spots by the door ("rock star" spot); otherwise loops.
  random  parks in a free spot with chance 1/2.

usage: python3 games/park_hunt.py [games_per_bot] [seed]
"""
import random, sys

N, LOOP, WALK, CAP = 40, 40, 2, 2000
BOTS = ["first", "half", "close", "front", "random"]

def start_p(i): return 0.97 - 0.6 * i / (N - 1)
def fill_p(i): return 0.02 + 0.08 * (1 - i / (N - 1))

def wants(bot, i, rng):
    if bot == "first": return True
    if bot == "half": return i < N // 2
    if bot == "close": return i < 10
    if bot == "front": return i < 3
    if bot == "random": return rng.random() < 0.5
    raise ValueError(bot)

def play(bot, rng, trace=False):
    taken = [rng.random() < start_p(i) for i in range(N)]
    pos, drive, loops, log = N - 1, 0, 0, []
    while True:
        if trace: log.append((pos, taken[:], loops, drive, None))
        if not taken[pos] and wants(bot, pos, rng):
            score = drive + WALK * pos
            if trace: log.append((pos, taken[:], loops, drive, score))
            return {"score": score, "spot": pos, "drive": drive, "loops": loops, "log": log}
        # world moves one tick
        for i in range(N):
            if taken[i]:
                if rng.random() < 1 / 150: taken[i] = False
            elif rng.random() < fill_p(i): taken[i] = True
        drive += 1
        if pos == 0:
            drive += LOOP - 1; loops += 1; pos = N - 1
            for _ in range(LOOP - 1):   # the lot keeps changing while you circle
                for i in range(N):
                    if taken[i]:
                        if rng.random() < 1 / 150: taken[i] = False
                    elif rng.random() < fill_p(i): taken[i] = True
        else:
            pos -= 1
        if drive >= CAP:
            score = CAP + WALK * N
            if trace: log.append((pos, taken[:], loops, drive, score))
            return {"score": score, "spot": None, "drive": drive, "loops": loops, "log": log}

def summary(bot, games, seed):
    rng = random.Random(seed)
    rs = [play(bot, rng) for _ in range(games)]
    sc = sorted(r["score"] for r in rs)
    parked = [r for r in rs if r["spot"] is not None]
    return {"avg": sum(sc) / games, "median": sc[games // 2], "worst": sc[-1],
            "drive": sum(r["drive"] for r in rs) / games,
            "walk": sum(WALK * r["spot"] for r in parked) / max(1, len(parked)),
            "spot": sum(r["spot"] for r in parked) / max(1, len(parked)),
            "loops": sum(r["loops"] for r in rs) / games,
            "gaveup": games - len(parked),
            "zero_loops": sum(r["loops"] == 0 for r in rs)}

if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 26
    for b in BOTS:
        s = summary(b, games, seed)
        print(f"{b:6s} avg {s['avg']:7.1f} med {s['median']:5d} worst {s['worst']:5d}  drive {s['drive']:6.1f}"
              f"  walk {s['walk']:5.1f} spot {s['spot']:5.1f}  loops {s['loops']:5.2f}  no-loop {s['zero_loops']:4d}  gave up {s['gaveup']}")
