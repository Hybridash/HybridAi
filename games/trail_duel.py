"""Trail Duel: an original two-player grid game, made for HybridAi Day 18.

Rules:
  A 16x16 board. Two riders start on opposite sides (mirror positions, random rows),
  facing each other. Every step BOTH riders move at the same time, one cell up, down,
  left or right (never straight back), and leave a permanent wall on the cell they left.
  A rider that moves into the board edge, any wall, or the other rider's current cell
  crashes. If both crash on the same step (or move into the same cell) it's a DRAW.
  Last rider moving wins. Games are capped at 300 steps (a draw if both survive).

Bots (each sees the whole board):
  random    picks a random move that doesn't crash this step.
  straight  keeps going straight; turns (random side) only when the cell ahead is blocked.
  hugger    of the safe moves, takes the one with the most walls/edges around it
            (fills space tightly, never leaves gaps). Ties: random.
  space     takes the safe move that leaves it the most cells it can still reach (flood fill).
            Ties: random.
  chaser    takes the safe move that gets closest to the other rider's head (tries to cut it off).
  territory for each safe move, counts the cells it would reach before the opponent
            (breadth-first race from both heads); takes the move with the biggest lead.
            When the two riders can no longer reach each other, it plays like hugger
            inside its own space.
  wary      the fix, added after the tournament: territory, but first throws out any move onto
            a cell the other rider could also step onto this turn (a possible head-on crash),
            unless every safe move is like that.

usage: python3 games/trail_duel.py [games_per_pair] [seed]
"""
import random, sys
from collections import deque

N = 16
CAP = 300
MOVES = ((0, -1), (1, 0), (0, 1), (-1, 0))
BOTS = ["random", "straight", "hugger", "space", "chaser", "territory"]

def inb(c): return 0 <= c[0] < N and 0 <= c[1] < N
def add(c, m): return (c[0] + m[0], c[1] + m[1])

def safe_moves(walls, me, d, other):
    out = []
    for m in MOVES:
        if d and m == (-d[0], -d[1]): continue
        c = add(me, m)
        if inb(c) and c not in walls and c != other: out.append(m)
    return out

def flood(start, walls, block=()):
    seen = {start}; q = deque([start])
    while q:
        c = q.popleft()
        for m in MOVES:
            n = add(c, m)
            if inb(n) and n not in walls and n not in seen and n not in block:
                seen.add(n); q.append(n)
    return len(seen)

def bfs_dist(start, walls):
    dist = {start: 0}; q = deque([start])
    while q:
        c = q.popleft()
        for m in MOVES:
            n = add(c, m)
            if inb(n) and n not in walls and n not in dist:
                dist[n] = dist[c] + 1; q.append(n)
    return dist

def tight(c, walls):
    return sum(1 for m in MOVES if not inb(add(c, m)) or add(c, m) in walls)

def best(opts, key, rng):
    top = max(key(m) for m in opts)
    return rng.choice([m for m in opts if key(m) == top])

def choose(bot, walls, me, d, other, rng):
    opts = safe_moves(walls, me, d, other)
    if not opts: return d or MOVES[1]
    if bot == "random":
        return rng.choice(opts)
    if bot == "straight":
        return d if d in opts else rng.choice(opts)
    if bot == "hugger":
        w2 = walls | {me}
        return best(opts, lambda m: tight(add(me, m), w2), rng)
    if bot == "space":
        w2 = walls | {me}
        return best(opts, lambda m: flood(add(me, m), w2, (other,)), rng)
    if bot == "chaser":
        return best(opts, lambda m: -(abs(add(me, m)[0] - other[0]) + abs(add(me, m)[1] - other[1])), rng)
    if bot == "wary":
        theirs = {add(other, m) for m in MOVES}
        calm = [m for m in opts if add(me, m) not in theirs]
        bot = "territory"
        if calm: opts = calm
    if bot == "territory":
        w2 = walls | {me}
        def score(m):
            c = add(me, m)
            dm = bfs_dist(c, w2 | {other})
            do = bfs_dist(other, w2 | {c})
            if not any(k in do for k in dm if k != c):   # separated: fill own space tightly
                return (0, flood(c, w2, (other,)), tight(c, w2))
            lead = sum(1 for k, v in dm.items() if v < do.get(k, 10 ** 9)) - \
                   sum(1 for k, v in do.items() if v < dm.get(k, 10 ** 9))
            return (1, lead, 0)
        scores = {m: score(m) for m in opts}
        top = max(scores.values())
        return rng.choice([m for m in opts if scores[m] == top])
    raise ValueError(bot)

LAST = {}
def play(b1, b2, rng, trace=False):
    """returns (result, steps, trails): result 1 = b1 wins, 2 = b2 wins, 0 = draw.
    LAST["how"] says how it ended: 'headon' (same cell), 'both' (both crashed elsewhere), 'one', 'cap'."""
    row = rng.randrange(2, N - 2)
    p = [(2, row), (N - 3, N - 1 - row)]
    d = [(1, 0), (-1, 0)]
    walls = set()
    frames = [(list(p), set())] if trace else None
    trails = [[p[0]], [p[1]]]
    for step in range(1, CAP + 1):
        m1 = choose(b1, walls, p[0], d[0], p[1], rng)
        m2 = choose(b2, walls, p[1], d[1], p[0], rng)
        walls |= {p[0], p[1]}
        n1, n2 = add(p[0], m1), add(p[1], m2)
        c1 = not inb(n1) or n1 in walls
        c2 = not inb(n2) or n2 in walls
        how = "one"
        if n1 == n2: c1 = c2 = True; how = "headon"
        elif c1 and c2: how = "both"
        d = [m1, m2]; p = [n1, n2]
        trails[0].append(n1); trails[1].append(n2)
        if trace: frames.append((list(p), set(walls)))
        if c1 or c2:
            res = 0 if (c1 and c2) else (2 if c1 else 1)
            LAST["how"] = how
            return res, step, (trails if trace else None)
    LAST["how"] = "cap"
    return 0, CAP, (trails if trace else None)

def tournament(games, seed):
    rng = random.Random(seed)
    table = {}
    for i, a in enumerate(BOTS):
        for b in BOTS[i + 1:]:
            w = [0, 0, 0]; steps = 0
            for g in range(games):
                # swap sides every other game so neither bot keeps the same start
                if g % 2 == 0:
                    r, s, _ = play(a, b, rng); w[{1: 0, 2: 1, 0: 2}[r]] += 1
                else:
                    r, s, _ = play(b, a, rng); w[{1: 1, 2: 0, 0: 2}[r]] += 1
                steps += s
            table[(a, b)] = (w, steps / games)
    return table

if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 18
    t = tournament(games, seed)
    tot = {b: [0, 0, 0] for b in BOTS}
    for (a, b), (w, st) in t.items():
        print(f"{a:>9} vs {b:<9}  {w[0]:4d} - {w[1]:4d}  draws {w[2]:4d}  avg steps {st:.1f}")
        tot[a][0] += w[0]; tot[a][1] += w[1]; tot[a][2] += w[2]
        tot[b][0] += w[1]; tot[b][1] += w[0]; tot[b][2] += w[2]
    print()
    for b in sorted(BOTS, key=lambda b: -tot[b][0]):
        W_, L, D = tot[b]
        print(f"{b:>9}  wins {W_:5d}  losses {L:5d}  draws {D:5d}  win% {100 * W_ / (W_ + L + D):.1f}")
