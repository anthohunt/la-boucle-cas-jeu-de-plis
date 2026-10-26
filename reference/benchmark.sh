#!/bin/bash
# LE BENCHMARK. Deux chiffres, ceux que l'operateur a demandes des le depart :
#
#   - POINTS MOYENS par partie
#   - PARTIES GAGNEES (part des parties ou le bot finit premier)
#
#   ./benchmark.sh <reseau.bin> [etiquette]
#
# Rend { "points": x, "victoires": 0.xx, "parties": n }.
#
# POURQUOI CE FICHIER REMPLACE L'ANCIEN JUGE (13/09, apres un degat reel). L'ancien juge mesurait
# « quelle part des points je prends AU CHAMPION DU MOMENT » : 0,50 voulait dire « a egalite avec le
# champion actuel ». Deux consequences, toutes deux constatees :
#
#   1. Ce n'etait pas le benchmark demande. l'operateur avait dit « gagner le plus de parties et faire
#      le plus de points en moyenne » — des mesures ABSOLUES. Le relatif s'y etait substitue sans
#      que personne ne le dise.
#   2. Battre le champion precedent n'est pas transitif. Le champion n° 3 avait battu le n° 2 de
#      2,2 points en duel direct, et s'effondrait a 35,7 % contre le bot du jeu la ou le n° 2
#      faisait 53,2 %. La boucle pouvait donc faire monter sa note en s'eloignant de la vraie force.
#
# L'adversaire est FIXE et ne changera jamais : le bot a regles deploye (`default`,
# a pleine reflexion). C'est ce qui rend deux mesures comparables a des semaines d'intervalle.
# Les graines sont FIXES aussi : deux reseaux voient exactement les memes donnes.
set -uo pipefail
BASE="${LOOP_DIR:-$(cd "$(dirname "$0")" && pwd)}"   # dossier de travail de la boucle
# Machines de jeu (alias ssh) et chemins distants : a regler pour votre installation.
GAME_HOSTS="${GAME_HOSTS:?liste d alias ssh des machines de jeu, ex: \"hote1 hote2\"}"
RB="${REMOTE_BENCH:-bench}"            # dossier du moteur de jeu sur les machines (contient dist/arena.mjs)
NODE_EXE="${NODE_EXE:-node}"
RESEAU="${1:?usage: benchmark.sh <reseau.bin> [etiquette]}"

# UN SEUL benchmark a la fois : deux instances s'ecrasent juge/candidat.bin (piege
# paye le 13/09 a 21h : baseline champion + benchmark d'essai en simultane). flock attend
# jusqu'a 45 min que la place se libere, puis abandonne proprement.
exec 9>"$BASE/.benchmark.verrou"
flock -w 2700 9 || { echo '{"erreur":"un autre benchmark occupe deja les machines (verrou, 45 min)"}'; exit 1; }
ETIQUETTE="${2:-}"
PARTIES="${PARTIES:-400}"          # au total, reparties sur les machines joignables
ECHANTILLONS="${ECHANTILLONS:-16}" # la reflexion du bot deploye, des deux cotes
PROFIL="${PROFIL:-ruthless}"
GRAINE="${GRAINE:-bench-fixe}"     # NE JAMAIS CHANGER : c'est ce qui rend l'histoire comparable

[ -f "$RESEAU" ] || { echo "{\"erreur\":\"reseau introuvable : $RESEAU\"}"; exit 1; }

# UNE SEULE MESURE A LA FOIS. Toutes les mesures ecrivent le candidat au MEME chemin sur les
# machines (juge/candidat.bin) : deux mesures simultanees se recouvrent, et l'une des deux
# fait jouer le reseau de l'autre sans que rien ne le signale. Constate en vrai le 13/09 au soir —
# deux invocations identiques du meme reseau sur les memes donnes ont rendu 265 et 261 points, avec
# 96 points d'ecart sur l'adversaire. Le verrou attend au lieu d'echouer : une mesure qui attend
# reste juste, une mesure qui se recouvre ment.
exec 8>"$BASE/.mesure.lock"
flock 8

MACHINES=()
for m in $GAME_HOSTS; do
  if scp -q -o ConnectTimeout=8 "$RESEAU" "$m:$RB/juge/candidat.bin" 2>/dev/null; then MACHINES+=("$m"); fi
done
[ ${#MACHINES[@]} -eq 0 ] && { echo '{"erreur":"aucune machine de jeu joignable"}'; exit 1; }

# Le decoupage est FIGE (13/09 soir) : toujours 2 lots de PARTIES/2, graines ${GRAINE}-0 et -1,
# quel que soit le nombre de machines presentes. Avant, LOTS suivait les machines joignables :
# avec 3 machines le jeu de donnes effectif devenait 3 x 134 donnes des graines -0/-1/-2 — un
# AUTRE jeu de donnes que le 2 x 200 habituel. La fixite des donnes n'etait pas garantie par
# construction ; elle l'est maintenant. Les lots d'une meme machine tournent en sequence.
LOTS=2
PAR_LOT=$(( PARTIES / LOTS ))

SORTIES=(); PIDS=()
N_MACH=${#MACHINES[@]}
for ((i = 0; i < LOTS; i++)); do
  f=$(mktemp); SORTIES+=("$f")
done
for ((m = 0; m < N_MACH && m < LOTS; m++)); do
  (
    for ((i = m; i < LOTS; i += N_MACH)); do
      ssh -o BatchMode=yes "${MACHINES[$m]}" \
        "cd $RB; $NODE_EXE dist/arena.mjs duel --a \"net:$RB/juge/candidat.bin${SIEGE_SUFFIXE:-#48}\" --b default --games $PAR_LOT --samples $ECHANTILLONS --profile $PROFIL --seed ${GRAINE}-$i --workers 8${BUDGET_A_MS:+ --budget-a $BUDGET_A_MS}" > "${SORTIES[$i]}" 2>/dev/null
    done
  ) &
  PIDS+=($!)
done
for pid in "${PIDS[@]}"; do wait "$pid"; done

python3 - "$ETIQUETTE" "$RESEAU" "${SORTIES[@]}" <<'PY'
import json, sys, datetime
etiquette, reseau, fichiers = sys.argv[1], sys.argv[2], sys.argv[3:]
points, victoires, adverse, parties = [], [], [], 0
for f in fichiers:
    try:
        d = json.load(open(f))
    except Exception:
        continue
    n = d.get('games', 0) or 0
    if not n:
        continue
    # `meanA` = points moyens par partie du cote A (le reseau). `winRateA` = part des parties ou il
    # finit premier. Ce sont exactement les deux chiffres demandes.
    points.append((d['meanA'], n))
    victoires.append((d['winRateA'], n))
    # On garde aussi les points du bot a regles sur les MEMES donnes : c'est la ligne de reference
    # du tableau, et elle rend le chiffre lisible (« 213 points » ne dit rien seul).
    adverse.append((d['meanB'], n))
    parties += n
if not parties:
    print(json.dumps({"erreur": "aucun resultat lisible"})); sys.exit(1)

pts = sum(v * n for v, n in points) / parties
vic = sum(v * n for v, n in victoires) / parties
adv = sum(v * n for v, n in adverse) / parties if adverse else None
sortie = {"points": round(pts, 2), "victoires": round(vic, 4), "parties": parties,
          "pointsAdversaire": round(adv, 2) if adv is not None else None,
          "contre": "bot a regles deploye", "reseau": reseau}
if etiquette:
    sortie["etiquette"] = etiquette
    sortie["date"] = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    with open(__import__('os').environ.get('LOOP_DIR', '.') + '/progression.jsonl', 'a') as f:
        f.write(json.dumps(sortie) + '\n')
print(json.dumps(sortie))
PY

rm -f "${SORTIES[@]}"
