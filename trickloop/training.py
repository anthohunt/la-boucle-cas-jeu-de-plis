# SPDX-License-Identifier: Apache-2.0
"""Training of the parameterised bot: evolution strategies with antithetic sampling, common
random numbers (all candidates of a generation play the same deals) and rank-shaped updates.

The recipe is a plain dict (see DEFAULT_RECIPE). Changing the recipe is what the researcher does.
Every recipe gets the SAME budget of training games (`budget_games`): two attempts are only
comparable at equal budget.
"""
from __future__ import annotations

import math
import random
import time

from .arena import N_PLAYERS
from .bots import N_PARAMS, N_PLAY_BASIC, N_PLAY_FULL, ParamBot, RuleBot
from .game import play_game

DEFAULT_RECIPE = {
    "budget_games": 24000,    # total games the training may play (fixed budget, same for every attempt)
    "pop": 24,                # candidates per generation (even: antithetic pairs)
    "games_per_eval": 40,     # games used to score one candidate
    "sigma": 0.5,             # std of the perturbations
    "lr": 0.35,               # step size
    "sigma_decay": 0.97,      # per generation
    "win_weight": 0.5,        # fitness = win_weight*win_rate + (1-win_weight)*points/100
    "features": "basic",      # "basic" (10 play features) | "full" (17)
    "bid_mode": "learned",    # "learned" | "rules" (use the reference's bid, learn only the play)
    "init": "zeros",          # "zeros" | "warm" (start from the champion)
}
RECIPE_KEYS = set(DEFAULT_RECIPE)
CHOICES = {"features": {"basic", "full"}, "bid_mode": {"learned", "rules"}, "init": {"zeros", "warm"}}


def validate_recipe(r: dict) -> dict:
    out = dict(DEFAULT_RECIPE)
    for k, v in r.items():
        if k not in RECIPE_KEYS:
            raise ValueError(f"unknown recipe key: {k}")
        if k in CHOICES and v not in CHOICES[k]:
            raise ValueError(f"recipe {k} must be one of {sorted(CHOICES[k])}")
        out[k] = v
    if out["pop"] % 2 or out["pop"] < 4:
        raise ValueError("pop must be even and >= 4")
    if not 0.0 <= out["win_weight"] <= 1.0:
        raise ValueError("win_weight must be in [0,1]")
    if out["budget_games"] < out["pop"] * out["games_per_eval"]:
        raise ValueError("budget_games is smaller than one generation")
    return out


def _mask(recipe) -> list[float]:
    m = [1.0] * N_PARAMS
    if recipe["features"] == "basic":
        for i in range(N_PLAY_BASIC, N_PLAY_FULL):
            m[i] = 0.0
    if recipe["bid_mode"] == "rules":
        for i in range(N_PLAY_FULL, N_PARAMS):
            m[i] = 0.0
    return m


def _fitness(theta, recipe, seed_label, n_games) -> float:
    bot = ParamBot(theta, recipe["features"], recipe["bid_mode"])
    ref = RuleBot()
    acc_w = acc_p = 0.0
    for j in range(n_games):
        seat = j % N_PLAYERS
        bots = [ref] * N_PLAYERS
        bots[seat] = bot
        res = play_game(bots, f"{seed_label}-{j}")
        top = max(res.scores)
        if res.scores[seat] == top:
            acc_w += 1.0 / sum(1 for s in res.scores if s == top)
        acc_p += res.scores[seat]
    ww = recipe["win_weight"]
    return ww * acc_w / n_games + (1 - ww) * (acc_p / n_games) / 100.0


def train(recipe: dict, seed: int, champion_theta=None, log=None):
    """Returns (theta, history). `history` has one entry per generation."""
    recipe = validate_recipe(recipe)
    rng = random.Random(f"es-{seed}")
    mask = _mask(recipe)
    if recipe["init"] == "warm" and champion_theta is not None:
        theta = [t * m for t, m in zip(champion_theta, mask)]
    else:
        theta = [0.0] * N_PARAMS
    pop, gpe = recipe["pop"], recipe["games_per_eval"]
    generations = recipe["budget_games"] // (pop * gpe)
    sigma = recipe["sigma"]
    history = []
    t0 = time.time()
    for gen in range(generations):
        eps = []
        for _ in range(pop // 2):
            e = [rng.gauss(0, 1) * m for m in mask]
            eps.append(e)
            eps.append([-x for x in e])
        label = f"train-{seed}-{gen}"             # common random numbers inside the generation
        fits = [_fitness([t + sigma * x for t, x in zip(theta, e)], recipe, label, gpe) for e in eps]
        order = sorted(range(pop), key=lambda i: fits[i])
        util = [0.0] * pop
        for rank, i in enumerate(order):
            util[i] = rank / (pop - 1) - 0.5
        grad = [sum(util[i] * eps[i][d] for i in range(pop)) / (pop * sigma) for d in range(N_PARAMS)]
        theta = [t + recipe["lr"] * g for t, g in zip(theta, grad)]
        sigma *= recipe["sigma_decay"]
        entry = {"gen": gen, "mean_fitness": sum(fits) / pop, "best_fitness": max(fits), "sigma": sigma}
        history.append(entry)
        if log and (gen % 10 == 0 or gen == generations - 1):
            log(f"  gen {gen + 1}/{generations}  mean fitness {entry['mean_fitness']:.3f}  best {entry['best_fitness']:.3f}"
                f"  ({time.time() - t0:.0f}s)")
    return [round(t, 6) for t in theta], history
