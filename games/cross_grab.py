"""Cross Grab: an original two-player number game, made for HybridAi Day 20.

Rules:
  A 5x5 board of random numbers 1-9. Two players take turns claiming one empty cell and
  adding its number to their score. The first move can be any cell. After that, you must
  claim a cell in the same ROW or the same COLUMN as the cell your opponent just claimed.
  When the player to move has no empty cell in that row or column, the game ends.
  Higher total wins; equal totals are a draw.

Bots:
  random   picks a random legal cell.
  greedy   takes the biggest number it is allowed to take. Ties: random.
  spoiler  looks one reply ahead: takes the cell that maximizes (its number minus the
           biggest number the opponent could take next). Ties: random.
  deep     minimax with alpha-beta, 4 moves ahead (its move + 3), scoring the point lead
           (game over = final lead). Ties: random.
  monte    Monte Carlo: for each legal cell, plays 40 games to the end with random moves
           for both sides and takes the cell with the best average final lead.
           ("monte400" = 400 playouts; a trailing "s" (e.g. "monte40s") = the fix, added after the
           tournament: playouts where both sides take the biggest number 80% of the time.)

usage: python3 games/cross_grab.py [games_per_pair] [seed]
"""
import random, sys

N = 5
BOTS = ["random", "greedy", "spoiler", "deep", "monte"]
DEPTH = 4
PLAYOUTS = 40

def new_board(rng): return [rng.randint(1, 9) for _ in range(N * N)]

def legal(taken, last):
    if last is None: return [i for i in range(N * N) if not taken[i]]
    r, c = divmod(last, N)
    out = [r * N + k for k in range(N) if not taken[r * N + k]]
    out += [k * N + c for k in range(N) if k != r and not taken[k * N + c]]
    return out

def rollout(board, taken, last, lead, sign, rng, smart=False):
    """play to the end (random moves, or 80% greedy if smart); lead is from the root player's
    view, sign = +1 if root to move"""
    taken = taken[:]
    while True:
        ms = legal(taken, last)
        if not ms: return lead
        if smart and rng.random() < 0.8:
            top = max(board[x] for x in ms); m = rng.choice([x for x in ms if board[x] == top])
        else: m = rng.choice(ms)
        taken[m] = True; lead += sign * board[m]; sign = -sign; last = m

def negamax(board, taken, last, depth, alpha, beta):
    """best lead for the player to move (from its own view), looking depth moves ahead"""
    ms = legal(taken, last)
    if not ms or depth == 0: return 0
    best = -10 ** 9
    for m in sorted(ms, key=lambda i: -board[i]):
        taken[m] = True
        v = board[m] - negamax(board, taken, m, depth - 1, board[m] - beta, board[m] - alpha)
        taken[m] = False
        if v > best: best = v
        if best > alpha: alpha = best
        if alpha >= beta: break
    return best

def choose(bot, board, taken, last, rng):
    ms = legal(taken, last)
    if bot == "random": return rng.choice(ms)
    if bot == "greedy":
        top = max(board[m] for m in ms)
        return rng.choice([m for m in ms if board[m] == top])
    scores = {}
    for m in ms:
        taken[m] = True
        if bot == "spoiler":
            rep = legal(taken, m)
            scores[m] = board[m] - (max(board[x] for x in rep) if rep else 0)
        elif bot == "deep":
            scores[m] = board[m] - negamax(board, taken, m, DEPTH - 1, -10 ** 9, 10 ** 9)
        elif bot.startswith("monte"):
            k = int(bot[5:].rstrip("s") or PLAYOUTS); smart = bot.endswith("s")
            scores[m] = sum(rollout(board, taken, m, board[m], -1, rng, smart) for _ in range(k)) / k
        taken[m] = False
    top = max(scores.values())
    return rng.choice([m for m in ms if scores[m] == top])

def play(a, b, board, rng, trace=False):
    """a moves first. returns (score_a, score_b, moves) ; moves = list of cells"""
    taken = [False] * (N * N); last = None; sc = [0, 0]; who = 0; moves = []
    bots = (a, b)
    while True:
        if not legal(taken, last): break
        m = choose(bots[who], board, taken, last, rng)
        taken[m] = True; sc[who] += board[m]; last = m; moves.append(m); who = 1 - who
    return sc[0], sc[1], moves

def match(a, b, games, seed):
    """games boards; each board is played twice, both sides moving first. returns W/D/L for a + stats"""
    w = dr = l = 0; ra = rb = 0
    for g in range(games // 2):
        board = new_board(random.Random(seed * 100003 + g))
        for first in (0, 1):
            rng = random.Random(seed * 7919 + g * 2 + first)
            if first == 0: sa, sb, _ = play(a, b, board, rng)
            else: sb, sa, _ = play(b, a, board, rng)
            ra += sa; rb += sb
            if sa > sb: w += 1
            elif sa < sb: l += 1
            else: dr += 1
    return w, dr, l, ra / games, rb / games

if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    tot = {b: [0, 0, 0] for b in BOTS}
    for i, a in enumerate(BOTS):
        for b in BOTS[i + 1:]:
            w, dr, l, sa, sb = match(a, b, games, seed)
            print(f"{a:8s} vs {b:8s}  {w:4d}-{dr:3d}-{l:4d}  avg {sa:5.1f} - {sb:5.1f}", flush=True)
            tot[a][0] += w; tot[a][1] += dr; tot[a][2] += l
            tot[b][0] += l; tot[b][1] += dr; tot[b][2] += w
    print("totals (W-D-L):")
    for b in sorted(BOTS, key=lambda x: -tot[x][0]):
        w, dr, l = tot[b]; n = w + dr + l
        print(f"  {b:8s} {w:5d}-{dr:4d}-{l:5d}  win {100 * w / n:5.1f}%")
