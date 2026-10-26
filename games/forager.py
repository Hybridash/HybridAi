"""Forager: an original grid game, made for HybridAi Day 14, where a genetic algorithm
evolves the bots instead of me writing them.

Rules:
  A 15x15 board with 20 food pellets in random cells. The bot starts in the middle
  with 20 energy. Each move (up/down/left/right, never off the board) costs 1 energy.
  Eating a pellet gives +6 energy. The game ends when energy hits 0, all food is
  eaten, or after 300 moves. Score = pellets eaten.
  The bot only sees food within 3 steps (Manhattan distance) of where it stands.

Brain (the genome): 4 numbers. For each legal move the bot adds up
  w_food    * (sum over visible pellets of 1 / (1 + distance from the new cell))
  w_visited * (times it has already stood on the new cell)
  w_center  * (distance from the new cell to the middle of the board)
  w_straight* (1 if the move keeps the same direction, else 0)
  and takes the move with the highest total (ties: lowest index).

Hand-written bot for comparison:
  greedy    walks to the nearest visible pellet; when it sees none, it moves at random.

Genetic algorithm: 60 genomes with random weights in [-1, 1]. Each generation every
genome plays the same 30 boards; the 12 best survive unchanged, the other 48 are
children: pick two survivors, mix their weights (uniform crossover), add a small
random change (gaussian, sigma 0.15) to each weight. 30 generations.

usage: python3 games/forager.py [seed]
"""
import random, sys

N, FOOD, START_E, GAIN, MAX_MOVES, SIGHT = 15, 20, 20, 6, 300, 3
MOVES = ((0, -1), (1, 0), (0, 1), (-1, 0))   # up, right, down, left
POP, KEEP, GENS, BOARDS, SIGMA = 60, 12, 30, 30, 0.15

def board(rng):
    cells = [(x, y) for x in range(N) for y in range(N) if (x, y) != (N // 2, N // 2)]
    return set(rng.sample(cells, FOOD))

def play(genome, food, rng=None, trace=None):
    """genome = (w_food, w_visited, w_center, w_straight) or the string 'greedy'."""
    food = set(food)
    x = y = N // 2
    e, eaten, moves, last = START_E, 0, 0, None
    seen = {(x, y): 1}
    if trace is not None: trace.append((x, y, e, eaten, frozenset(food)))
    while e > 0 and food and moves < MAX_MOVES:
        vis = [f for f in food if abs(f[0] - x) + abs(f[1] - y) <= SIGHT]
        legal = [k for k, (dx, dy) in enumerate(MOVES) if 0 <= x + dx < N and 0 <= y + dy < N]
        if genome == "greedy":
            if vis:
                fx, fy = min(vis, key=lambda f: (abs(f[0] - x) + abs(f[1] - y), f))
                best = min(legal, key=lambda k: (abs(fx - x - MOVES[k][0]) + abs(fy - y - MOVES[k][1]), k))
            else:
                best = rng.choice(legal)
        else:
            wf, wv, wc, ws = genome
            def score(k):
                nx, ny = x + MOVES[k][0], y + MOVES[k][1]
                fs = sum(1.0 / (1 + abs(f[0] - nx) + abs(f[1] - ny)) for f in vis)
                return (wf * fs + wv * seen.get((nx, ny), 0)
                        + wc * (abs(nx - N // 2) + abs(ny - N // 2)) + ws * (k == last))
            best = max(legal, key=lambda k: (score(k), -k))
        x, y = x + MOVES[best][0], y + MOVES[best][1]
        last = best
        moves += 1
        e -= 1
        seen[(x, y)] = seen.get((x, y), 0) + 1
        if (x, y) in food:
            food.discard((x, y)); eaten += 1; e += GAIN
        if trace is not None: trace.append((x, y, e, eaten, frozenset(food)))
    return eaten

def evolve(seed, log=None):
    rng = random.Random(seed)
    pop = [tuple(rng.uniform(-1, 1) for _ in range(4)) for _ in range(POP)]
    history = []
    for gen in range(GENS + 1):
        boards = [board(rng) for _ in range(BOARDS)]
        scored = sorted(((sum(play(g, b) for b in boards) / BOARDS, g) for g in pop), key=lambda t: -t[0])
        history.append((gen, scored[0][0], sum(s for s, _ in scored) / POP, scored[0][1]))
        if log: log(gen, scored)
        if gen == GENS: break
        keep = [g for _, g in scored[:KEEP]]
        kids = []
        while len(kids) < POP - KEEP:
            a, b = rng.sample(keep, 2)
            kids.append(tuple((a[i] if rng.random() < 0.5 else b[i]) + rng.gauss(0, SIGMA) for i in range(4)))
        pop = keep + kids
    return history, [g for _, g in scored], pop

def test(genome, n=1000, seed=999):
    """returns (avg pellets, share of boards cleared, share of moves onto a cell already visited)."""
    rng = random.Random(seed)
    tot = full = mv = rev = 0
    for _ in range(n):
        b = board(rng)
        tr = []
        s = play(genome, b, rng, tr)
        tot += s; full += s == FOOD
        cells = set()
        for x, y, *_ in tr:
            if (x, y) in cells: rev += 1
            cells.add((x, y))
        mv += len(tr) - 1
    return tot / n, full / n, rev / mv

if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    hist, ranked, pop = evolve(seed)
    for gen, best, avg, g in hist:
        if gen in (0, 1, 2, 3, 5, 10, 15, 20, 25, 30):
            print(f"gen {gen:3d}  best {best:5.2f}  avg {avg:5.2f}  genome {tuple(round(v, 2) for v in g)}")
    ev = ranked[0]
    print("champion genome", tuple(round(v, 3) for v in ev))
    print("test on 1,000 new boards (seed 999): pellets, cleared, revisit share")
    for name, g in (("greedy", "greedy"), ("gen0 best", hist[0][3]), ("evolved", ev),
                    ("evolved, straight=0", (ev[0], ev[1], ev[2], 0.0)),
                    ("evolved, visited=0", (ev[0], 0.0, ev[2], ev[3]))):
        a, c, r = test(g)
        print(f"  {name:22s} {a:6.2f}  {c*100:5.1f}%  {r*100:5.1f}%")
