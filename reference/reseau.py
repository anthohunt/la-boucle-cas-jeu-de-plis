"""Le reseau lui-meme, partage par l'entrainement, l'export et le controle de parite."""
import torch.nn as nn
import torch.nn.functional as F


class Bloc(nn.Module):
    """Une couche du tronc : une transformation lineaire, une normalisation, un seuil a zero."""

    def __init__(self, entree, sortie):
        super().__init__()
        self.lin = nn.Linear(entree, sortie)
        self.norme = nn.LayerNorm(sortie)

    def forward(self, x):
        return F.relu(self.norme(self.lin(x)))


class Reseau(nn.Module):
    """Tronc partage, deux tetes : le coup a jouer, et les points attendus."""

    def __init__(self, d, v, largeur, couches, cartes=0, emplacements=0):
        super().__init__()
        blocs = []
        entree = d
        for _ in range(couches):
            blocs.append(Bloc(entree, largeur))
            entree = largeur
        self.tronc = nn.ModuleList(blocs)
        self.politique = nn.Linear(largeur, v)
        self.valeur = nn.Linear(largeur, 1)
        self.cartes = cartes
        self.emplacements = emplacements
        # Troisieme sortie : pour chaque carte que je ne vois pas, chez qui elle est. C'est elle
        # qui remplacera le tirage au hasard dans les simulations du bot.
        self.lieu = nn.Linear(largeur, cartes * emplacements) if cartes and emplacements else None
        # Quatrieme sortie : ce que CHAQUE coup rapporte reellement (Deep Monte-Carlo, facon
        # DouZero). C'est elle qui decide en jeu — la politique ne fait plus qu'imiter le bot
        # actuel, ce qui sert de garde-fou et d'aide au demarrage, pas de but.
        self.gain = nn.Linear(largeur, v)

    def forward(self, x):
        h = x
        for b in self.tronc:
            h = b(h)
        lieu = None
        if self.lieu is not None:
            lieu = self.lieu(h).view(-1, self.cartes, self.emplacements)
        return self.politique(h), self.valeur(h).squeeze(-1), lieu, self.gain(h)


