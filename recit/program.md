# Consignes de la boucle (récit : la méthode donnée au chercheur avant la remise à zéro du jour 3)

> **Lecture.** C'est la version condensée et réécrite du fichier de méthode que lisait l'agent
> chercheur à chaque tour, dans l'état où il était juste avant la « remise à zéro » du soir du
> jour 3 (voir `ETAT-CHERCHEUR.md`). Ses mesures de l'époque ont ensuite été jugées fausses (deux
> machines jugeaient avec deux versions différentes du juge) : **les chiffres et les verdicts de
> cette période ont été retirés ici**, il ne reste que les règles de méthode et les erreurs qu'elles
> corrigent. Après la remise à zéro, ce fichier a été remplacé par `mission.md`.
> Pour la méthode générale de La boucle, voir le dépôt `la-boucle-engine` (section « méthode »).

Ce fichier est la seule chose qu'un humain écrit. L'agent le lit à chaque tour, change ce qu'il
juge utile, relance un essai, garde le changement si la note monte, le jette sinon. Personne ne
valide à la main.

## Ce que l'opérateur attend (posé au jour 2, ne se renégocie pas)

1. **Il ne veut pas arbitrer la méthode.** Ne lui demande pas de choisir entre deux stratégies
   d'apprentissage : c'est le travail du chercheur.
2. **Il n'attend qu'une chose : que la note monte.** Ni un indicateur d'entraînement plus joli, ni
   une idée élégante.
3. **Le chercheur est libre.** Son périmètre couvre tout ce qui peut faire monter la note : la
   production des données, l'encodage, la vitesse du système. Seuls restent verrouillés les quatre
   interdits plus bas, qui protègent la mesure.
4. **La boucle doit tourner et continuer de tourner.** Une boucle arrêtée est un échec, même avec
   une bonne raison.
5. **Le matériel est une donnée du problème, pas une excuse** : apprendre vite avec peu fait partie
   de la recherche.

## Le benchmark (refait au jour 3)

**Deux chiffres, mesurés contre un adversaire qui ne change JAMAIS : le bot à règles déployé en
production**, à pleine réflexion, sur des donnes fixes (`benchmark.sh`).

- **PARTIES GAGNÉES : ce qui DÉCIDE.** Un candidat est promu s'il gagne au moins 3 points de
  pourcentage de parties de plus que le champion, sur les mêmes donnes.
- **POINTS MOYENS par partie : ce qui SURVEILLE.** Une promotion qui ferait chuter les points de
  plus de 10 est refusée, même si elle gagne plus souvent.
- **Confirmation obligatoire** sur un second jeu de donnes, jamais utilisé pour décider : le
  benchmark est déterministe (graines fixes, bots déterministes), donc le risque n'est pas le bruit
  de mesure, c'est de coller à ces donnes-là.

**Pourquoi ce changement.** Jusqu'au jour 3, la mesure était RELATIVE : « quelle part des points je
prends au champion du moment ». Deux dégâts réels :

1. **Ce n'était pas le benchmark demandé.** L'opérateur avait demandé « gagner le plus de parties et
   faire le plus de points en moyenne », des mesures ABSOLUES. Le relatif s'y était substitué sans
   que personne ne le dise.
2. **Battre le champion précédent n'est pas transitif.** Un champion avait battu son prédécesseur en
   duel direct, et s'effondrait contre le bot du jeu là où son prédécesseur tenait. La boucle
   pouvait monter sa note en s'éloignant de la vraie force. Le titre a été rendu à l'ancien champion.

**Un mètre qui bouge n'est pas un mètre.** Ne remets jamais le champion comme référence de mesure.

**Règle du jour où la référence saturera** : quand un champion dépassera 75 % de parties gagnées
contre le bot du jeu, on FIGE ce champion-là comme SECONDE référence permanente et on mesure contre
les deux. On n'en remplace jamais une, on en ajoute.

## D'où le chercheur repart à chaque tour

L'entraînement ne contient pas toujours la recette du champion. À chaque tour, la boucle tire au
sort un essai passé dans l'archive et met SA recette dans le fichier d'entraînement ; le tirage
favorise les bons scores et les lignées peu explorées, mais un essai rejeté peut très bien être le
point de départ : un essai qui n'a pas payé reste souvent le meilleur tremplin. Conséquences :
- lire le fichier d'entraînement avant de le modifier, il n'est pas dans l'état supposé ;
- ce qui compte est le couple (point de départ, changement), pas le changement seul.

## Deux corrections de méthode, décidées après une longue série d'essais jetés

Le motif était toujours le même : les indicateurs d'entraînement montaient (accord avec le
champion) pendant que la note en duel descendait. On optimisait la copie.

1. **L'imitation n'est plus un objectif.** Apprendre à rejouer la carte du champion, c'est au mieux
   l'égaler. La tâche reste calculée comme indicateur, jamais comme critère.
2. **L'auto-jeu explore.** Si le champion ne joue QUE son meilleur coup, la tête qui décide en jeu
   n'apprend la valeur d'aucun autre coup et tranche entre eux sur du bruit d'initialisation. Un coup
   sur dix environ est donc tiré au hasard parmi les autres coups légaux, et ces parties portent
   `auto-explore-` dans leur nom.
   Corollaire : **les verdicts d'avant portent sur des données qui ne contenaient aucune alternative
   jouée.** Ils sont une mémoire de ce qui a été tenté, pas une preuve que ces idées ne marchent pas.

## La note

Un essai vaut une note et une seule : la mesure du benchmark ci-dessus. **L'accord avec le champion
n'est pas un progrès** : il monte quand le réseau copie mieux, et c'est exactement ce qu'on ne veut
plus. Un essai dont l'accord grimpe et dont la note stagne est un échec, pas un espoir.

Deux indicateurs secondaires sont journalisés à chaque essai et servent de signal précoce, jamais de
critère de promotion : la part de cartes adverses correctement attribuées, et l'erreur de prévision
de gain en points.

## Ce que l'agent a le droit de changer : TOUT, sauf quatre choses

Carte blanche au sens littéral : le système entier est à lui (serveur, PC de calcul, ferme, scripts
d'orchestration, cadences). Si quelque chose le gêne, il le change. S'il manque quelque chose, il le
construit. **Il vérifie l'état réel du système, pas seulement le code** : exemple vécu, après deux
promotions, les deux machines faisaient encore jouer le champion de la veille parce que personne ne
le leur avait envoyé, et une grande quantité de parties avait été produite par un joueur périmé.

Exemples de ce qui se modifie sans demander : l'entraînement (architecture, ce qu'on prédit,
pondération des tâches, pas d'apprentissage, régularisation) ; l'encodage (avec la contrainte de
parité plus bas) ; la production des parties (taux d'exploration, nombre de simulations, vitesse) ;
la taille et la fraîcheur de l'instantané ; le budget d'entraînement (à condition de l'annoncer dans
l'hypothèse, car un essai plus long n'est comparable qu'à budget égal) ; la façon dont le réseau
décide en jeu.

## Interdits : il n'en reste que quatre, et ils protègent la mesure

1. **Ne jamais toucher à ce que le juge MESURE** : les règles du jeu, l'arène, et dans le juge les
   graines, l'appariement, l'alternance des sièges, la barre et les risques du test. Modifier le
   thermomètre n'est pas un progrès. La *mécanique* du juge (quelles machines, combien de vagues) est
   modifiable à condition de vérifier après coup que la mesure n'a pas bougé (le champion contre
   lui-même doit rendre « pas mieux »).
2. **Jamais d'entraînement sur les parties du juge.** Elles viennent d'un jeu de graines disjoint.
3. **Le garde-fou devant le réseau reste en place, et le modèle exporté reste sous 3 Mo** : il
   tourne dans le navigateur de vrais joueurs.
4. **Toute modification de l'encodage impose de repasser la parité** PyTorch contre le jeu et
   d'incrémenter la version d'encodage. Deux encodages qui divergent, c'est un réseau qui joue au
   hasard sans que rien ne le signale.

Un seul changement par essai reste la règle de prudence quand on veut une conclusion nette ; un
ensemble cohérent de changements est permis s'il est annoncé dans l'hypothèse.

**Si le chercheur casse la production de parties, il la répare** : c'est elle qui nourrit tout le
reste, et une ferme à l'arrêt ne se voit pas dans la note avant plusieurs heures.

## Directions à explorer (de l'époque)

- La tête « où sont les cartes adverses » : le levier le plus prometteur et le plus sous-exploité.
- L'estimation de gain (Deep Monte-Carlo) : l'apprendre sur le score de la partie plutôt que de la manche.
- Séparer le pari et le jeu de la carte : deux problèmes distincts.
- Encodage : donner l'historique des plis, pas seulement leur résumé.
- Architecture : plus large plutôt que plus profond, normalisation, abandon.

## La promotion exige aussi un plancher ABSOLU

La boucle a produit un champion qui battait son prédécesseur en tête-à-tête mais perdait nettement
contre le bot à règles, que le prédécesseur battait. Cycle non transitif classique : à force de ne
mesurer que le tête-à-tête contre le champion en titre, la lignée s'était spécialisée à battre son
prédécesseur en régressant contre tout le reste. Personne ne l'aurait vu sans une mesure
d'ancrage absolue. Corrections : le champion fautif est démis ; toute promotion exige, en plus de la
barre contre le champion, un plancher contre le bot à règles ; **leçon de méthode : mesurer
régulièrement le champion en ABSOLU, pas seulement en relatif.** Une note relative qui monte peut
cacher une force qui descend.

## Critère d'arrêt

L'ancien critère (« dix essais consécutifs sans promotion : arrêt ») contredisait l'exigence n° 4 :
c'est lui qui avait tué la boucle en plein plateau. Désormais :

- **Dix essais consécutifs sans promotion = changement de stratégie OBLIGATOIRE**, pas un arrêt :
  changer de famille d'idées (données, vitesse, encodage, architecture, mesure) au lieu de
  continuer à raffiner la même.
- La boucle ne s'arrête que **sur ordre explicite de l'opérateur**.
- Si le juge devient indisponible, on répare le juge au lieu de conclure : une note manquante ne
  vaut jamais « pas de progrès ».
