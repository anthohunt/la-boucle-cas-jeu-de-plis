# SPDX-License-Identifier: Apache-2.0
"""Command line: python3 -m trickloop <command>."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .arena import measure
from .bots import N_PARAMS, ParamBot, RandomBot, RuleBot
from .dashboard import write_dashboard
from .game import card_name, play_game
from .loop import PRESETS, run_loop
from .researcher import AgentResearcher, NeedsPaidAgent, ScriptedResearcher
from .training import DEFAULT_RECIPE, train, validate_recipe


def _cmd_play(a):
    bots = [RuleBot() for _ in range(4)]
    res = play_game(bots, a.seed, a.rounds)
    for i, rl in enumerate(res.rounds, 1):
        print(f"round {i}: bids {rl.bids}  tricks {rl.won}  scores {rl.scores}")
    print("final scores:", res.scores)


def _cmd_measure(a):
    if a.theta:
        theta = json.loads(Path(a.theta).read_text())
        recipe = validate_recipe(json.loads(Path(a.recipe).read_text())) if a.recipe else DEFAULT_RECIPE
        cand = ParamBot(theta, recipe["features"], recipe["bid_mode"])
    else:
        cand = {"rules": RuleBot, "random": RandomBot}[a.bot]()
    print(json.dumps(measure(cand, a.label, a.games).summary()))


def _cmd_train(a):
    recipe = validate_recipe(json.loads(Path(a.recipe).read_text()) if a.recipe else {})
    theta, _ = train(recipe, a.seed, log=print)
    Path(a.out).write_text(json.dumps(theta))
    print(f"wrote {a.out} ({N_PARAMS} weights)")


def _cmd_loop(a):
    if a.researcher == "agent":
        base = {**DEFAULT_RECIPE, **PRESETS[a.preset]["recipe"]}
        researcher = AgentResearcher(base["budget_games"])
        try:
            researcher._command()                      # fail early, before any training starts
        except NeedsPaidAgent as e:
            print(e, file=sys.stderr)
            return 3
    else:
        researcher = ScriptedResearcher()
    res = run_loop(a.workdir, a.passes, a.preset, researcher, log=print)
    print(json.dumps(res))
    return 0


def _cmd_dashboard(a):
    out = write_dashboard(a.journal, a.out, a.title, reference=0.25 if a.reference else None)
    print(f"wrote {out}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="trickloop", description="Self-improvement loop on a small pirate trick-taking game.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("play", help="play one game between four reference bots and print it")
    s.add_argument("--seed", default="demo")
    s.add_argument("--rounds", type=int, default=6)
    s.set_defaults(fn=_cmd_play)
    s = sub.add_parser("measure", help="measure a bot against three reference bots")
    s.add_argument("--bot", choices=["rules", "random"], default="rules")
    s.add_argument("--theta", help="weights file produced by `train` or by the loop")
    s.add_argument("--recipe", help="recipe file matching the weights")
    s.add_argument("--games", type=int, default=400)
    s.add_argument("--label", default="bench-fixe")
    s.set_defaults(fn=_cmd_measure)
    s = sub.add_parser("train", help="train the parameterised bot with one recipe")
    s.add_argument("--recipe", help="JSON file (see DEFAULT_RECIPE in training.py)")
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--out", default="theta.json")
    s.set_defaults(fn=_cmd_train)
    s = sub.add_parser("loop", help="run the improvement loop (zero point, then N attempts)")
    s.add_argument("--workdir", default="run")
    s.add_argument("--passes", type=int, default=4)
    s.add_argument("--preset", choices=sorted(PRESETS), default="fast")
    s.add_argument("--researcher", choices=["scripted", "agent"], default="scripted")
    s.set_defaults(fn=_cmd_loop)
    s = sub.add_parser("dashboard", help="render an HTML dashboard from a journal (also reads recit/journal.jsonl)")
    s.add_argument("journal")
    s.add_argument("-o", "--out", default="dashboard.html")
    s.add_argument("--title", default="Loop dashboard")
    s.add_argument("--reference", action="store_true", help="draw the 25%% line (equal strength)")
    s.set_defaults(fn=_cmd_dashboard)
    a = p.parse_args(argv)
    return a.fn(a) or 0
