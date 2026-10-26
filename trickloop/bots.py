# SPDX-License-Identifier: Apache-2.0
"""Bots: a fixed rule-based reference (the "meter") and a parameterised bot that gets trained."""
from __future__ import annotations

import random

from .game import (CAPTAIN, ESCAPE, KIND, PIRATE, POWER, RANK, SIREN, SPECIAL, SUIT, TRUMP,
                   View, trick_winner)


# --------------------------------------------------------------------------------------------
# Reference bot. It never changes: a meter that moves is not a meter.
# --------------------------------------------------------------------------------------------
def _trick_chance(c: int) -> float:
    """Rough chance that card c wins a trick by itself (hand-written, never tuned)."""
    k = KIND[c]
    if k == CAPTAIN:
        return 0.90
    if k == PIRATE:
        return 0.75
    if k == SIREN:
        return 0.50
    if k == ESCAPE:
        return 0.0
    r = RANK[c]
    if SUIT[c] == TRUMP:
        return 0.75 if r >= 9 else 0.45 if r >= 7 else 0.15 if r >= 5 else 0.03
    return 0.40 if r == 10 else 0.22 if r == 9 else 0.08 if r == 8 else 0.0


class RuleBot:
    """Bids the (rounded) expected number of tricks; then tries to win while below its bid and
    to lose once it has reached it."""
    name = "rules"

    def bid(self, v: View) -> int:
        return max(0, min(v.round_no, round(sum(_trick_chance(c) for c in v.hand))))

    def play(self, v: View) -> int:
        want = v.bids[v.seat] - v.won[v.seat]
        winning, losing = [], []
        for c in v.legal:
            (winning if trick_winner(v.plays + [(v.seat, c)]) == v.seat else losing).append(c)
        if want > 0:
            if winning:
                return min(winning, key=lambda c: (POWER[c], c))     # win as cheaply as possible
            return min(losing, key=lambda c: (POWER[c], c))          # cannot win now: keep strength
        if losing:
            return max(losing, key=lambda c: (POWER[c], c))          # dump the strongest card that loses
        return min(winning, key=lambda c: (POWER[c], c))             # forced to win: use the weakest


# --------------------------------------------------------------------------------------------
# Parameterised bot: a linear scoring of legal cards + a linear bid model.
# --------------------------------------------------------------------------------------------
N_PLAY_BASIC, N_PLAY_FULL, N_BID = 10, 17, 12
N_PARAMS = N_PLAY_FULL + N_BID


def _static(c: int) -> tuple:
    k = KIND[c]
    trump = 1.0 if (k == "suit" and SUIT[c] == TRUMP) else 0.0
    plain = 1.0 if (k == "suit" and SUIT[c] != TRUMP) else 0.0
    return (1.0 if k == ESCAPE else 0.0, 1.0 if k == PIRATE else 0.0, 1.0 if k == SIREN else 0.0,
            1.0 if k == CAPTAIN else 0.0, trump, trump * RANK[c] / 10.0, plain * RANK[c] / 10.0,
            POWER[c] / 60.0, 1.0 if SPECIAL[c] else 0.0)


_STATIC = [_static(c) for c in range(48)]


def play_context(v: View) -> tuple:
    want = v.bids[v.seat] - v.won[v.seat]
    after = v.players_after_me / max(1, v.n_players - 1)
    slack = max(-3, min(3, v.tricks_left - want)) / 3.0
    return (1.0 if want > 0 else 0.0, after, slack, 1.0 if not v.plays else 0.0)


def play_features(v: View, c: int, n: int = N_PLAY_FULL, ctx: tuple | None = None) -> list[float]:
    """Features of playing card c now. The first 10 are the "basic" set, all 17 the "full" set."""
    pos, after, slack, leading = ctx or play_context(v)
    esc, pir, sir, cap, trump, rtrump, rplain, power, special = _STATIC[c]
    wins = 1.0 if trick_winner(v.plays + [(v.seat, c)]) == v.seat else 0.0
    f = [esc, pir, sir, cap, trump, rtrump, rplain, wins, wins * pos, wins * (1 - pos)]
    if n > N_PLAY_BASIC:
        f += [power * pos, power * (1 - pos), special * pos, special * (1 - pos),
              wins * after * pos, slack * wins, leading * power]
    return f


def bid_features(v: View) -> list[float]:
    f = [0.0] * N_BID
    for c in v.hand:
        k = KIND[c]
        if k == ESCAPE:
            f[0] += 1
        elif k == PIRATE:
            f[1] += 1
        elif k == SIREN:
            f[2] += 1
        elif k == CAPTAIN:
            f[3] += 1
        elif SUIT[c] == TRUMP:
            f[4 if RANK[c] >= 8 else 5 if RANK[c] >= 5 else 6] += 1
        else:
            f[7 if RANK[c] >= 9 else 8 if RANK[c] >= 7 else 9] += 1
    f[10] = 1.0
    f[11] = float(v.round_no)
    return f


class ParamBot:
    """theta = [17 play weights | 12 bid weights]. `features` ("basic"|"full") masks the play
    weights; `bid_mode` ("learned"|"rules") says whether the bid comes from theta or from RuleBot."""
    name = "param"

    def __init__(self, theta, features: str = "full", bid_mode: str = "learned"):
        self.theta = list(theta)
        self.n_play = N_PLAY_FULL if features == "full" else N_PLAY_BASIC
        self.bid_mode = bid_mode
        self._rules = RuleBot()

    def bid(self, v: View) -> int:
        if self.bid_mode == "rules":
            return self._rules.bid(v)
        w = self.theta[N_PLAY_FULL:]
        x = bid_features(v)
        return max(0, min(v.round_no, round(sum(a * b for a, b in zip(w, x)))))

    def play(self, v: View) -> int:
        if len(v.legal) == 1:
            return v.legal[0]
        w = self.theta[:self.n_play]
        ctx = play_context(v)
        best, best_s = None, None
        for c in v.legal:
            f = play_features(v, c, self.n_play, ctx)
            s = sum(a * b for a, b in zip(w, f))
            if best_s is None or s > best_s or (s == best_s and c < best):
                best, best_s = c, s
        return best


class RandomBot:
    """Plays a random legal card, bids at random: a floor for sanity checks."""
    name = "random"

    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def bid(self, v: View) -> int:
        return self.rng.randint(0, v.round_no)

    def play(self, v: View) -> int:
        return self.rng.choice(v.legal)
