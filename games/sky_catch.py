"""Sky Catch: an original falling-objects game, made for HybridAi Day 12.

Rules:
  The board is 5 columns wide and 8 rows tall. The player sits in the bottom row.
  Every tick, everything falls one row, then a new object may appear in the top row
  (60% chance): a coin (70%) or a bomb (30%), in a random column.
  Each tick the player moves left, stays, or moves right.
  Catch a coin (it lands in your column): +1. Catch a bomb: game over.
  A game lasts at most 200 ticks.

Bots:
  random   picks left / stay / right at random
  chaser   walks toward the lowest coin it can see, ignores bombs
  dodger   stays still unless a bomb is about to land on it, then steps aside
  learner  starts knowing nothing. It sees only the 3x3 patch above its head
           (empty / coin / bomb) plus which walls are next to it, and learns
           from rewards (tabular Q-learning: +1 coin, -10 bomb).

usage: python3 games/sky_catch.py [eval_games] [seed]
"""
import random, sys

COLS, ROWS, TICKS = 5, 8, 200
P_SPAWN, P_COIN = 0.6, 0.7
EMPTY, COIN, BOMB = 0, 1, 2
ACTIONS = (-1, 0, 1)

class Game:
    def __init__(self, rng):
        self.rng = rng
        self.grid = [[EMPTY] * COLS for _ in range(ROWS)]   # row 0 = top, row ROWS-1 = player's row
        self.col = COLS // 2
        self.score = 0
        self.tick = 0
        self.over = False
        self.died = False

    def step(self, a):
        """move, then everything falls. returns reward."""
        self.col = max(0, min(COLS - 1, self.col + a))
        self.grid.pop()                       # bottom row leaves the board
        row = [EMPTY] * COLS
        if self.rng.random() < P_SPAWN:
            row[self.rng.randrange(COLS)] = COIN if self.rng.random() < P_COIN else BOMB
        self.grid.insert(0, row)
        self.tick += 1
        landed = self.grid[ROWS - 1][self.col]
        self.grid[ROWS - 1] = [EMPTY] * COLS   # everything in the bottom row is caught or missed
        r = 0
        if landed == COIN: self.score += 1; r = 1
        elif landed == BOMB: self.over = True; self.died = True; r = -10
        if self.tick >= TICKS: self.over = True
        return r

def state(g):
    """3x3 patch: rows ROWS-2..ROWS-4 (just above the player), columns col-1..col+1; off-board = 3."""
    s = []
    for dr in (2, 3, 4):
        r = ROWS - dr
        for dc in (-1, 0, 1):
            c = g.col + dc
            s.append(g.grid[r][c] if 0 <= c < COLS else 3)
    return tuple(s)

def lowest(g, kind):
    for r in range(ROWS - 2, -1, -1):
        for c in range(COLS):
            if g.grid[r][c] == kind: return r, c
    return None

def act(bot, g, rng, Q=None):
    if bot == "random": return rng.choice(ACTIONS)
    if bot == "chaser":
        t = lowest(g, COIN)
        if not t: return 0
        return (t[1] > g.col) - (t[1] < g.col)
    if bot == "dodger":
        # bomb that would land on me next tick (it is in row ROWS-2, my column)
        if g.grid[ROWS - 2][g.col] == BOMB:
            for a in (-1, 1):
                c = g.col + a
                if 0 <= c < COLS and g.grid[ROWS - 2][c] != BOMB: return a
        return 0
    if bot == "learner":
        q = Q.get(state(g))
        if not q: return 0
        best = max(q)
        return ACTIONS[[i for i in range(3) if q[i] == best][0]]
    raise ValueError(bot)

def train(Q, games, rng, alpha=0.2, gamma=0.9, eps=0.1):
    for _ in range(games):
        g = Game(rng)
        s = state(g)
        while not g.over:
            q = Q.setdefault(s, [0.0, 0.0, 0.0])
            i = rng.randrange(3) if rng.random() < eps else max(range(3), key=lambda k: q[k])
            r = g.step(ACTIONS[i])
            s2 = state(g)
            nxt = 0.0 if g.over else max(Q.setdefault(s2, [0.0, 0.0, 0.0]))
            q[i] += alpha * (r + gamma * nxt - q[i])
            s = s2

def play(bot, rng, Q=None, trace=None):
    g = Game(rng)
    if trace is not None: trace.append(snap(g))
    while not g.over:
        g.step(act(bot, g, rng, Q))
        if trace is not None: trace.append(snap(g))
    return g.score, g.died, g.tick

def snap(g):
    return ([row[:] for row in g.grid], g.col, g.score, g.died, g.tick)

def evaluate(bot, n, seed, Q=None):
    rng = random.Random(seed)
    sc = died = ticks = 0
    for _ in range(n):
        s, d, t = play(bot, rng, Q)
        sc += s; died += d; ticks += t
    return sc / n, died / n, ticks / n

CHECKPOINTS = (0, 10, 100, 1000, 10000, 100000)

def learner_curve(seed, n_eval):
    """train one learner, freezing a copy at each checkpoint. returns {checkpoint: (Q copy, eval)}."""
    rng = random.Random(seed)
    Q, done, out = {}, 0, {}
    for cp in CHECKPOINTS:
        train(Q, cp - done, rng); done = cp
        Qc = {k: v[:] for k, v in Q.items()}
        out[cp] = (Qc, evaluate("learner", n_eval, seed + 1000, Qc))
    return out

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    for b in ("random", "chaser", "dodger"):
        s, d, t = evaluate(b, n, seed + 1000)
        print(f"{b:8s} coins {s:6.2f}  bombed {d*100:5.1f}%  ticks {t:6.1f}")
    for cp, (Q, (s, d, t)) in learner_curve(seed, n).items():
        print(f"learner after {cp:6d} games: coins {s:6.2f}  bombed {d*100:5.1f}%  ticks {t:6.1f}  states {len(Q)}")
