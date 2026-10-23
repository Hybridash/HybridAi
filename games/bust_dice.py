"""Bust Dice: an original push-your-luck dice game, made for HybridAi Day 10.

Rules (one die):
  On your turn, roll as many times as you like. Each roll adds its number to your pot.
  If you roll a number you ALREADY rolled this turn, you bust: the pot is lost, turn over.
  Stop any time to bank the pot. After 6 different numbers (pot 21) you must bank.
  First player to TARGET banked points wins.
So the 2nd roll busts 1 time in 6, the 3rd 2 in 6, ... the risk climbs every roll.

Bots (each decides only from its pot, the numbers already rolled, and the scores):
  once     banks after 1 roll (can never bust)
  twice    banks after 2 rolls
  three    banks after 3 rolls
  pot12    keeps rolling until the pot is 12 or more
  math     rolls only if the average gain beats the average loss on the next roll:
           sum(unrolled numbers)/6 > (numbers rolled/6) * pot
  never    never banks: rolls until it busts or gets all 6

usage: python3 games/bust_dice.py [games_per_pair] [seed]
"""
import random, sys, itertools

TARGET = 50
BOTS = ["once", "twice", "three", "pot12", "math", "never"]

def wants_roll(bot, pot, used, me, them):
    n = len(used)
    if n == 0: return True
    if n == 6: return False
    if bot == "once": return n < 1
    if bot == "twice": return n < 2
    if bot == "three": return n < 3
    if bot == "pot12": return pot < 12
    if bot == "math": return sum(f for f in range(1, 7) if f not in used) > n * pot
    if bot == "never": return True
    raise ValueError(bot)

def turn(bot, rng, me=0, them=0, trace=None):
    """returns points banked this turn (0 on bust)."""
    pot, used = 0, []
    while wants_roll(bot, pot, used, me, them):
        r = rng.randint(1, 6)
        if trace is not None: trace.append(r)
        if r in used: return 0
        used.append(r); pot += r
    return pot

def game(a, b, rng, first=0):
    s = [0, 0]; bots = [a, b]; p = first; turns = 0
    while True:
        s[p] += turn(bots[p], rng, s[p], s[1 - p]); turns += 1
        if s[p] >= TARGET: return p, turns
        p = 1 - p

def solo(bot, rng, n):
    pts = busts = 0
    for _ in range(n):
        t = []; v = turn(bot, rng, trace=t)
        pts += v; busts += (v == 0)
    return pts / n, busts / n

if __name__ == "__main__":
    G = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    rng = random.Random(seed)
    print("solo, 100,000 turns each: avg points per turn, bust rate")
    for b in BOTS:
        avg, br = solo(b, rng, 100000)
        print(f"  {b:6s} {avg:6.2f}  {br*100:5.1f}%")
    wins = {b: 0 for b in BOTS}; played = {b: 0 for b in BOTS}
    print(f"\nhead to head, {G:,} games per pair (first player alternates), target {TARGET}")
    table = {}
    for a, b in itertools.combinations(BOTS, 2):
        wa = 0
        for g in range(G):
            w, _ = game(a, b, rng, g % 2)
            wa += (w == 0)
        table[(a, b)] = wa
        wins[a] += wa; wins[b] += G - wa; played[a] += G; played[b] += G
        print(f"  {a:6s} vs {b:6s}: {wa:6,} - {G-wa:6,}")
    print("\noverall")
    for b in sorted(BOTS, key=lambda b: -wins[b]):
        print(f"  {b:6s} {wins[b]:7,} / {played[b]:,}  ({wins[b]/played[b]*100:.1f}%)")
