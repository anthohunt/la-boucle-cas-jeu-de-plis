#!/usr/bin/env python3
"""Regenere le tableau de bord de la boucle a partir des fichiers de verite.

    python3 tableau.py [sortie.html]

Il ne calcule rien qu'on ne puisse retrouver sur le disque : journal.jsonl pour les essais et leurs
verdicts, archive/index.jsonl pour les lignees, chercheur.log pour les reveils, incidents.log et
ferme.log pour la etat_systeme. Aucun etat cache, donc aucune facon de mentir sur l'avancement.

Appele apres chaque essai juge par tour.sh — le tableau n'est jamais en retard sur la realite.
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import os
BASE = Path(os.environ.get('LOOP_DIR', '.'))   # dossier de travail de la boucle
SORTIE = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / 'tableau-de-bord.html'


def horodate(s):
    """Une date de journal, toujours rendue avec son fuseau : les lignes anciennes n'en ont pas
    toujours, et soustraire une date naive d'une date fusee leve une exception."""
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.astimezone()


def lire_jsonl(chemin):
    """Une ligne non-JSON (marqueur « fini … » d'un script de mesure) ne doit pas faire tomber
    tout le tableau : on la saute."""
    try:
        lignes = chemin.read_text().splitlines()
    except FileNotFoundError:
        return []
    out = []
    for l in lignes:
        l = l.strip()
        if not l.startswith('{'):
            continue
        try:
            out.append(json.loads(l))
        except json.JSONDecodeError:
            continue
    return out


# --- les essais, dedoublonnes, dans l'ordre ------------------------------------------------------
essais, vus = [], set()
for d in lire_jsonl(BASE / 'journal.jsonl'):
    if d.get('victoires') is None and d.get('note') is None:
        continue
    nom = d.get('essai')
    if nom in vus:
        # Une seconde ligne pour le meme essai = une promotion rendue apres coup : on corrige le
        # verdict de la premiere plutot que de compter l'essai deux fois.
        if 'promu' in str(d.get('verdict', '')):
            for e in essais:
                if e['essai'] == nom:
                    e['verdict'] = 'promu'
        continue
    vus.add(nom)
    # Depuis le 13/09 le journal parle en victoires et en points ; avant, en note relative.
    note = d.get('victoires', d.get('note'))
    essais.append({'essai': nom, 'note': float(note), 'points': d.get('points'),
                   'ancienne': 'victoires' not in d,
                   'verdict': 'promu' if 'promu' in str(d.get('verdict', '')) else 'jete',
                   'parent': d.get('parent', ''), 'hypothese': (d.get('hypothese') or '').strip(),
                   'parties': d.get('parties')})

promotions = [i for i, e in enumerate(essais) if e['verdict'] == 'promu']

# Le champion change a chaque promotion : les notes d'un troncon ne se comparent pas a celles d'un
# autre, et le tableau doit le dire au lieu de les aligner.
troncons, debut = [], 0
for n, i in enumerate(promotions, 1):
    troncons.append({'de': debut, 'a': i, 'titre': f'contre le champion n° {n}'})
    debut = i + 1
troncons.append({'de': debut, 'a': len(essais) - 1, 'titre': f'contre le champion n° {len(promotions) + 1}'})
troncons = [t for t in troncons if t['a'] >= t['de']]


def texte(chemin, defaut=''):
    try:
        return (BASE / chemin).read_text().strip()
    except FileNotFoundError:
        return defaut


# --- etat_systeme du systeme ---------------------------------------------------------------------------
maintenant = datetime.now().astimezone()

reveils = []
for ligne in texte('chercheur.log').splitlines():
    m = re.match(r'(\S+) reveil \(session', ligne)
    if m:
        d = horodate(m.group(1))
        if d:
            reveils.append(d)
dernier_reveil = reveils[-1] if reveils else None

incidents_24h = 0
for ligne in texte('incidents.log').splitlines():
    m = re.match(r'(\S+) ', ligne)
    if m:
        d = horodate(m.group(1))
        if d and maintenant - d < timedelta(hours=24):
            incidents_24h += 1

vivant = subprocess.run(['pgrep', '-f', 'chercheur.sh'], capture_output=True).returncode == 0
essai_en_cours = subprocess.run(['pgrep', '-f', f'{BASE}/tour.sh'], capture_output=True).returncode == 0

ferme = [l for l in texte('ferme.log').splitlines()][-3:]

# Debit : ecart entre essais consecutifs, mesure sur l'horodatage de leur nom.
horaires = []
for e in essais:
    m = re.search(r'-(\d{6})$', e['essai']) or re.search(r'-(\d{6})', e['essai'])
    if m:
        horaires.append(m.group(1))
durees = []
for a, b in zip(horaires, horaires[1:]):
    try:
        ta = datetime.strptime(a, '%H%M%S'); tb = datetime.strptime(b, '%H%M%S')
        d = (tb - ta).total_seconds() / 60
        if 0 < d < 120:
            durees.append(d)
    except ValueError:
        pass
durees.sort()
mediane = durees[len(durees) // 2] if durees else 0
par_jour = round(1440 / mediane) if mediane else 0

parties = [e['parties'] for e in essais if isinstance(e.get('parties'), (int, float))]
moy_parties = round(sum(parties) / len(parties)) if parties else None

# LE NIVEAU ATTEINT, contre une reference qui ne bouge pas. Sans lui, le tableau montre la
# difficulte de chaque tentative et jamais le niveau : la barre de promotion est toujours a 0,53
# parce qu'elle est relative au champion du moment. C'est le seul escalier qui monte.
progression = lire_jsonl(BASE / 'progression.jsonl')

# LA FORCE EN FONCTION DU TEMPS DE REFLEXION. En production le bot est plafonne en TEMPS, pas en
# nombre de simulations : un gain obtenu au banc sans limite de temps peut ne pas exister en jeu.
# Cette courbe dit ce que le champion vaut reellement pour chaque duree qu'on accepte de faire
# attendre un joueur — c'est elle qui decide ce qu'on deploie.
budgets = [d for d in lire_jsonl(BASE / 'mesure-budget.jsonl') if d.get('budgetMs')]
budgets.sort(key=lambda d: d['budgetMs'])

champion_pts = texte('champion/points.txt', '—')
champion_vict = texte('champion/victoires.txt', '—')
try:
    champion_vict_pc = f"{float(champion_vict) * 100:.1f} %"
except ValueError:
    champion_vict_pc = '—'
champion_adv = f"{progression[-1]['pointsAdversaire']:.0f}" if progression and progression[-1].get('pointsAdversaire') else '—'


def ech(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


# --- le graphique, en SVG, un panneau par champion -----------------------------------------------
L, H = 1080, 400
mg = {'haut': 50, 'bas': 40, 'gauche': 48, 'droite': 14}
ecart = 30
ht = H - mg['haut'] - mg['bas']
ymin, ymax = 0.44, 0.56
notes = [e['note'] for e in essais] or [0.5]
ymin = min(ymin, min(notes) - 0.01)
ymax = max(ymax, max(notes) + 0.01)


def y(v):
    return mg['haut'] + (ymax - v) / (ymax - ymin) * ht


svg = []
total = max(1, len(essais))
utile = L - mg['gauche'] - mg['droite'] - ecart * max(0, len(troncons) - 1)
pas = utile / total
larg_barre = max(4, pas * 0.62)
yeg = y(0.50)

v = 0.46
while v <= ymax:
    yy = y(v)
    svg.append(f'<line x1="{mg["gauche"]}" y1="{yy:.1f}" x2="{L - mg["droite"]}" y2="{yy:.1f}" stroke="var(--trait)" stroke-width="1" opacity="0.5"/>')
    svg.append(f'<text x="{mg["gauche"] - 8}" y="{yy + 3.5:.1f}" text-anchor="end" font-family="IBM Plex Mono, monospace" font-size="9.5" fill="var(--encre-pale)">{v * 100:.0f} %</text>')
    v += 0.02

x = mg['gauche']
for k, tr in enumerate(troncons):
    nb = tr['a'] - tr['de'] + 1
    lg = nb * pas
    svg.append(f'<rect x="{x:.1f}" y="{mg["haut"]}" width="{lg:.1f}" height="{ht}" fill="var(--trait)" opacity="{0.3 if k % 2 else 0.13}"/>')
    svg.append(f'<text x="{x:.1f}" y="{mg["haut"] - 12}" font-family="IBM Plex Mono, monospace" font-size="9.5" letter-spacing="0.7" fill="var(--encre-pale)">{ech(tr["titre"].upper())} · {nb} ESSAIS</text>')
    svg.append(f'<line x1="{x:.1f}" y1="{yeg:.1f}" x2="{x + lg:.1f}" y2="{yeg:.1f}" stroke="var(--encre-douce)" stroke-width="1.6"/>')
    ys = y(0.53)
    svg.append(f'<line x1="{x:.1f}" y1="{ys:.1f}" x2="{x + lg:.1f}" y2="{ys:.1f}" stroke="var(--laiton)" stroke-width="1.8" stroke-dasharray="6 4"/>')
    for i in range(tr['de'], tr['a'] + 1):
        e = essais[i]
        x0 = x + (i - tr['de']) * pas + (pas - larg_barre) / 2
        yv = y(e['note'])
        haut = max(1.5, abs(yv - yeg))
        promu = e['verdict'] == 'promu'
        col = 'var(--vert)' if promu else 'var(--encre-pale)'
        op = '1' if promu else ('0.9' if e['note'] >= 0.5 else '0.45')
        svg.append(f'<rect x="{x0:.1f}" y="{min(yv, yeg):.1f}" width="{larg_barre:.1f}" height="{haut:.1f}" fill="{col}" opacity="{op}"><title>{ech(e["essai"])} — {e["note"] * 100:.2f} %{" — promu" if promu else ""}</title></rect>')
        if promu:
            svg.append(f'<circle cx="{x0 + larg_barre / 2:.1f}" cy="{yv - 10:.1f}" r="3.2" fill="var(--vert)"/>')
    svg.append(f'<line x1="{x:.1f}" y1="{mg["haut"] + ht:.1f}" x2="{x + lg:.1f}" y2="{mg["haut"] + ht:.1f}" stroke="var(--trait)" stroke-width="1"/>')
    svg.append(f'<text x="{x:.1f}" y="{mg["haut"] + ht + 15:.1f}" font-family="IBM Plex Mono, monospace" font-size="9" fill="var(--encre-pale)">{tr["de"] + 1}</text>')
    svg.append(f'<text x="{x + lg:.1f}" y="{mg["haut"] + ht + 15:.1f}" text-anchor="end" font-family="IBM Plex Mono, monospace" font-size="9" fill="var(--encre-pale)">{tr["a"] + 1}</text>')
    x += lg + ecart

svg.append(f'<text x="{L - mg["droite"]}" y="{y(0.53) - 6:.1f}" text-anchor="end" font-family="IBM Plex Mono, monospace" font-size="9.5" letter-spacing="0.6" fill="var(--laiton)">BARRE DE PROMOTION</text>')

# --- l'escalier du niveau atteint ---------------------------------------------------------------
esc_svg = ''
if len(progression) >= 1:
    EL, EH = 1080, 210
    emg = {'haut': 26, 'bas': 40, 'gauche': 48, 'droite': 90}
    eht = EH - emg['haut'] - emg['bas']
    vals = [p.get('victoires', p.get('note', 0)) for p in progression]
    bas = min(0.48, min(vals) - 0.01)
    hautv = max(0.56, max(vals) + 0.015)

    def ey(v):
        return emg['haut'] + (hautv - v) / (hautv - bas) * eht

    n = len(progression)
    epas = (EL - emg['gauche'] - emg['droite']) / max(n, 2)
    parts = []
    v = round(bas + 0.02 - (bas * 100 % 2) / 100, 2)
    while v <= hautv:
        yy = ey(v)
        parts.append(f'<line x1="{emg["gauche"]}" y1="{yy:.1f}" x2="{EL - emg["droite"]}" y2="{yy:.1f}" stroke="var(--trait)" stroke-width="1" opacity="0.5"/>')
        parts.append(f'<text x="{emg["gauche"] - 8}" y="{yy + 3.5:.1f}" text-anchor="end" font-family="IBM Plex Mono, monospace" font-size="9.5" fill="var(--encre-pale)">{v * 100:.0f} %</text>')
        v = round(v + 0.02, 2)

    # la ligne des 50 % : c'est le bot deploye lui-meme, la reference
    y50 = ey(0.50)
    parts.append(f'<line x1="{emg["gauche"]}" y1="{y50:.1f}" x2="{EL - emg["droite"]}" y2="{y50:.1f}" stroke="var(--rouge)" stroke-width="1.6"/>')
    parts.append(f'<text x="{EL - emg["droite"] + 6}" y="{y50 + 3.5:.1f}" font-family="IBM Plex Mono, monospace" font-size="9.5" fill="var(--rouge)">bot en prod</text>')

    # l'escalier : un palier par champion, la largeur du palier = son regne
    chemin = []
    for i, pr in enumerate(progression):
        x0 = emg['gauche'] + i * epas
        x1 = x0 + epas
        yy = ey(pr.get('victoires', pr.get('note', 0)))
        chemin.append(f'{"M" if i == 0 else "L"} {x0:.1f} {yy:.1f} L {x1:.1f} {yy:.1f}')
        parts.append(f'<rect x="{x0:.1f}" y="{yy:.1f}" width="{epas:.1f}" height="{max(0, y50 - yy):.1f}" fill="var(--vert)" opacity="0.14"/>')
        parts.append(f'<circle cx="{x0 + epas / 2:.1f}" cy="{yy:.1f}" r="4" fill="var(--vert)"><title>{ech(pr.get("etiquette", pr.get("champion", "champion")))} — {pr.get("victoires", pr.get("note", 0)) * 100:.1f} % contre le bot en prod, {pr.get("parties", "?")} parties</title></circle>')
        parts.append(f'<text x="{x0 + epas / 2:.1f}" y="{yy - 11:.1f}" text-anchor="middle" font-family="Fraunces, serif" font-weight="600" font-size="14" fill="var(--vert)">{pr.get("victoires", pr.get("note", 0)) * 100:.1f} %</text>')
        parts.append(f'<text x="{x0 + epas / 2:.1f}" y="{emg["haut"] + eht + 16:.1f}" text-anchor="middle" font-family="IBM Plex Mono, monospace" font-size="9.5" fill="var(--encre-pale)">{ech(pr.get("etiquette", pr.get("champion", "champion")).upper())}</text>')
    parts.append(f'<path d="{" ".join(chemin)}" fill="none" stroke="var(--vert)" stroke-width="2.4"/>')
    esc_svg = ''.join(parts)

    # de combien on a bouge depuis le premier champion mesure
    gain = (progression[-1].get('victoires', progression[-1].get('note', 0)) - progression[0].get('victoires', progression[0].get('note', 0))) * 100
    gain_txt = f'{gain:+.1f} point{"s" if abs(gain) >= 2 else ""} depuis le premier champion mesuré'
else:
    gain_txt = 'pas encore de mesure'

# --- la force en fonction du temps de reflexion --------------------------------------------------
temps_svg = ''
if len(budgets) >= 2:
    TL, TH = 1080, 230
    tmg = {'haut': 26, 'bas': 46, 'gauche': 52, 'droite': 60}
    tht = TH - tmg['haut'] - tmg['bas']
    vs = [b['victoires'] for b in budgets]
    tbas, thaut = min(0.45, min(vs) - 0.02), max(0.65, max(vs) + 0.02)
    xs = [b['budgetMs'] for b in budgets]
    xmin, xmax = min(xs), max(xs)

    def ty(v):
        return tmg['haut'] + (thaut - v) / (thaut - tbas) * tht

    def tx(ms):
        import math
        lo, hi = math.log(max(xmin, 1)), math.log(max(xmax, 2))
        f = 0.5 if hi == lo else (math.log(max(ms, 1)) - lo) / (hi - lo)
        return tmg['gauche'] + f * (TL - tmg['gauche'] - tmg['droite'])

    parts = []
    v = round(tbas + 0.05 - (tbas * 100 % 5) / 100, 2)
    while v <= thaut:
        yy = ty(v)
        parts.append(f'<line x1="{tmg["gauche"]}" y1="{yy:.1f}" x2="{TL - tmg["droite"]}" y2="{yy:.1f}" stroke="var(--trait)" stroke-width="1" opacity="0.5"/>')
        parts.append(f'<text x="{tmg["gauche"] - 8}" y="{yy + 3.5:.1f}" text-anchor="end" font-family="IBM Plex Mono, monospace" font-size="9.5" fill="var(--encre-pale)">{v * 100:.0f} %</text>')
        v = round(v + 0.05, 2)

    y50 = ty(0.50)
    parts.append(f'<line x1="{tmg["gauche"]}" y1="{y50:.1f}" x2="{TL - tmg["droite"]}" y2="{y50:.1f}" stroke="var(--rouge)" stroke-width="1.6"/>')
    parts.append(f'<text x="{TL - tmg["droite"] + 6}" y="{y50 + 3.5:.1f}" font-family="IBM Plex Mono, monospace" font-size="9.5" fill="var(--rouge)">bot en prod</text>')

    # la duree reellement servie en production, pour situer les points
    xprod = tx(1000)
    parts.append(f'<line x1="{xprod:.1f}" y1="{tmg["haut"]}" x2="{xprod:.1f}" y2="{tmg["haut"] + tht:.1f}" stroke="var(--laiton)" stroke-width="1.6" stroke-dasharray="6 4"/>')
    parts.append(f'<text x="{xprod + 6:.1f}" y="{tmg["haut"] + 11:.1f}" font-family="IBM Plex Mono, monospace" font-size="9.5" letter-spacing="0.6" fill="var(--laiton)">RÉGLAGE ACTUEL</text>')

    chemin = ' '.join(f'{"M" if i == 0 else "L"} {tx(b["budgetMs"]):.1f} {ty(b["victoires"]):.1f}' for i, b in enumerate(budgets))
    parts.append(f'<path d="{chemin}" fill="none" stroke="var(--vert)" stroke-width="2.4"/>')
    for b in budgets:
        x0, y0 = tx(b['budgetMs']), ty(b['victoires'])
        ms = b['budgetMs']
        lib = f'{ms} ms' if ms < 1000 else f'{ms / 1000:g} s'
        parts.append(f'<circle cx="{x0:.1f}" cy="{y0:.1f}" r="4" fill="var(--vert)"><title>{lib} — {b["victoires"] * 100:.1f} % de parties gagnées, {b.get("points", "?")} points</title></circle>')
        parts.append(f'<text x="{x0:.1f}" y="{y0 - 11:.1f}" text-anchor="middle" font-family="Fraunces, serif" font-weight="600" font-size="13" fill="var(--vert)">{b["victoires"] * 100:.1f} %</text>')
        parts.append(f'<text x="{x0:.1f}" y="{tmg["haut"] + tht + 17:.1f}" text-anchor="middle" font-family="IBM Plex Mono, monospace" font-size="10" fill="var(--encre-pale)">{lib}</text>')
        parts.append(f'<text x="{x0:.1f}" y="{tmg["haut"] + tht + 31:.1f}" text-anchor="middle" font-family="IBM Plex Mono, monospace" font-size="9" fill="var(--encre-pale)">{ms * 3 / 1000:g} s d\'attente</text>')
    temps_svg = ''.join(parts)

# --- les derniers essais --------------------------------------------------------------------------
lignes = []
for e in reversed(essais[-12:]):
    h = e['hypothese']
    h = (h[:180] + '…') if len(h) > 180 else h
    etat = '<span class="pastille p">promu</span>' if e['verdict'] == 'promu' else '<span class="pastille j">jeté</span>'
    lignes.append(f'<tr><td class="mono">{ech(e["essai"])}</td><td class="mono num">{e["note"] * 100:.1f} %{"*" if e.get("ancienne") else ""}</td><td class="mono num">{e["points"] if e.get("points") else "—"}</td>'
                  f'<td>{etat}</td><td class="mono petit">{ech(e["parent"])}</td><td class="hypo">{ech(h)}</td></tr>')

# --- le chantier en cours : la derniere « marque » du journal (les grandes manoeuvres qui ne sont
# pas des essais — changement de gate, test A/A… ), pour que le tableau dise ce que le chercheur
# fait VRAIMENT quand aucun essai ne tourne.
chantier_html = ''
marques = [d for d in lire_jsonl(BASE / 'journal.jsonl') if d.get('marque')]
if marques:
    m = marques[-1]['marque']
    m = (m[:260] + '…') if len(m) > 260 else m
    chantier_html = f'<p class="sous" style="border-left:3px solid var(--laiton); padding-left:0.8rem;"><strong>Chantier en cours</strong> — {ech(m)}</p>'

etat_systeme = []
etat_systeme.append(('Chercheur', 'éveillé' if vivant else 'ARRÊTÉ', 'bon' if vivant else 'mauvais'))
etat_systeme.append(('Essai en cours', 'oui' if essai_en_cours else 'non', 'neutre'))
if dernier_reveil:
    age = (maintenant - dernier_reveil).total_seconds() / 60
    etat_systeme.append(('Dernier réveil', f'il y a {age:.0f} min', 'bon' if age < 60 else 'mauvais'))
etat_systeme.append(('Incidents (24 h)', str(incidents_24h), 'bon' if incidents_24h == 0 else 'mauvais'))

html = f"""<!doctype html>
<html lang="fr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="900">
<title>Progression des bots</title>
<style>
:root {{
  --encre:#12211f; --encre-pale:#6f8681; --papier:#f1f3f0; --papier-creux:#e5e9e5;
  --trait:#cdd5d1; --laiton:#9a6f1f; --vert:#14705a; --rouge:#9c3b2c;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --encre:#e8efec; --encre-pale:#6f8681; --papier:#0d1817; --papier-creux:#142322;
    --trait:#26403c; --laiton:#d9a941; --vert:#4fc3a1; --rouge:#e08472;
  }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--papier); color:var(--encre);
  font-family:"Source Sans 3",system-ui,sans-serif; display:flex; justify-content:center;
  padding:2rem 1rem 3rem; }}
.page {{ width:100%; max-width:1000px; display:flex; flex-direction:column; gap:1.6rem; }}
h2 {{ font-family:"Fraunces",serif; font-weight:600; font-size:1.25rem;
  letter-spacing:-0.015em; margin:0 0 0.4rem; }}
h1 {{ font-family:"Fraunces",serif; font-weight:600;
  font-size:clamp(1.6rem,4vw,2.4rem); line-height:1.1; margin:0; letter-spacing:-0.02em; }}
h1 em {{ font-style:normal; color:var(--vert); }}
.sous {{ margin:0; color:var(--encre-pale); font-size:0.95rem; }}
.cadre {{ border:1px solid var(--trait); background:var(--papier-creux); padding:1.2rem 0.8rem;
  overflow-x:auto; }}
.cadre svg {{ display:block; min-width:520px; width:100%; height:auto; }}
.terminal {{ display:flex; flex-direction:column; gap:0.5rem; }}
.etiquette {{ font-family:"IBM Plex Mono",monospace; font-size:0.63rem; letter-spacing:0.12em;
  text-transform:uppercase; color:var(--encre-pale); }}
#compte {{ color:var(--laiton); font-variant-numeric:tabular-nums; }}
.terminal iframe {{ width:100%; height:min(58vh,520px); border:1px solid var(--trait);
  background:#0d1817; display:block; }}
footer {{ font-family:"IBM Plex Mono",monospace; font-size:0.7rem; color:var(--encre-pale);
  display:flex; justify-content:space-between; gap:1rem; flex-wrap:wrap; }}
</style></head><body><div class="page">

<h1>Parties gagnées contre le bot du jeu : <em>{champion_vict_pc}</em></h1>
<p class="sous">Chaque marche est un champion successif. Au-dessus de la ligne rouge, les bots sont meilleurs que ceux du jeu aujourd'hui. {gain_txt}.</p>
{chantier_html}

<div class="cadre">{"<svg viewBox='0 0 1080 210' role='img' aria-label='Parties gagnées par chaque champion'>" + esc_svg + "</svg>" if esc_svg else "<p class='sous'>Aucune mesure encore.</p>"}</div>

<section>
  <h2>Ce que valent les bots selon le temps qu'on leur laisse</h2>
  <p class="sous">En jeu, un bot est limité par le TEMPS, pas par le nombre de simulations. Sous chaque point : ce que le joueur attend entre deux de ses tours, trois bots jouant l'un après l'autre.</p>
  <div class="cadre">{"<svg viewBox='0 0 1080 230' role='img' aria-label='Parties gagnées selon le temps de réflexion'>" + temps_svg + "</svg>" if temps_svg else "<p class='sous'>Mesure en cours — il faut au moins deux durées.</p>"}</div>
</section>

<footer>
  <span>{len(essais)} idées essayées · {len(promotions)} retenues · {champion_pts} points par partie</span>
  <span>{maintenant.strftime("%d/%m à %H:%M")} · {"chercheur éveillé" if vivant else "chercheur arrêté"}</span>
</footer>
</div>
<script>
// Le decompte jusqu'au prochain reveil. Le cron reveille le chercheur au quart d'heure (0, 15, 30,
// 45) ; il peut demander un reveil plus tard, mais le cron passe de toute facon — c'est donc le
// quart d'heure qui borne l'attente, et c'est ce qu'on affiche.
const cible = document.getElementById("compte");
function tic() {{
  const n = new Date();
  const prochain = new Date(n);
  prochain.setMinutes(Math.floor(n.getMinutes() / 15) * 15 + 15, 0, 0);
  const s = Math.max(0, Math.round((prochain - n) / 1000));
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  cible.textContent = " · prochain réveil dans " + mm + ":" + ss;
}}
tic(); setInterval(tic, 1000);
</script>
</body></html>
"""

SORTIE.write_text(html)
print(f'{SORTIE} : {len(essais)} essais, {len(promotions)} promotions')
