# SPDX-License-Identifier: Apache-2.0
"""A self-contained HTML dashboard (no script, no external file) from a loop journal.

It reads the journal of this repository (English keys) and also the journal of the original
experiment kept in recit/journal.jsonl (French keys): the KEY_ALIASES below translate them.
Nothing is computed that cannot be found again in the journal: no hidden state.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

KEY_ALIASES = {"essai": "attempt", "hypothese": "hypothesis", "victoires": "wins", "points": "points",
               "champion_victoires": "champion_wins", "champion_points": "champion_points",
               "marque": "mark", "raison": "reason"}
VERDICT_WORDS = {"kept": "kept", "discarded": "discarded", "promu": "kept", "promoted": "kept"}


def _norm(row: dict) -> dict:
    out = {KEY_ALIASES.get(k, k): v for k, v in row.items()}
    v = str(out.get("verdict", ""))
    if v:
        out["verdict"] = VERDICT_WORDS.get(v, "kept" if v.startswith("promu") else "discarded" if v.startswith("jet") else "pending")
    return out


def read_journal(path) -> list[dict]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                rows.append(_norm(json.loads(line)))
            except json.JSONDecodeError:
                continue
    return rows


CSS = """
:root{--bg:#fafaf7;--fg:#1d2327;--mut:#5d676d;--card:#fff;--line:#d9dcd6;--kept:#1d7a46;--disc:#a33a2b;--pend:#8a7a1f;--ref:#6a5acd}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#14181a;--fg:#e6e8e3;--mut:#9aa4aa;--card:#1c2124;--line:#33393d;--kept:#4cc07a;--disc:#e8806f;--pend:#d8c44c;--ref:#a99bff}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}
main{max-width:980px;margin:0 auto;padding:16px}
h1{font-size:1.4rem;margin:.2rem 0}h2{font-size:1.1rem;margin:1.6rem 0 .5rem}
.sub{color:var(--mut);margin:0 0 1rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0}
.kept{border-left:5px solid var(--kept)}.discarded{border-left:5px solid var(--disc)}.pending{border-left:5px solid var(--pend)}
.mark{border-left:5px solid var(--ref)}
.tag{font-weight:600}.tag.kept{color:var(--kept)}.tag.discarded{color:var(--disc)}
.nums{color:var(--mut);font-variant-numeric:tabular-nums}
svg{width:100%;height:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}
.ax{stroke:var(--line)}.lbl{fill:var(--mut);font-size:11px}
"""


def _chart(attempts: list[dict], reference) -> str:
    pts = [a for a in attempts if isinstance(a.get("wins"), (int, float))]
    if not pts:
        return "<p class='sub'>No measured attempt yet.</p>"
    W, H, L, R, T, B = 760, 280, 46, 14, 14, 34
    vals = [a["wins"] for a in pts] + [a.get("champion_wins") for a in pts if isinstance(a.get("champion_wins"), (int, float))]
    if reference is not None:
        vals.append(reference)
    lo, hi = max(0.0, min(vals) - 0.04), min(1.0, max(vals) + 0.04)
    if hi - lo < 0.1:
        hi = lo + 0.1

    def x(i):
        return L + (W - L - R) * (i + 0.5) / len(pts)

    def y(v):
        return T + (H - T - B) * (1 - (v - lo) / (hi - lo))

    s = [f"<svg viewBox='0 0 {W} {H}' role='img' aria-label='Win rate of each attempt against the reference, with the champion level at that time'>"]
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        s.append(f"<line class='ax' x1='{L}' x2='{W - R}' y1='{y(v):.1f}' y2='{y(v):.1f}'/>"
                 f"<text class='lbl' x='{L - 6}' y='{y(v) + 4:.1f}' text-anchor='end'>{v * 100:.0f}%</text>")
    if reference is not None and lo <= reference <= hi:
        s.append(f"<line x1='{L}' x2='{W - R}' y1='{y(reference):.1f}' y2='{y(reference):.1f}' stroke='var(--ref)' stroke-dasharray='5 4'/>"
                 f"<text class='lbl' x='{W - R}' y='{y(reference) - 4:.1f}' text-anchor='end' fill='var(--ref)'>equal strength to the reference (25%)</text>")
    for i, a in enumerate(pts):
        if isinstance(a.get("champion_wins"), (int, float)):
            s.append(f"<line x1='{x(i) - 14:.1f}' x2='{x(i) + 14:.1f}' y1='{y(a['champion_wins']):.1f}' y2='{y(a['champion_wins']):.1f}' "
                     f"stroke='var(--mut)' stroke-width='3'><title>champion at that time: {a['champion_wins'] * 100:.1f}%</title></line>")
        col = "var(--kept)" if a.get("verdict") == "kept" else "var(--disc)" if a.get("verdict") == "discarded" else "var(--pend)"
        s.append(f"<circle cx='{x(i):.1f}' cy='{y(a['wins']):.1f}' r='6' fill='{col}'>"
                 f"<title>{html.escape(str(a.get('attempt', i)))}: {a['wins'] * 100:.1f}%</title></circle>"
                 f"<text class='lbl' x='{x(i):.1f}' y='{H - 14}' text-anchor='middle'>{i + 1}</text>")
    s.append(f"<text class='lbl' x='{L}' y='{H - 1}'>attempt number (grey bar = champion it was compared to; dot = candidate; "
             f"green kept, red discarded)</text></svg>")
    return "".join(s)


def render(rows: list[dict], title: str, reference=None) -> str:
    attempts = [r for r in rows if "attempt" in r]
    kept = sum(1 for a in attempts if a.get("verdict") == "kept")
    parts = [f"<h1>{html.escape(title)}</h1>",
             f"<p class='sub'>{len(attempts)} attempts, {kept} kept, {len(attempts) - kept} discarded. "
             f"Every number below comes from the journal.</p>", _chart(attempts, reference), "<h2>Journal</h2>"]
    for r in rows:
        if "mark" in r:
            parts.append(f"<div class='card mark'>{html.escape(str(r['mark']))}</div>")
            continue
        if "attempt" not in r:
            continue
        v = r.get("verdict", "pending")
        nums = []
        if isinstance(r.get("wins"), (int, float)):
            nums.append(f"wins {r['wins'] * 100:.1f}%")
        if isinstance(r.get("points"), (int, float)):
            nums.append(f"{r['points']:.1f} points")
        if isinstance(r.get("champion_wins"), (int, float)):
            nums.append(f"champion {r['champion_wins'] * 100:.1f}% / {r.get('champion_points', 0):.1f}")
        why = f"<div>{html.escape(str(r['reason']))}</div>" if r.get("reason") else ""
        parts.append(f"<div class='card {html.escape(v)}'><div><span class='tag {html.escape(v)}'>{html.escape(v.upper())}</span> "
                     f"<strong>{html.escape(str(r['attempt']))}</strong> <span class='nums'>{' · '.join(nums)}</span></div>"
                     f"<div>{html.escape(str(r.get('hypothesis', '')))}</div>{why}</div>")
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body><main>{''.join(parts)}</main></body></html>")


def write_dashboard(journal_path, out_path, title: str = "Loop dashboard", reference=None) -> Path:
    out = Path(out_path)
    out.write_text(render(read_journal(journal_path), title, reference), encoding="utf-8")
    return out
