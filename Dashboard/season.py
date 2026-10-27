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
    """(label, column, colour, dash, width, shown), newest crop year first (Manual, Eikon, Forestero within a year).
    The running year and the one before are shown; older years start hidden (click the legend to bring them back)."""
    y = start_year()
    spec = [  # (years back, manual colour, eikon colour, forestero colour, forestero dash, width, shown)
        (0, "#0a2463", "#f08a00", "#12a38a", "dash", 3, True),
        (1, "#8e44ad", "#d62f3a", "#6c7a89", "dot", 1.8, True),
        (2, "#9aa5b8", "#8a5a12", "#c0a23a", "dot", 1.5, False),
        (3, "#3949ab", None, "#8bc34a", "dot", 1.5, False),
        (4, None, None, "#e91e63", "dot", 1.5, False),
        (5, None, None, "#00acc1", "dot", 1.5, False),
    ]
    out = []
    for back, man, eik, fo, fdash, width, shown in spec:
        t, lab = tag(y - back), label(y - back)
        if man:
            out.append((f"Manual ({lab})", f"etg_{t}", man, "solid", width, shown))
        if eik:
            out.append((f"Eikon ({lab})", f"eikon_{t}", eik, "solid", width - 0.8 if back == 0 else width, shown))
        out.append((f"Forestero ({lab})", f"fo_{t}", fo, fdash, 2.2 if back == 0 else width, shown))
    return out


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


MONTH_TICKS = {1: "Oct", 5: "Nov", 9: "Dec", 14: "Jan", 18: "Feb", 22: "Mar", 27: "Apr", 31: "May", 35: "Jun", 40: "Jul", 44: "Aug", 48: "Sep"}


def _rgba(hex_: str, a: float) -> str:
    return f"rgba({int(hex_[1:3], 16)},{int(hex_[3:5], 16)},{int(hex_[5:7], 16)},{a})"


SOURCE_COLOUR = {"Manual": "#0a2463", "Eikon": "#f08a00", "Forestero": "#12a38a"}
SOURCES = list(SOURCE_COLOUR)


def _fade(hex_: str, t: float) -> str:
    """Mix a colour toward white: t=0 is the colour itself, t=1 is white."""
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(round(c + (255 - c) * t) for c in (r, g, b))


def season_years() -> list:
    y = start_year()
    return [label(y - i) for i in range(6)]                # newest first


def chart(df: pd.DataFrame, cumulative: bool, height: int, years: list | None = None, sources: list | None = None):
    fig = go.Figure()
    cur = tag(start_year())
    years = years or season_years()[:2]
    sources = sources or SOURCES
    rank = {lab: i for i, lab in enumerate(sorted(years, key=season_years().index))}      # 0 = newest selected year
    for name, col, *_ in series_list():
        src, lab = name.split(" (")[0], name.split("(")[1].rstrip(")")
        if src not in sources or lab not in rank or col not in df or df[col].notna().sum() == 0:
            continue
        colour = _fade(SOURCE_COLOUR[src], min(0.7, rank[lab] * 0.3))
        width = 3 if rank[lab] == 0 else 1.8
        name = f"{src} {lab}"
        y = df[col].cumsum(skipna=True).where(df[col].notna()) if cumulative else df[col]
        is_cur = col.endswith(cur)
        main = col == f"etg_{cur}"
        stepped = src == "Forestero" and not cumulative
        fig.add_scatter(x=df.week, y=y, name=name, mode="lines", connectgaps=False,
                        line=dict(color=colour, dash="dash" if src == "Forestero" else "solid", width=width + (0.6 if main else 0), shape="hv" if stepped else "linear"),
                        fill="tozeroy" if main else None, fillcolor=_rgba(colour, 0.07) if main else None,
                        legendgroup=name, hovertemplate="%{y:,.1f}")
        if is_cur and src != "Forestero" and y.notna().any():              # this season: a dot + value on the latest week
            last = y.last_valid_index()
            fig.add_scatter(x=[df.week[last]], y=[y[last]], mode="markers+text" if main else "markers", showlegend=False, legendgroup=name,
                            hoverinfo="skip", text=[f"{y[last]:,.1f}"] if main else None, textposition="top center", textfont=dict(size=11, color=colour),
                            marker=dict(size=9, color=colour, line=dict(width=2, color="#ffffff")))
    if label(start_year()) in rank and "Manual" in sources and f"etg_{cur}_proj" in df and df[f"etg_{cur}_proj"].any():          # the running week: projected, not final
        y = df[f"etg_{cur}"].cumsum(skipna=True).where(df[f"etg_{cur}"].notna()) if cumulative else df[f"etg_{cur}"]
        m = df[f"etg_{cur}_proj"]
        fig.add_scatter(x=df.week[m], y=y[m], name=f"Manual {label(start_year())} projected", mode="markers",
                        marker=dict(symbol="circle-open", size=12, color="#0a2463", line=dict(width=2)), hovertemplate="%{y:,.1f} (projected)")
    fig.update_layout(
        hovermode="x unified", height=height, margin=dict(t=44, b=10, l=10, r=14),
        hoverlabel=dict(bgcolor="rgba(255,255,255,0.96)", bordercolor="rgba(43,74,138,0.2)", font=dict(size=12, color="#1a1a2e")),
        xaxis=dict(tickmode="array", tickvals=list(MONTH_TICKS), ticktext=list(MONTH_TICKS.values()), range=[0.5, 51.5], showgrid=True,
                   gridcolor="rgba(10,36,99,0.05)", showline=False, ticks="", tickfont=dict(size=11, color="#4a5578"),
                   showspikes=True, spikemode="across", spikecolor="rgba(10,36,99,0.25)", spikethickness=1, spikedash="dot"),
        yaxis=dict(gridcolor="rgba(10,36,99,0.07)", showline=False, zeroline=False, ticks="", tickformat=",", hoverformat=",.1f",
                   rangemode="tozero", title=dict(text="kt", font=dict(size=11, color="#7a86a8"))),
        legend=dict(orientation="h", x=0, y=1.14, xanchor="left", yanchor="top", font=dict(size=11), bgcolor="rgba(0,0,0,0)", itemsizing="trace", itemwidth=44),
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
    typ = "Stat"                                           # Forestero series behind the dashed lines
    df = weekly.copy()
    y = start_year()
    for yy in range(y - 5, y + 1):
        df[f"fo_{tag(yy)}"] = df.week.map(forestero_weekly(monthly, origin, typ, label(yy)))
    for yy in range(y - 3, y + 1):                         # the running year, and older years weekly.csv lacks (23/24), come from the entry data
        if yy != y and f"etg_{tag(yy)}" in df:
            continue
        live = projection.crop_series(projection.build(), projection.load_eikon(), yy).set_index("week")
        df[f"etg_{tag(yy)}"] = df.week.map(live["etg"])
        df[f"eikon_{tag(yy)}"] = df.week.map(live["eikon"])
        if yy == y:
            df[f"etg_{tag(yy)}_proj"] = df.week.map(live["proj"]).fillna(False).astype(bool)

    pick = st.columns([2.2, 2.2, 4], vertical_alignment="center")
    years = pick[0].multiselect("Crop year", season_years(), default=season_years()[:2], key="season_years")
    sources = pick[1].multiselect("Source", SOURCES, default=SOURCES, key="season_sources")
    with st.container(border=True):
        st.markdown(f"<div class='card-title'>Weekly arrivals {origin}</div>", unsafe_allow_html=True)
        st.plotly_chart(chart(df, False, 430, years, sources), width="stretch")
    with st.container(border=True):
        st.markdown(f"<div class='card-title'>Cumulative arrivals {origin}</div>", unsafe_allow_html=True)
        st.plotly_chart(chart(df, True, 430, years, sources), width="stretch")
    for cum in (False, True):
        with st.container(border=True):
            st.markdown(f"<div class='card-title'>{'Cumulative' if cum else 'Weekly'} arrivals {origin} - by week of crop year</div>", unsafe_allow_html=True)
            st.markdown(TABLE_CSS + table_html(df, cum), unsafe_allow_html=True)
