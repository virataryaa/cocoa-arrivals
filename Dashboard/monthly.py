"""Forestero monthly arrivals (Stat / Tree) for IVC, Ghana and the two combined. Crop year Oct-Sep, thousand tonnes."""
import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ghstore as gh
import projection
import season

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


TYPES = ["Stat", "Tree"]
DASH = {"Stat": "solid", "Tree": "dot"}


def _layout(fig, height):
    fig.update_layout(
        template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#1a1a2e", size=11),
        hovermode="x unified", height=height, margin=dict(t=6, b=6, l=6, r=6),
        xaxis=dict(gridcolor="rgba(10,36,99,0.08)", color="#4a5578"),
        yaxis=dict(gridcolor="rgba(10,36,99,0.08)", color="#4a5578", tickformat=",", hoverformat=",.0f", rangemode="tozero"),
        legend=dict(orientation="h", x=0, y=-0.1, xanchor="left", yanchor="top", font=dict(size=10), bgcolor="rgba(0,0,0,0)"))
    return fig


def years_of(origin: str) -> list:
    tabs = [table(origin, typ) for typ in TYPES]
    return sorted(set().union(*[t.index[t.notna().any(axis=1)] for t in tabs]))


def line_chart(origin: str, cumulative: bool, last_n: int):
    """Stat (solid) and Tree (dotted) together, one colour per crop year; a year's two lines toggle together in the legend."""
    fig = go.Figure()
    years = years_of(origin)
    years = years[-last_n:] if last_n else years
    for typ in TYPES:
        t = table(origin, typ)
        for i, cy in enumerate(years):
            if cy not in t.index or t.loc[cy].isna().all():
                continue
            s = t.loc[cy]
            y = s.cumsum(skipna=True).where(s.notna()) if cumulative else s
            newest, prev = cy == years[-1], len(years) > 1 and cy == years[-2]
            colour = CURRENT if newest else PREVIOUS if prev else OLD[i % len(OLD)]
            fig.add_scatter(x=CROP_MONTHS, y=y, name=cy, legendgroup=cy, showlegend=typ == "Stat", mode="lines", connectgaps=False,
                            line=dict(color=colour, dash=DASH[typ], width=3 if newest else 2 if prev else 1.4),
                            hovertemplate=f"{cy} {typ}: %{{y:,.0f}}<extra></extra>")
    for typ in TYPES:                                   # legend key for the line styles
        fig.add_scatter(x=[None], y=[None], name=typ, mode="lines", line=dict(color="#5a6688", dash=DASH[typ], width=2))
    return _layout(fig, 300)


def _cell(v, lo, hi):
    if pd.isna(v):
        return "<td class='na'>-</td>"
    a = 0.0 if hi <= lo else (v - lo) / (hi - lo)
    return f"<td style='background:rgba(31,138,156,{0.06 + 0.34 * a:.2f})'>{v:,.0f}</td>"


def table_html(origin: str) -> str:
    """Months down (Stat block, then Tree block, each with Total and YTD YoY), crop years across."""
    years = years_of(origin)
    head = "<tr><th>Type</th><th>Month</th>" + "".join(f"<th>{cy}</th>" for cy in years) + "</tr>"
    rows = []
    for typ in TYPES:
        t = table(origin, typ).reindex(years)
        for j, m in enumerate(CROP_MONTHS):
            col = t[m]
            lead = f"<td class='cy' rowspan=14>{typ}</td>" if j == 0 else ""
            rows.append(f"<tr>{lead}<td class='cy'>{m}</td>" + "".join(_cell(col[cy], col.min(), col.max()) for cy in years) + "</tr>")
        tot = "".join(f"<td class='tot'>{t.loc[cy].sum(min_count=1):,.0f}</td>" if t.loc[cy].notna().any() else "<td class='na'>-</td>"
                      for cy in years)
        rows.append(f"<tr><td class='cy'>Total</td>{tot}</tr>")
        yoy = []
        for i, cy in enumerate(years):
            done = t.loc[cy].notna()
            g = np.nan
            if i > 0 and done.any():
                prev = t.iloc[i - 1][done]
                if prev.notna().all() and prev.sum() > 0:
                    g = t.loc[cy][done].sum() / prev.sum() - 1
            yoy.append("<td class='na'>-</td>" if np.isnan(g) else f"<td class='{'up' if g >= 0 else 'dn'}'>{g:+.0%}</td>")
        rows.append(f"<tr style='border-bottom:2px solid #0a2463'><td class='cy'>YTD YoY</td>{''.join(yoy)}</tr>")
    return f"<div class='mt-wrap' style='display:inline-block;max-width:100%'><table class='mt' style='width:auto'>{head}{''.join(rows)}</table></div>"


# ---------------------------------------------------------------------------------------------
# edit: Stat and Tree in one Month x Crop-year grid (like the desk sheet), saved to Database/monthly.csv (GitHub, like the weeks)
# ---------------------------------------------------------------------------------------------
MON_CSV = DB / "monthly.csv"
MON_PATH = "Database/monthly.csv"
ORIGIN_ORDER, TYPE_ORDER = {"IVC": 0, "Ghana": 1}, {"Stat": 0, "Tree": 1}


def _next_cy(cy: str) -> str:
    y = int(cy[:2]) + 1
    return f"{y % 100:02d}/{(y + 1) % 100:02d}"


def edit_grid(origin: str) -> pd.DataFrame:
    """Rows = Stat Oct..Sep then Tree Oct..Sep; columns = every crop year on file + one blank new crop year."""
    m = load()
    years = sorted(set(m[m.origin == origin].crop_year))
    years.append(_next_cy(years[-1]))                   # provision for the next crop year, left blank
    blocks = []
    for typ in TYPES:
        g = m[(m.origin == origin) & (m.type == typ)].pivot_table(index="month", columns="crop_year", values="kt")
        g = g.reindex(index=CROP_MONTHS, columns=years).astype(float)
        g.insert(0, "Type", typ)
        g.insert(0, "Month", CROP_MONTHS)
        blocks.append(g.reset_index(drop=True))
    return pd.concat(blocks, ignore_index=True)


def _as_text(grid: pd.DataFrame) -> pd.DataFrame:
    out = grid.copy()
    for c in grid.columns[2:]:
        out[c] = grid[c].map(lambda v: "" if pd.isna(v) else f"{v:.0f}" if float(v).is_integer() else f"{v}")
    return out


def _parse(grid: pd.DataFrame, orig: pd.DataFrame, bad: list) -> pd.DataFrame:
    out = orig.copy()
    for i in range(len(orig)):
        for cy in orig.columns[2:]:
            txt = grid.iloc[i][cy]
            txt = "" if txt is None or (isinstance(txt, float) and np.isnan(txt)) else str(txt).replace(",", "").strip()
            try:
                v = float(txt) if txt else np.nan
                if v < 0:
                    raise ValueError
            except ValueError:
                bad.append(f"{orig.Type[i]} {orig.Month[i]} {cy}: '{txt}' is not a valid number - kept the stored value.")
                v = orig.iloc[i][cy]
            out.loc[i, cy] = v
    return out


def _changes(orig: pd.DataFrame, new: pd.DataFrame) -> dict:
    """{(type, month, crop_year): value or None} where the cell differs."""
    out = {}
    for i in range(len(orig)):
        for cy in orig.columns[2:]:
            a, b = orig.iloc[i][cy], new.iloc[i][cy]
            if not (pd.isna(a) and pd.isna(b)) and not (a == b):
                out[(orig.Type[i], orig.Month[i], cy)] = None if pd.isna(b) else float(b)
    return out


def _mon_csv(frame: pd.DataFrame) -> str:
    frame = frame.copy()
    frame["_o"] = frame.origin.map(ORIGIN_ORDER)
    frame["_t"] = frame.type.map(TYPE_ORDER)
    frame["_m"] = frame.month.map({m: i for i, m in enumerate(CROP_MONTHS)})
    frame = frame.sort_values(["_o", "crop_year", "_t", "_m"]).drop(columns=["_o", "_t", "_m"])
    if (frame.kt % 1 == 0).all():
        frame["kt"] = frame.kt.astype("Int64")
    return frame[["origin", "month", "type", "crop_year", "kt"]].to_csv(index=False, lineterminator="\n")


def save_monthly(origin: str, changes: dict):
    msg = f"Forestero {origin}: " + "; ".join(f"{t} {m} {cy} {'cleared' if v is None else f'{v:,.0f}'}" for (t, m, cy), v in changes.items())

    def change(text):
        frame = pd.read_csv(io.StringIO(text), dtype={"crop_year": str})
        for (typ, mon, cy), v in changes.items():
            hit = (frame.origin == origin) & (frame.type == typ) & (frame.month == mon) & (frame.crop_year == cy)
            frame = frame[~hit]
            if v is not None:
                frame = pd.concat([frame, pd.DataFrame([{"origin": origin, "month": mon, "type": typ, "crop_year": cy, "kt": v}])],
                                  ignore_index=True)
        return _mon_csv(frame), None

    if projection.entry_enabled():
        new_text, _ = gh.commit(MON_PATH, change, msg)
    else:                                                # local run: write the file directly
        new_text, _ = change(MON_CSV.read_text(encoding="utf-8"))
    MON_CSV.write_text(new_text, encoding="utf-8", newline="")   # show it now, before Cloud redeploys
    load.clear()
    season.load.clear()


def render_edit(origin: str):
    orig = edit_grid(origin)
    years = list(orig.columns[2:])
    ver = st.session_state.get(f"mo_ver_{origin}", 0)
    with st.container(border=True):
        st.markdown(f"<div class='card-title'>Edit Forestero {origin}</div>", unsafe_allow_html=True)
        cfg = {"Month": st.column_config.TextColumn("Month", width=60, disabled=True),
               "Type": st.column_config.TextColumn("Type", width=56, disabled=True)}
        cfg.update({cy: st.column_config.TextColumn(cy, width=64) for cy in years})
        typed = st.data_editor(_as_text(orig), key=f"mo_ed_{origin}_{ver}", width="content", row_height=26, hide_index=True,
                               height=26 * (len(orig) + 1) + 16, column_config=cfg)
        bad = []
        new = _parse(typed, orig, bad)
        changes = _changes(orig, new)
        for n in bad:
            st.error(n)
        vals = orig[years].to_numpy(float)
        cap = np.nanmax(vals) if np.isfinite(vals).any() else np.inf
        notes = [f"{t} {m} {cy}: {v:,.0f} is above 1.5x the highest month on file ({cap:,.0f}). Extra zero?"
                 for (t, m, cy), v in changes.items() if v is not None and v > 1.5 * cap]
        override = st.checkbox("Override warnings", key=f"mo_override_{origin}") if notes else True
        for n in notes:
            st.warning(n)
        c = st.columns([1, 6])
        if not projection.entry_enabled():
            c[1].markdown("<div style='color:#c94a4a;font-size:12px;margin-top:8px'>Save is off: add github_token in Streamlit Secrets "
                          "(without it nothing is stored).</div>", unsafe_allow_html=True)
        if c[0].button("Save", type="primary", width="stretch", disabled=not (changes and override and projection.entry_enabled()),
                       key=f"mo_save_{origin}"):
            try:
                save_monthly(origin, changes)
            except gh.GitHubError as ex:
                st.error(str(ex))
            else:
                st.session_state[f"mo_ver_{origin}"] = ver + 1
                st.rerun()
        if changes:
            c[1].markdown(f"<div class='card-desc' style='margin-top:8px'>{len(changes)} cell(s) changed, not saved yet.</div>",
                          unsafe_allow_html=True)


def render(origin: str):
    top = st.columns([1.8, 1.4, 5], vertical_alignment="center")
    with top[0]:
        view = st.radio("View", ["Charts", "Table"], horizontal=True, label_visibility="collapsed", key=f"mo_view_{origin}")
    if view == "Charts":
        with top[1]:
            last_n = {"Last 5": 5, "All": 0}[st.radio("Years", ["Last 5", "All"], horizontal=True, label_visibility="collapsed", key=f"mo_n_{origin}")]
        left, right = st.columns(2)
        with left, st.container(border=True):
            st.markdown(f"<div class='card-title'>Monthly arrivals {origin}</div>",
                        unsafe_allow_html=True)
            st.plotly_chart(line_chart(origin, False, last_n), width="stretch")
        with right, st.container(border=True):
            st.markdown(f"<div class='card-title'>Cumulative arrivals {origin}</div>", unsafe_allow_html=True)
            st.plotly_chart(line_chart(origin, True, last_n), width="stretch")
    else:
        if origin != COMBINED:
            render_edit(origin)
        with st.container(border=True):
            st.markdown(f"<div class='card-title'>Monthly arrivals {origin} - all crop years</div>",
                        unsafe_allow_html=True)
            st.markdown(CSS + table_html(origin), unsafe_allow_html=True)
