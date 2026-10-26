# SPDX-License-Identifier: Apache-2.0
"""A small, generic pirate-themed trick-taking game (standard library only).

This is NOT the commercial game that inspired the original experiment: the deck, the names and
the scoring are our own simplification of the general family ("bid how many tricks you will win,
then try to hit your bid exactly"). Game mechanics are not protected; no text, picture or card
art from any commercial game is used here.

Deck (48 cards, card = integer 0..47):
  * 3 plain suits ("coral", "anchor", "shell"), ranks 1..10          ids  0..29
  * 1 trump suit ("flag"), ranks 1..10                                 ids 30..39
  * 3 escapes   (never win a trick, unless everyone escapes)           ids 40..42
  * 3 pirates   (beat every suited card)                               ids 43..45
  * 1 siren     (beats suited cards and the captain, loses to pirates) id 46
  * 1 captain   (beats pirates, loses to the siren)                    id 47

Round r (r = 1..rounds): every player gets r cards, bids a number of tricks 0..r, then r tricks
are played. The first player rotates every round.

Scoring per round: bid 0 -> +10*r if no trick won, else -10*r. Bid b>0 -> +20*b if exactly b
tricks won, else -10*|b - won|.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

SUIT_NAMES = ("coral", "anchor", "shell", "flag")
TRUMP = 3
ESCAPE, PIRATE, SIREN, CAPTAIN = "escape", "pirate", "siren", "captain"

N_CARDS = 48
KIND = [""] * N_CARDS   # "suit" | "escape" | "pirate" | "siren" | "captain"
SUIT = [-1] * N_CARDS   # 0..3 for suited cards, -1 otherwise
RANK = [0] * N_CARDS    # 1..10 for suited cards, 0 otherwise
POWER = [0] * N_CARDS   # a rough strength used by bots (not by the rules)
for _i in range(40):
    KIND[_i], SUIT[_i], RANK[_i] = "suit", _i // 10, _i % 10 + 1
    POWER[_i] = RANK[_i] + (20 if SUIT[_i] == TRUMP else 0)
for _i in range(40, 43):
    KIND[_i], POWER[_i] = ESCAPE, 0
for _i in range(43, 46):
    KIND[_i], POWER[_i] = PIRATE, 50
KIND[46], POWER[46] = SIREN, 45
KIND[47], POWER[47] = CAPTAIN, 60
SPECIAL = [k in (PIRATE, SIREN, CAPTAIN) for k in KIND]


def card_name(c: int) -> str:
    k = KIND[c]
    if k == "suit":
        return f"{SUIT_NAMES[SUIT[c]]}{RANK[c]}"
    return k if k in (SIREN, CAPTAIN) else f"{k}{c - (40 if k == ESCAPE else 43) + 1}"


def trick_winner(plays: list[tuple[int, int]]) -> int:
    """plays = [(seat, card), ...] in play order. Returns the winning seat."""
    cards = [c for _, c in plays]
    has_captain = any(KIND[c] == CAPTAIN for c in cards)
    has_siren = any(KIND[c] == SIREN for c in cards)
    if has_captain and has_siren:
        return next(s for s, c in plays if KIND[c] == SIREN)
    if has_captain:
        return next(s for s, c in plays if KIND[c] == CAPTAIN)
    for s, c in plays:
        if KIND[c] == PIRATE:
            return s
    if has_siren:
        return next(s for s, c in plays if KIND[c] == SIREN)
    suited = [(s, c) for s, c in plays if KIND[c] == "suit"]
    if not suited:                      # everybody escaped: the first card wins
        return plays[0][0]
    trumps = [(s, c) for s, c in suited if SUIT[c] == TRUMP]
    pool = trumps or [(s, c) for s, c in suited if SUIT[c] == SUIT[suited[0][1]]]
    return max(pool, key=lambda p: RANK[p[1]])[0]


def lead_suit(plays: list[tuple[int, int]]) -> int:
    """Suit to follow: the suit of the first suited card played, -1 if none yet."""
    for _, c in plays:
        if KIND[c] == "suit":
            return SUIT[c]
    return -1


def legal_cards(hand: list[int], plays: list[tuple[int, int]]) -> list[int]:
    ls = lead_suit(plays)
    if ls < 0:
        return list(hand)
    follow = [c for c in hand if KIND[c] == "suit" and SUIT[c] == ls]
    if not follow:
        return list(hand)
    return [c for c in hand if c in follow or KIND[c] != "suit"]


def round_score(bid: int, won: int, hand_size: int) -> int:
    if bid == 0:
        return 10 * hand_size if won == 0 else -10 * hand_size
    return 20 * bid if won == bid else -10 * abs(bid - won)


@dataclass
class View:
    """What a bot is allowed to see when it must decide."""
    seat: int
    n_players: int
    round_no: int
    hand: list[int]
    legal: list[int]
    plays: list[tuple[int, int]]            # current trick, in order
    bids: list[int]                         # -1 for players who have not bid yet
    won: list[int]                          # tricks won so far this round, per seat
    played: list[int] = field(default_factory=list)  # cards already played this round (all seats)

    @property
    def tricks_left(self) -> int:           # tricks still to play this round, including this one
        return len(self.hand)

    @property
    def players_after_me(self) -> int:
        return self.n_players - len(self.plays) - 1


@dataclass
class RoundLog:
    bids: list[int]
    won: list[int]
    scores: list[int]


@dataclass
class GameResult:
    scores: list[int]
    rounds: list[RoundLog]


def play_game(bots, seed, rounds: int = 6) -> GameResult:
    """Play one game. `bots` = list of objects with .bid(view) and .play(view). Deterministic in `seed`."""
    n = len(bots)
    rng = random.Random(seed)
    totals = [0] * n
    logs: list[RoundLog] = []
    for r in range(1, rounds + 1):
        deck = list(range(N_CARDS))
        rng.shuffle(deck)
        hands = [sorted(deck[i * r:(i + 1) * r]) for i in range(n)]
        first = (r - 1) % n
        bids = [-1] * n
        played: list[int] = []
        for k in range(n):
            s = (first + k) % n
            v = View(s, n, r, list(hands[s]), list(hands[s]), [], list(bids), [0] * n, [])
            b = int(bots[s].bid(v))
            bids[s] = max(0, min(r, b))
        won = [0] * n
        leader = first
        for _ in range(r):
            plays: list[tuple[int, int]] = []
            for k in range(n):
                s = (leader + k) % n
                legal = legal_cards(hands[s], plays)
                v = View(s, n, r, list(hands[s]), legal, list(plays), list(bids), list(won), list(played))
                c = bots[s].play(v)
                if c not in legal:
                    raise ValueError(f"illegal card {c} by seat {s}")
                hands[s].remove(c)
                plays.append((s, c))
                played.append(c)
            w = trick_winner(plays)
            won[w] += 1
            leader = w
        sc = [round_score(bids[i], won[i], r) for i in range(n)]
        for i in range(n):
            totals[i] += sc[i]
        logs.append(RoundLog(list(bids), list(won), sc))
    return GameResult(totals, logs)
