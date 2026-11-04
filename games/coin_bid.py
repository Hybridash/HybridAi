"""Coin Bid: an original two-player bidding game, made for HybridAi Day 22.

Rules:
  Each player starts with 100 coins. Nine prize cards worth 1 to 9 points are shuffled and
  revealed one at a time. For each card both players secretly bid any whole number of their
  remaining coins (0 is allowed). The higher bid takes the card's points and pays its bid; the
  lower bidder pays nothing. Equal bids: nobody gets the card and nobody pays.
  After 9 cards, more points wins (45 points exist, so 23 always wins); equal points = draw.

Bots:
  random  bids a random amount from 0 to all its coins.
  even    splits its coins evenly over the cards left.
  value   bids its coins times (this card / points still left in the deck).
  big3    only bids on the 7, 8 and 9 (7+8+9 = 24, enough to win), splitting its coins
          evenly over the big cards left; bids 0 on everything else.
  mirror  bids the rival's last bid + 1 (first card: like value).
  allin   bids everything on the first card worth 8 or more, then 1 on every other card.
  counter (the fix, added after the tournament) bids like value, but never more than 1 above the
          most the rival has bid on any card so far, and never more than twice value's bid.

usage: python3 games/coin_bid.py [games_per_pair] [seed]
"""
import random, sys

START, CARDS = 100, list(range(1, 10))
BOTS = ["random", "even", "value", "big3", "mirror", "allin"]

def bid(bot, card, coins, left, deck_left, rival_last, rng, spent_big, rival_hist=()):
    """left = cards still to come including this one; deck_left = their point total"""
    if bot == "random": b = rng.randint(0, coins)
    elif bot == "even": b = coins // left
    elif bot == "value": b = round(coins * card / deck_left)
    elif bot == "big3":
        b = 0
        if card >= 7: b = coins // spent_big  # spent_big = big cards still to come incl. this one
    elif bot == "mirror": b = round(coins * card / deck_left) if rival_last is None else rival_last + 1
    elif bot == "counter":
        share = round(coins * card / deck_left)
        b = min(2 * share, max(rival_hist) + 1) if rival_hist else share
    elif bot == "allin": b = coins if (card >= 8 and spent_big) else min(1, coins)
    return max(0, min(coins, b))

def play(a, b, rng, trace=False):
    deck = CARDS[:]; rng.shuffle(deck)
    coins, pts, last = [START, START], [0, 0], [None, None]
    allin_ready = [True, True]
    hist = [[], []]
    log = []
    for i, card in enumerate(deck):
        rest = deck[i:]
        left, dl = len(rest), sum(rest)
        bigs = sum(1 for c in rest if c >= 7)
        bids = []
        for p, bot in enumerate((a, b)):
            extra = bigs if bot == "big3" else allin_ready[p]
            bids.append(bid(bot, card, coins[p], left, dl, last[1 - p], rng, extra, hist[1 - p]))
        for p, bot in enumerate((a, b)):
            if bot == "allin" and card >= 8 and allin_ready[p]: allin_ready[p] = False
        w = None if bids[0] == bids[1] else (0 if bids[0] > bids[1] else 1)
        if w is not None:
            coins[w] -= bids[w]; pts[w] += card
        last = bids[:]
        hist[0].append(bids[0]); hist[1].append(bids[1])
        if trace: log.append((card, bids[:], w, coins[:], pts[:]))
    return (pts, log) if trace else pts

def match(a, b, n, rng):
    w = [0, 0, 0]
    for g in range(n):
        if g % 2 == 0: pa, pb = play(a, b, rng)
        else: pb, pa = play(b, a, rng)
        w[0 if pa > pb else (1 if pb > pa else 2)] += 1
    return w

def tournament(n, seed):
    rng = random.Random(seed)
    res = {}
    for i, a in enumerate(BOTS):
        for b in BOTS[i + 1:]:
            w = [0, 0, 0]
            for g in range(n):
                # swap seats every other game (bids are simultaneous, but keep it fair anyway)
                if g % 2 == 0: pa, pb = play(a, b, rng)
                else: pb, pa = play(b, a, rng)
                w[0 if pa > pb else (1 if pb > pa else 2)] += 1
            res[(a, b)] = w
    return res

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 22
    res = tournament(n, seed)
    tot = {k: [0, 0, 0] for k in BOTS}
    for (a, b), (wa, wb, d) in res.items():
        print(f"{a:>7} vs {b:<7} {wa:5d} {wb:5d} draws {d}")
        tot[a][0] += wa; tot[a][1] += wb; tot[a][2] += d
        tot[b][0] += wb; tot[b][1] += wa; tot[b][2] += d
    print()
    rng = random.Random(seed + 1)
    for b in BOTS: print("counter vs", b, match("counter", b, n, rng))
    print()
    for k, (w, l, d) in sorted(tot.items(), key=lambda kv: -kv[1][0]):
        print(f"{k:>7} wins {w:5d} losses {l:5d} draws {d:5d}  win% {100 * w / (w + l + d):.1f}")
