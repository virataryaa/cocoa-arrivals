"""IVC weekly arrivals by port (Abidjan / San Pedro, Mon-Sat) with the projection of unfinished weeks.

Projection = known days / historical share of those days in the full week, where the share is the ratio of sums over
every earlier week that has all six days. Works for any set of known days (Mon-Thu, a blank Monday, ...).
"""
import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ghstore as gh

DB = Path(__file__).resolve().parent.parent / "Database"
CSV = DB / "ivc_projection.csv"
REPO_PATH = "Database/ivc_projection.csv"
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


# ---------------------------------------------------------------------------------------------
# entry: type Mon-Thu, press Project to see the full week, Save to store it (GitHub, like Cecafe Daily)
# ---------------------------------------------------------------------------------------------
def entry_enabled() -> bool:
    try:
        return "github_token" in st.secrets
    except Exception:                                   # no secrets file at all (local run)
        return False


def _frame(text: str) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(text))


def _to_csv(frame: pd.DataFrame) -> str:
    frame = frame.sort_values(["port", "week"]).copy()
    frame["week"] = pd.to_datetime(frame["week"]).dt.strftime("%Y-%m-%d")
    for d in DAYS:                                      # whole tonnes stay whole numbers in the file
        if (frame[d].dropna() % 1 == 0).all():
            frame[d] = frame[d].astype("Int64")
    return frame.to_csv(index=False, lineterminator="\n")


def apply_week(frame: pd.DataFrame, week: pd.Timestamp, vals: dict) -> pd.DataFrame:
    """Replace the given week of each port by vals[port] = {day: number or None}; a port with nothing entered loses the row."""
    frame = frame.copy()
    frame["week"] = pd.to_datetime(frame["week"])
    frame = frame[~((frame.week == week) & frame.port.isin(vals))]
    new = [{"port": p, "week": week, **v} for p, v in vals.items() if any(x is not None for x in v.values())]
    if new:
        frame = pd.concat([frame, pd.DataFrame(new)], ignore_index=True)
    return frame.reindex(columns=["port", "week", *DAYS])


def current_week_values(raw: pd.DataFrame, week: pd.Timestamp) -> pd.DataFrame:
    g = raw[raw.week == week].set_index("port")
    return pd.DataFrame({d: [g[d].get(p, np.nan) if p in g.index else np.nan for p in PORTS] for d in DAYS}, index=PORTS)


def grid_vals(grid: pd.DataFrame) -> dict:
    return {p: {d: (None if pd.isna(grid.loc[p, d]) else float(grid.loc[p, d])) for d in DAYS} for p in PORTS}


def preview(raw: pd.DataFrame, week: pd.Timestamp, vals: dict) -> dict:
    """Projection of the entered week, using only the weeks before it."""
    out = {}
    for p in PORTS:
        sub = apply_week(raw[raw.port == p], week, {p: vals[p]})
        r = project_port(sub.drop(columns="port")).set_index("week")
        out[p] = r.loc[week] if week in r.index else None
    return out


def entry_notes(raw: pd.DataFrame, vals: dict) -> list[str]:
    """Things to double check: a day far above anything seen at that port (extra zero?)."""
    notes = []
    for p in PORTS:
        cap = np.nanmax(raw[raw.port == p][DAYS].to_numpy())
        for d, v in vals[p].items():
            if v is not None and v > 1.5 * cap:
                notes.append(f"{p} {d} {v:,.0f} is above 1.5x the highest day ever recorded ({cap:,.0f}). Extra zero?")
    return notes


def save_week(week: pd.Timestamp, vals: dict):
    msg = f"Week {week:%Y-%m-%d}: " + "; ".join(
        f"{p} " + ",".join(f"{d} {v:,.0f}" for d, v in vals[p].items() if v is not None) for p in PORTS)

    def change(text):
        return _to_csv(apply_week(_frame(text), week, vals)), None

    if entry_enabled():
        new_text, _ = gh.commit(REPO_PATH, change, msg)
    else:                                                # local run: write the file directly
        new_text, _ = change(CSV.read_text(encoding="utf-8"))
    CSV.write_text(new_text, encoding="utf-8", newline="")   # show it now, before Cloud redeploys
    load.clear()
    build.clear()


def preview_html(res: dict, vals: dict) -> str:
    rows = []
    for p in PORTS:
        r = res[p]
        if r is None or pd.isna(r["total"]):
            rows.append(f"<tr><td class='wk'>{p}</td><td colspan=7 class='na'>nothing entered</td></tr>")
            continue
        tds = [f"<td class='wk'>{p}</td>"]
        for d in DAYS:
            tds.append(f"<td class='{'est' if vals[p][d] is None else ''}'>{_fmt(r[f'est_{d}'])}</td>")
        tds.append(f"<td class='tot est'>{_fmt(r['total'])}<span class='tag'>P</span></td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    tot = sum(r["total"] for r in res.values() if r is not None and not pd.isna(r["total"]))
    head = "<tr><th>Port</th>" + "".join(f"<th>{d}</th>" for d in DAYS) + "<th>Week total</th></tr>"
    rows.append(f"<tr><td class='wk'>Combined</td><td colspan=6></td><td class='tot'>{_fmt(tot)}</td></tr>")
    return f"<div class='pj-wrap' style='max-height:none'><table class='pj'>{head}{''.join(rows)}</table></div>"


def render_entry(data: dict):
    raw = load()
    allw = sorted(raw.week.unique())
    latest = pd.Timestamp(allw[-1])
    full_last = all(not data[p][data[p].week == latest][[f"is_{d}" for d in DAYS]].to_numpy().any() for p in PORTS)
    choices = [latest + pd.Timedelta(days=7)] + [pd.Timestamp(w) for w in allw[-8:][::-1]]
    with st.container(border=True):
        st.markdown("<div class='card-title'>Enter a week</div><div class='card-desc'>Type the days reported so far "
                    "(Mon-Thu is enough), leave the rest blank, press <b>Project</b> to see the full week, "
                    "<b>Save</b> to store it. A 0 means no arrivals; blank means not reported yet.</div>", unsafe_allow_html=True)
        top = st.columns([1.5, 5], vertical_alignment="center")
        with top[0]:
            week = st.selectbox("Week", choices, index=0 if full_last else 1, label_visibility="collapsed", key="pj_week",
                                format_func=lambda w: f"Week of  |  {w:%d-%b-%Y}")
        grid = st.data_editor(
            current_week_values(raw, week), key=f"pj_ed_{week:%Y%m%d}", width="stretch",
            column_config={d: st.column_config.NumberColumn(d, min_value=0, step=1, format="%d") for d in DAYS})
        vals = grid_vals(grid)
        notes = entry_notes(raw, vals)
        override = st.checkbox("Override warnings", key="pj_override") if notes else True
        for n in notes:
            st.warning(n)
        b = st.columns([1, 1, 6])
        do_project = b[0].button("Project", type="primary", width="stretch")
        do_save = b[1].button("Save", width="stretch", disabled=not override)
        if do_project:
            st.session_state["pj_show"] = week
        if st.session_state.get("pj_show") == week and any(x is not None for p in PORTS for x in vals[p].values()):
            st.markdown(CSS + preview_html(preview(raw, week, vals), vals), unsafe_allow_html=True)
            st.markdown("<div class='pj-note'>Italic = projected from the share those days normally make of the week "
                        "(complete weeks before this one). Not saved until you press Save.</div>", unsafe_allow_html=True)
        if do_save:
            try:
                save_week(week, vals)
            except gh.GitHubError as ex:
                st.error(str(ex))
            else:
                st.session_state["pj_show"] = None
                st.rerun()
        if entry_enabled():
            with st.expander("Save history", expanded=False):
                try:
                    for ts, m in gh.history(REPO_PATH, 15):
                        st.markdown(f"<div class='pj-note'>{ts[:16].replace('T', ' ')} UTC - {m.splitlines()[0]}</div>",
                                    unsafe_allow_html=True)
                except gh.GitHubError as ex:
                    st.caption(str(ex))


PORT_COL = {"Abidjan": "#1f8a9c", "San Pedro": "#0a2463"}
MONTHS_CROP = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]


def _layout(fig, height):
    fig.update_layout(
        template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#1a1a2e"),
        hovermode="x unified", height=height, margin=dict(t=10, b=10, l=10, r=10),
        xaxis=dict(gridcolor="rgba(10,36,99,0.08)", color="#4a5578"),
        yaxis=dict(gridcolor="rgba(10,36,99,0.08)", color="#4a5578", tickformat=",", hoverformat=",.0f"),
        legend=dict(orientation="h", x=0, y=-0.15, xanchor="left", yanchor="top", font=dict(size=11), bgcolor="rgba(0,0,0,0)"))
    return fig


def weekly_totals(data: dict) -> pd.DataFrame:
    ab, sp = data["Abidjan"].set_index("week"), data["San Pedro"].set_index("week")
    idx = ab.index.union(sp.index)
    df = pd.DataFrame({"Abidjan": ab["total"].reindex(idx), "San Pedro": sp["total"].reindex(idx)})
    df["proj"] = (ab["projected"].reindex(idx).fillna(False).astype(bool) | sp["projected"].reindex(idx).fillna(False).astype(bool))
    df["Combined"] = df["Abidjan"] + df["San Pedro"]
    return df


def render_week_chart(data: dict):
    """Last 16 weeks stacked by port (projected weeks hatched) + the same week a year earlier."""
    df = weekly_totals(data).tail(16)
    allw = weekly_totals(data)
    ly = allw["Combined"].reindex(df.index - pd.Timedelta(days=364))
    with st.container(border=True):
        st.markdown("<div class='card-title'>Last 16 weeks, combined (tonnes)</div>"
                    "<div class='card-desc'>Abidjan + San Pedro. Hatched bars are projected weeks. The marker is the same week a year earlier.</div>",
                    unsafe_allow_html=True)
        fig = go.Figure()
        for port in PORTS:
            fig.add_bar(x=df.index, y=df[port], name=port, marker_color=PORT_COL[port],
                        marker_pattern_shape=["/" if p else "" for p in df["proj"]], marker_pattern_fgcolor="rgba(255,255,255,0.7)",
                        hovertemplate="%{y:,.0f}")
        fig.add_scatter(x=df.index, y=ly.to_numpy(), name="Same week last year", mode="markers",
                        marker=dict(symbol="diamond", size=9, color="#c98a1f", line=dict(color="#fff", width=1)), hovertemplate="%{y:,.0f}")
        fig.update_layout(barmode="stack")
        fig.update_xaxes(tickformat="%d-%b", dtick=7 * 86400000 * 2)
        st.plotly_chart(_layout(fig, 360), width="stretch")


def share_heatmap(data: dict, port: str):
    """Mean share of the week's total made by each weekday, per crop-year month, complete weeks only."""
    d = data[port]
    d = d[~d["projected"]].copy()
    d["m"] = d.week.dt.strftime("%b")
    z = []
    for m in MONTHS_CROP:
        g = d[d.m == m]
        tot = g[DAYS].sum().sum()
        z.append([g[x].sum() / tot if tot else np.nan for x in DAYS])
    z = np.array(z)
    fig = go.Figure(go.Heatmap(z=z, x=DAYS, y=MONTHS_CROP, colorscale=[[0, "#f4f9fa"], [1, "#1f8a9c"]], zmin=0.0,
                               text=[[f"{v:.0%}" if not np.isnan(v) else "" for v in r] for r in z], texttemplate="%{text}",
                               hovertemplate="%{y} %{x}: %{z:.1%}<extra></extra>", showscale=False))
    fig.update_yaxes(autorange="reversed")
    return _layout(fig, 380)


def port_share_chart(data: dict):
    df = weekly_totals(data)
    df = df[df["Abidjan"].notna() & df["San Pedro"].notna() & (df["Combined"] > 0)]
    share = (df["Abidjan"] / df["Combined"])
    fig = go.Figure()
    fig.add_scatter(x=df.index, y=share, name="Abidjan share (weekly)", mode="lines", line=dict(color="rgba(31,138,156,0.35)", width=1.2),
                    hovertemplate="%{y:.0%}")
    fig.add_scatter(x=df.index, y=(df["Abidjan"].rolling(8).sum() / df["Combined"].rolling(8).sum()), name="8-week",
                    mode="lines", line=dict(color="#1f8a9c", width=3), hovertemplate="%{y:.0%}")
    _layout(fig, 340)
    fig.update_yaxes(tickformat=".0%", hoverformat=".0%", range=[0, 1])
    return fig


def backtest(data: dict) -> pd.DataFrame:
    """Thursday projection (Mon-Thu known) of every complete week against its real total, using only earlier complete weeks."""
    rows = []
    for port in PORTS:
        d = data[port].reset_index(drop=True)
        vals = d[DAYS].to_numpy(float)
        full = ~np.isnan(vals).any(axis=1)
        for i in range(len(d)):
            if not full[i]:
                continue
            hist = vals[:i][full[:i]]
            if len(hist) < 20 or vals[i].sum() <= 0:
                continue
            proj = vals[i, :4].sum() / (hist[:, :4].sum() / hist.sum())
            rows.append((port, d.week[i], proj / vals[i].sum() - 1))
    return pd.DataFrame(rows, columns=["port", "week", "miss"])


def render_accuracy(data: dict):
    bt = backtest(data)
    with st.container(border=True):
        st.markdown("<div class='card-title'>Projection accuracy - Thursday cut-off</div>"
                    "<div class='card-desc'>For every complete week: project the full week from Monday-Thursday only (using the weeks "
                    "before it) and compare with the real total. Miss % = projection / actual - 1; positive = projection too high.</div>",
                    unsafe_allow_html=True)
        fig = go.Figure()
        for port in PORTS:
            g = bt[bt.port == port]
            fig.add_scatter(x=g.week, y=g.miss, name=port, mode="lines+markers", marker=dict(size=4),
                            line=dict(color=PORT_COL[port], width=1.6), hovertemplate="%{y:+.1%}")
        fig.add_hline(y=0, line_color="#8a94a8", line_width=1)
        _layout(fig, 360)
        fig.update_yaxes(tickformat=".0%", hoverformat="+.1%")
        st.plotly_chart(fig, width="stretch")
        rows = []
        for port in PORTS:
            g = bt[bt.port == port].sort_values("week")
            rec = g.tail(26)
            rows.append(f"<tr><td class='wk'>{port}</td><td>{len(g)}</td><td>{g.miss.abs().mean():.1%}</td><td>{g.miss.mean():+.1%}</td>"
                        f"<td>{rec.miss.abs().mean():.1%}</td><td>{rec.miss.mean():+.1%}</td></tr>")
        head = ("<tr><th>Port</th><th>Weeks tested</th><th>Avg miss (all)</th><th>Bias (all)</th>"
                "<th>Avg miss (last 26)</th><th>Bias (last 26)</th></tr>")
        st.markdown(CSS + f"<div class='pj-wrap' style='max-height:none'><table class='pj'>{head}{''.join(rows)}</table></div>"
                    "<div class='pj-note'>Avg miss = typical size of the error; bias = its direction (+ means the projection was too high).</div>",
                    unsafe_allow_html=True)


def render_week():
    data = build()
    render_entry(data)
    render_week_chart(data)


def render_ports():
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

    left, right = st.columns(2)
    with left, st.container(border=True):
        st.markdown("<div class='card-title'>Weekday profile</div>"
                    "<div class='card-desc'>Share of the week's arrivals that lands on each day, by month (complete weeks). "
                    "This is the pattern the projection relies on.</div>", unsafe_allow_html=True)
        port = st.radio("Port", PORTS, horizontal=True, label_visibility="collapsed", key="pj_hm_port")
        st.plotly_chart(share_heatmap(data, port), width="stretch")
    with right, st.container(border=True):
        st.markdown("<div class='card-title'>Abidjan share of combined arrivals</div>"
                    "<div class='card-desc'>Abidjan / (Abidjan + San Pedro), weekly and 8-week.</div>", unsafe_allow_html=True)
        st.plotly_chart(port_share_chart(data), width="stretch")
