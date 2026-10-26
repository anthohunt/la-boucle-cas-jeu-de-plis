# SPDX-License-Identifier: Apache-2.0
"""One full loop: diagnose -> gesture -> train at equal budget -> measure -> keep or discard -> journal.

Files written in the work directory:
  champion/{theta,recipe,measure}.json   the current champion
  attempts/<name>.json                   every attempt (recipe, weights, measures)
  journal.jsonl                          one line per mark or attempt (the story of the loop)
  progression.jsonl                      one line per promotion (the staircase)
  state.json                             gestures already tried from the current champion
  dashboard.html                         the dashboard, regenerated after every attempt
"""
from __future__ import annotations

import datetime
import json
import time
from pathlib import Path

from .arena import measure, paired_delta
from .bots import ParamBot, RuleBot
from .dashboard import write_dashboard
from .researcher import ScriptedResearcher, diagnose
from .training import DEFAULT_RECIPE, train, validate_recipe

PRESETS = {
    "normal": {"recipe": {}, "eval_games": 800},
    "fast": {"recipe": {"budget_games": 4800, "games_per_eval": 20, "pop": 24}, "eval_games": 300},
}
DECISION_LABEL = "bench-fixe"        # seeds used to decide
CONTROL_LABEL = "bench-controle"     # seeds used only to confirm, never to decide
MIN_MARGIN = 0.02                    # never conclude on less than +2 points of win rate
POINTS_GUARD = 5.0                   # a promotion may not lose more than this many points per game


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _jwrite(path: Path, row: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _jread(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def _bot(theta, recipe) -> ParamBot:
    return ParamBot(theta, recipe["features"], recipe["bid_mode"])


def run_loop(workdir, passes: int = 4, preset: str = "fast", researcher=None, log=print) -> dict:
    cfg = PRESETS[preset]
    work = Path(workdir)
    (work / "champion").mkdir(parents=True, exist_ok=True)
    (work / "attempts").mkdir(exist_ok=True)
    journal, progression = work / "journal.jsonl", work / "progression.jsonl"
    researcher = researcher or ScriptedResearcher()
    n = cfg["eval_games"]
    base_recipe = validate_recipe({**DEFAULT_RECIPE, **cfg["recipe"]})
    result = {"kept": 0, "discarded": 0, "stopped": None}

    # ---- point zero: is the meter fair, where does the first champion stand, how big is the noise? ----
    ref_fixed = measure(RuleBot(), DECISION_LABEL, n)
    state = _jread(work / "state.json", {"tried": [], "noise": None, "attempt_no": 0})
    if not (work / "champion" / "theta.json").exists():
        log(f"[zero] meter check: reference vs reference = {ref_fixed.win_rate:.1%} wins (fair would be 25.0%)")
        _jwrite(journal, {"mark": f"ZERO POINT. Meter check: three references and one more reference on the same deals win "
                                  f"{ref_fixed.win_rate:.1%} of the games (fair = 25%), {ref_fixed.mean_points:.1f} points. "
                                  f"Preset {preset}: {n} games per seed set, training budget {base_recipe['budget_games']} games.",
                          "date": _now()})
        t0 = time.time()
        log("[zero] training the first champion ...")
        theta, _ = train(base_recipe, seed=0, log=log)
        champ_m = measure(_bot(theta, base_recipe), DECISION_LABEL, n)
        log("[zero] noise check: same recipe, another training seed ...")
        theta2, _ = train(base_recipe, seed=1)
        twin_m = measure(_bot(theta2, base_recipe), DECISION_LABEL, n)
        noise = abs(champ_m.win_rate - twin_m.win_rate)
        state["noise"] = noise
        _save_champion(work, theta, base_recipe, champ_m, measure(_bot(theta, base_recipe), CONTROL_LABEL, n), "champion-0")
        _jwrite(journal, {"mark": f"First champion trained from zero: {champ_m.win_rate:.1%} wins / {champ_m.mean_points:.1f} points "
                                  f"on {DECISION_LABEL}. Same recipe with another training seed: {twin_m.win_rate:.1%}. "
                                  f"Initialisation lottery = {noise * 100:.1f} points of win rate; the keep margin is "
                                  f"max({MIN_MARGIN * 100:.0f}, that) points.", "date": _now(), "seconds": round(time.time() - t0)})
        _jwrite(progression, {"label": "champion-0", "wins": round(champ_m.win_rate, 4), "points": round(champ_m.mean_points, 2),
                              "games": n, "date": _now()})
        state["tried"], state["attempt_no"] = [], 0
        (work / "state.json").write_text(json.dumps(state))
        write_dashboard(journal, work / "dashboard.html", reference=0.25)

    margin = max(MIN_MARGIN, state.get("noise") or 0.0)
    for _ in range(passes):
        champ = _load_champion(work)
        champ_recipe = champ["recipe"]
        diag = diagnose(_measure_from(champ["measure"], n), ref_fixed)
        history = [r for r in _read_rows(journal) if "attempt" in r]
        prop = researcher.propose(champ_recipe, diag, set(state["tried"]), history)
        if prop is None:
            result["stopped"] = "no gesture left in the catalogue: change family of ideas or stop"
            _jwrite(journal, {"mark": "NO GESTURE LEFT for this champion. The loop stops here; a human (or an agent) must "
                                      "extend the catalogue.", "date": _now()})
            log("[loop] " + result["stopped"])
            break
        gid, patch, hypothesis = prop
        state["attempt_no"] += 1
        name = f"{state['attempt_no']:02d}-{gid}"
        recipe = validate_recipe({**champ_recipe, **patch})
        if recipe["budget_games"] != base_recipe["budget_games"]:
            raise ValueError("unequal training budget: attempts are not comparable")
        log(f"[{name}] hypothesis: {hypothesis}")
        t0 = time.time()
        theta, _ = train(recipe, seed=100 + state["attempt_no"], champion_theta=champ["theta"], log=log)
        cand = measure(_bot(theta, recipe), DECISION_LABEL, n)
        cand_c = measure(_bot(theta, recipe), CONTROL_LABEL, n)
        champ_fixed = measure(_bot(champ["theta"], champ_recipe), DECISION_LABEL, n)
        champ_ctrl = measure(_bot(champ["theta"], champ_recipe), CONTROL_LABEL, n)
        d_fix, d_ctl = paired_delta(cand, champ_fixed), paired_delta(cand_c, champ_ctrl)
        reasons = []
        if d_fix["win_delta"] < margin:
            reasons.append(f"win gain on {DECISION_LABEL} {d_fix['win_delta'] * 100:+.1f} pts is under the margin ({margin * 100:.1f})")
        if d_ctl["win_delta"] < 0:
            reasons.append(f"not confirmed on {CONTROL_LABEL} ({d_ctl['win_delta'] * 100:+.1f} pts)")
        if d_fix["points_delta"] < -POINTS_GUARD:
            reasons.append(f"points fell by {-d_fix['points_delta']:.1f} (guard {POINTS_GUARD})")
        keep = not reasons
        verdict = "kept" if keep else "discarded"
        row = {"attempt": name, "gesture": gid, "hypothesis": hypothesis, "recipe_patch": patch,
               "wins": round(cand.win_rate, 4), "points": round(cand.mean_points, 2),
               "champion_wins": round(champ_fixed.win_rate, 4), "champion_points": round(champ_fixed.mean_points, 2),
               "control_wins": round(cand_c.win_rate, 4), "control_champion_wins": round(champ_ctrl.win_rate, 4),
               "delta_wins": round(d_fix["win_delta"], 4), "delta_se": round(d_fix["win_se"], 4), "margin": round(margin, 4),
               "verdict": verdict,
               "reason": "all three tests passed" if keep else "; ".join(reasons),
               "seconds": round(time.time() - t0), "date": _now()}
        _jwrite(journal, row)
        (work / "attempts" / f"{name}.json").write_text(json.dumps({"recipe": recipe, "theta": theta, "row": row}))
        log(f"[{name}] {cand.win_rate:.1%} / {cand.mean_points:.1f} pts vs champion {champ_fixed.win_rate:.1%} / "
            f"{champ_fixed.mean_points:.1f}  ->  {verdict.upper()} ({row['reason']})")
        if keep:
            _save_champion(work, theta, recipe, cand, cand_c, name)
            _jwrite(progression, {"label": name, "wins": row["wins"], "points": row["points"], "games": n, "date": _now()})
            state["tried"] = []                # a new champion: every gesture is worth trying again from it
            result["kept"] += 1
        else:
            state["tried"].append(gid)
            result["discarded"] += 1
        (work / "state.json").write_text(json.dumps(state))
        write_dashboard(journal, work / "dashboard.html", reference=0.25)
    write_dashboard(journal, work / "dashboard.html", reference=0.25)
    result["dashboard"] = str(work / "dashboard.html")
    return result


def _read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip().startswith("{")]


def _save_champion(work: Path, theta, recipe, m, m_ctrl, label):
    (work / "champion" / "theta.json").write_text(json.dumps(theta))
    (work / "champion" / "recipe.json").write_text(json.dumps(recipe, indent=1))
    (work / "champion" / "measure.json").write_text(json.dumps({"label": label, **m.summary(), "control": m_ctrl.summary()}, indent=1))


def _load_champion(work: Path) -> dict:
    return {"theta": json.loads((work / "champion" / "theta.json").read_text()),
            "recipe": json.loads((work / "champion" / "recipe.json").read_text()),
            "measure": json.loads((work / "champion" / "measure.json").read_text())}


class _MeasureView:
    """Just enough of a Measure for diagnose(), rebuilt from the saved summary."""

    def __init__(self, s: dict):
        self.win_rate, self.mean_points = s["win_rate"], s["points"]
        self.bid_exact_rate, self.bid_bias = s["bid_exact_rate"], s["bid_bias"]


def _measure_from(saved: dict, n: int) -> _MeasureView:
    return _MeasureView(saved)
