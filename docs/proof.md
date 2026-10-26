# Install proof (disposable container)

Image `python:3.12-slim` (Python 3.12.15, no torch, no third-party package), fresh copy of this
repository without git history, one CPU. Commands run in the container, then the container was removed:

```
python3 -m unittest discover -s tests -t .
scripts/demo.sh run 3            # meter check + zero point + 3 attempts + dashboard
python3 -m trickloop dashboard recit/journal.jsonl -o /tmp/story.html
python3 -m trickloop loop --researcher agent --workdir /tmp/x     # must stop, call nothing
```

Output (training progress lines left out). The 3-attempt loop took 21 s of CPU; everything is seeded,
so the same numbers come out on any machine with the same Python:

```
Python 3.12.15
0
----------------------------------------------------------------------
Ran 20 tests in 1.612s
OK
{"label": "bench-fixe", "games": 200, "win_rate": 0.2592, "points": 63.25, "opp_points": 60.65, "bid_exact_rate": 0.6608, "bid_bias": -0.272}
[zero] meter check: reference vs reference = 25.2% wins (fair would be 25.0%)
[zero] training the first champion ...
[zero] noise check: same recipe, another training seed ...
[01-bid-from-rules] hypothesis: The champion hits its bid 51% of the time, the reference 65%. Bidding and playing are two different problems: let the reference choose the bid and spend the whole train
[01-bid-from-rules] 21.8% / 55.6 pts vs champion 10.3% / -26.0  ->  KEPT (all three tests passed)
[02-full-features] hypothesis: The play model only sees 10 features (card kind, rank, 'would win now'). Adding the 7 interaction features (strength x need to win, risk of being overtaken, slack) gives
[02-full-features] 21.7% / 56.2 pts vs champion 21.8% / 55.6  ->  DISCARDED (win gain on bench-fixe -0.1 pts is under the margin (2.9); not confirmed on bench-controle (-1.3 pts))
[03-warm-restart] hypothesis: Restart from the champion's weights with smaller perturbations instead of from zero: the same budget refines what is already learned rather than rediscovering it.
[03-warm-restart] 29.2% / 68.3 pts vs champion 21.8% / 55.6  ->  KEPT (all three tests passed)
{"kept": 2, "discarded": 1, "stopped": null, "dashboard": "run/dashboard.html"}
journal:   run/journal.jsonl
dashboard: run/dashboard.html
wrote /tmp/story.html
 5376 run/dashboard.html
44572 /tmp/story.html
49948 total
STOP: the 'agent' researcher would call a paid Claude agent. Nothing was called.
To go on: make sure the `claude` CLI is logged in (or ANTHROPIC_API_KEY is set), then run again with
  TRICKLOOP_ALLOW_PAID_AGENT=1 [TRICKLOOP_AGENT_CMD='claude -p'] python3 -m trickloop loop --researcher agent ...
The scripted researcher (default) needs no key.
agent-stop exit code=3
```

Reading it: the first champion, trained from zero with the learned bid, is very weak (10 %). Attempt 1
(use the reference's bid, learn only the card to play) is kept; attempt 2 (more features) is
discarded for being under the margin and not confirmed on the control deals; attempt 3 (restart from the
champion with smaller steps) is kept. A 5-attempt run (not in the container) discarded two more and kept none.
This is a toy: the point is the mechanics of keep/discard on a fixed meter, not the numbers.

Not exercised: the paid agent researcher beyond its stop (no key); the `reference/` code (needs the
original engine and torch).
