"""Tail Trap: an original snake-style grid game, made for HybridAi Day 16 (the first long bot video).

Rules:
  A 10x10 board. The snake starts 3 cells long in the middle, facing right. One apple sits
  on a random empty cell. Each step the head moves up/down/left/right (never straight back).
  Eating an apple grows the snake by 1 and a new apple appears on a random empty cell.
  Hitting a wall or the snake's own body ends the game (moving into the cell the tail is
  leaving is allowed). Filling all 100 cells is a WIN. If the snake goes 400 steps without
  eating it STALLS (game over). Score = final length.

Bots:
  random    picks a random move that doesn't crash this step.
  greedy    of the moves that don't crash this step, takes the one closest to the apple
            (Manhattan distance; ties: random).
  careful   like greedy, but first throws out any move that leaves the head with fewer
            free cells reachable (flood fill) than the snake's length. If every move fails
            that test, it takes the move with the most reachable space.
  cycle     ignores the apple and walks one fixed loop through all 100 cells
            (a Hamiltonian cycle), forever. It can never hit itself.
  shortcut  walks the same loop, but while it is shorter than 50 it may jump ahead along the
            loop toward the apple, as long as the jump stays at least 4 cells short of its own
            tail (in loop order). From length 50 on it just walks the loop.

usage: python3 games/snake_bots.py [games] [seed]
"""
import random, sys
from collections import deque

N = 10
CELLS = N * N
STALL = 400
CUTOFF, BUFFER = 50, 4   # shortcut bot: only cut corners while shorter than CUTOFF
MOVES = ((0, -1), (1, 0), (0, 1), (-1, 0))   # up, right, down, left

def cycle_next():
    """A fixed Hamiltonian cycle on the NxN board (N even): row 0 left->right is the
    'highway' back, the rest snakes up and down in columns 1..N-1 rows 1..N-1, column 0 goes up."""
    order = [(x, 0) for x in range(N)]
    for x in range(N - 1, 0, -1):
        ys = range(1, N) if (N - 1 - x) % 2 == 0 else range(N - 1, 0, -1)
        order += [(x, y) for y in ys]
    order += [(0, y) for y in range(N - 1, 0, -1)]
    assert len(order) == CELLS and len(set(order)) == CELLS
    nxt = {order[i]: order[(i + 1) % CELLS] for i in range(CELLS)}
    for a, b in nxt.items(): assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1
    return nxt

NEXT = cycle_next()
IDX = {}
_c = (0, 0)
for _i in range(CELLS):
    IDX[_c] = _i; _c = NEXT[_c]

def ahead(a, b):
    """how many steps along the loop from cell a to cell b."""
    return (IDX[b] - IDX[a]) % CELLS

def flood(start, blocked):
    seen = {start}; q = deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in MOVES:
            c = (x + dx, y + dy)
            if 0 <= c[0] < N and 0 <= c[1] < N and c not in blocked and c not in seen:
                seen.add(c); q.append(c)
    return len(seen)

def place_apple(body, rng):
    empty = [(x, y) for x in range(N) for y in range(N) if (x, y) not in body]
    return rng.choice(empty) if empty else None

def play(bot, rng, trace=None, max_steps=20000, info=None):
    body = deque([(5, 5), (4, 5), (3, 5)])        # head first
    occ = set(body)
    apple = place_apple(occ, rng)
    steps = since = 0
    result = None
    if trace is not None: trace.append((tuple(body), apple))
    while result is None:
        hx, hy = body[0]
        opts = []
        for k, (dx, dy) in enumerate(MOVES):
            c = (hx + dx, hy + dy)
            if not (0 <= c[0] < N and 0 <= c[1] < N): continue
            if c == body[1]: continue                     # no reversing
            grow = c == apple
            if c in occ and not (c == body[-1] and not grow): continue
            opts.append(c)
        if bot == "cycle" or (bot == "shortcut" and (steps < 3 or len(body) >= CUTOFF)):
            c = NEXT[(hx, hy)]
            choice = c if c in opts else None
        elif bot == "shortcut":
            # skip ahead along the loop toward the apple, but never past the tail (minus a buffer),
            # so the body always stays in loop order and the loop can't be blocked.
            room = ahead(body[0], body[-1])
            goal = ahead(body[0], apple)
            ok = [c for c in opts if ahead(body[0], c) < room - BUFFER and ahead(body[0], c) <= goal]
            choice = max(ok, key=lambda c: ahead(body[0], c)) if ok else NEXT[(hx, hy)]
            if choice not in opts: choice = None
        elif not opts:
            choice = None
        elif bot == "random":
            choice = rng.choice(opts)
        else:
            def dist(c): return abs(c[0] - apple[0]) + abs(c[1] - apple[1])
            pool = opts
            if bot == "careful":
                space = {}
                for c in opts:
                    blocked = set(occ)
                    if c != apple: blocked.discard(body[-1])   # tail moves away unless we grow
                    blocked.discard(c)
                    space[c] = flood(c, blocked)
                safe = [c for c in opts if space[c] >= len(body)]
                if safe: pool = safe
                else:
                    pool = [max(opts, key=lambda c: (space[c], -dist(c)))]
                    if info is not None: info.setdefault("trapped", []).append(steps)
            best = min(dist(c) for c in pool)
            choice = rng.choice([c for c in pool if dist(c) == best])
        if choice is None:
            result = "crash"
            break
        grow = choice == apple
        body.appendleft(choice); occ.add(choice)
        if not grow:
            t = body.pop()
            if t != choice: occ.discard(t)
        steps += 1; since += 1
        if grow:
            since = 0
            if len(body) == CELLS:
                result = "win"
            else:
                apple = place_apple(occ, rng)
        if trace is not None: trace.append((tuple(body), apple))
        if result is None and since >= STALL: result = "stall"
        if result is None and steps >= max_steps: result = "cap"
    return {"len": len(body), "steps": steps, "result": result}

BOTS = ("random", "greedy", "careful", "cycle", "shortcut")

if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    for b in BOTS:
        rng = random.Random(seed)
        rs = [play(b, rng) for _ in range(games)]
        wins = [r for r in rs if r["result"] == "win"]
        print(f"{b:8s} avg len {sum(r['len'] for r in rs)/games:6.2f}  max {max(r['len'] for r in rs):3d}  "
              f"wins {len(wins):5d}  crash {sum(r['result']=='crash' for r in rs):5d}  stall {sum(r['result']=='stall' for r in rs):5d}  "
              f"avg steps {sum(r['steps'] for r in rs)/games:8.1f}  "
              f"steps/win {sum(r['steps'] for r in wins)/max(1,len(wins)):8.1f}")
