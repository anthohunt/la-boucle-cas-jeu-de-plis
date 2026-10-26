# SPDX-License-Identifier: Apache-2.0
"""The researcher: looks at what the meter says about the champion (diagnosis), picks ONE change
to the training recipe (gesture), writes down why (hypothesis).

Two researchers:
  * ScriptedResearcher: a deterministic catalogue of gestures, ordered by family. Free, offline,
    reproducible. This is what the demo and the tests use.
  * AgentResearcher: asks a Claude agent for the next recipe change. It is a PAID step and it is
    off by default: without the explicit opt-in below it stops, calls nothing, and says so.
    It was not exercised by the install proof (no key was available there).
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess

from .training import CHOICES, RECIPE_KEYS, validate_recipe

# (id, family, patch | patch(recipe), applies(recipe, diag) -> bool, why(diag) -> str)
GESTURES = [
    ("bid-from-rules", "model",
     {"bid_mode": "rules"},
     lambda r, d: r["bid_mode"] == "learned" and d["bid_exact_rate"] < d["ref_bid_exact_rate"] - 0.03,
     lambda d: f"The champion hits its bid {d['bid_exact_rate']:.0%} of the time, the reference {d['ref_bid_exact_rate']:.0%}. "
               "Bidding and playing are two different problems: let the reference choose the bid and spend the whole "
               "training budget on the card to play."),
    ("full-features", "model",
     {"features": "full"},
     lambda r, d: r["features"] == "basic",
     lambda d: "The play model only sees 10 features (card kind, rank, 'would win now'). Adding the 7 interaction features "
               "(strength x need to win, risk of being overtaken, slack) gives it a way to express 'win cheaply when I "
               "need the trick, dump high when I do not'."),
    ("warm-restart", "optimiser",
     {"init": "warm", "sigma": 0.25},
     lambda r, d: r["init"] == "zeros",
     lambda d: "Restart from the champion's weights with smaller perturbations instead of from zero: the same budget "
               "refines what is already learned rather than rediscovering it."),
    ("fewer-noisier-more-games", "optimiser",
     lambda r: {"games_per_eval": r["games_per_eval"] * 2, "pop": max(4, (r["pop"] // 4) * 2)},
     lambda r, d: r["games_per_eval"] <= 80,
     lambda d: "Each candidate is scored on a few dozen games, so its fitness is mostly luck of the deal (a win rate "
               "on that few games has a standard error of several points). Score half as many candidates on twice "
               "as many games each."),
    ("win-weight-up", "objective",
     {"win_weight": 0.85},
     lambda r, d: r["win_weight"] < 0.8,
     lambda d: "The meter's decisive number is the win rate, but the training fitness is half points. Weight the fitness "
               "towards wins."),
    ("smaller-steps", "optimiser",
     {"lr": 0.2, "sigma": 0.3},
     lambda r, d: r["lr"] > 0.2,
     lambda d: "Plateau suspected: smaller steps and smaller perturbations to stop jumping around the optimum."),
    ("points-weight-up", "objective",
     {"win_weight": 0.2},
     lambda r, d: r["win_weight"] > 0.3,
     lambda d: "Points are a denser signal than wins (a game gives one win bit but 6 rounds of points): weight the "
               "fitness towards points to reduce the noise of the training signal."),
]


def diagnose(champion_measure, reference_measure) -> dict:
    return {
        "win_rate": champion_measure.win_rate,
        "points": champion_measure.mean_points,
        "bid_exact_rate": champion_measure.bid_exact_rate,
        "bid_bias": champion_measure.bid_bias,
        "ref_bid_exact_rate": reference_measure.bid_exact_rate,
        "ref_win_rate": reference_measure.win_rate,
    }


class ScriptedResearcher:
    name = "scripted"

    def propose(self, champion_recipe: dict, diag: dict, tried: set[str], history: list[dict]):
        """Returns (gesture_id, patch, hypothesis) or None when the catalogue is exhausted."""
        for gid, _family, patch, applies, why in GESTURES:
            if gid in tried:
                continue
            if applies(champion_recipe, diag):
                return gid, dict(patch(champion_recipe) if callable(patch) else patch), why(diag)
        return None


class NeedsPaidAgent(RuntimeError):
    """Raised when the agent researcher is selected without the explicit paid opt-in."""


PROMPT = """You are the researcher of an automated improvement loop. A bot for a small trick-taking
game is trained by evolution strategies; a fixed meter measures it against a rule-based reference
bot. You may change ONLY the training recipe, and propose ONE change per attempt.

Allowed recipe keys and defaults: {keys}
Allowed values for enumerated keys: {choices}
Fixed rule: the total training budget (budget_games) must stay {budget}.

Current champion recipe: {recipe}
Latest diagnosis (win rate, points, how often it hits its bid, reference figures): {diag}
Gestures already tried from this champion (all discarded): {tried}
Recent verdicts: {history}

Answer with ONE JSON object only: {{"gesture": "<short-id>", "patch": {{...}}, "hypothesis": "<one or two sentences: what you saw, what you change, what you expect>"}}"""


class AgentResearcher:
    name = "agent"

    def __init__(self, budget: int):
        self.budget = budget

    def _command(self) -> list[str]:
        if os.environ.get("TRICKLOOP_ALLOW_PAID_AGENT") != "1":
            raise NeedsPaidAgent(
                "STOP: the 'agent' researcher would call a paid Claude agent. Nothing was called.\n"
                "To go on: make sure the `claude` CLI is logged in (or ANTHROPIC_API_KEY is set), then run again with\n"
                "  TRICKLOOP_ALLOW_PAID_AGENT=1 [TRICKLOOP_AGENT_CMD='claude -p'] python3 -m trickloop loop --researcher agent ...\n"
                "The scripted researcher (default) needs no key.")
        return shlex.split(os.environ.get("TRICKLOOP_AGENT_CMD", "claude -p"))

    def propose(self, champion_recipe, diag, tried, history):
        cmd = self._command()
        prompt = PROMPT.format(keys=json.dumps(sorted(RECIPE_KEYS)), choices={k: sorted(v) for k, v in CHOICES.items()},
                               budget=self.budget, recipe=json.dumps(champion_recipe), diag=json.dumps(diag),
                               tried=sorted(tried), history=json.dumps(history[-5:]))
        out = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=600)
        if out.returncode != 0:
            raise RuntimeError(f"agent command failed: {out.stderr[:300]}")
        text = out.stdout
        a, b = text.find("{"), text.rfind("}")
        data = json.loads(text[a:b + 1])
        patch = dict(data["patch"])
        patch.pop("budget_games", None)                  # the budget is not the researcher's to change
        validate_recipe({**champion_recipe, **patch})    # refuses unknown keys / values
        return str(data.get("gesture", "agent-gesture")), patch, str(data.get("hypothesis", ""))
