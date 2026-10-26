# État du chercheur : note de reprise (récit, version réécrite pour la publication)

> **Lecture.** C'est le carnet que l'agent chercheur tenait pour se retrouver après chaque
> résumé de sa conversation (sa « mémoire sur disque »), du jour 3 au jour 5. Il est publié presque
> tel quel : machines nommées « machine A / B / C », chemins, adresses, empreintes de commits et
> dates absolues retirés (J1 = premier jour de l'expérience, J5 = dernier). Les chiffres suivis
> d'une mesure peuvent se recouper avec `journal.jsonl` et `progression.jsonl`.
> Jargon de l'époque : « lieu » = la sortie du réseau qui devine où sont les cartes adverses ;
> « bench-fixe » / « conf-… » = jeux de graines fixes ; « tirages » / « échantillons » = nombre de
> répartitions des cartes adverses simulées par la recherche à chaque coup ; « lot 0 / lot 1 » =
> les deux moitiés de 200 donnes d'une mesure.

## MISSION (consigne de l'opérateur, J4 14h20) : faire monter les benchmarks, rien d'autre.
Victoires et points contre le bot déployé (mètre fixe : règles, 16 éch., graines bench-fixe).
Aucune contrainte de méthode, aucun compte rendu du comment. Niveau à battre (budget produit
1000 ms) : règles seules = 64-66 % / 233-237. Réseau = piste seulement avec un rôle différent.
Balayage poids en cours (chaînes directes) : prudenceVar 0,7 → malice ×2 (machine A) ; plafond 1024
seul → zeroBidPenalty 2 (machine B). Repère lot 0 : 66,5 / 239,6.


## J3 ~20h45 — TERRAIN REMIS À ZÉRO, NOUVELLE STRATÉGIE

Tout l'historique d'avant est invalide (mesures faussées : builds de juge différents pendant
2 jours). Les faits établis sont dans mission.md §« Ce qui est vrai ». Le pivot :

**LE RÉSEAU N'AGIT QUE PAR LA TÊTE « LIEU »** (où sont les cartes adverses → oriente la
déterminisation de la recherche). Sa précision : ~38 % vs 33 % de hasard — à peine mieux.
TOUT l'effort d'entraînement va sur cette tête. Les 3 autres sorties sont inertes en jeu.

## Fait ce soir (20h30-20h50)
- Builds des 2 juges synchronisés (hashes identiques), sanity : 198,9/0,52 IDENTIQUE des 2 côtés.
- Production relancée PROPRE des 2 côtés : ε=0,02 + graine horodatée (fini les 20 % de doublons)
  — machine B 22h38, machine A 22h44 (heure locale machine). Toutes les vieilles données → périmées.
- Benchmark de BASE du champion en cours sur juge réparé → le fichier de mesure de base.
  (~8 min : 400 donnes.) C'est LE point zéro du tableau.

## Prochaines actions, dans l'ordre
1. Lire le fichier de mesure de base → journal + tableau (point zéro).
2. **Essai lieu-1** : entraîner avec poidsLieu DOMINANT (ex. 4.0, autres têtes réduites ou à 0)
   sur données fraîches ε=0,02 à graines horodatées (attendre ~25-30 k parties, rafraichir).
   Métrique de pilotage = « cartes devinées » (lieu), PAS l'accord/écart-gain (têtes mortes).
   Q ouverte : entraîner la tête lieu sur les VRAIES mains (rejeu = vérité gratuite) plutôt que
   sur l'encodage actuel — vérifier ce que lieu.bin contient déjà (vraie main ou estimation).
3. Warm-start : entrainer.py a --reprise-bin défaut le fichier de reprise du champion (poids essai-004).
   Pour un from-scratch, le débrancher (default=''). En reprise : LR constant 8e-5 (déjà câblé).
4. Promotion : PAS de gate automatique pour l'instant (tour.sh n'existe plus). Décision manuelle :
   ≥ +2 pts de victoires sur 400 donnes ET points ≥ champion −10 (loterie d'init = ±1,6).
   Benchmark ~8 min ; confirmer sur une 2e graine (GRAINE=xxx ./benchmark.sh) avant de promouvoir.
5. Si promu : scp → le fichier du champion sur les 2 machines + le script de relance (renouveler-ferme.sh).

## Leviers en réserve (par ordre de conviction)
- Précision lieu ↑ = recherche mieux informée (LE levier direct).
- Recherche elle-même : samples/temps dans le budget <1 s navigateur (levier non-ML, jamais exploré).
- Inférence bayésienne exacte des mains à partir des coups joués (non-ML, complète la tête lieu).
- Duplicate sièges au benchmark (réduction de variance) si les 8 min deviennent le goulot.

## Pièges connus
- le lanceur d'entraînement ne passe AUCUN flag : tout réglage = un défaut d'entrainer.py.
- Deux benchmarks en parallèle s'écrasent (le fichier candidat du juge) : un seul à la fois.
- machine C éteinte. Machines : machine A (8 fils), machine B (16 fils + RTX 2080 Super = entraînement).
- Loterie d'init : ±1,6 pt entre deux runs identiques — jamais conclure sous +2 pts.
- Le « tu » de mission.md = cette session tmux `chercheur` (un fichier d'avertissement le verrouille).

## J3 21h10-21h20 — PREMIER SIGNAL FORT DE LA STRATÉGIE LIEU
- Point zéro (juge réparé) : champion = 47,13 % / 196,3 (bot : 197,1). Inscrit partout.
- **lieu-warm-1 : 51,5 % / 196,1 = +4,4 pts de victoires** (>> loterie ±1,6). Confirmation
  appariée en cours sur graine conf-0913 (candidat puis champion).
  Si l'écart apparié tient (≥ +2) → PROMOTION (scp les 2 machines + relancer, cf. renouveler-ferme).
- lieu-scratch-1 lancé (from-scratch, OneCycle 2e-3, poidsLieu 4,0) — son benchmark attendra
  le verrou. entrainer.py a maintenant reprise DÉSACTIVÉ par défaut — le REMETTRE pour le prochain warm.
- Verrou flock posé sur benchmark.sh après la quasi-collision de 21h00.

## J3 22h10 — PROMOTION : lieu-warm-1 = CHAMPION n° 1 (ère juge réparé)
51,5 % / 196,1 sur fixe (+4,4 sur essai-004) ; confirmé apparié conf-0913 : 55,25 vs 53,0 (+2,25).
Ferme renouvelée sur lieu-warm-1, fichier de reprise du champion poussé. lieu-scratch-1 (52,25)
valide la stratégie en double aveugle. EN COURS : lieu-warm-2 (reprise du nouveau champion,
même instantané = époques 11-20, poidsLieu 4,0) — surveiller si « cartes devinées » dépasse 39,3.
ENSUITE : dès ~23h, rafraîchir sur les parties du NOUVEAU champion (ε 0,02, graines horodatées)
et lancer lieu-warm-3 dessus — la boucle cumulative on-policy commence là.
- 23h00 : machines rendues à la production (~6 Mo/h à deux). determinize.ts vérifié : voids +
  inférence des paris + croyance réseau déjà en place — le levier est bien la PRÉCISION de
  netLocations, pas la plomberie. Prochain geste 23h45 : MINIMUM=1 rafraichir (~9-10 k parties
  du champion lieu-warm-1) puis lieu-warm-3. NE PAS benchmarker d'ici là (contention CPU).
- 23h30 : lieu-warm-3 entraîné — **lieu 40,2 %** (39,5 → 40,2 sur 5 900 parties fraîches, la
  fraîcheur nourrit bien). PIÈGE CONFIRMÉ 2× : un `setsid nohup ./essai.sh X &` lancé depuis un
  tour meurt après la phase d'entraînement (warm-2 ET warm-3 : jamais de benchmark, json vide).
  → TOUJOURS lancer essai.sh/benchmark.sh via le mécanisme d'arrière-plan du harnais
  (run_in_background), qui survit aux tours. Benchmark de warm-3 relancé ainsi, en cours.

## J4 01h20 — CHAMPION n° 2 : lieu-warm-4 — 59,62 % / 204,0 pts
+8,1 pts de victoires en UN tour de boucle cumulative (14 650 parties fraîches, 20 min, lieu 40,2).
Confirmé apparié conf2-0914 (+2,1). Ferme renouvelée sur lui, graine warm poussée.
La recette qui marche : reprise du champion + poidsLieu 4,0 + LR 8e-5 + MAX de parties fraîches
on-policy + budget 20 min. RYTHME DE CROISIÈRE : toutes les ~2 h — rafraîchir (MINIMUM=1),
essai.sh warm suivant (via UN job harnais unique), benchmark, confirmation appariée si > +2, promotion.
Les jobs chaînés ou setsid meurent parfois : UN essai.sh par job harnais, benchmarks de
confirmation en jobs séparés (ils se sérialisent sur le flock).

## J4 05h20 — LA CONFIG 48 ÉCHANTILLONS EST ADOPTÉE : 60,62 % / 224,6 pts
Nuit résumée : baseline 47,1/196,3 → lieu-warm-1 (51,5) → lieu-warm-4 (59,62/204,0) →
**config 48 échantillons : 60,62 / 224,6** (+13,5 pts de victoires et +28 points depuis hier soir).
- Le benchmark mesure désormais notre siège à #48 (SIEGE_SUFFIXE défaut) ; adversaire inchangé.
- champion/config.json porte la config produit. Vigilance : latence navigateur à valider (#32 en repli).
- Entraînement : plateau à lieu 40,5 (warm-5/6/7 jetés) — prochaine idée : plus d'échantillons
  aussi en PRODUCTION (samples 4 → 8-16) pour des parties mieux jouées = meilleures cibles lieu ?
  Ou architecture de la tête lieu. Les tours warm restent possibles à chaque gros lot frais.

## J4 06h20 — MESURE À BUDGET DE TEMPS (demande de l'opérateur) EN COURS
Prod = 250 ms + 60 échantillons ; budgetFor plafonnait à 250 (corrigé dans le banc,
arène --budget-a). Chaîne `deployer-arene-et-mesurer.sh` (job harnais) : attend warm-8 → déploie
→ parité (références ancien et nouveau build comparées)
→ `mesure-budget.sh` → `mesure-budget.jsonl` (prod-250ms-60ech, 250ms, 500ms, 1000ms).
Si parité KO : ancien dist restauré automatiquement (*.avant-budget), mesure annulée.
warm-8 (38 k parties) : verdict dans un fichier de résultat, barre 60,62/224,6 (#48).
- 06h20 : parité ancien/nouveau build OK (198,25/0,60/155,88 identiques) ; mesure-budget.sh en cours (point 1/4 : prod 250 ms + 60 éch.). warm-8 encore en entraînement (lent, contention), son benchmark suivra derrière le verrou.
- 07h45 : budget 500 ms = 61,25 % / 229,1 (deployable depuis ce matin, plafond prod 1000 ms). 1000 ms en cours, puis 125/750 (mesure-budget-2.sh en file).

## J4 08h30 — COURBE TEMPS DE RÉFLEXION LIVRÉE (mesure-budget.jsonl, champ budgetMs)
prod exacte 250 ms+60 éch. = 59,1 % / 212,0 · 250 ms = 55,5 / 215,5 · 500 ms = 61,25 / 229,1 ·
**1000 ms = 64,25 % / 232,6** (adv 175,2). Plafond prod = 1000 ms depuis ce matin → déployer à
1000 ms = +5 pts de victoires / +20 points sur la prod actuelle. 125 et 750 ms en cours
(mesure-budget-2.sh, marqueur JSON en fin). tableau.py tolère désormais les lignes non-JSON.
Prochain axe : sous 1000 ms de budget, c'est la RECHERCHE qui a de la marge (points montent
encore à 1000) → idées : 2000 ms (hors plafond, pour connaître l'asymptote), puis améliorer
l'efficacité de la recherche (déterminisations mieux échantillonnées par le réseau lieu).
- 09h05 : 750 ms = 67,13 % / 234,7 (record) ; plateau 750-1000. Recommandation : déployer à 1000 ms. Confirmation seconde graine (mesure-budget-3.sh) en cours ~2h45.

## J4 11h20 — COURBE CONFIRMÉE, CONFIG PRODUIT = 1000 ms
2 graines × (250/500/1000) : 1000 ms ≈ 66 % / 233 sur 800 donnes. champion/config.json = 1000 ms.
Tableau : point « config 1000 ms » = 64,25 / 232,6 (bench-fixe). MESURE : la référence produit se
mesure à BUDGET_A_MS=1000 (85 min/400 donnes) ; pour trier les candidats vite, garder #48 sans
temps (15 min) comme proxy, et ne mesurer à 1000 ms que les promotions. Machines libres : la
recherche est le levier (points montent avec le temps) → prochaines idées : efficacité de la
recherche à budget fixe (déterminisations mieux guidées par la tête lieu, élagage des candidats).

## J4 12h20 — LE RÉSEAU N'APPORTE RIEN À 1000 ms (isolation sur 400 donnes)
Bot à règles seul, 1000 ms : 64,13 % / 236,6 ; champion + réseau, 1000 ms : 64,25 % / 232,6.
→ Le gain est le TEMPS DE RECHERCHE. Confirmation appariée sur conf-budget en cours (sans réseau,
1000 ms, 2 lots). Si confirmé : (1) recommander « bot à règles à 1000 ms » comme produit (plus
simple, aussi fort) ; (2) réorienter TOUTE la recherche vers l'efficacité de la recherche à budget
fixe : profil des coûts (déterminisation vs playout), élagage des candidats, mémoïsation,
playouts plus courts ; le réseau lieu ne sert que si la recherche est courte (250 ms ?) — à
mesurer : sans-réseau à 250 ms vs champion à 250 ms (59,1/212).

## J4 13h00 — VERDICT : LE RÉSEAU N'APPORTE RIEN, LE TEMPS DE RECHERCHE FAIT TOUT
400 donnes : prod actuelle (règles, 250 ms, 60) = 60,13 / 220,6 ; champion+réseau idem = 59,1 / 212 ;
règles 1000 ms = 64,1 / 236,6 ; champion+réseau 1000 ms = 64,25 / 232,6. Le point zéro à 47 %
mesurait une config (16 éch. non bornés) plus faible que la prod. PRODUIT : règles seules à 1000 ms.
RECHERCHE désormais = efficacité de la recherche à budget fixe (aucun apprentissage tant qu'un
réseau ne bat pas les règles seules À BUDGET ÉGAL — c'est le nouveau critère de promotion).
Attente : sans-réseau 1000 ms lot 1 graine neuve (lot 0 : 65,0 / 244,4).
- 13h20 : levier recherche n°1 code : elimination progressive des candidats (le banc, --elim-a). A/B en cours sur bench-fixe-0 a 1000 ms vs 66,5/239,6 sans elimination. Idees suivantes : moins de candidats a force 10 (keep=6), cout de la determinisation ponderee par le reseau (elle mange du budget).
- 13h15 : isolation confirmée 2e graine (sans réseau 63,9/236,8 vs avec 67,5/232,9 = bruit). Tests plafond 1024 ± élimination à 1000 ms en cours (repère 66,5/239,6).
- 13h45 : élimination+1024 = repère → recherche saturée à 1000 ms. Prochain levier : poids d'évaluation (bidSamplesMult, prudenceVar, zeroBidPenalty, oppScore) via fichier JSON --a <poids.json>... ATTENTION : --a <poids.json> = bot à règles avec poids partiels, sans réseau (ce qu'on veut).
- 14h00 : balayage des poids d'évaluation à 1000 ms (#256, lot 0, repère 66,5/239,6) : oppScore 0,5 (en cours), prudenceVar 0,7 et zeroBidPenalty 2 (en file). Arène : <poids.json>#N supporté (le banc).
- 14h05 : PIÈGE (3e fois) : `until ! pgrep -f "motif"` depuis un job dont la ligne de commande contient le motif = attente infinie (auto-match). 4 jobs perdus 13h50-14h05. Règle : jamais de pgrep-attente ; chaîner directement avec ';' dans UN job, ou pgrep -f '[m]otif'.
- 14h30 PLAN sans contrainte : (1) finir le balayage poids (chaînes en cours, ne rien lancer en
  parallèle : les mesures à budget de temps sont sensibles à la charge CPU). (2) Mesurer le réseau
  en mode « seul » (netseul:, décision directe sans simulation) contre le mètre — s'il tient ~50 %
  en 1 ms/coup, il devient une politique de playout candidate. (3) DISTILLATION : produire des
  parties du bot à règles à 1000 ms (fort) et entraîner le réseau à l'imiter (mode seul), puis
  l'utiliser comme politique de playout → simulations plus réalistes = le levier restant.
  (4) Spécialisation contre le mètre : le mètre est fixe et déterministe → entraîner/régler
  contre LUI directement (parties vs reference, pas self-play).

## ARRÊT FINAL PROGRAMMÉ : mardi J5 12h00 heure française (10h00 UTC) — cron arret-final.sh
l'opérateur (J4 15h) : tout s'arrête (réveils, mesures, production), puis je livre les résultats
finaux et on discute du déroulé. À FAIRE AVANT : au réveil de ~09h45 UTC, écrire la section
« BILAN FINAL » ici + message final à l'opérateur (chiffres du tableau, ce qui a marché, ce qui a raté).
- RÈGLE D'ARRÊT précisée : à 10h00 UTC, plus AUCUN lancement (mesure, essai) ; ce qui tourne finit ; le script pose .arret-final et attend la fin avant de figer le bilan. Si je suis réveillé après 10h00 UTC : ne rien lancer, seulement relever et bilanter.

## J4 15h50 — MEILLEURE CONFIG : règles + 1000 ms + malice ×2 = 70,37 % / 232,0 (400 donnes)
maliceLeader 0,6 / maliceZero 0,8 (défauts 0,3/0,4). +6,2 pts de victoires sur les règles seules à
1000 ms, −4,6 points. Fichier : poids-malice03.json (= le fichier de poids).
En cours : confirmation conf-budget (machine A) ; machine B : parité → 1024 corrigé → malice ×3.
Si ×3 monte encore → ×4 ; sinon explorer maliceZero seul vs maliceLeader seul.
- 16h20 : malice ×2 confirmé graine neuve (66,25/230,9 vs 63,9/236,8) ; cumul 800 donnes +4,3 victoires / −5,3 points. ×1,5 lancé (machine A), ×3 en file (machine B).
- 16h20 : FERME ARRÊTÉE (contention CPU faussait les mesures à budget de temps ; 1024@1000ms reste pire que #256 même après correctif). À remesurer ferme éteinte : #1024@1000, #60 sans limite (prod).
- 17h05 : levier repéré : bidInference (inférence des mains à partir des paris dans la déterminisation) est à 0 par défaut = DÉSACTIVÉ. Test bidInference 1 seul et + malice ×2, en file sur machine B.
- 17h55 : plafond prod 60 éch. sans limite = 59,25/226,6 vs 256 = 66,5/239,6 → recommander cap 60 → 256 + 1000 ms + malice ×2.
- 18h15 : leader seul = 57 % (pire) ; malice ×2 sous vrai 1000 ms lot 0 = 59,0 vs 61,5 règles → le gain malice dépend du nombre de tirages (256 ≈ 2 s). Bilan à écrire en 2 colonnes : « 256 tirages » et « 1000 ms réels sur la machine 8 cœurs ». zero-seul, bidInference et lot 1 en cours.
- 19h50 : VRAI 1000 ms 400 donnes : règles 63,5/235,7 = malice ×2 64,4/232,2. Déployable à 1000 ms (machine 8 cœurs) = règles + cap ≥256 ≈ 63-64 % / 234 (prod actuelle 60/220) ; malice ×2 seulement si 256 tirages tiennent dans la seconde (→ 70/232). Consolidation conf-budget en cours (machine A).
- 21h35 : DÉPLOYABLE CONSOLIDÉ 800 donnes : règles, cap 1024, vrai 1000 ms = 64,6 % / 241,4 (prod actuelle 60,1 / 220,6). 2000 ms lancé sur machine A (info matériel). bluff0+malice (256) sur machine B.
- 23h30 : CPU/partie : prod 14,8 s ; #256 sans limite 50 s ; cap1024@1000ms 105 s ; 2000 ms 167 s. → déployable = cap 256 + garde-fou 1000 ms (validation en cours : #256 --budget-a 1000, règles puis malice ×2).
- 00h00 : ANOMALIE : #256 avec garde 1000 ms = 61,75 %/82 s/partie vs #256 sans garde = 66,5 %/50 s. A/B strict en file sur machine B. Si le mode timé est cassé : c'est le mode de la PROD → à dire dans le bilan, et suspecter le correctif de 15h10.
- 00h50 : CAUSE : machine B (hyperthreading) ne fait pas 256 tirages en 1000 ms → tous ses rejets en mode borné sont suspects ; remesure SANS limite (x3, leader06, zero08, bidinf1 sur machine B ; bluff0, bonus40, bonus80 sur machine A). Conclusions machine A valides. Le 'vrai 1000 ms' est machine-dépendant → calibrer sur le serveur de prod.
- 01h00 : bonusScale inerte (classic). malice x2 SANS limite lot 0 = 65,0 vs règles 66,5 → le gain malice était un artefact des mesures bornées. Lot 1 sans limite en file ; si confirmé, bilan = règles + 256 tirages, sans malice.
- 01h45 : MALICE x2 RETIRÉ (sans limite : 62,75 vs 64,13 règles). CONFIG FINALE = règles + 256 tirages, sans réseau, poids par défaut : 64,0 % / 236,7 sur 800 donnes. Dernier point : 3e graine (machine A). machine B finit leader/zéro/bidInference (peu d'enjeu).
- 02h40 : CONFIG FINALE sur 1200 donnes = 64,5 % / 238,0 (prod 60,1 / 220,6). Dernier test : 512 tirages sans limite lot 0 (machine A).

## BILAN FINAL (brouillon 04h00 UTC, à envoyer à l'opérateur avant 12h00 Paris)
**Chiffres (contre le bot déployé, 400 donnes/graine, mêmes donnes pour tous)**
- Prod actuelle (règles, 60 tirages, 250 ms) : 61,1 % / 223,0 pts (800 donnes).
- Config finale (règles, 256 tirages, sans réseau, poids par défaut) : **63,8 % / 239,4 sur
  1600 donnes (4 graines)** ; prod actuelle 60,0 % / 220,9 sur 1200 donnes. → **+3,8 pts de
  victoires, +18,5 points**, par un seul réglage : plafond d'échantillons 60 → 256 (le budget temps doit
  laisser ~0,6 s/coup en moyenne, jusqu'à ~2 s sur les coups ouverts, sur un processeur 8 cœurs).
- Réseau (tête « lieu » entraînée) : aucun apport mesurable à aucun budget (800 donnes).
- 512 tirages : victoires égales, +6 points, coût ×2. 2000 ms : rendement décroissant.
- 9 réglages de poids balayés (dont bidInference, désactivé par défaut) : aucun ne bat les défauts entraînés (malice ×2 = artefact
  des mesures bornées en temps, retiré).
**Ce qui a marché** : le mètre fixe + graines partagées ; l'isolation « sans réseau » ;
la détection des artefacts (juges à builds différents, doublons de production, mode borné
machine-dépendant, bonusScale inerte). **Ce qui a raté** : 2 jours d'entraînement du réseau
mesurés sur un juge cassé ; les promotions warm-1/warm-4 (n'ont jamais battu les règles seules à
tirages égaux) ; tous les résultats « bornés en temps » sur machine B (hyperthreading).
**Recommandation** : déployer règles + 256 tirages ; calibrer le budget temps sur le serveur ;
mesurer toute future variante à NOMBRE DE TIRAGES FIXE, jamais au chrono.
- 04h20 : bidInference sans limite = 64,5/229,3 (jeté). FIN DES MESURES. Plus rien à lancer ; bilan final à envoyer ~11h45 Paris ; arret-final.sh à 10h00 UTC.
- 06h00 : bidSamplesMult 3 = aucun gain (62,75/239,5, coût ×4). FIN DES EXPÉRIENCES. Bilan final à envoyer ~09h45 UTC ; arret-final.sh à 10h00 UTC.
- 07h00 : CHIFFRES FINAUX : finale 63,8 % / 239,4 (1600 donnes) vs prod 60,0 % / 220,9 (1200 donnes). Plus aucune mesure. Bilan à envoyer ~09h45 UTC.

## J5 14h40 UTC — DÉPLOYÉ EN PRODUCTION (sur ordre de l'opérateur de déployer le meilleur bot)
Production mise à jour : règles + 256 tirages, budgetFor mis à l'échelle
au-delà de 250 ms (sinon HARD_BUDGET_MS=1000 ne faisait rien à force 10), pas de coupure au milieu
d'un tirage. Élimination progressive NON portée. Conteneur sain, paquet public vérifié.
Campagne de vérification arrêtée (leader06 g4 = 64,12/239,89 → +3 victoires / −4 pts sur 3 graines,
non retenu ; prud015, bidmult2, 512/g4 non mesurés). Chaînes tuées serveur + machine B, production machine B
arrêtée. Expérience CLOSE.
