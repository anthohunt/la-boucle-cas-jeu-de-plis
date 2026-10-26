# What is not shipped, and how to get it back

| left out | why | how to regenerate |
|---|---|---|
| network weights (`reseau.bin`, `reseau.pt`), champions | large, binary, tied to one encoding | `reference/entrainer.py` on a dataset (below); or, for the example, `python3 -m trickloop loop` rebuilds a champion in under a minute |
| recorded games (`parties-*.jsonl`, about gigabytes) and encoded snapshots (`x.bin`, `masque.bin`, ...) | size; they are produced by the game engine | run the original game engine's recorder with bots playing each other, with a small exploration rate (about 10 % random legal moves) and **time-stamped seeds** (two launches must never replay the same deals), then encode with its dataset tool. The format read by `entrainer.py` is `meta.json` + `x.bin` (uint8 inputs) + `masque.bin` (legal moves) + `coup.bin` (played move) + `y.bin` (outcome) + `lieu.bin`/`lieu-masque.bin` (hidden card locations) |
| raw logs (`ferme.log`, `chercheur.log`, `incidents.log`) | operational noise, machine names | not needed: `recit/journal.jsonl` is the distilled record |
| the game engine and the production bots | another project, and the commercial game's name and art are not ours | none: the `trickloop/` example replaces it |
| the original paper PDF | not redistributable | [arXiv:1912.11323](https://arxiv.org/abs/1912.11323) |

## Weights file format (`reference/exporter.py`)
4 bytes little-endian = length of the JSON header, the header (`versionEncodage`, `entrees`, `coups`,
`cartes`, `emplacements`, list of tensors with name and shape), then all tensors in half precision (float16), C order.
Layer names are cleaned: `tronc.0.lin.weight` becomes `tronc.0.weight`.

## Redoing the real experiment
You need an engine with (1) a rules package that is never touched by the researcher, (2) a headless arena
that plays a candidate against the reference with fixed seeds and alternating seats, (3) a recorder and a
dataset encoder. Then follow `recit/mission.md` and `recit/program.md`; the fixed meter is `reference/benchmark.sh`.
Keep the three rules that cost the most to learn: the meter never moves; measure at a fixed number of
simulations, never by the clock; never conclude below the initialisation lottery.
