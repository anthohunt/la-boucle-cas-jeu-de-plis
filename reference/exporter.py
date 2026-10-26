"""Ecrit les poids sous la forme que le jeu sait relire (`packages/bots/src/net.ts`).

Format : 4 octets = longueur de l'entete, l'entete JSON (dimensions et ordre des tableaux), puis
les tableaux en demi-precision. Demi-precision = deux fois plus petit qu'en flottants simples, et
l'ecart introduit (~1/1000) est sans effet sur le choix d'un coup.

Les noms sont nettoyes au passage : `tronc.0.lin.weight` devient `tronc.0.weight`, parce que le
cote jeu range chaque couche avec sa normalisation, sans le detour par les sous-modules.
"""
import json
import struct
import numpy as np


def _nom_pour_le_jeu(k: str) -> str:
    return k.replace('.lin.weight', '.weight').replace('.lin.bias', '.bias')


def ecrire(etat, chemin, version_encodage: int, entrees: int, coups: int, cartes: int = 0, emplacements: int = 0) -> int:
    tenseurs = [(_nom_pour_le_jeu(k), np.asarray(v.detach().cpu().numpy(), dtype=np.float16)) for k, v in etat.items()]
    entete = json.dumps({
        'versionEncodage': version_encodage,
        'entrees': entrees,
        'coups': coups,
        'cartes': cartes,
        'emplacements': emplacements,
        'tenseurs': [{'nom': n, 'forme': list(t.shape)} for n, t in tenseurs],
    }).encode('utf-8')
    with open(chemin, 'wb') as f:
        f.write(struct.pack('<I', len(entete)))
        f.write(entete)
        for _, t in tenseurs:
            f.write(t.tobytes(order='C'))
    return chemin.stat().st_size
