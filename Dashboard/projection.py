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
EIKON_CSV = DB / "eikon_weekly.csv"
EIKON_PATH = "Database/eikon_weekly.csv"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
PORTS = ["Abidjan", "San Pedro"]
BAR = {"Abidjan": "rgba(31,138,156,0.28)", "San Pedro": "rgba(10,36,99,0.22)", "Combined": "rgba(201,138,31,0.32)", "Eikon": "rgba(107,74,138,0.28)"}

CSS = """
<style>
.pj-wrap { max-height: 640px; overflow: auto; border: 1px solid #e3e7f0; border-radius: 10px; background: #fff; }
.pj { border-collapse: separate; border-spacing: 0; font-size: 12px; width: 100%; }
.pj th { position: sticky; top: 0; z-index: 2; background: #0a2463; color: #fff; font-weight: 600; padding: 4px 8px; text-align: center; white-space: nowrap; }
.pj th.p1 { background: #1f8a9c; } .pj th.p2 { background: #0a2463; } .pj th.p4 { background: #6b4a8a; } .pj th.p3 { background: #8a5a12; }
.pj tr.h2 th { top: 25px; background: #eef0f6; color: #0a2463; font-size: 11px; }
.pj td { padding: 2px 8px; text-align: right; border-bottom: 1px solid #eef0f6; white-space: nowrap; color: #1a1a2e;
         font-variant-numeric: tabular-nums; }
.pj td.wk { text-align: center; background: #f6f7fb; font-weight: 600; position: sticky; left: 0; z-index: 1; }
.pj td.tot { font-weight: 700; border-left: 1px solid #dfe3ee; }
.pj td.mk { background: #fff1cf; }
.pj td.est { font-style: italic; color: #6f7895; }
.pj td.est.tot { color: #0a2463; }
.pj td.na { color: #b8bfd2; }
.pj td.up { color: #1f9d6f; } .pj td.dn { color: #c94a4a; }
.pj .tag { font-size: 9px; color: #8a5a12; font-weight: 700; margin-left: 3px; }
.pj-wrap.fit { display: inline-block; max-width: 100%; }
.pj.fit { width: auto; font-size: 11.5px; }
.pj.fit td, .pj.fit th { padding: 2px 7px; }
.pj-note { font-size: 11px; color: #7a86a8; margin-top: 6px; }
</style>
"""


@st.cache_data(ttl=600)
def load() -> pd.DataFrame:
    d = pd.read_csv(DB / "ivc_projection.csv", parse_dates=["week"])
    return d.sort_values(["port", "week"]).reset_index(drop=True)


@st.cache_data(ttl=600)
def load_eikon() -> pd.Series:
    """Eikon weekly total of both ports, tonnes, indexed by the Monday of the week."""
    d = pd.read_csv(EIKON_CSV, parse_dates=["week"])
    return d.set_index("week")["eikon"].astype(float).sort_index()


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


def table_html(data: dict, weeks: pd.DatetimeIndex, fit: bool = False, mark: frozenset = frozenset(),
               eik: pd.Series | None = None) -> str:
    ab, sp = data["Abidjan"].set_index("week"), data["San Pedro"].set_index("week")
    all_w = ab.index.union(sp.index)
    comb_all = ab["total"].reindex(all_w) + sp["total"].reindex(all_w)
    dmax = {p: np.nanmax(data[p][[f"est_{x}" for x in DAYS]].to_numpy()) for p in PORTS}
    tmax = {p: np.nanmax(data[p]["total"]) for p in PORTS}
    cmax = np.nanmax(comb_all)

    h1 = ("<tr><th rowspan=2>Week of</th><th class='p1' colspan=7>Abidjan</th><th class='p2' colspan=7>San Pedro</th>"
          "<th class='p3' rowspan=2>Combined</th>" + ("<th class='p4' colspan=2>Eikon</th>" if eik is not None else "") + "</tr>")
    h2 = "<tr class='h2'>" + ("".join(f"<th>{x}</th>" for x in DAYS) + "<th>Total</th>") * 2 + ("<th>Total</th><th>ETG - Eikon</th>" if eik is not None else "") + "</tr>"
    rows = []
    for w in weeks:
        tds = [f"<td class='wk{' mk' if w in mark else ''}'>{w:%d-%b-%y}</td>"]
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
        if eik is not None:
            ev = eik.get(w, np.nan)
            tds.append(f"<td style=\"{_bar(ev, np.nanmax(eik.to_numpy()), BAR['Eikon'], False)}\">{_fmt(ev)}</td>")
            gap = c - ev if pd.notna(ev) and pd.notna(c) else np.nan
            tds.append("<td class='na'>-</td>" if np.isnan(gap) else f"<td class='{'up' if gap >= 0 else 'dn'}'>{gap:+,.0f}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    cls = " fit" if fit else ""
    return f"<div class='pj-wrap{cls}'><table class='pj{cls}'>{h1}{h2}{''.join(rows)}</table></div>"


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


N_WEEKS = 6                                             # rows in the entry grid: the coming week + the last 5
GRID_COLS = [f"A_{d}" for d in DAYS] + [f"S_{d}" for d in DAYS] + ["Eikon"]
W_WEEK, W_DAY, W_EIK = 74, 58, 70                      # pixel widths: the header strip above the grid uses the same numbers


def _eik_frame(text: str) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(text))


def _eik_csv(frame: pd.DataFrame) -> str:
    frame = frame.drop_duplicates("week", keep="last").sort_values("week").copy()
    frame["week"] = pd.to_datetime(frame["week"]).dt.strftime("%Y-%m-%d")
    frame["eikon"] = frame["eikon"].round(0).astype("Int64")
    return frame.to_csv(index=False, lineterminator="\n")


def apply_eikon(frame: pd.DataFrame, week: pd.Timestamp, value) -> pd.DataFrame:
    frame = frame.copy()
    frame["week"] = pd.to_datetime(frame["week"])
    frame = frame[frame.week != week]
    if value is not None:
        frame = pd.concat([frame, pd.DataFrame([{"week": week, "eikon": value}])], ignore_index=True)
    return frame


def week_grid(raw: pd.DataFrame, eik: pd.Series):
    """One grid: rows = the coming week (blank) then the latest weeks, newest first; columns = Abidjan Mon-Sat, San Pedro Mon-Sat, Eikon."""
    latest = pd.Timestamp(raw.week.max())
    past = [pd.Timestamp(w) for w in sorted(raw.week.unique())[-(N_WEEKS - 1):][::-1]]
    weeks = [latest + pd.Timedelta(days=7)] + past
    ab, sp = (raw[raw.port == p].set_index("week") for p in PORTS)
    rows = []
    for w in weeks:
        row = [ab[d].get(w, np.nan) if w in ab.index else np.nan for d in DAYS]
        row += [sp[d].get(w, np.nan) if w in sp.index else np.nan for d in DAYS]
        row.append(eik.get(w, np.nan))
        rows.append(row)
    return weeks, pd.DataFrame(rows, columns=GRID_COLS, index=[f"{w:%d-%b-%y}" for w in weeks]).astype(float)


def as_text(grid: pd.DataFrame) -> pd.DataFrame:
    """Numbers as plain text, empty cell = '' (a number column would show None)."""
    return grid.apply(lambda col: col.map(lambda v: "" if pd.isna(v) else f"{v:.0f}" if float(v).is_integer() else f"{v}"))


def to_number(grid: pd.DataFrame, orig: pd.DataFrame, bad: list) -> pd.DataFrame:
    """Text grid back to numbers; '' / None = not reported; anything unreadable keeps the stored value and is reported in `bad`."""
    out = grid.copy().astype(object)
    for i in range(len(grid)):
        for col in grid.columns:
            txt = grid.iloc[i][col]
            txt = "" if txt is None or (isinstance(txt, float) and np.isnan(txt)) else str(txt).replace(",", "").strip()
            try:
                v = float(txt) if txt else np.nan
                if v < 0:
                    raise ValueError
            except ValueError:
                label = "Eikon" if col == "Eikon" else f"{'Abidjan' if col[0] == 'A' else 'San Pedro'} {col[2:]}"
                bad.append(f"{grid.index[i]} {label}: '{txt}' is not a valid number - kept the stored value.")
                v = orig.iloc[i][col]
            out.iloc[i, out.columns.get_loc(col)] = v
    return out.astype(float)


def collect(weeks, orig: pd.DataFrame, edited: pd.DataFrame) -> dict:
    """{week: {"ports": {port: {day: number|None}}, "eikon": number|None, "p": ports changed, "e": eikon changed}} for changed weeks."""
    out = {}
    for i, w in enumerate(weeks):
        o, e = orig.iloc[i], edited.iloc[i]
        p_changed = not np.array_equal(o[GRID_COLS[:12]].to_numpy(float), e[GRID_COLS[:12]].to_numpy(float), equal_nan=True)
        e_changed = not np.array_equal([o["Eikon"]], [e["Eikon"]], equal_nan=True)
        if not (p_changed or e_changed):
            continue
        num = lambda x: None if np.isnan(x) else float(x)
        out[w] = {"ports": {"Abidjan": {d: num(e[f"A_{d}"]) for d in DAYS}, "San Pedro": {d: num(e[f"S_{d}"]) for d in DAYS}},
                  "eikon": num(e["Eikon"]), "p": p_changed, "e": e_changed}
    return out


def entry_notes(raw: pd.DataFrame, eik: pd.Series, changes: dict) -> list[str]:
    """A day (or Eikon week) far above anything seen before (extra zero?)."""
    notes = []
    for p in PORTS:
        cap = np.nanmax(raw[raw.port == p][DAYS].to_numpy())
        for w, c in changes.items():
            for d, v in c["ports"][p].items():
                if c["p"] and v is not None and v > 1.5 * cap:
                    notes.append(f"{p} {w:%d-%b} {d} {v:,.0f} is above 1.5x the highest day ever recorded ({cap:,.0f}). Extra zero?")
    if len(eik):
        cap = eik.max()
        for w, c in changes.items():
            if c["e"] and c["eikon"] is not None and c["eikon"] > 1.5 * cap:
                notes.append(f"Eikon {w:%d-%b} {c['eikon']:,.0f} is above 1.5x the highest week on file ({cap:,.0f}). Extra zero?")
    return notes


def preview_data(raw: pd.DataFrame, eik: pd.Series, changes: dict):
    """Projection of the grid as typed: stored data with the edited weeks swapped in."""
    frame, e = raw.copy(), eik.copy()
    for w, c in changes.items():
        frame = apply_week(frame, w, c["ports"])
        if c["eikon"] is None:
            e = e.drop(w, errors="ignore")
        else:
            e.loc[w] = c["eikon"]
    data = {p: project_port(frame[frame.port == p].drop(columns="port").sort_values("week")) for p in PORTS}
    return data, e.sort_index()


def _commit_or_write(path: str, local: Path, change, msg: str):
    if entry_enabled():
        new_text, _ = gh.commit(path, change, msg)
    else:                                                # local run: write the file directly
        new_text, _ = change(local.read_text(encoding="utf-8"))
    local.write_text(new_text, encoding="utf-8", newline="")   # show it now, before Cloud redeploys


def save_changes(changes: dict):
    port_w = {w: c for w, c in changes.items() if c["p"]}
    eik_w = {w: c for w, c in changes.items() if c["e"]}
    if port_w:
        msg = "Weeks " + "; ".join(f"{w:%Y-%m-%d}: " + " | ".join(
            f"{p} " + ",".join(f"{v:,.0f}" for v in c["ports"][p].values() if v is not None) for p in PORTS) for w, c in port_w.items())

        def change_ports(text):
            frame = _frame(text)
            for w, c in port_w.items():
                frame = apply_week(frame, w, c["ports"])
            return _to_csv(frame), None

        _commit_or_write(REPO_PATH, CSV, change_ports, msg)
    if eik_w:
        msg = "Eikon " + "; ".join(f"{w:%Y-%m-%d}: " + (f"{c['eikon']:,.0f}" if c["eikon"] is not None else "cleared") for w, c in eik_w.items())

        def change_eikon(text):
            frame = _eik_frame(text)
            for w, c in eik_w.items():
                frame = apply_eikon(frame, w, c["eikon"])
            return _eik_csv(frame), None

        _commit_or_write(EIKON_PATH, EIKON_CSV, change_eikon, msg)
    load.clear()
    load_eikon.clear()
    build.clear()


def render_entry(data: dict):
    """Returns (projected data, edited weeks, eikon series) after Project, else None."""
    raw, eik = load(), load_eikon()
    weeks, orig = week_grid(raw, eik)
    ver = st.session_state.get("pj_ver", 0)
    with st.container(border=True):
        st.markdown("<div class='card-title'>Enter / override weeks</div><div class='card-desc'>Blank = not reported, 0 = no arrivals.</div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='display:flex;font-size:12px;font-weight:600;color:#fff;text-align:center;margin-bottom:1px'>"
            f"<div style='width:{W_WEEK}px'></div>"
            f"<div style='width:{6 * W_DAY}px;background:#1f8a9c;padding:2px 0;border-radius:6px 0 0 0'>Abidjan</div>"
            f"<div style='width:{6 * W_DAY}px;background:#0a2463;padding:2px 0'>San Pedro</div>"
            f"<div style='width:{W_EIK}px;background:#6b4a8a;padding:2px 0;border-radius:0 6px 0 0'>Eikon</div></div>", unsafe_allow_html=True)
        cfg = {"_index": st.column_config.Column("Week", width=W_WEEK)}
        for pre in ("A", "S"):
            cfg.update({f"{pre}_{d}": st.column_config.TextColumn(d, width=W_DAY) for d in DAYS})
        cfg["Eikon"] = st.column_config.TextColumn("Total", width=W_EIK)
        edited = st.data_editor(as_text(orig), key=f"pj_ed_{ver}", width="content", row_height=26,
                                height=26 * (len(weeks) + 1) + 16, column_config=cfg)
        bad = []
        edited = to_number(edited, orig, bad)
        changes = collect(weeks, orig, edited)
        notes = entry_notes(raw, eik, changes)
        for n in bad:
            st.error(n)
        override = st.checkbox("Override warnings", key="pj_override") if notes else True
        for n in notes:
            st.warning(n)
        b = st.columns([1, 1, 6])
        do_project = b[0].button("Project", type="primary", width="stretch")
        do_save = b[1].button("Save", width="stretch", disabled=not (changes and override))
        if do_project:
            st.session_state["pj_show"] = True
        shown = None
        if st.session_state.get("pj_show"):
            if changes:
                pdata, e2 = preview_data(raw, eik, changes)
                shown = (pdata, frozenset(changes), e2)
                st.markdown("<div class='pj-note'>History below now shows what you typed (highlighted weeks), with the days not "
                            "reported filled in by the projection. Not saved until you press Save.</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='pj-note'>Nothing changed in the grid - History below already shows the projection "
                            "for incomplete weeks.</div>", unsafe_allow_html=True)
        if do_save:
            try:
                save_changes(changes)
            except gh.GitHubError as ex:
                st.error(str(ex))
            else:
                st.session_state["pj_ver"] = ver + 1
                st.session_state["pj_show"] = False
                st.rerun()
        if entry_enabled():
            with st.expander("Save history", expanded=False):
                try:
                    for ts, m in gh.history(REPO_PATH, 15):
                        st.markdown(f"<div class='pj-note'>{ts[:16].replace('T', ' ')} UTC - {m.splitlines()[0]}</div>",
                                    unsafe_allow_html=True)
                except gh.GitHubError as ex:
                    st.caption(str(ex))
    return shown


def crop_week_one(start_year: int) -> pd.Timestamp:
    """Monday of the week that contains 1 October - crop-year week 1 (matches the desk's weekly ETG series)."""
    d = pd.Timestamp(start_year, 10, 1)
    return d - pd.Timedelta(days=d.weekday())


def crop_series(data: dict, eik: pd.Series, start_year: int) -> pd.DataFrame:
    """Weeks 1-51 of the crop year starting `start_year`: ETG = Abidjan + San Pedro (running week = projected total, flagged in `proj`), Eikon, both in thousand tonnes."""
    ab, sp = data["Abidjan"].set_index("week"), data["San Pedro"].set_index("week")
    w1 = crop_week_one(start_year)
    rows = []
    for n in range(1, 52):
        w = w1 + pd.Timedelta(days=7 * (n - 1))
        etg, proj = np.nan, False
        if w in ab.index and w in sp.index:                      # a week still running counts with its projected total
            etg = (ab.loc[w, "total"] + sp.loc[w, "total"]) / 1000
            proj = bool(ab.loc[w, "projected"] or sp.loc[w, "projected"])
        rows.append((n, etg, proj, eik.get(w, np.nan) / 1000))
    return pd.DataFrame(rows, columns=["week", "etg", "proj", "eikon"])


def render_history(data: dict, mark: frozenset = frozenset(), eik: pd.Series | None = None):
    allw = sorted(set(data["Abidjan"].week) | set(data["San Pedro"].week), reverse=True)
    eik = load_eikon() if eik is None else eik
    with st.container(border=True):
        st.markdown("<div class='card-title'>History</div>", unsafe_allow_html=True)
        st.markdown(CSS + table_html(data, pd.DatetimeIndex(allw), fit=True, mark=mark, eik=eik), unsafe_allow_html=True)


def render_week():
    data = build()
    shown = render_entry(data)
    if shown:
        pdata, mark, e2 = shown
        render_history(pdata, mark, e2)
    else:
        render_history(data)
