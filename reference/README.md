# reference/ : the code of the real experiment (read-only reference)

These files are the training and measurement code the real research agent used and modified during
the experiment told in `../recit/`. They are published **as a reference of what such a loop looks
like in practice**, not as something you can run from this repository:

* They need the game engine of the original project (a Node.js engine with a headless arena
  `dist/arena.mjs` and a dataset encoder), which is **not** part of this repository.
* `entrainer.py` / `reseau.py` / `exporter.py` need `torch` (BSD-3-Clause license) and `numpy`
  (`pip install -r requirements.txt`) and a dataset produced by that engine (`meta.json`, `x.bin`, ...);
  the weights file format is described in `exporter.py`.
* `benchmark.sh`, `essai.sh`, `promouvoir.sh`, `verifier-candidats.sh` drive remote machines through
  `ssh`/`scp`; the machine aliases and paths are settings (`GAME_HOSTS`, `TRAIN_HOST`, `TRAIN_CMD`,
  `REMOTE_BENCH`, `REMOTE_TRAIN`, `LOOP_DIR`). `promouvoir.sh` also calls a script that restarts the
  game farm, which is specific to the original installation and not provided.
* `tableau.py` rebuilds the original HTML dashboard from the loop's files (`journal.jsonl`,
  `progression.jsonl`, ...) in `LOOP_DIR`. The runnable dashboard of this repository is
  `../trickloop/dashboard.py`.

To see the same loop actually run on your machine, use the self-contained example in `../trickloop/`.
Comments in these files are in French, as written by the agent.
