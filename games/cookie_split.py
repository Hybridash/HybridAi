"""Cookie Split: an original sharing game, made for HybridAi Day 28.

Rules:
  Two bots, one jar, ROUNDS rounds per match. Each round both secretly pick SHARE or GRAB.
    both share        -> 3 cookies each
    one grabs         -> the grabber gets 5, the sharer gets 0
    both grab         -> 1 cookie each
  Most cookies after the last round wins the match. (The payoffs are the classic iterated
  prisoner's dilemma, the game from Robert Axelrod's 1980 computer tournaments.)
  SLIP: with chance `slip` a bot's hand slips and it plays the opposite of what it picked.
  Bots only see what was actually played, not what was meant.

Bots:
  pushover  always shares.
  grabber   always grabs.
  copycat   shares first, then copies the rival's last move (tit for tat).
  grudge    shares until the rival grabs once, then grabs forever.
  forgiver  shares unless the rival grabbed in both of the last two rounds (tit for two tats).
  sneak     copycat, but 1 round in 10 it grabs anyway.
  random    coin flip.

usage: python3 games/cookie_split.py [matches_per_pair] [seed] [slip]
"""
import random, sys

ROUNDS = 200
BOTS = ["copycat", "grudge", "forgiver", "pushover", "sneak", "random", "grabber"]
PAY = {(0, 0): (3, 3), (0, 1): (0, 5), (1, 0): (5, 0), (1, 1): (1, 1)}   # 0 = share, 1 = grab

def pick(bot, mine, theirs, rng):
    if bot == "pushover": return 0
    if bot == "grabber": return 1
    if bot == "copycat": return theirs[-1] if theirs else 0
    if bot == "grudge": return 1 if 1 in theirs else 0
    if bot == "forgiver": return 1 if theirs[-2:] == [1, 1] else 0
    if bot == "sneak": return 1 if rng.random() < 0.1 else (theirs[-1] if theirs else 0)
    if bot == "random": return int(rng.random() < 0.5)
    raise ValueError(bot)

def play(a, b, rng, slip=0.0, trace=False):
    ha, hb, sa, sb, log = [], [], 0, 0, []
    for _ in range(ROUNDS):
        ma, mb = pick(a, ha, hb, rng), pick(b, hb, ha, rng)
        if slip:
            if rng.random() < slip: ma ^= 1
            if rng.random() < slip: mb ^= 1
        pa, pb = PAY[(ma, mb)]
        sa += pa; sb += pb
        ha.append(ma); hb.append(mb)
        if trace: log.append((ma, mb, sa, sb))
    return {"a": sa, "b": sb, "log": log}

def tournament(games, seed, slip=0.0, bots=BOTS):
    """Every bot meets every bot (and its own twin) `games` times. Returns per-bot totals."""
    rng = random.Random(seed)
    T = {b: {"cookies": 0, "matches": 0, "won": 0, "tied": 0, "lost": 0, "vs": {}} for b in bots}
    for i, a in enumerate(bots):
        for b in bots[i:]:
            ca = cb = wa = wb = 0
            for _ in range(games):
                r = play(a, b, rng, slip)
                ca += r["a"]; cb += r["b"]
                wa += r["a"] > r["b"]; wb += r["b"] > r["a"]
            T[a]["vs"][b] = ca / games
            if a == b:   # twin match: count one seat
                T[a]["cookies"] += ca; T[a]["matches"] += games
                T[a]["tied"] += games - wa - wb   # a twin can't "beat" itself in the standings
                continue
            T[b]["vs"][a] = cb / games
            for x, cx, wx, lx in ((a, ca, wa, wb), (b, cb, wb, wa)):
                T[x]["cookies"] += cx; T[x]["matches"] += games
                T[x]["won"] += wx; T[x]["lost"] += lx; T[x]["tied"] += games - wx - lx
    for b in bots: T[b]["avg"] = T[b]["cookies"] / T[b]["matches"]
    return T

def show(T):
    for b in sorted(T, key=lambda b: -T[b]["avg"]):
        t = T[b]
        print(f"{b:9s} avg {t['avg']:6.1f}  won {t['won']:5d} tied {t['tied']:5d} lost {t['lost']:5d}   "
              + " ".join(f"{o[:4]} {t['vs'][o]:5.0f}" for o in T))

if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 28
    slip = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    # self-check: the two fixed matchups everyone can do by hand
    assert play("pushover", "grabber", random.Random(0))["b"] == 5 * ROUNDS
    r = play("copycat", "grabber", random.Random(0)); assert (r["a"], r["b"]) == (ROUNDS - 1, ROUNDS + 4)
    show(tournament(games, seed, slip))
