# Deux expériences annexes (récit)

> Ces deux chantiers ont précédé et suivi l'expérience principale (`ETAT-CHERCHEUR.md`). Leur code
> dépend du moteur du jeu d'origine et de plusieurs gigaoctets de parties : **il n'est pas publié**.
> Reste ce qu'ils ont appris, résumé ici à partir des notes et des rapports d'audit de l'époque. Les
> chiffres cités viennent de ces rapports ; leurs fichiers de mesure bruts ne sont pas dans ce dépôt.
> Les jours J1 à J5 sont ceux de l'expérience principale ; « J7 à J9 » désigne les trois jours qui
> ont suivi sa clôture.

## 1. Le réseau « imitateur » (avant l'expérience principale, J1)

Un cycle automatique (relancé toutes les 6 heures par le planificateur du serveur) : rapatrier les
parties jouées par les bots à règles sur les PC de calcul, les encoder, entraîner un petit réseau à
**copier le coup du bot à règles**, exporter les poids dans un fichier binaire compact (moins de
3 Mo, demi-précision, vérifié identique au jeu sur des positions réelles).

| cycle | exemples | accord avec le bot | écart de points |
|---|---|---|---|
| 1 | 1 040 000 | 56,6 % | 38,8 |
| 2 | 10 400 000 | 57,9 % | 37,2 |
| 3 | 5 200 000 | 57,2 % | 38,2 |

(Source : l'historique des cycles. « Accord » = part des coups où le réseau joue la même carte que
le bot ; « écart de points » = erreur de prévision des points de la manche.)

**Ce que ça a appris.** Multiplier les exemples par dix a déplacé l'accord de moins de deux points.
Plus important : *copier* un bot n'est pas *le battre*. C'est ce constat qui a conduit à abandonner
l'imitation comme objectif (voir `program.md`, « L'imitation n'est plus un objectif »).

## 2. Le chantier « élève » : distiller un professeur clairvoyant (J7 à J9)

Idée : un « professeur » qui voit les mains cachées (donc joue mieux) produit des parties et des
étiquettes ; un « élève » qui ne voit que ce qu'un joueur voit apprend à l'imiter, avec une boucle
de correction (type DAgger : l'élève joue, le professeur dit ce qu'il aurait fait). Deux revues
**adverses** (un agent dont le seul travail est de chercher des fautes, sans rien modifier) ont
été faites pendant le chantier. Elles ont trouvé, **par la mesure**, ce qui suit.

**Revue 1 : le chiffre qui portait tout l'espoir était faux.**
- L'élève « gagnait 54,8 % » (200 parties). Mais dans la mesure utilisée, le camp de l'élève
  occupait **2 sièges sur 4** : à force égale le hasard donne **50 %, pas 25 %**. Intervalle de
  confiance à 95 % : [47,9 % ; 61,7 %], il contient 50 % : non significatif.
- Une mesure propre existait déjà sur le disque : 600 parties, l'adversaire à pleine réflexion
  (256 tirages au lieu de 16) : **35,7 %** pour l'élève (z = −7,3 contre 50 %). Brider l'adversaire de
  256 à 16 simulations expliquait à lui seul le chiffre flatteur.
- La boucle de correction n'enregistrait **rien d'exploitable** : 2 780 parties sur 2 780 étaient
  irrejouables, parce que le format n'avait qu'un champ de coup et qu'on y écrivait le coup du
  professeur alors que la partie avait avancé avec celui de l'élève. Le test de fumée ne rejouait
  pas sa sortie ; l'ingestion de ces parties aurait produit un jeu de données vide **avec un code
  de sortie 0**.
- Bonne nouvelle, aussi : l'export des poids était irréprochable (parité refaite à la main) et il
  n'y avait aucun doublon de partie.

**Revue 2 : le correctif de la revue 1 était 44 fois plus destructeur que la maladie.**
Un correctif d'encodage (changement d'échelle d'une entrée partagée entre l'entraînement et le jeu)
a été appliqué *sans réentraîner* le modèle déployé, puis une campagne de 150 minutes a été lancée
dessus. Mesure sur 60 000 positions réelles : le défaut qu'on réparait changeait **0,84 %** des
coups, le correctif en changeait **37,08 %**, et la justesse d'imitation tombait de 65,9 % à
51,9 %. Le numéro de version d'encodage existait mais personne ne le comparait. Le débit de la
production s'était en outre effondré d'un facteur 12, visible à la première ligne du journal.

**Les règles de méthode qui en sont sorties** (celles-là valent bien au-delà de ce jeu) :
1. Tout producteur de données **relit et rejoue un échantillon de ce qu'il vient d'écrire**,
   compare aux résultats enregistrés, et sort en erreur si ça ne colle pas : dans le producteur
   lui-même, pas dans un outil optionnel.
2. Un réglage ne traverse jamais une frontière **reconstruit à la main champ par champ** : on
   transporte l'objet entier, ou un test d'égalité garde le transport.
3. **Aucun taux ne se publie sans son intervalle de confiance et son plancher explicite** (ici 50 %,
   pas 25 %).
4. Un correctif qui touche une frontière partagée se **mesure avant**, sur cette frontière. Un champ
   de version que personne ne compare est pire qu'aucun champ : il donne le sentiment d'être protégé.
5. On ne lance pas une campagne sans avoir **chronométré un lot**.
