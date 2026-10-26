#!/bin/bash
# Promotion d'un essai : il devient le champion, la ferme repart avec lui, tout est journalise.
#
#   ./promouvoir.sh <nom-essai> <victoires_fixe> <points_fixe> "<justification>"
#
# La DECISION de promouvoir reste au chercheur (ecarts >= +2 pts de victoires, confirmes sur
# une 2e graine appariee ; points pas en chute > 10). Ce script n'execute que la mecanique.
set -uo pipefail
BASE="${LOOP_DIR:-$(cd "$(dirname "$0")" && pwd)}"   # dossier de travail de la boucle
cd "$BASE"
NOM="${1:?usage: promouvoir.sh <nom> <victoires> <points> <justification>}"
VICT="${2:?victoires}"
PTS="${3:?points}"
POURQUOI="${4:?justification}"
BIN="essais/$NOM.bin"
[ -f "$BIN" ] || { echo "introuvable : $BIN" >&2; exit 1; }

cp "$BIN" champion/reseau.bin
printf '%s' "$VICT" > champion/victoires.txt
printf '%s' "$PTS"  > champion/points.txt
cp entrainer.py champion/entrainer.py 2>/dev/null || true

# La graine de warm-start des prochains essais = le champion en titre.
[ -n "${TRAIN_HOST:-}" ] && { scp -q -o ConnectTimeout=10 champion/reseau.bin "$TRAIN_HOST:${REMOTE_TRAIN:-train}/champion-reprise.bin" \
  || echo "$(date -Is) $NOM : champion-reprise.bin PAS pousse" >> ferme.log; }
# La ferme de production de parties doit repartir avec le nouveau champion (script propre a l'installation).
[ -x ./renouveler-ferme.sh ] && ./renouveler-ferme.sh champion/reseau.bin || true

python3 - "$NOM" "$VICT" "$PTS" "$POURQUOI" <<'PY'
import json, sys, datetime
nom, vict, pts, why = sys.argv[1:5]
now = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
n = sum(1 for l in open('progression.jsonl') if 'champion' in l) + 1
open('progression.jsonl', 'a').write(json.dumps({
  "points": float(pts), "victoires": float(vict), "parties": 400,
  "contre": "bot a regles deploye", "reseau": f"essais/{nom}.bin",
  "etiquette": f"champion n° {n}", "date": now}) + '\n')
open('journal.jsonl', 'a').write(json.dumps({
  "essai": nom, "verdict": "promu", "victoires": float(vict), "points": float(pts),
  "raison": why, "date": now}, ensure_ascii=False) + '\n')
PY
python3 tableau.py >/dev/null 2>&1 || true
git add -A >/dev/null 2>&1 && git commit -qm "promotion : $NOM ($VICT victoires, $PTS pts)" >/dev/null 2>&1 || true
echo "{\"promu\":\"$NOM\",\"victoires\":$VICT,\"points\":$PTS}"
