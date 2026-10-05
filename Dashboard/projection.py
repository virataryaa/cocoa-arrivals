"""IVC weekly arrivals by port (Abidjan / San Pedro, Mon-Sat) with the projection of unfinished weeks.

Projection = known days / historical share of those days in the full week, where the share is the ratio of sums over
every earlier week that has all six days. Works for any set of known days (Mon-Thu, a blank Monday, ...).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DB = Path(__file__).resolve().parent.parent / "Database"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
PORTS = ["Abidjan", "San Pedro"]
BAR = {"Abidjan": "rgba(31,138,156,0.28)", "San Pedro": "rgba(10,36,99,0.22)", "Combined": "rgba(201,138,31,0.32)"}

CSS = """
<style>
.pj-wrap { max-height: 640px; overflow: auto; border: 1px solid #e3e7f0; border-radius: 10px; background: #fff; }
.pj { border-collapse: separate; border-spacing: 0; font-size: 12px; width: 100%; }
.pj th { position: sticky; top: 0; z-index: 2; background: #0a2463; color: #fff; font-weight: 600; padding: 4px 8px; text-align: center; white-space: nowrap; }
.pj th.p1 { background: #1f8a9c; } .pj th.p2 { background: #0a2463; } .pj th.p3 { background: #8a5a12; }
.pj tr.h2 th { top: 25px; background: #eef0f6; color: #0a2463; font-size: 11px; }
.pj td { padding: 2px 8px; text-align: right; border-bottom: 1px solid #eef0f6; white-space: nowrap; color: #1a1a2e;
         font-variant-numeric: tabular-nums; }
.pj td.wk { text-align: center; background: #f6f7fb; font-weight: 600; position: sticky; left: 0; z-index: 1; }
.pj td.tot { font-weight: 700; border-left: 1px solid #dfe3ee; }
.pj td.est { font-style: italic; color: #6f7895; }
.pj td.est.tot { color: #0a2463; }
.pj td.na { color: #b8bfd2; }
.pj td.up { color: #1f9d6f; } .pj td.dn { color: #c94a4a; }
.pj .tag { font-size: 9px; color: #8a5a12; font-weight: 700; margin-left: 3px; }
.pj-note { font-size: 11px; color: #7a86a8; margin-top: 6px; }
</style>
"""


@st.cache_data(ttl=600)
def load() -> pd.DataFrame:
    d = pd.read_csv(DB / "ivc_projection.csv", parse_dates=["week"])
    return d.sort_values(["port", "week"]).reset_index(drop=True)


def project_port(d: pd.DataFrame) -> pd.DataFrame:
    """Adds est_<day> (value or projected fill), total, projected flag, n_known. Point-in-time: only earlier weeks feed the share."""
    d = d.reset_index(drop=True).copy()
    vals = d[DAYS].to_numpy(float)
    known = ~np.isnan(vals)
    full = known.all(axis=1)
    out = np.full(len(d), np.nan)
    fill = vals.copy()
    for i in range(len(d)):
        if full[i]:
            out[i] = vals[i].sum()
            continue
        hist = vals[:i][full[:i]]
        if len(hist) < 4 or not known[i].any():
            continue
        share = hist[:, known[i]].sum() / hist.sum()
        if share <= 0:
            continue
        out[i] = vals[i][known[i]].sum() / share
        miss = ~known[i]
        w = hist[:, miss].sum(axis=0)
        fill[i, miss] = (out[i] - vals[i][known[i]].sum()) * (w / w.sum() if w.sum() else 0)
    d["total"] = out
    d["projected"] = ~full
    d["n_known"] = known.sum(axis=1)
    for j, day in enumerate(DAYS):
        d[f"est_{day}"] = fill[:, j]
        d[f"is_{day}"] = ~known[:, j]
    return d


@st.cache_data(ttl=600)
def build() -> dict:
    raw = load()
    return {p: project_port(raw[raw.port == p].drop(columns="port")) for p in PORTS}


def crop_year(ts: pd.Timestamp) -> str:
    y = ts.year if ts.month >= 10 else ts.year - 1
    return f"{y % 100:02d}/{(y + 1) % 100:02d}"


def _bar(v, vmax, colour, hatch):
    if v is None or np.isnan(v) or vmax <= 0:
        return ""
    pct = max(0.0, min(100.0, v / vmax * 100))
    layer = (f"repeating-linear-gradient(135deg,{colour} 0 3px,rgba(255,255,255,0.55) 3px 6px)" if hatch else
             f"linear-gradient({colour},{colour})")
    return f"background-image:{layer};background-repeat:no-repeat;background-size:{pct:.0f}% 100%;"


def _fmt(v):
    return "-" if v is None or np.isnan(v) else f"{v:,.0f}"


def table_html(data: dict, weeks: pd.DatetimeIndex) -> str:
    ab, sp = data["Abidjan"].set_index("week"), data["San Pedro"].set_index("week")
    all_w = ab.index.union(sp.index)
    comb_all = ab["total"].reindex(all_w) + sp["total"].reindex(all_w)
    prev_all = comb_all.reindex(all_w - pd.Timedelta(days=7)).set_axis(all_w)   # NaN when the previous week is missing
    dmax = {p: np.nanmax(data[p][[f"est_{x}" for x in DAYS]].to_numpy()) for p in PORTS}
    tmax = {p: np.nanmax(data[p]["total"]) for p in PORTS}
    cmax = np.nanmax(comb_all)

    h1 = ("<tr><th rowspan=2>Week of</th><th class='p1' colspan=7>Abidjan</th><th class='p2' colspan=7>San Pedro</th>"
          "<th class='p3' colspan=2>Combined</th></tr>")
    h2 = "<tr class='h2'>" + ("".join(f"<th>{x}</th>" for x in DAYS) + "<th>Total</th>") * 2 + "<th>Total</th><th>WoW</th></tr>"
    rows = []
    for w in weeks:
        tds = [f"<td class='wk'>{w:%d-%b-%y}</td>"]
        for p, t in (("Abidjan", ab), ("San Pedro", sp)):
            r = t.loc[w] if w in t.index else None
            for day in DAYS:
                if r is None:
                    tds.append("<td class='na'>-</td>")
                    continue
                v, est = r[f"est_{day}"], bool(r[f"is_{day}"])
                tds.append(f"<td class='{'est' if est else ''}' style=\"{_bar(v, dmax[p], BAR[p], est)}\">{_fmt(v)}</td>")
            if r is None:
                tds.append("<td class='tot na'>-</td>")
            else:
                tag = "<span class='tag'>P</span>" if r["projected"] else ""
                tds.append(f"<td class='tot {'est' if r['projected'] else ''}' "
                           f"style=\"{_bar(r['total'], tmax[p], BAR[p], bool(r['projected']))}\">{_fmt(r['total'])}{tag}</td>")
        c = comb_all[w]
        proj = any(bool(t.loc[w, "projected"]) for t in (ab, sp) if w in t.index)
        tds.append(f"<td class='tot {'est' if proj else ''}' style=\"{_bar(c, cmax, BAR['Combined'], proj)}\">{_fmt(c)}</td>")
        pv = prev_all[w]
        wow = c / pv - 1 if pd.notna(pv) and pv else np.nan
        tds.append("<td class='na'>-</td>" if np.isnan(wow) else f"<td class='{'up' if wow >= 0 else 'dn'}'>{wow:+.0%}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return f"<div class='pj-wrap'><table class='pj'>{h1}{h2}{''.join(rows)}</table></div>"


def render():
    data = build()
    allw = sorted(set(data["Abidjan"].week) | set(data["San Pedro"].week))
    cys = sorted({crop_year(w) for w in allw}, reverse=True)
    c1, _ = st.columns([1.2, 5], vertical_alignment="center")
    with c1:
        cy = st.selectbox("Crop year", cys, label_visibility="collapsed", format_func=lambda s: f"Crop year  |  {s}")
    weeks = pd.DatetimeIndex([w for w in allw if crop_year(w) == cy]).sort_values(ascending=False)

    with st.container(border=True):
        st.markdown("<div class='card-title'>Weekly arrivals by port (tonnes)</div>"
                    "<div class='card-desc'>Monday to Saturday as reported. Hatched, italic figures are not reported yet and are "
                    "projected: the days we have, divided by the share those days normally make of a full week "
                    "(history of complete weeks, per port). <b>P</b> marks a projected week total.</div>", unsafe_allow_html=True)
        st.markdown(CSS + table_html(data, weeks), unsafe_allow_html=True)
        st.markdown(f"<div class='pj-note'>Latest week in the data: {max(allw):%d-%b-%Y}. Bars are scaled to the largest value in "
                    "each column group; WoW compares the combined total with the previous week.</div>", unsafe_allow_html=True)
