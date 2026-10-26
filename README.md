# la-boucle-cas-jeu-de-plis

A worked case of **La boucle** ("the loop"): an automatic improvement loop with no human in it. A
research agent changes how a bot of a pirate trick-taking game (of the Skull King type) is trained,
a fixed meter measures it against the rule-based reference bot, and the change is **kept or thrown
away** by the numbers. This repository has two parts:

| | what | language | licence |
|---|---|---|---|
| [`recit/`](recit/) | the **real experiment**, five days, told through the files the agent itself used: mission, method, memory notebook, journal of every attempt, staircase of results | French | CC BY 4.0 |
| [`trickloop/`](trickloop/) | a **small, self-contained, runnable version** of the same loop on a generic pirate trick-taking game written for this repository (standard library only, no model, no key) | English | Apache 2.0 |
| [`reference/`](reference/) | the real training / measurement code of the experiment (needs the original game engine and torch: read-only reference) | French comments | Apache 2.0 |

> Not affiliated with Grandpa Beck's Games; Skull King is a trademark of its owner. No rules text, illustrations or card art from the commercial game are included.

The game in `trickloop/` is our own simplified pirate trick-taking game (48 cards, bids, six rounds):
the general mechanics of the family, with our own deck and scoring (see the docstring of
[`trickloop/game.py`](trickloop/game.py)). The method itself (benches, sealed exam, judge, attempts
tree) is **not** copied here: it lives in
[`la-boucle-engine`](https://github.com/anthohunt/la-boucle-engine) (see its README and
`docs/method.md`). This repository is a case study that shows the loop on a bot.

## What happened in the real experiment (five days)

An agent was given a mission file ([`recit/mission.md`](recit/mission.md)): make the game's bots
stronger, measured as **games won** (decisive) and **average points** (guard) against the rule-based
bot of the production game, a Monte-Carlo search bot. Full freedom of method, one hard rule: the meter
never moves. Figures below are from [`recit/journal.jsonl`](recit/journal.jsonl) and
[`recit/progression.jsonl`](recit/progression.jsonl) (400 deals per measure unless said otherwise).

* Starting point (after a reset, see below): the trained network wins 47.1 % of the games and scores 196.3 points per game, against 197.1 for the reference bot.
* The agent first trained a network head that guesses where the hidden cards are. A "champion" reached 59.6 % / 204.0 points, confirmed once on fresh deals (+2.1 points paired). **Three more rounds of the same recipe all fell back to 49-52 %**: the 59.6 % was largely a lucky draw. Initialisation alone moves results by about 1.6 points.
* It then found a lever that was not machine learning: more simulated deals per move for its own seat (16 → 48: 60.6 % / 224.6). Mapping the win rate against thinking time showed a plateau between 750 and 1000 ms.
* **Isolation test:** the rule bot alone at 1000 ms (64.1 % / 236.6) equals the champion with its network (64.3 % / 232.6). **The trained network added nothing.** The research was redirected to the search itself.
* A sweep of evaluation weights found one "winner" (+4.3 points of win rate over 800 deals) that **disappeared when the measure was made without a time limit** (62.8 % vs 64.1 %): it was an artefact of time-bounded measuring on a machine that could not complete its simulations in time. Thirteen weight variants, three sample budgets, six time budgets and eight training rounds ended with: no change to the weights, no network.
* **Delivered and put in production:** rules + 256 simulated deals per move: **63.8 % / 239.4 points over 1600 deals vs 60.0 % / 220.9 over 1200 deals for the bot that was in production** (+3.8 points of win rate, +18.5 points per game) from a single setting.

The most valuable outputs were a one-line change and a negative result (the network is useless at equal search budget), plus measurement mistakes caught on the way: two machines judging with two different builds of the judge for two days; 20 % duplicate deals in the production data; a relative measure ("share of points taken from the current champion") that rewarded a champion for beating its predecessor while losing to everyone else. The method that corrects them is in [`recit/program.md`](recit/program.md); two side experiments and their adversarial reviews are in [`recit/experiences-annexes.md`](recit/experiences-annexes.md).

The human wrote and rewrote the mission, and stopped the experiment and ordered the deployment; no human validated individual attempts.
A paper on a closely related card game is cited for background: Cohensius, Meir, Oved, Stern, *Bidding in Spades*, [arXiv:1912.11323](https://arxiv.org/abs/1912.11323) (not redistributed here).

## Run the example loop (no key, no model, standard library)

Python ≥ 3.10.

```bash
git clone <this repository> && cd la-boucle-cas-jeu-de-plis
python3 -m unittest discover -s tests -t .       # 20 tests, a few seconds

python3 -m trickloop play --seed demo            # one game between four reference bots
python3 -m trickloop measure --bot rules         # the meter checks itself: about 25 % (four equal players)
python3 -m trickloop loop --workdir run --passes 4 --preset fast
python3 -m trickloop dashboard recit/journal.jsonl -o story.html   # the REAL experiment's journal as a dashboard
```

`loop` does, in order (this is the real loop, in miniature):

1. **Zero point**: checks the meter is fair (reference vs reference ≈ 25 %), trains a first champion
   from nothing, then trains the same recipe again with another seed to measure the *initialisation
   lottery*; the keep margin is `max(2 points, lottery)`.
2. For each pass: **diagnosis** (how often does the champion hit its bid? how does that compare
   with the reference?) → one **gesture** (a single change of the training recipe, with its
   hypothesis written down) → training at the **same budget of games** as every other attempt →
   **measure** on fixed deals (`bench-fixe`) and on a **control** set used only to confirm
   (`bench-controle`), paired with the champion on the same deals → **keep or discard**:
   kept only if the win gain is above the margin, not negative on the control set, and the points
   do not fall by more than 5 per game.
3. Every attempt is written to `journal.jsonl` (hypothesis, numbers, verdict, reason), promotions to
   `progression.jsonl`, and `dashboard.html` is regenerated (open it in a browser; no script, no
   network).

Presets: `fast` (a few minutes on a laptop; 300 deals per set, so a verdict can be noise: that is
shown by the margin) and `normal` (800 deals per set, five times the training budget). The numbers
vary with the preset, not with the machine: everything is seeded. A real run, with its output, is
described in [`docs/proof.md`](docs/proof.md).

### The researcher, and the one paid step
By default the researcher is **scripted** (`trickloop/researcher.py`): a deterministic catalogue of
gestures ordered by family, each applicable under a condition on the diagnosis, none retried from the
same champion. It is free and reproducible.

`--researcher agent` asks a Claude agent for the next recipe change instead. **That step is paid and
stops by itself**: unless you set `TRICKLOOP_ALLOW_PAID_AGENT=1` (and have the `claude` CLI logged in,
or `TRICKLOOP_AGENT_CMD` pointing to your own command), it prints why, exits with code 3 and
calls nothing. The agent's answer is validated against the recipe's allowed keys, and the training
budget cannot be changed. This path was **not exercised** in the install proof (no key was available);
the stop was tested.

## How the example maps to the real experiment

| real experiment (`recit/`, `reference/`) | `trickloop/` |
|---|---|
| game engine of the commercial-style game (Node.js, not included) | `game.py`: small generic engine |
| reference = rule bot with Monte-Carlo search | `bots.RuleBot` (fixed, never tuned) |
| network trained by PyTorch (`entrainer.py`) | `ParamBot` (linear card scoring + bid model) trained by evolution strategies (`training.py`) |
| `benchmark.sh`: fixed seeds, 400 deals, seats rotated | `arena.measure`: fixed labels, candidate rotates through the 4 seats |
| "never conclude below +2 points" (initialisation lottery 1.6) | margin = `max(2 points, measured lottery)` |
| confirmation on a second set of deals | `bench-controle` |
| equal training time per attempt | equal training budget in games |
| journal + HTML dashboard (`tableau.py`) | `journal.jsonl` + `dashboard.py` |

The gate used here is deliberately simple. The full gate (sealed exam, paired comparison, second
confirming run, forbidden errors, pause after two failures) is in
[`la-boucle-engine`](https://github.com/anthohunt/la-boucle-engine).

## What is not in this repository, and how to regenerate it
No weights (`.bin`, `.pt`), no recorded games, no datasets, no training snapshots, no raw logs. The
example regenerates everything it needs in seconds (`python3 -m trickloop loop`). To redo the real
experiment you need the game engine; see [`docs/regenerate.md`](docs/regenerate.md).

## Licences and third parties
* Code (`trickloop/`, `reference/`, `tests/`): Apache 2.0, see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
* Narrative, journal and docs (`recit/`, `docs/`, this README): CC BY 4.0, see [`LICENSE-docs`](LICENSE-docs).
* `trickloop/` has **no dependency** beyond the Python standard library. `reference/` needs
  `numpy` (BSD-3-Clause) and `torch` (BSD-3-Clause-style licence), not bundled.
* The arXiv paper above is only linked.

## Limits
* The example game is small and our own: its numbers say nothing about the commercial game. A learned bot that beats the reference here would not be a result about that game.
* In `fast` mode the measures are short; a "kept" verdict can still be luck (that is why the control set and the margin exist, and why the journal prints both).
* The real experiment ran on one game and one reference bot, for five days; its lessons are method lessons, not a benchmark.
