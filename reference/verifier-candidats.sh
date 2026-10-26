#!/bin/bash
# Verification des points prometteurs du graphique (demande de l'operateur, J5) : chaque candidat est rejoue
# SANS limite de temps (nombre de tirages fixe, resultat deterministe) sur les MEMES graines neuves
# que la config finale (conf-budget, graine3-0915, graine4-0915), 400 donnes chacune.
#   ./verifier-candidats.sh <machine> <nom> <siege> <graine> [<graine>...]
# Une ligne JSON par graine dans verifications.jsonl.
set -uo pipefail
BASE="${LOOP_DIR:-$(cd "$(dirname "$0")" && pwd)}"   # dossier de travail de la boucle; cd "$BASE"
RB="${REMOTE_BENCH:-bench}"; NODE_EXE="${NODE_EXE:-node}"
M="$1"; NOM="$2"; SIEGE="$3"; shift 3
for G in "$@"; do
  for L in 0 1; do
    timeout 9000 ssh -o BatchMode=yes "$M" "cd $RB; $NODE_EXE dist/arena.mjs duel --a \"$SIEGE\" --b default --games 200 --samples 16 --profile ruthless --seed $G-$L --workers 8" 2>/dev/null > "/tmp/verif-$NOM-$G-$L.json"
  done
  python3 - "$NOM" "$G" "$SIEGE" "$M" <<'PY' >> verifications.jsonl
import json, sys, datetime
nom, g, siege, m = sys.argv[1:5]
try:
    a = json.load(open(f'/tmp/verif-{nom}-{g}-0.json')); b = json.load(open(f'/tmp/verif-{nom}-{g}-1.json'))
    print(json.dumps({"candidat": nom, "siege": siege, "graine": g, "victoires": round((a['winRateA']+b['winRateA'])/2, 4), "points": round((a['meanA']+b['meanA'])/2, 2), "parties": 400, "machine": m, "date": datetime.datetime.now().astimezone().isoformat(timespec='seconds')}))
except Exception as e:
    print(json.dumps({"candidat": nom, "graine": g, "erreur": str(e)}))
PY
done
