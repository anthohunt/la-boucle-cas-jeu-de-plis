#!/usr/bin/env python3
"""Entraine le reseau des bots du jeu de plis sur les parties encodees.

Deux sorties sur le meme tronc :
  - la politique : parmi les coups LEGAUX, lequel jouer (les coups interdits sont ecartes avant
    le calcul, le reseau ne peut donc pas apprendre a les proposer) ;
  - la valeur : combien de points la manche va rapporter a celui qui decide.

Le reseau est minuscule (quelques centaines de milliers de poids) : il tourne sur processeur, et
il tournera plus tard dans le navigateur.

  python3 entrainer.py --jeu jeu --sortie modele --epoques 8
"""
import argparse, json, math, time
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

p = argparse.ArgumentParser()
p.add_argument('--jeu', default='jeu')
p.add_argument('--sortie', default='modele')
p.add_argument('--epoques', type=int, default=8)
p.add_argument('--lot', type=int, default=1024)
p.add_argument('--largeur', type=int, default=512)
p.add_argument('--couches', type=int, default=3)
p.add_argument('--pas', type=float, default=2e-3)
p.add_argument('--validation', type=float, default=0.05)
p.add_argument('--fils', type=int, default=0, help='fils processeur (0 = tous)')
p.add_argument('--budget', type=float, default=0, help='minutes maximum (0 = pas de limite)')
p.add_argument('--appareil', default='auto', help='auto | cpu | cuda')
p.add_argument('--releve', type=int, default=25, help='un point de courbe tous les N lots')
p.add_argument('--poidsLieu', type=float, default=4.0, help='poids de la tache « ou sont les cartes »')
p.add_argument('--poidsGain', type=float, default=1.0, help='poids de la tache « ce que ce coup rapporte »')
p.add_argument('--bloc', type=int, default=4096, help='taille d un bloc lu d un seul tenant sur le disque')
p.add_argument('--tampon', type=int, default=48, help='nombre de blocs melanges ensemble en memoire')
p.add_argument('--reprise-bin', default='',
               help='reprendre les poids de ce reseau .bin (warm-start) au lieu du hasard ; vide = hasard')
a = p.parse_args()

if a.fils:
    torch.set_num_threads(a.fils)

# La boucle compare des essais entre eux : chacun doit disposer du MEME temps, sinon « meilleur »
# ne veut plus rien dire (program.md, interdit n° 6).
appareil = torch.device('cuda' if (a.appareil == 'auto' and torch.cuda.is_available()) or a.appareil == 'cuda' else 'cpu')
budget_s = a.budget * 60 if a.budget > 0 else float('inf')
print(f"appareil : {appareil}" + (f", budget {a.budget:.0f} min" if a.budget else ""), flush=True)

jeu = Path(a.jeu)
meta = json.loads((jeu / 'meta.json').read_text())
N, D, V = meta['exemples'], meta['entrees'], meta['coups']
C, P = meta.get('cartes', 0), meta.get('emplacements', 0)
print(f"{N} exemples, {D} entrees, {V} coups possibles", flush=True)

X = np.memmap(jeu / 'x.bin', dtype=np.uint8, mode='r').reshape(N, D)
M = np.memmap(jeu / 'masque.bin', dtype=np.uint8, mode='r').reshape(N, V)
A = np.memmap(jeu / 'coup.bin', dtype=np.uint16, mode='r').reshape(N)
Y = np.memmap(jeu / 'y.bin', dtype=np.float32, mode='r').reshape(N, 2)
L = np.memmap(jeu / 'lieu.bin', dtype=np.uint8, mode='r').reshape(N, C) if C else None
LM = np.memmap(jeu / 'lieu-masque.bin', dtype=np.uint8, mode='r').reshape(N, C) if C else None

rng = np.random.default_rng(0)
perm = rng.permutation(N)
nval = max(1, int(N * a.validation))
idx_val, idx_tr = perm[:nval], perm[nval:]


from reseau import Reseau

modele = Reseau(D, V, a.largeur, a.couches, C, P).to(appareil)

# Warm-start : reprendre les poids d'un reseau exporte (.bin) au lieu de partir du hasard. Le .bin
# est le format compact d'exporter.py (entete JSON + tenseurs float16) ; on inverse le renommage
# des couches du tronc (.weight -> .lin.weight) via _nom_pour_le_jeu. Round-trip valide par
# test-import-bin.py (byte-identique a l'export pres).
if getattr(a, 'reprise_bin', ''):
    import struct, exporter
    with open(a.reprise_bin, 'rb') as _f:
        (_n,) = struct.unpack('<I', _f.read(4))
        _entete = json.loads(_f.read(_n).decode('utf-8'))
        _blob = _f.read()
    _tens, _off = {}, 0
    for _t in _entete['tenseurs']:
        _cnt = int(np.prod(_t['forme'])) if _t['forme'] else 1
        _arr = np.frombuffer(_blob, dtype=np.float16, count=_cnt, offset=_off).reshape(_t['forme']).astype(np.float32)
        _tens[_t['nom']] = torch.from_numpy(_arr.copy()); _off += _cnt * 2
    _etat = modele.state_dict()
    modele.load_state_dict({k: _tens[exporter._nom_pour_le_jeu(k)].reshape(_etat[k].shape).to(appareil) for k in _etat})
    print(f'reprise depuis {a.reprise_bin} : {len(_etat)} tenseurs charges', flush=True)
# En reprise (warm-start), l'OneCycleLR qui remonte a 2e-3 detruit la calibration des poids
# repris (essai-warm-001 : 205,8 -> 188,0 points). Un warm-start s'affine a pas constant et bas.
if getattr(a, 'reprise_bin', ''):
    a.pas = 3e-4
opt = torch.optim.AdamW(modele.parameters(), lr=a.pas, weight_decay=1e-4)
etapes = a.epoques * max(1, len(idx_tr) // a.lot)
if getattr(a, 'reprise_bin', ''):
    plan = torch.optim.lr_scheduler.ConstantLR(opt, factor=1.0, total_iters=1)
else:
    plan = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.pas, total_steps=etapes)


def lot(indices):
    """Un lot de donnees, converti a la volee (les fichiers restent sur le disque)."""
    i = np.sort(np.asarray(indices))
    d = appareil
    x = torch.from_numpy(np.asarray(X[i], dtype=np.float32) / 255.0).to(d, non_blocking=True)
    m = torch.from_numpy(np.asarray(M[i], dtype=np.bool_)).to(d, non_blocking=True)
    y = torch.from_numpy(np.asarray(A[i], dtype=np.int64)).to(d, non_blocking=True)
    v = torch.from_numpy(np.asarray(Y[i, 0], dtype=np.float32)).to(d, non_blocking=True)
    if L is None:
        return x, m, y, v, None, None
    l = torch.from_numpy(np.asarray(L[i], dtype=np.int64)).to(d, non_blocking=True)
    lm = torch.from_numpy(np.asarray(LM[i], dtype=np.bool_)).to(d, non_blocking=True)
    return x, m, y, v, l, lm


def evalue(indices, taille=4096):
    modele.eval()
    justes = vus = 0
    lieu_justes = lieu_vus = 0
    gain_justes = 0
    erreur_gain = 0.0
    erreur_points = 0.0
    perte = 0.0
    with torch.no_grad():
        for d in range(0, len(indices), taille):
            x, m, y, v, l, lm = lot(indices[d:d + taille])
            logits, val, lieu, gain = modele(x)
            logits = logits.masked_fill(~m, -1e9)
            justes += int((logits.argmax(1) == y).sum())
            # Le coup que le Deep Monte-Carlo choisirait, et ce que sa prevision vaut.
            q = gain.masked_fill(~m, -1e9)
            gain_justes += int((q.argmax(1) == y).sum())
            erreur_gain += float(F.mse_loss(gain.gather(1, y.unsqueeze(1)).squeeze(1), v, reduction='sum'))
            erreur_points += float(F.mse_loss(val, v, reduction='sum'))
            perte += float(F.cross_entropy(logits, y, reduction='sum'))
            vus += len(y)
            if lieu is not None:
                # On ne juge l'inference que sur les cartes qui sont VRAIMENT dans une main
                # adverse : deviner « hors jeu » est facile et represente 80 % des cas.
                chez_qqn = lm & (l >= 1) & (l <= 5)
                if bool(chez_qqn.any()):
                    # On compare CHEZ QUI, pas si la carte est distribuee : le tirage connaît deja
                    # le nombre de cartes de chaque main, il n'a besoin que du classement entre
                    # adversaires. Hasard = 1 / nombre d'adversaires (33 % a quatre joueurs).
                    entre_adversaires = lieu[..., 1:6].argmax(-1) + 1
                    lieu_justes += int((entre_adversaires[chez_qqn] == l[chez_qqn]).sum())
                    lieu_vus += int(chez_qqn.sum())
    modele.train()
    n = max(vus, 1)
    return (justes / n, math.sqrt(erreur_points / n) * 100, perte / n,
            lieu_justes / max(lieu_vus, 1), gain_justes / n, math.sqrt(erreur_gain / n) * 100)


# Le journal des courbes : un point tous les N lots, comme le fait n'importe quel suivi
# d'entrainement. Sans cela il n'y a qu'un point par cycle, et aucune courbe a lire.
journal = []
sortie = Path(a.sortie)
sortie.mkdir(parents=True, exist_ok=True)

def lots_de_l_epoque(indices, graine):
    """Rend les lots d une epoque en lisant le disque PAR BLOCS CONTIGUS.

    Le jeu de donnees (plusieurs gigaoctets) ne tient pas en memoire. Tirer les exemples un par un
    au hasard oblige le disque a sauter partout : mesure sur le serveur d'entrainement, l entrainement tombait a
    0,6 lot par seconde, soit trente fois trop lent. On lit donc des blocs entiers d un seul tenant,
    on en melange plusieurs ensemble en memoire, et on decoupe les lots la-dedans : le disque lit
    en continu et le melange reste suffisant pour que deux exemples voisins ne se suivent pas.
    """
    r = np.random.default_rng(graine)
    appartient = np.zeros(N, dtype=bool)
    appartient[indices] = True
    debuts = np.arange(0, N, a.bloc)
    r.shuffle(debuts)
    for k in range(0, len(debuts), a.tampon):
        groupe = debuts[k:k + a.tampon]
        morceaux = [np.arange(d, min(d + a.bloc, N)) for d in groupe]
        tampon = np.concatenate(morceaux)
        tampon = tampon[appartient[tampon]]
        r.shuffle(tampon)
        for d in range(0, len(tampon) - a.lot + 1, a.lot):
            yield tampon[d:d + a.lot]


t0 = time.time()
etape = 0
perte_glissante = None
for ep in range(a.epoques):
    if time.time() - t0 > budget_s:
        break
    for indices_lot in lots_de_l_epoque(idx_tr, 1000 + ep):
        x, m, y, v, l, lm = lot(indices_lot)
        logits, val, lieu, gain = modele(x)
        logits = logits.masked_fill(~m, -1e9)
        # Le gain n'est appris que pour le coup REELLEMENT joue : c'est la seule case dont on
        # connaisse le resultat. Les autres restent libres (aucune perte ne les tire).
        joue = gain.gather(1, y.unsqueeze(1)).squeeze(1)
        perte = F.cross_entropy(logits, y) + 0.5 * F.mse_loss(val, v) + a.poidsGain * F.mse_loss(joue, v)
        if lieu is not None and bool(lm.any()):
            perte = perte + a.poidsLieu * F.cross_entropy(lieu[lm], l[lm])
        opt.zero_grad(set_to_none=True)
        perte.backward()
        nn.utils.clip_grad_norm_(modele.parameters(), 1.0)
        opt.step()
        if etape + 1 < etapes:
            plan.step()
        etape += 1
        if time.time() - t0 > budget_s:
            print(f"budget atteint a l etape {etape}", flush=True)
            break
        v = float(perte.detach())
        perte_glissante = v if perte_glissante is None else 0.98 * perte_glissante + 0.02 * v
        if etape % a.releve == 0 or etape == 1:
            journal.append({
                'etape': etape,
                'epoque': round(etape / max(1, len(idx_tr) // a.lot), 3),
                'perteEntrainement': round(perte_glissante, 4),
                'pas': round(opt.param_groups[0]['lr'], 6),
                'secondes': round(time.time() - t0, 1),
            })
            (sortie / 'courbes.jsonl').write_text('\n'.join(json.dumps(x) for x in journal))
    acc, ecart, perte_val, acc_lieu, acc_gain, ecart_gain = evalue(idx_val)
    journal.append({
        'etape': etape,
        'epoque': ep + 1,
        'perteEntrainement': round(perte_glissante, 4) if perte_glissante is not None else None,
        'perteValidation': round(perte_val, 4),
        'accordValidation': round(acc, 4),
        'inferenceCartes': round(acc_lieu, 4), 'accordGain': round(acc_gain, 4), 'ecartGain': round(ecart_gain, 2),
        'accordGain': round(acc_gain, 4),
        'ecartGain': round(ecart_gain, 2),
        'ecartPoints': round(ecart, 2),
        'pas': round(opt.param_groups[0]['lr'], 6),
        'secondes': round(time.time() - t0, 1),
    })
    (sortie / 'courbes.jsonl').write_text('\n'.join(json.dumps(x) for x in journal))
    print(f"epoque {ep + 1}/{a.epoques} — accord avec le bot {acc * 100:.1f} % — ecart de points {ecart:.1f} — perte {perte_val:.4f} — cartes devinees {acc_lieu * 100:.1f} % — gain {ecart_gain:.1f} pts — {time.time() - t0:.0f} s", flush=True)

torch.save({k: v.cpu() for k, v in modele.state_dict().items()}, sortie / 'reseau.pt')
# Les poids pour le jeu : un binaire compact (voir exporter.py), pas un JSON de 17 Mo.
import exporter
exporter.ecrire({k: v.cpu() for k, v in modele.state_dict().items()}, sortie / 'reseau.bin', meta['versionEncodage'], D, V, C, P)
acc, ecart, perte_val, acc_lieu, acc_gain, ecart_gain = evalue(idx_val)
(sortie / 'resultat.json').write_text(json.dumps({
    'exemples': N, 'epoques': a.epoques,
    'accordAvecLeBot': round(acc, 4), 'ecartDePoints': round(ecart, 2), 'perteValidation': round(perte_val, 4),
    'inferenceCartes': round(acc_lieu, 4), 'accordGain': round(acc_gain, 4), 'ecartGain': round(ecart_gain, 2),
    'secondes': round(time.time() - t0),
}, indent=1))
print(f"modele ecrit dans {sortie} — accord {acc * 100:.1f} %, cartes devinees {acc_lieu * 100:.1f} %, erreur de gain {ecart_gain:.1f} pts", flush=True)
