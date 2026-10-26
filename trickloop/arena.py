# SPDX-License-Identifier: Apache-2.0
"""The meter: one candidate seat against three copies of the fixed reference bot.

Seeds are fixed by label, the candidate rotates through the four seats, so two candidates measured
with the same label see exactly the same deals (that is what makes a paired comparison possible).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .bots import RuleBot
from .game import play_game

N_PLAYERS = 4


@dataclass
class Measure:
    label: str
    games: int
    wins: list[float] = field(repr=False)        # per game: 1, 0 or 1/k when k players tie for first
    points: list[float] = field(repr=False)      # per game: candidate's final score
    opp_points: list[float] = field(repr=False)  # per game: mean score of the three references
    bid_hits: int = 0
    bid_total: int = 0
    bid_bias_sum: float = 0.0                    # sum of (bid - tricks won)

    @property
    def win_rate(self) -> float:
        return sum(self.wins) / self.games

    @property
    def mean_points(self) -> float:
        return sum(self.points) / self.games

    @property
    def mean_opp_points(self) -> float:
        return sum(self.opp_points) / self.games

    @property
    def bid_exact_rate(self) -> float:
        return self.bid_hits / self.bid_total if self.bid_total else 0.0

    @property
    def bid_bias(self) -> float:
        return self.bid_bias_sum / self.bid_total if self.bid_total else 0.0

    def summary(self) -> dict:
        return {"label": self.label, "games": self.games, "win_rate": round(self.win_rate, 4),
                "points": round(self.mean_points, 2), "opp_points": round(self.mean_opp_points, 2),
                "bid_exact_rate": round(self.bid_exact_rate, 4), "bid_bias": round(self.bid_bias, 3)}


def measure(candidate, label: str, games: int, rounds: int = 6, reference_factory=RuleBot) -> Measure:
    m = Measure(label, games, [], [], [])
    for g in range(games):
        seat = g % N_PLAYERS
        bots = [reference_factory() for _ in range(N_PLAYERS)]
        bots[seat] = candidate
        res = play_game(bots, f"{label}-{g}", rounds)
        top = max(res.scores)
        k = sum(1 for s in res.scores if s == top)
        m.wins.append(1.0 / k if res.scores[seat] == top else 0.0)
        m.points.append(res.scores[seat])
        m.opp_points.append((sum(res.scores) - res.scores[seat]) / (N_PLAYERS - 1))
        for rl in res.rounds:
            b, w = rl.bids[seat], rl.won[seat]
            m.bid_total += 1
            m.bid_hits += int(b == w)
            m.bid_bias_sum += b - w
    return m


def paired_delta(a: Measure, b: Measure) -> dict:
    """Candidate a minus champion b on the same deals: difference of win rates with its standard error."""
    assert a.games == b.games and a.label == b.label, "paired comparison needs the same deals"
    d = [x - y for x, y in zip(a.wins, b.wins)]
    n = len(d)
    mean = sum(d) / n
    var = sum((x - mean) ** 2 for x in d) / max(1, n - 1)
    dp = [x - y for x, y in zip(a.points, b.points)]
    return {"win_delta": mean, "win_se": math.sqrt(var / n), "points_delta": sum(dp) / n}
