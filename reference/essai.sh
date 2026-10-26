#!/bin/bash
# UN essai : entraine sous budget sur la machine a carte graphique, rapatrie le modele, le juge.
# Rend un JSON sur la sortie standard. Ne decide rien — c'est la boucle qui garde ou jette.
#
#   ./essai.sh <nom-de-l-essai>
set -uo pipefail
BASE="${LOOP_DIR:-$(cd "$(dirname "$0")" && pwd)}"   # dossier de travail de la boucle
TRAIN_HOST="${TRAIN_HOST:?alias ssh de la machine d entrainement}"
RT="${REMOTE_TRAIN:-train}"     # dossier d entrainement sur cette machine
NOM="${1:?usage: essai.sh <nom>}"
BUDGET_MIN="${BUDGET_MIN:-5}"
CHAMPION="${CHAMPION:-$BASE/champion/reseau.bin}"

# 1) le code de l'essai part sur la machine d'entrainement
scp -q "$BASE/entrainer.py" "$BASE/reseau.py" "$BASE/exporter.py" "$TRAIN_HOST:$RT/" || { echo '{"erreur":"envoi du code"}'; exit 1; }

# 2) entrainement, budget strict
ssh -o BatchMode=yes "$TRAIN_HOST" "$TRAIN_CMD -Budget $BUDGET_MIN -Nom $NOM"   # TRAIN_CMD : commande qui lance entrainer.py sur la machine > "$BASE/essais/$NOM.entrainement.log" 2>&1
if ! scp -q "$TRAIN_HOST:$RT/sorties/$NOM/reseau.bin" "$BASE/essais/$NOM.bin" 2>/dev/null; then
  echo '{"erreur":"pas de modele produit"}'; exit 1
fi
scp -q "$TRAIN_HOST:$RT/sorties/$NOM/resultat.json" "$BASE/essais/$NOM.resultat.json" 2>/dev/null

# 3) taille du modele : il doit tourner dans un navigateur (interdit n° 7)
TAILLE=$(stat -c%s "$BASE/essais/$NOM.bin")
if [ "$TAILLE" -gt 3145728 ]; then echo "{\"erreur\":\"modele trop gros ($TAILLE octets)\"}"; exit 1; fi

# 4) le benchmark : points moyens et parties gagnees contre le bot deploye, donnes fixes.
# L'ancien juge (duel contre le champion du moment) est remplace depuis le 13/09 — voir
# benchmark.sh pour ce que ce changement repare.
"$BASE/benchmark.sh" "$BASE/essais/$NOM.bin"
