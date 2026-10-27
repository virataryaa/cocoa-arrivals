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


SOURCES = ["Manual", "Eikon", "Forestero"]
# Running year: Manual black, Eikon deep red, Forestero green. Older years: one vibrant colour per (year, source), shaded lighter the older they are.
# Fixed per series, so a line keeps its colour whatever else is selected.
VIBRANT = ["#0b0b0b", "#a4111c", "#00a67e",          # running year: Manual, Eikon, Forestero
           "#1d4ed8", "#ff6b00", "#d6249f",
           "#8e24aa", "#00a8e8", "#ffb300",
           "#00897b", "#7ed321", "#5c6bc0",
           "#e53935", "#f06292", "#26c6da",
           "#6d4c41", "#ab47bc", "#43a047"]
SOURCE_STYLE = {"Manual": ("solid", 1.0), "Eikon": ("dot", 0.95), "Forestero": ("solid", 0.7)}      # (dash, width factor)


def _fade(hex_: str, t: float) -> str:
    """Mix a colour toward white: t=0 is the colour itself, t=1 is white."""
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(round(c + (255 - c) * t) for c in (r, g, b))


def season_years() -> list:
    y = start_year()
    return [label(y - i) for i in range(6)]                # newest first


MAIN_LAST_WEEK = 26                                       # weeks 1-26 = main crop (Oct-Mar), 27-51 = mid crop (Apr-Sep)
PROJ_COLOUR = "#0b0b0b"                                 # same black as the running-year Manual line


def project(df: pd.DataFrame, main: float, mid: float):
    """Weekly projection for the weeks still to come in the running year. Each crop's target minus what the Manual series
    already shows for it is spread over its remaining weeks in the average weekly shape of the last three Manual seasons.
    Returns (weekly projection, last actual week, {crop: (received, remaining, weeks left)})."""
    wk, act = df.week, df[f"etg_{tag(start_year())}"]
    done = int(wk[act.notna()].max()) if act.notna().any() else 0
    hist = [c for c in (f"etg_{tag(start_year() - i)}" for i in range(1, 4)) if c in df and df[c].notna().sum() > 20]
    shape = df[hist].clip(lower=0).mean(axis=1).fillna(0) if hist else pd.Series(1.0, index=df.index)
    out, info = pd.Series(float("nan"), index=df.index), {}
    for crop, lo, hi, target in (("Main", 1, MAIN_LAST_WEEK, main), ("Mid", MAIN_LAST_WEEK + 1, int(wk.max()), mid)):
        if not target:
            continue
        seg = (wk >= lo) & (wk <= hi)
        got = float(act[seg & (wk <= done)].sum())
        rest = seg & (wk > done)
        left = max(target - got, 0.0)
        info[crop] = (got, left, int(rest.sum()))
        if rest.any():
            w = shape[rest] if shape[rest].sum() > 0 else pd.Series(1.0, index=wk[rest].index)
            out[rest] = left * w / w.sum()
    return out, done, info


def _add_projection(fig, df: pd.DataFrame, proj: pd.Series, done: int, cumulative: bool):
    cur = df[f"etg_{tag(start_year())}"]
    anchor = df.week == done                                # join the dashed line onto the last actual point
    base = float(cur.fillna(0).sum()) if cumulative else (float(cur[anchor].iloc[0]) if anchor.any() else 0.0)
    y = proj.cumsum() + base if cumulative else proj
    keep = proj.notna() | anchor
    y = y.where(~anchor, base)
    fig.add_scatter(x=df.week[keep], y=y[keep], name=f"Projection {label(start_year())}", mode="lines",
                    line=dict(color=PROJ_COLOUR, dash="dash", width=2.6, shape="spline", smoothing=0.45),
                    fill="tozeroy", fillcolor=_rgba(PROJ_COLOUR, 0.06), hovertemplate="%{y:,.1f} (proj)")


def chart(df: pd.DataFrame, cumulative: bool, height: int, years: list | None = None, sources: list | None = None, title: str = "",
          proj: tuple | None = None):
    fig = go.Figure()
    cur = tag(start_year())
    years = years or season_years()[:2]
    sources = sources or SOURCES
    rank = {lab: i for i, lab in enumerate(sorted(years, key=season_years().index))}      # 0 = newest selected year
    for name, col, *_ in series_list():
        src, lab = name.split(" (")[0], name.split("(")[1].rstrip(")")
        if src not in sources or lab not in rank or col not in df or df[col].notna().sum() == 0:
            continue
        dash_, wf = SOURCE_STYLE[src]
        yi = season_years().index(lab)
        colour = _fade(VIBRANT[yi * 3 + SOURCES.index(src)], min(0.55, 0.15 * max(yi - 1, 0)) if yi else 0)
        width = (3 if rank[lab] == 0 else 2.2) * wf
        name = f"{src} {lab}"
        y = df[col].cumsum(skipna=True).where(df[col].notna()) if cumulative else df[col]
        main = col == f"etg_{cur}"
        stepped = src == "Forestero" and not cumulative
        fig.add_scatter(x=df.week, y=y, name=name, mode="lines", connectgaps=False,
                        line=dict(color=colour, dash=dash_, width=width + (0.6 if main else 0), shape="hv" if stepped else "spline", smoothing=0.45),
                        fill="tozeroy" if main else None, fillcolor=_rgba(colour, 0.09) if main else None,
                        legendgroup=name, hovertemplate="%{y:,.1f}")
    if label(start_year()) in rank and "Manual" in sources and f"etg_{cur}_proj" in df and df[f"etg_{cur}_proj"].any():          # the running week: projected, not final
        y = df[f"etg_{cur}"].cumsum(skipna=True).where(df[f"etg_{cur}"].notna()) if cumulative else df[f"etg_{cur}"]
        m = df[f"etg_{cur}_proj"]
        fig.add_scatter(x=df.week[m], y=y[m], name=f"Manual {label(start_year())} projected", mode="markers",
                        marker=dict(symbol="circle-open", size=12, color="#0a2463", line=dict(width=2)), hovertemplate="%{y:,.1f} (projected)")
    if proj is not None and proj[0].notna().any() and label(start_year()) in rank:
        _add_projection(fig, df, proj[0], proj[1], cumulative)
    fig.update_layout(
        hovermode="x unified", height=height, margin=dict(t=40, b=8, l=8, r=12),
        hoverlabel=dict(bgcolor="rgba(255,255,255,0.97)", bordercolor="rgba(10,36,99,0.12)", font=dict(size=12, color="#1a1a2e")),
        xaxis=dict(tickmode="array", tickvals=list(MONTH_TICKS), ticktext=list(MONTH_TICKS.values()), range=[0.5, 51.5], showgrid=False,
                   showline=True, linecolor="rgba(10,36,99,0.15)", ticks="outside", ticklen=4, tickcolor="rgba(10,36,99,0.15)",
                   tickfont=dict(size=11, color="#6b7796"),
                   showspikes=True, spikemode="across", spikecolor="rgba(10,36,99,0.22)", spikethickness=1, spikedash="solid"),
        yaxis=dict(gridcolor="rgba(10,36,99,0.06)", showline=False, zeroline=False, ticks="", tickformat=",", hoverformat=",.1f",
                   rangemode="tozero", tickfont=dict(size=11, color="#6b7796")),
        legend=dict(orientation="h", x=0, y=1.13, xanchor="left", yanchor="top", font=dict(size=11, color="#4a5578"), bgcolor="rgba(0,0,0,0)",
                    itemsizing="constant", itemwidth=36, tracegroupgap=0),
    )
    return theme.style(fig)


TABLE_CSS = """
<style>
.ice-wrap { display: flex; justify-content: center; overflow-x: auto; padding: 2px 2px 8px; }
.ice-tab { border-collapse: separate; border-spacing: 0; background: #fff; border-radius: 10px; overflow: hidden; font-size: 10px;
    box-shadow: 0 1px 2px rgba(10,36,99,.05), 0 6px 20px rgba(10,36,99,.08); font-variant-numeric: tabular-nums; }
.ice-tab th { background: linear-gradient(180deg, #f7f9fd, #e9eff9); color: #1e3a6e; font-family: 'Plus Jakarta Sans','Inter',sans-serif; font-size: 8.5px;
    font-weight: 700; letter-spacing: .06em; text-transform: uppercase; padding: 2px 5px; text-align: center; white-space: nowrap; line-height: 1.2; }
.ice-tab tr.yr th { font-size: 9.5px; letter-spacing: .04em; padding: 3px 5px 2px; border-bottom: 1px solid rgba(43,74,138,.12);
    border-left: 1px solid rgba(43,74,138,.10); }
.ice-tab tr.src th { border-bottom: 1px solid rgba(43,74,138,.14); font-weight: 600; color: #5a6688; }
.ice-tab td { padding: 0 5px; text-align: center; border-bottom: 1px solid rgba(43,74,138,.05); white-space: nowrap; color: #1a1a2e; line-height: 1.15; }
.ice-tab tr:last-child td { border-bottom: 0; }
.ice-tab td.wk { font-weight: 700; color: #1e3a6e; background: #f6f8fd; padding: 0 7px; }
.ice-tab td.na { color: #c3cadb; }
.ice-tab tbody tr:hover td { filter: brightness(0.97); }
</style>
"""


def table_html(df: pd.DataFrame, cumulative: bool) -> str:
    cols = [(name, col) for name, col, *_ in series_list() if col in df and df[col].notna().any()]
    data = {}
    for label, col in cols:
        data[label] = df[col].cumsum(skipna=True).where(df[col].notna()) if cumulative else df[col]
    groups = []                                            # consecutive columns of one crop year share a top header cell
    for label, _ in cols:
        yr = label.split("(")[1].rstrip(")")
        if groups and groups[-1][0] == yr:
            groups[-1][1] += 1
        else:
            groups.append([yr, 1])
    head = ("<tr class='yr'><th rowspan=2>Wk</th>" + "".join(f"<th colspan={n}>{yr}</th>" for yr, n in groups) + "</tr>"
            "<tr class='src'>" + "".join(f"<th>{label.split(' (')[0]}</th>" for label, _ in cols) + "</tr>")
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
                tds.append(f"<td style='background:rgba(63,120,200,{0.04 + 0.30 * a:.2f})'>{v:,.0f}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return f"<div class='ice-wrap'><table class='ice-tab'><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table></div>"


PROJ_CSS = """
<style>
.pj-strip { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; margin: 2px 0 6px; }
.pj-kpi { background: #fff; border-radius: 12px; padding: 6px 14px; box-shadow: 0 1px 2px rgba(10,36,99,.05), 0 6px 18px rgba(10,36,99,.07);
    text-align: center; min-width: 120px; }
.pj-kpi .k { font-family: 'Plus Jakarta Sans','Inter',sans-serif; font-size: 8.5px; font-weight: 700; letter-spacing: .12em;
    text-transform: uppercase; color: #6b7796; }
.pj-kpi .v { font-size: 15px; font-weight: 700; color: #1e3a6e; font-variant-numeric: tabular-nums; }
.pj-kpi .s { font-size: 10px; color: #8a94ad; }
</style>
"""


def proj_strip(info: dict, main: float, mid: float) -> str:
    cards = []
    for crop, (got, left, n) in info.items():
        cards.append(f"<div class='pj-kpi'><div class='k'>{crop} received</div><div class='v'>{got:,.0f}</div>"
                     f"<div class='s'>{got / (main if crop == 'Main' else mid):.0%} of target</div></div>")
        cards.append(f"<div class='pj-kpi'><div class='k'>{crop} to come</div><div class='v'>{left:,.0f}</div>"
                     f"<div class='s'>{n} wks · {left / n if n else 0:,.1f} kt/wk</div></div>")
    cards.append(f"<div class='pj-kpi'><div class='k'>Total crop</div><div class='v'>{main + mid:,.0f}</div><div class='s'>main + mid kt</div></div>")
    return "<div class='pj-strip'>" + "".join(cards) + "</div>"


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
        if yy != y:                                        # finished season with holes in the port entries: bridge them (week 1 takes week 2)
            df[f"etg_{tag(yy)}"] = df[f"etg_{tag(yy)}"].interpolate(limit_area="inside").bfill(limit=1)
        df[f"eikon_{tag(yy)}"] = df.week.map(live["eikon"])
        if yy == y:
            df[f"etg_{tag(yy)}_proj"] = df.week.map(live["proj"]).fillna(False).astype(bool)

    pick = st.columns([2.2, 2.2, 1.3, 1.3], vertical_alignment="bottom")
    years = pick[0].multiselect("Crop year", season_years(), default=season_years()[:2], key="season_years")
    sources = pick[1].multiselect("Source", SOURCES, default=SOURCES, key="season_sources")
    main = pick[2].number_input(f"Main crop {label(y)} kt (Oct-Mar)", min_value=0.0, step=50.0, format="%.0f", key="proj_main")
    mid = pick[3].number_input(f"Mid crop {label(y)} kt (Apr-Sep)", min_value=0.0, step=25.0, format="%.0f", key="proj_mid")
    proj = project(df, main, mid) if (main or mid) else None
    if proj:
        st.markdown(PROJ_CSS + proj_strip(proj[2], main, mid), unsafe_allow_html=True)
    st.plotly_chart(chart(df, False, 330, years, sources, f"{origin} — Weekly arrivals kt", proj), width="stretch")
    st.plotly_chart(chart(df, True, 330, years, sources, f"{origin} — Cumulative arrivals kt", proj), width="stretch")
    with st.container():
        st.markdown(f"<div class='card-title'>Weekly arrivals {origin} - by week of crop year</div>", unsafe_allow_html=True)
        st.markdown(TABLE_CSS + table_html(df, False), unsafe_allow_html=True)
