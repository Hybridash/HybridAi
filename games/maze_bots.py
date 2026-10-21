"""Maze Bots: an original maze experiment, made for HybridAi Day 8.

Each maze is a grid. A bot starts in the top-left cell and must reach the exit cell.
No bot sees the whole maze: each step it only knows which walls touch its own cell.

Bots:
  random    picks a random open direction every step
  hand      keeps its right hand on the wall (classic wall follower)
  memory    remembers every cell it has visited: goes to an unvisited neighbor if
            there is one, otherwise walks back the way it came (depth-first search)

Two kinds of maze:
  perfect   exactly one path between any two cells (no loops)
  loops     the same maze with some extra walls knocked out, so paths form loops

The exit is a random cell (not on the edge for the loop test, see EXIT_INNER).
A run stops at MAX_STEPS and counts as "stuck".

usage: python3 games/maze_bots.py [mazes] [seed]
"""
import random, sys

N = 12                 # maze is N x N cells
MAX_STEPS = 5000       # a bot that hasn't found the exit by now is stuck
LOOP_FRAC = 0.12       # share of remaining inner walls removed to make loops
DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]   # up, right, down, left (clockwise)

def make_maze(rng, loops=False):
    """open[(x,y)] = set of direction indexes with no wall."""
    open_ = {(x, y): set() for x in range(N) for y in range(N)}
    seen, stack = {(0, 0)}, [(0, 0)]
    while stack:
        x, y = stack[-1]
        nb = [(d, (x + DIRS[d][0], y + DIRS[d][1])) for d in range(4)]
        nb = [(d, c) for d, c in nb if c in open_ and c not in seen]
        if not nb:
            stack.pop(); continue
        d, c = rng.choice(nb)
        open_[(x, y)].add(d); open_[c].add((d + 2) % 4)
        seen.add(c); stack.append(c)
    if loops:
        walls = [((x, y), d) for x in range(N) for y in range(N) for d in (1, 2)
                 if (x + DIRS[d][0], y + DIRS[d][1]) in open_ and d not in open_[(x, y)]]
        for (x, y), d in rng.sample(walls, int(len(walls) * LOOP_FRAC)):
            open_[(x, y)].add(d); open_[(x + DIRS[d][0], y + DIRS[d][1])].add((d + 2) % 4)
    return open_

def pick_exit(rng):
    # an inner cell (not touching the outer edge), far-ish from the start
    while True:
        e = (rng.randrange(1, N - 1), rng.randrange(1, N - 1))
        if e[0] + e[1] >= N: return e

def shortest(open_, start, goal):
    from collections import deque
    q, dist = deque([start]), {start: 0}
    while q:
        c = q.popleft()
        if c == goal: return dist[c]
        for d in open_[c]:
            n = (c[0] + DIRS[d][0], c[1] + DIRS[d][1])
            if n not in dist: dist[n] = dist[c] + 1; q.append(n)

def step(c, d): return (c[0] + DIRS[d][0], c[1] + DIRS[d][1])

def run_bot(bot, open_, goal, rng, trace=False):
    """Returns (steps or None if stuck, path)."""
    c, path = (0, 0), [(0, 0)]
    facing = 1  # start facing right
    visited, back = {c}, []
    for s in range(1, MAX_STEPS + 1):
        if bot == "random":
            d = rng.choice(sorted(open_[c]))
        elif bot == "hand":
            # try right, straight, left, back
            for turn in (1, 0, 3, 2):
                d = (facing + turn) % 4
                if d in open_[c]: break
            facing = d
        else:  # memory
            fresh = [d for d in sorted(open_[c]) if step(c, d) not in visited]
            if fresh:
                d = rng.choice(fresh); back.append((d + 2) % 4)
            else:
                d = back.pop()
        c = step(c, d)
        visited.add(c)
        if trace: path.append(c)
        if c == goal: return s, path
    return None, path

BOTS = ["random", "hand", "memory"]

def run(n, seed, loops):
    rng = random.Random(seed)
    res = {b: [] for b in BOTS}
    best = []
    for i in range(n):
        m = make_maze(rng, loops)
        g = pick_exit(rng)
        best.append(shortest(m, (0, 0), g))
        for b in BOTS:
            res[b].append(run_bot(b, m, g, rng)[0])
    return res, best

def summary(res, best):
    out = {}
    for b, r in res.items():
        ok = [s for s in r if s is not None]
        out[b] = {"solved": len(ok), "stuck": len(r) - len(ok),
                  "avg_steps": sum(ok) / len(ok) if ok else None}
    out["shortest_avg"] = sum(best) / len(best)
    return out

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    for loops in (False, True):
        res, best = run(n, seed, loops)
        print("LOOPS" if loops else "PERFECT", summary(res, best))

def play(bot, seed, loops):
    """One reproducible game for the video: maze + exit from Random(seed), bot moves from Random(seed + 1)."""
    rng = random.Random(seed)
    m = make_maze(rng, loops)
    g = pick_exit(rng)
    steps, path = run_bot(bot, m, g, random.Random(seed + 1), trace=True)
    return m, g, steps, path
