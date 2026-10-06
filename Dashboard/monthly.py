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
    """t: rows = crop year, columns = month. Rendered with months down and crop years across."""
    years = list(t.index)
    running = {cy: not t.loc[cy].notna().all() for cy in years}
    head = "<tr><th>Month</th>" + "".join(f"<th>{cy}{'*' if running[cy] else ''}</th>" for cy in years) + "</tr>"
    rows = []
    for m in CROP_MONTHS:
        col = t[m]
        rows.append(f"<tr><td class='cy'>{m}</td>" + "".join(_cell(col[cy], col.min(), col.max()) for cy in years) + "</tr>")
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
    rows.append(f"<tr><td class='cy'>YTD YoY</td>{''.join(yoy)}</tr>")
    return f"<div class='mt-wrap' style='display:inline-block;max-width:100%'><table class='mt' style='width:auto'>{head}{''.join(rows)}</table></div>"


# ---------------------------------------------------------------------------------------------
# edit: Forestero figures typed straight into a Month x Crop-year grid, saved to Database/monthly.csv (GitHub, like the weeks)
# ---------------------------------------------------------------------------------------------
MON_CSV = DB / "monthly.csv"
MON_PATH = "Database/monthly.csv"
ORIGIN_ORDER, TYPE_ORDER = {"IVC": 0, "Ghana": 1}, {"Stat": 0, "Tree": 1}


def current_crop_year(today: pd.Timestamp | None = None) -> str:
    t = today or pd.Timestamp.today()
    y = t.year if t.month >= 10 else t.year - 1
    return f"{y % 100:02d}/{(y + 1) % 100:02d}"


def edit_grid(origin: str, typ: str) -> pd.DataFrame:
    """Rows Oct..Sep, columns = every crop year on file for this origin (+ the current one), thousand tonnes."""
    m = load()
    years = sorted(set(m[m.origin == origin].crop_year) | {current_crop_year()})
    g = m[(m.origin == origin) & (m.type == typ)].pivot_table(index="month", columns="crop_year", values="kt")
    return g.reindex(index=CROP_MONTHS, columns=years).astype(float)


def _as_text(grid: pd.DataFrame) -> pd.DataFrame:
    return grid.apply(lambda col: col.map(lambda v: "" if pd.isna(v) else f"{v:.0f}" if float(v).is_integer() else f"{v}"))


def _parse(grid: pd.DataFrame, orig: pd.DataFrame, bad: list) -> pd.DataFrame:
    out = orig.copy()
    for mon in grid.index:
        for cy in grid.columns:
            txt = grid.loc[mon, cy]
            txt = "" if txt is None or (isinstance(txt, float) and np.isnan(txt)) else str(txt).replace(",", "").strip()
            try:
                v = float(txt) if txt else np.nan
                if v < 0:
                    raise ValueError
            except ValueError:
                bad.append(f"{mon} {cy}: '{txt}' is not a valid number - kept the stored value.")
                v = orig.loc[mon, cy]
            out.loc[mon, cy] = v
    return out


def _changes(orig: pd.DataFrame, new: pd.DataFrame) -> dict:
    """{(month, crop_year): value or None} where the cell differs."""
    out = {}
    for mon in orig.index:
        for cy in orig.columns:
            a, b = orig.loc[mon, cy], new.loc[mon, cy]
            if not (pd.isna(a) and pd.isna(b)) and not (a == b):
                out[(mon, cy)] = None if pd.isna(b) else float(b)
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


def save_monthly(origin: str, typ: str, changes: dict):
    msg = f"Forestero {origin} {typ}: " + "; ".join(f"{m} {cy} {'cleared' if v is None else f'{v:,.0f}'}" for (m, cy), v in changes.items())

    def change(text):
        frame = pd.read_csv(io.StringIO(text), dtype={"crop_year": str})
        for (mon, cy), v in changes.items():
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


def render_edit(origin: str, typ: str):
    orig = edit_grid(origin, typ)
    ver = st.session_state.get(f"mo_ver_{origin}", 0)
    with st.container(border=True):
        st.markdown(f"<div class='card-title'>Edit Forestero {origin} ({typ})</div><div class='card-desc'>Thousand tonnes. Type over any "
                    "cell, blank = no figure. Switch Stat / Tree above to edit the other series. <b>Save</b> stores the changes; the table below updates after Save.</div>",
                    unsafe_allow_html=True)
        cfg = {"_index": st.column_config.Column("Month", width=74)}
        cfg.update({cy: st.column_config.TextColumn(cy, width=64) for cy in orig.columns})
        typed = st.data_editor(_as_text(orig), key=f"mo_ed_{origin}_{typ}_{ver}", width="content", row_height=26,
                               height=26 * (len(orig) + 1) + 16, column_config=cfg)
        bad = []
        new = _parse(typed, orig, bad)
        changes = _changes(orig, new)
        for n in bad:
            st.error(n)
        cap = np.nanmax(orig.to_numpy()) if np.isfinite(orig.to_numpy()).any() else np.inf
        notes = [f"{m} {cy}: {v:,.0f} is above 1.5x the highest month on file ({cap:,.0f}). Extra zero?"
                 for (m, cy), v in changes.items() if v is not None and v > 1.5 * cap]
        override = st.checkbox("Override warnings", key=f"mo_override_{origin}") if notes else True
        for n in notes:
            st.warning(n)
        c = st.columns([1, 6])
        if c[0].button("Save", type="primary", width="stretch", disabled=not (changes and override), key=f"mo_save_{origin}"):
            try:
                save_monthly(origin, typ, changes)
            except gh.GitHubError as ex:
                st.error(str(ex))
            else:
                st.session_state[f"mo_ver_{origin}"] = ver + 1
                st.rerun()
        if changes:
            c[1].markdown(f"<div class='card-desc' style='margin-top:8px'>{len(changes)} cell(s) changed, not saved yet.</div>",
                          unsafe_allow_html=True)


def render(origin: str):
    top = st.columns([1.2, 1.8, 1.2, 3.6], vertical_alignment="center")
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
        if origin != COMBINED:
            render_edit(origin, typ)
        with st.container(border=True):
            st.markdown(f"<div class='card-title'>Monthly arrivals {origin} ({typ}) - all crop years</div>"
                        "<div class='card-desc'>Thousand tonnes. Shading compares each month with the same month in other years. "
                        "* = crop year still running; YTD YoY compares the months reported so far with the same months a year earlier.</div>",
                        unsafe_allow_html=True)
            st.markdown(CSS + table_html(t), unsafe_allow_html=True)
