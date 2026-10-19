"""Gap Runner: a tiny original game, made for HybridAi Day 6.

A dot sits on the left. Walls slide in from the right, each with one gap.
Every tick the dot can move up, move down, or stay. Touch a wall and it's over.
Score = walls passed.

usage: python3 games/gap_runner.py [games_per_bot] [seed]
"""
import random, sys, json

FIELD = 100.0      # field height
SPEED = 2.0        # max dot movement per tick
SPACING = 30       # ticks between walls
GAP = 20.0         # gap height
R = 2.0            # dot radius
MAX_WALLS = 1000   # a game stops here even if the bot never dies

def new_gap(rng):
    return rng.uniform(GAP / 2 + 5, FIELD - GAP / 2 - 5)

def bot_statue(y, gaps, rng): return 0
def bot_random(y, gaps, rng): return rng.choice((-1, 0, 1))
def bot_chaser(y, gaps, rng):
    tgt = gaps[0]
    if abs(tgt - y) < SPEED / 2: return 0
    return 1 if tgt > y else -1

def bot_planner(y, gaps, rng):
    # like chaser, but it also looks at the NEXT gap and slips through
    # the current gap on the side closest to it
    lean = GAP / 2 - R - SPEED
    tgt = gaps[0] + max(-lean, min(lean, gaps[1] - gaps[0]))
    if abs(tgt - y) < SPEED / 2: return 0
    return 1 if tgt > y else -1

BOTS = {"statue": bot_statue, "random": bot_random, "chaser": bot_chaser, "planner": bot_planner}

def play(bot, rng, trace=False):
    """Returns (score, frames). frames = [(y, ticks_to_wall, gap_center, next_gap, score)] if trace."""
    y = FIELD / 2
    gaps = [new_gap(rng), new_gap(rng)]
    t_wall = SPACING
    score, frames = 0, []
    while score < MAX_WALLS:
        a = BOTS[bot](y, gaps, rng)
        y = min(FIELD - R, max(R, y + a * SPEED))
        t_wall -= 1
        if trace: frames.append((round(y, 2), t_wall, round(gaps[0], 2), round(gaps[1], 2), score))
        if t_wall == 0:
            if abs(y - gaps[0]) > GAP / 2 - R:
                return score, frames
            score += 1
            gaps = [gaps[1], new_gap(rng)]
            t_wall = SPACING
    return score, frames

def run(n, seed):
    rng = random.Random(seed)
    out = {}
    for b in BOTS:
        scores = [play(b, rng)[0] for _ in range(n)]
        out[b] = {"games": n, "avg": sum(scores) / n, "best": max(scores),
                  "zero": sum(s == 0 for s in scores), "maxed": sum(s >= MAX_WALLS for s in scores),
                  "scores": scores}
    return out

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    res = run(n, seed)
    for b, r in res.items():
        print(f"{b:7s} games={r['games']} avg={r['avg']:.2f} best={r['best']} scored_zero={r['zero']} hit_cap={r['maxed']}")
