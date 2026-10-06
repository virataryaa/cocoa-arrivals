"""Forestero monthly arrivals (Stat / Tree) for IVC, Ghana and the two combined. Crop year Oct-Sep, thousand tonnes."""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DB = Path(__file__).resolve().parent.parent / "Database"
CROP_MONTHS = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
COMBINED = "IVC + Ghana"
OLD = ["#a6a6a6", "#c98a1f", "#1f9d6f", "#1f8a9c", "#8a5a9c", "#c94a4a"]   # older crop years, newest last
CURRENT, PREVIOUS = "#0a2463", "#2e75b6"

CSS = """
<style>
.mt-wrap { overflow: auto; border: 1px solid #e3e7f0; border-radius: 10px; background: #fff; }
.mt { border-collapse: collapse; font-size: 12.5px; width: 100%; }
.mt th { background: #0a2463; color: #fff; font-weight: 600; padding: 4px 9px; text-align: center; white-space: nowrap; }
.mt td { padding: 3px 9px; text-align: right; border-bottom: 1px solid #eef0f6; white-space: nowrap; font-variant-numeric: tabular-nums; color: #1a1a2e; }
.mt td.cy { text-align: center; font-weight: 700; background: #f6f7fb; }
.mt td.tot { font-weight: 700; border-left: 1px solid #dfe3ee; }
.mt td.na { color: #b8bfd2; }
.mt td.up { color: #1f9d6f; font-weight: 600; } .mt td.dn { color: #c94a4a; font-weight: 600; }
</style>
"""


@st.cache_data(ttl=600)
def load() -> pd.DataFrame:
    return pd.read_csv(DB / "monthly.csv")


def table(origin: str, typ: str) -> pd.DataFrame:
    """Rows = crop year (oldest first), columns = Oct..Sep, kt. Combined = IVC + Ghana, a month needs both."""
    m = load()
    m = m[m.type == typ]
    if origin == COMBINED:
        piv = m.pivot_table(index=["crop_year", "origin"], columns="month", values="kt").reindex(columns=CROP_MONTHS)
        ivc, gh = piv.xs("IVC", level="origin"), piv.xs("Ghana", level="origin")
        t = ivc.add(gh, fill_value=np.nan).where(ivc.notna() & gh.notna())
    else:
        t = m[m.origin == origin].pivot_table(index="crop_year", columns="month", values="kt").reindex(columns=CROP_MONTHS)
    return t.sort_index()


def _layout(fig, height, ytitle=None):
    fig.update_layout(
        template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#1a1a2e"),
        hovermode="x unified", height=height, margin=dict(t=10, b=10, l=10, r=10),
        xaxis=dict(gridcolor="rgba(10,36,99,0.08)", color="#4a5578"),
        yaxis=dict(gridcolor="rgba(10,36,99,0.08)", color="#4a5578", tickformat=",", hoverformat=",.0f", rangemode="tozero", title=ytitle),
        legend=dict(orientation="h", x=0, y=-0.12, xanchor="left", yanchor="top", font=dict(size=11), bgcolor="rgba(0,0,0,0)"))
    return fig


def line_chart(t: pd.DataFrame, cumulative: bool, last_n: int):
    fig = go.Figure()
    years = list(t.index)[-last_n:] if last_n else list(t.index)
    for i, cy in enumerate(years):
        s = t.loc[cy]
        y = s.cumsum(skipna=True).where(s.notna()) if cumulative else s
        newest, prev = cy == years[-1], len(years) > 1 and cy == years[-2]
        colour = CURRENT if newest else PREVIOUS if prev else OLD[(i) % len(OLD)]
        fig.add_scatter(x=CROP_MONTHS, y=y, name=cy, mode="lines+markers" if newest else "lines", connectgaps=False,
                        line=dict(color=colour, width=3.5 if newest else 2.2 if prev else 1.6), marker=dict(size=6),
                        hovertemplate="%{y:,.0f}")
    return _layout(fig, 400)


def _cell(v, lo, hi):
    if pd.isna(v):
        return "<td class='na'>-</td>"
    a = 0.0 if hi <= lo else (v - lo) / (hi - lo)
    return f"<td style='background:rgba(31,138,156,{0.06 + 0.34 * a:.2f})'>{v:,.0f}</td>"


def table_html(t: pd.DataFrame) -> str:
    lo, hi = t.min(), t.max()                                # colour each month column against its own range
    head = "<tr><th>Crop year</th>" + "".join(f"<th>{m}</th>" for m in CROP_MONTHS) + "<th>Total</th><th>YTD YoY</th></tr>"
    rows = []
    for cy in reversed(list(t.index)):
        s = t.loc[cy]
        tot = s.sum(min_count=1)
        done = s.notna()
        yoy = ""
        i = list(t.index).index(cy)
        if i > 0 and done.any():
            prev = t.iloc[i - 1][done]
            if prev.notna().all() and prev.sum() > 0:
                g = s[done].sum() / prev.sum() - 1
                yoy = f"<td class='{'up' if g >= 0 else 'dn'}'>{g:+.0%}</td>"
        yoy = yoy or "<td class='na'>-</td>"
        cells = "".join(_cell(s[m], lo[m], hi[m]) for m in CROP_MONTHS)
        part = "" if done.all() else "*"
        rows.append(f"<tr><td class='cy'>{cy}{part}</td>{cells}<td class='tot'>{tot:,.0f}</td>{yoy}</tr>")
    return f"<div class='mt-wrap'><table class='mt'>{head}{''.join(rows)}</table></div>"


def render(origin: str):
    top = st.columns([1.2, 1.4, 1.2, 4], vertical_alignment="center")
    with top[0]:
        typ = st.radio("Series", ["Stat", "Tree"], horizontal=True, label_visibility="collapsed", key=f"mo_typ_{origin}",
                       help="Forestero monthly series. Stat = statistical, Tree = tree-count based.")
    with top[1]:
        view = st.radio("View", ["Charts", "Table"], horizontal=True, label_visibility="collapsed", key=f"mo_view_{origin}")
    t = table(origin, typ)
    if view == "Charts":
        with top[2]:
            last_n = {"Last 5": 5, "All": 0}[st.radio("Years", ["Last 5", "All"], horizontal=True, label_visibility="collapsed", key=f"mo_n_{origin}")]
        with st.container(border=True):
            st.markdown(f"<div class='card-title'>Monthly arrivals {origin} ({typ})</div>"
                        "<div class='card-desc'>Forestero, thousand tonnes, crop year Oct-Sep. Dark blue = current crop year, "
                        "blue = previous. Click a name in the legend to hide it.</div>", unsafe_allow_html=True)
            st.plotly_chart(line_chart(t, False, last_n), width="stretch")
        with st.container(border=True):
            st.markdown(f"<div class='card-title'>Cumulative arrivals {origin} ({typ})</div>", unsafe_allow_html=True)
            st.plotly_chart(line_chart(t, True, last_n), width="stretch")
    else:
        with st.container(border=True):
            st.markdown(f"<div class='card-title'>Monthly arrivals {origin} ({typ}) - all crop years</div>"
                        "<div class='card-desc'>Thousand tonnes. Shading compares each month with the same month in other years. "
                        "* = crop year still running; YTD YoY compares the months reported so far with the same months a year earlier.</div>",
                        unsafe_allow_html=True)
            st.markdown(CSS + table_html(t), unsafe_allow_html=True)
