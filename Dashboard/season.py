"""IVC season view: weekly + cumulative arrivals (ETG, Eikon, Forestero) for the crop year."""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import theme

import projection

DB = Path(__file__).resolve().parent.parent / "Database"
CROP_MONTHS = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
WEEKS_IN_MONTH = [4] * 12                               # every month = 4 weeks -> weeks 1-48; weeks 49-51 have no Forestero value


def start_year() -> int:
    """Start year of the running crop year (Oct-Sep): 2026 for 26/27."""
    t = pd.Timestamp.today()
    return t.year if t.month >= 10 else t.year - 1


def tag(y: int) -> str:
    return f"{y % 100:02d}{(y + 1) % 100:02d}"            # 2026 -> "2627"


def label(y: int) -> str:
    return f"{y % 100:02d}/{(y + 1) % 100:02d}"           # 2026 -> "26/27"


def series_list() -> list:
    """(label, column, colour, dash, width, shown) for the running crop year and the two before it; shown=False starts hidden."""
    y = start_year()
    c, p, q = tag(y), tag(y - 1), tag(y - 2)
    return [
        (f"Manual ({label(y)})", f"etg_{c}", "#0a2463", "solid", 3.5, True),
        (f"Eikon ({label(y)})", f"eikon_{c}", "#e07b39", "solid", 3, True),
        (f"Forestero ({label(y)})", f"fo_{c}", "#9c7a00", "dash", 2.5, True),
        (f"Manual ({label(y - 1)})", f"etg_{p}", "#2e75b6", "solid", 2.5, True),
        (f"Eikon ({label(y - 1)})", f"eikon_{p}", "#c00000", "solid", 2.5, True),
        (f"Forestero ({label(y - 1)})", f"fo_{p}", "#d9d9d9", "dash", 2.5, True),
        (f"Manual ({label(y - 2)})", f"etg_{q}", "#a6a6a6", "solid", 2.5, False),
        (f"Eikon ({label(y - 2)})", f"eikon_{q}", "#843c0c", "dot", 2.5, False),
    ]


@st.cache_data(ttl=600)
def load():
    return pd.read_csv(DB / "weekly.csv"), pd.read_csv(DB / "monthly.csv")


def forestero_weekly(monthly: pd.DataFrame, origin: str, typ: str, crop_year: str) -> pd.Series:
    """Monthly Forestero figure spread evenly over the weeks of that month -> weekly step series (index = week 1-48)."""
    m = monthly[(monthly.origin == origin) & (monthly.type == typ) & (monthly.crop_year == crop_year)]
    kt = m.set_index("month").kt
    out, wk = {}, 1
    for mon, n in zip(CROP_MONTHS, WEEKS_IN_MONTH):
        for w in range(wk, wk + n):
            out[w] = kt.get(mon, float("nan")) / n
        wk += n
    return pd.Series(out)


def chart(df: pd.DataFrame, cumulative: bool, height: int):
    fig = go.Figure()
    for name, col, colour, dash, width, shown in series_list():
        if col not in df or df[col].notna().sum() == 0:
            continue
        y = df[col].cumsum(skipna=True).where(df[col].notna()) if cumulative else df[col]
        live = col.endswith(tag(start_year())) and dash != "dash"           # this season: markers, so a single week is visible too
        fig.add_scatter(x=df.week, y=y, name=name, mode="lines+markers" if live else "lines", connectgaps=False,
                        marker=dict(size=7, color=colour),
                        line=dict(color=colour, dash=dash, width=width, shape="hv" if (dash == "dash" and not cumulative) else "linear"),
                        hovertemplate="%{y:,.0f}", visible=True if shown else "legendonly")
    cur = tag(start_year())
    if f"etg_{cur}_proj" in df and df[f"etg_{cur}_proj"].any():          # the running week: projected, not final
        y = df[f"etg_{cur}"].cumsum(skipna=True).where(df[f"etg_{cur}"].notna()) if cumulative else df[f"etg_{cur}"]
        m = df[f"etg_{cur}_proj"]
        fig.add_scatter(x=df.week[m], y=y[m], name=f"Manual ({label(start_year())}) projected", mode="markers",
                        marker=dict(symbol="circle-open", size=11, color="#0a2463", line=dict(width=2)), hovertemplate="%{y:,.1f} (projected)")
    fig.update_layout(
        template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1a1a2e"), hovermode="x unified", height=height,
        xaxis=dict(title="Week of crop year (1 = first week of October)", gridcolor="rgba(10,36,99,0.08)", color="#4a5578", dtick=2, range=[0.5, 51.5]),
        yaxis=dict(gridcolor="rgba(10,36,99,0.08)", color="#4a5578", tickformat=",", hoverformat=",.0f", rangemode="tozero"),
        legend=dict(orientation="h", x=0, y=-0.2, xanchor="left", yanchor="top", font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=10, b=10, l=10, r=10),
    )
    return theme.style(fig)


TABLE_CSS = """
<style>
.st-wrap { overflow: auto; max-height: 560px; border: 1px solid #e3e7f0; border-radius: 10px; background: #fff; display: inline-block; max-width: 100%; }
.st-tab { border-collapse: separate; border-spacing: 0; font-size: 12px; }
.st-tab th { position: sticky; top: 0; background: #0a2463; color: #fff; font-weight: 600; padding: 4px 10px; text-align: center; white-space: nowrap; }
.st-tab td { padding: 2px 10px; text-align: right; border-bottom: 1px solid #eef0f6; white-space: nowrap; font-variant-numeric: tabular-nums; color: #1a1a2e; }
.st-tab td.wk { text-align: center; font-weight: 600; background: #f6f7fb; }
.st-tab td.na { color: #b8bfd2; }
</style>
"""


def table_html(df: pd.DataFrame, cumulative: bool) -> str:
    cols = [(name, col) for name, col, *_ in series_list() if col in df and df[col].notna().any()]
    data = {}
    for label, col in cols:
        data[label] = df[col].cumsum(skipna=True).where(df[col].notna()) if cumulative else df[col]
    head = "<tr><th>Week</th>" + "".join(f"<th>{label}</th>" for label, _ in cols) + "</tr>"
    rows = []
    for i, wk in enumerate(df.week):
        tds = [f"<td class='wk'>{wk}</td>"]
        for label, _ in cols:
            v = data[label].iloc[i]
            s = data[label]
            if pd.isna(v):
                tds.append("<td class='na'>-</td>")
            else:
                a = (v - s.min()) / (s.max() - s.min()) if s.max() > s.min() else 0
                tds.append(f"<td style='background:rgba(31,138,156,{0.04 + 0.28 * a:.2f})'>{v:,.0f}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return f"<div class='st-wrap'><table class='st-tab'>{head}{''.join(rows)}</table></div>"


def render(origin: str = "IVC"):
    weekly, monthly = load()
    oc = st.columns([1.3, 1.4, 1.6, 4], vertical_alignment="center")
    with oc[0]:
        typ = st.radio("Forestero", ["Stat", "Tree"], horizontal=True, label_visibility="collapsed", key="fo_type",
                       help="Forestero monthly series used for the dashed lines: Stat = statistical, Tree = tree-count based.")
    with oc[1]:
        view = st.radio("View", ["Charts", "Table"], horizontal=True, label_visibility="collapsed", key="season_view")
    df = weekly.copy()
    y = start_year()
    for yy in (y - 1, y):
        df[f"fo_{tag(yy)}"] = df.week.map(forestero_weekly(monthly, origin, typ, label(yy)))
    for yy in (y - 1, y):                                  # the running year (and the one before, if weekly.csv lacks it) come from the entry data
        if yy != y and f"etg_{tag(yy)}" in df:
            continue
        live = projection.crop_series(projection.build(), projection.load_eikon(), yy).set_index("week")
        df[f"etg_{tag(yy)}"] = df.week.map(live["etg"])
        df[f"eikon_{tag(yy)}"] = df.week.map(live["eikon"])
        if yy == y:
            df[f"etg_{tag(yy)}_proj"] = df.week.map(live["proj"]).fillna(False).astype(bool)

    if view == "Table":
        with oc[2]:
            cum = st.radio("Basis", ["Weekly", "Cumulative"], horizontal=True, label_visibility="collapsed", key="season_basis") == "Cumulative"
        with st.container(border=True):
            st.markdown(f"<div class='card-title'>{'Cumulative' if cum else 'Weekly'} arrivals {origin} - by week of crop year</div>", unsafe_allow_html=True)
            st.markdown(TABLE_CSS + table_html(df, cum), unsafe_allow_html=True)
        return

    with st.container(border=True):
        st.markdown(f"<div class='card-title'>Weekly arrivals {origin}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(chart(df, False, 430), width="stretch")
    with st.container(border=True):
        st.markdown(f"<div class='card-title'>Cumulative arrivals {origin}</div>", unsafe_allow_html=True)
        st.plotly_chart(chart(df, True, 430), width="stretch")
