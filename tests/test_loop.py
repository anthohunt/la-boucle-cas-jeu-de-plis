# SPDX-License-Identifier: Apache-2.0
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from trickloop.arena import measure, paired_delta
from trickloop.bots import N_PARAMS, ParamBot, RandomBot, RuleBot
from trickloop.dashboard import read_journal, render
from trickloop.researcher import GESTURES, AgentResearcher, NeedsPaidAgent, ScriptedResearcher
from trickloop.training import DEFAULT_RECIPE, train, validate_recipe

ROOT = Path(__file__).resolve().parent.parent
TINY = {"budget_games": 480, "pop": 8, "games_per_eval": 10}


class TestMeter(unittest.TestCase):
    def test_reference_against_itself_is_fair(self):
        m = measure(RuleBot(), "meter-check", 400)
        self.assertAlmostEqual(m.win_rate, 0.25, delta=0.05)        # 4 equal players -> about 25 %

    def test_same_label_same_deals(self):
        a, b = measure(RuleBot(), "same", 40), measure(RuleBot(), "same", 40)
        self.assertEqual(a.wins, b.wins)
        self.assertEqual(paired_delta(a, b)["win_delta"], 0.0)

    def test_random_bot_is_clearly_worse(self):
        self.assertLess(measure(RandomBot(1), "floor", 200).win_rate, 0.10)


class TestTraining(unittest.TestCase):
    def test_recipe_validation(self):
        validate_recipe({})
        for bad in ({"nope": 1}, {"features": "x"}, {"pop": 5}, {"budget_games": 10}, {"win_weight": 2}):
            with self.assertRaises(ValueError):
                validate_recipe(bad)

    def test_training_is_deterministic_and_has_the_right_shape(self):
        t1, h1 = train({**DEFAULT_RECIPE, **TINY}, seed=3)
        t2, _ = train({**DEFAULT_RECIPE, **TINY}, seed=3)
        self.assertEqual(t1, t2)
        self.assertEqual(len(t1), N_PARAMS)
        self.assertEqual(len(h1), 480 // (8 * 10))

    def test_masked_weights_stay_zero(self):
        theta, _ = train({**DEFAULT_RECIPE, **TINY, "features": "basic", "bid_mode": "rules"}, seed=1)
        self.assertTrue(all(w == 0 for w in theta[10:]))      # no full-only play weight, no bid weight


class TestResearcher(unittest.TestCase):
    DIAG = {"win_rate": 0.1, "points": -20, "bid_exact_rate": 0.5, "bid_bias": -0.8,
            "ref_bid_exact_rate": 0.65, "ref_win_rate": 0.25}

    def test_scripted_researcher_skips_what_was_tried(self):
        r = ScriptedResearcher()
        gid, patch, why = r.propose(dict(DEFAULT_RECIPE), self.DIAG, set(), [])
        self.assertEqual(gid, "bid-from-rules")
        self.assertEqual(patch, {"bid_mode": "rules"})
        self.assertTrue(why)
        gid2, _, _ = r.propose(dict(DEFAULT_RECIPE), self.DIAG, {"bid-from-rules"}, [])
        self.assertEqual(gid2, "full-features")
        self.assertIsNone(r.propose(dict(DEFAULT_RECIPE), self.DIAG, {g[0] for g in GESTURES}, []))

    def test_agent_researcher_stops_without_opt_in(self):
        os.environ.pop("TRICKLOOP_ALLOW_PAID_AGENT", None)
        with self.assertRaises(NeedsPaidAgent):
            AgentResearcher(1000).propose(dict(DEFAULT_RECIPE), self.DIAG, set(), [])

    def test_cli_agent_mode_exits_3_and_calls_nothing(self):
        env = {k: v for k, v in os.environ.items() if k != "TRICKLOOP_ALLOW_PAID_AGENT"}
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run([sys.executable, "-m", "trickloop", "loop", "--researcher", "agent", "--workdir", d],
                               cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(p.returncode, 3)
            self.assertIn("paid", p.stderr)
            self.assertEqual(os.listdir(d), [])                 # nothing was started


class TestDashboard(unittest.TestCase):
    def test_renders_both_journals(self):
        rows = [{"mark": "zero <b>point</b>"},
                {"attempt": "01-x", "hypothesis": "h", "wins": 0.3, "points": 70.0, "champion_wins": 0.2, "champion_points": 60.0,
                 "verdict": "kept", "reason": "ok"},
                {"attempt": "02-y", "hypothesis": "h2", "wins": 0.2, "verdict": "discarded", "reason": "no"}]
        h = render(rows, "T", reference=0.25)
        self.assertIn("KEPT", h)
        self.assertIn("DISCARDED", h)
        self.assertNotIn("<b>point</b>", h)                       # escaped
        story = read_journal(ROOT / "recit" / "journal.jsonl")    # the real experiment, French keys
        self.assertGreater(len([r for r in story if "attempt" in r]), 5)
        self.assertIn("kept", render(story, "story"))


if __name__ == "__main__":
    unittest.main()
