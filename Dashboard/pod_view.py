"""Cocoa Pod Counts (Ghana & Ivory Coast) inside Cocoa Arrivals: Overview (the old PodCounts dashboard) + Entry Table.

Data: Database/pod_counts.csv (Month, Year, NUMBER, CLASS, REGION, COUNTRY; Year 1950 = LTA), saved from the Entry Table
through GitHub like the other grids. Crop year Apr-Mar.
"""
import io
import os
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

import ghstore as gh
import projection
from pod.charts import cumulative_forecast, monthly_comparison
from pod.data_loader import (ALL_COUNTRIES, ATOMIC_CLASSES, COUNTRIES, DATA_PATH, LTA_YEAR, MAIN_CROP_PERIODS, MID_CROP_PERIODS,
                             TOTAL, classes, flow_wide, load_raw, window_wide, year_columns, ytd_period_window)
from pod.table_html import seasonal_table_html

POD_PATH = "Database/pod_counts.csv"
ENTRY_CLASSES = ["1. Tiny", "2.1 Small-1", "2.2 Small-2", "2. Small", "3. Large", "4. Mature", "5. Ripe",
                 "6. Insect", "7. Forced", "8. Damaged", "9. Black", "TOTAL"]
SHORT = {c: c.split(" ", 1)[1] if c[0].isdigit() else c.title() for c in ENTRY_CLASSES}   # "2.1 Small-1" -> "Small-1"
N_MONTHS = 6                                            # grid rows: the coming month + the last 5 reported
PANEL_H = 300
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

CSS = """
<style>
.pod-sub { color: #898781; font-size: 12px; margin: 0 0 8px; }
div[data-testid="stSelectbox"] label p { font-size: 11px !important; font-weight: 700 !important; text-transform: uppercase;
    letter-spacing: 0.06em; color: #898781 !important; }
</style>
"""


# ---------------------------------------------------------------------------------------------
# Overview - the old PodCounts page
# ---------------------------------------------------------------------------------------------
def _latest_period_label(df):
    df_wide = flow_wide(df, ALL_COUNTRIES, TOTAL)
    year_cols = [y for y in year_columns(df_wide) if y != "LTA"]
    current_year = year_cols[-1]
    idx = df_wide[current_year].last_valid_index()
    return current_year if idx is None else f"{df_wide.loc[idx, 'Period']} {current_year}"


def render_overview():
    df = load_raw()
    updated = datetime.fromtimestamp(os.path.getmtime(DATA_PATH)).strftime("%d %b %Y, %H:%M")
    st.markdown(CSS + f"<div class='pod-sub'>Data last updated {updated} &middot; latest survey through {_latest_period_label(df)}</div>",
                unsafe_allow_html=True)
    col_country, col_class, _ = st.columns([1, 2, 2])
    with col_country:
        country = st.selectbox("Country", COUNTRIES + [ALL_COUNTRIES], key="pod_slicer_country")
    with col_class:
        opts = classes(df)
        class_ = st.selectbox("Class", opts, index=opts.index(TOTAL), key="pod_slicer_class")

    df_wide = flow_wide(df, country, class_)
    year_cols = year_columns(df_wide)
    main_wide = window_wide(df_wide, MAIN_CROP_PERIODS)
    mid_wide = window_wide(df_wide, MID_CROP_PERIODS)
    ctx = f"{country} · {class_}"

    row1 = st.columns(2)
    with row1[0]:
        st.plotly_chart(monthly_comparison(df_wide, year_cols, title=f"{ctx} — Monthly Counts", height=PANEL_H), width="stretch")
    with row1[1]:
        cum_year_cols = [y for y in year_cols if y != "22/23"]                 # 22/23 dropped from this view by request
        st.plotly_chart(cumulative_forecast(df_wide, cum_year_cols, title=f"{ctx} — Cumulative Counts", height=PANEL_H), width="stretch")
    row2 = st.columns(2)
    with row2[0]:
        st.plotly_chart(cumulative_forecast(main_wide, year_cols, title=f"{ctx} — Main Crop Cumulative", height=PANEL_H), width="stretch")
    with row2[1]:
        st.plotly_chart(cumulative_forecast(mid_wide, year_cols, title=f"{ctx} — Mid Crop Cumulative", height=PANEL_H), width="stretch")

    _, ytd = ytd_period_window(df_wide, year_cols)
    st.markdown(seasonal_table_html(df_wide, year_cols, title=f"{class_} Pod Counts — {country}", unit="", kind="flow",
                                    ytd_label=ytd), unsafe_allow_html=True)
    _, ytd = ytd_period_window(main_wide, year_cols)
    st.markdown(seasonal_table_html(main_wide, year_cols, title=f"{class_} — Main Crop ({country})", unit="", kind="flow",
                                    ytd_label=ytd, full_label="Main Crop Total"), unsafe_allow_html=True)
    _, ytd = ytd_period_window(mid_wide, year_cols)
    st.markdown(seasonal_table_html(mid_wide, year_cols, title=f"{class_} — Mid Crop ({country})", unit="", kind="flow",
                                    ytd_label=ytd, full_label="Mid Crop Total"), unsafe_allow_html=True)


# ---------------------------------------------------------------------------------------------
# Entry Table - one row per survey month, one column per class
# ---------------------------------------------------------------------------------------------
def _raw_file() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def entry_months(raw: pd.DataFrame, country: str) -> list:
    """(year, month) rows, newest first: the month after the latest reported one (blank), then the latest reported ones."""
    real = raw[(raw.COUNTRY == country) & (raw.Year != LTA_YEAR)]
    ym = sorted({(int(y), int(m)) for y, m in zip(real.Year, real.Month)})
    y, m = ym[-1]
    nxt = (y + (m == 12), 1 if m == 12 else m + 1)
    return [nxt] + ym[::-1][:N_MONTHS - 1]


def entry_grid(raw: pd.DataFrame, country: str):
    months = entry_months(raw, country)
    sub = raw[raw.COUNTRY == country]
    rows = []
    for y, m in months:
        g = sub[(sub.Year == y) & (sub.Month == m)].groupby("CLASS")["NUMBER"].last()
        rows.append([g.get(c, np.nan) for c in ENTRY_CLASSES])
    grid = pd.DataFrame(rows, columns=ENTRY_CLASSES, index=[f"{MON[m - 1]}-{str(y)[2:]}" for y, m in months]).astype(float)
    return months, grid


def _as_text(grid: pd.DataFrame) -> pd.DataFrame:
    return grid.apply(lambda col: col.map(lambda v: "" if pd.isna(v) else f"{v:g}"))


def _to_number(typed: pd.DataFrame, orig: pd.DataFrame, bad: list) -> pd.DataFrame:
    out = orig.copy()
    for i in range(len(orig)):
        for c in ENTRY_CLASSES:
            txt = typed.iloc[i][c]
            txt = "" if txt is None or (isinstance(txt, float) and np.isnan(txt)) else str(txt).replace(",", "").strip()
            try:
                v = float(txt) if txt else np.nan
                if v < 0:
                    raise ValueError
            except ValueError:
                bad.append(f"{orig.index[i]} {SHORT[c]}: '{txt}' is not a valid number - kept the stored value.")
                v = orig.iloc[i][c]
            out.iloc[i, out.columns.get_loc(c)] = v
    return out


def _changes(months, orig, new) -> dict:
    """{(year, month, class): value or None} where the cell differs."""
    out = {}
    for i, (y, m) in enumerate(months):
        for c in ENTRY_CLASSES:
            a, b = orig.iloc[i][c], new.iloc[i][c]
            if not (pd.isna(a) and pd.isna(b)) and not (a == b):
                out[(y, m, c)] = None if pd.isna(b) else float(b)
    return out


def _notes(raw, country, months, new) -> list:
    """Same checks as the old validate_xlsx: Small = Small-1 + Small-2, TOTAL >= sum of classes, and extra-zero guard."""
    notes = []
    caps = raw[(raw.COUNTRY == country) & (raw.Year != LTA_YEAR)].groupby("CLASS")["NUMBER"].max()
    for i, (y, m) in enumerate(months):
        r, lab = new.iloc[i], new.index[i]
        if r[["2.1 Small-1", "2.2 Small-2", "2. Small"]].notna().all() and abs(r["2.1 Small-1"] + r["2.2 Small-2"] - r["2. Small"]) > 0.15:
            notes.append(f"{lab}: Small ({r['2. Small']:g}) is not Small-1 + Small-2 ({r['2.1 Small-1'] + r['2.2 Small-2']:g}).")
        atoms = r[ATOMIC_CLASSES]
        if pd.notna(r["TOTAL"]) and atoms.notna().any() and r["TOTAL"] + 0.5 < atoms.sum():
            notes.append(f"{lab}: TOTAL ({r['TOTAL']:g}) is below the sum of the classes ({atoms.sum():g}).")
        for c in ENTRY_CLASSES:
            cap = caps.get(c, np.nan)
            if pd.notna(r[c]) and pd.notna(cap) and cap > 0 and r[c] > 3 * cap:
                notes.append(f"{lab} {SHORT[c]}: {r[c]:g} is above 3x the highest on file ({cap:g}). Extra zero?")
    return notes


def _pod_csv(frame: pd.DataFrame) -> str:
    order = {c: i for i, c in enumerate(ENTRY_CLASSES)}
    frame = frame.assign(_c=frame.CLASS.map(order).fillna(99)).sort_values(["COUNTRY", "Year", "Month", "_c"]).drop(columns="_c")
    return frame[["Month", "Year", "NUMBER", "CLASS", "REGION", "COUNTRY"]].to_csv(index=False, lineterminator="\n")


def save_pod(country: str, changes: dict):
    msg = f"Pod counts {country}: " + "; ".join(
        f"{MON[m - 1]}-{y} {SHORT[c]} {'cleared' if v is None else f'{v:g}'}" for (y, m, c), v in changes.items())

    def change(text):
        frame = pd.read_csv(io.StringIO(text))
        for (y, m, c), v in changes.items():
            hit = (frame.COUNTRY == country) & (frame.Year == y) & (frame.Month == m) & (frame.CLASS == c)
            frame = frame[~hit]
            if v is not None:
                frame = pd.concat([frame, pd.DataFrame([{"Month": m, "Year": y, "NUMBER": v, "CLASS": c, "REGION": "ALL",
                                                         "COUNTRY": country}])], ignore_index=True)
        return _pod_csv(frame), None

    new_text, _ = gh.commit(POD_PATH, change, msg)
    DATA_PATH.write_text(new_text, encoding="utf-8", newline="")   # show it now, before Cloud redeploys
    load_raw.clear()


def render_entry():
    raw = _raw_file()
    top = st.columns([1.2, 6], vertical_alignment="center")
    with top[0]:
        country = st.radio("Country", COUNTRIES, horizontal=True, label_visibility="collapsed", key="pod_entry_country")
    months, orig = entry_grid(raw, country)
    ver = st.session_state.get("pod_ver", 0)
    with st.container(border=True):
        st.markdown(f"<div class='card-title'>Enter pod counts - {country}</div><div class='card-desc'>Blank = not surveyed. "
                    "Top row is the coming month.</div>", unsafe_allow_html=True)
        cfg = {"_index": st.column_config.Column("Month", width=78)}
        cfg.update({c: st.column_config.TextColumn(SHORT[c], width=74) for c in ENTRY_CLASSES})
        typed = st.data_editor(_as_text(orig), key=f"pod_ed_{country}_{ver}", width="content", row_height=26,
                               height=26 * (len(orig) + 1) + 16, column_config=cfg)
        bad = []
        new = _to_number(typed, orig, bad)
        changes = _changes(months, orig, new)
        for n in bad:
            st.error(n)
        notes = _notes(raw, country, months, new) if changes else []
        override = st.checkbox("Override warnings", key="pod_override") if notes else True
        for n in notes:
            st.warning(n)
        b = st.columns([1.3, 6])
        ok = projection.entry_enabled()
        if b[0].button("Save", type="primary", width="stretch", disabled=not (changes and override and ok), key="pod_save"):
            try:
                save_pod(country, changes)
            except gh.GitHubError as ex:
                st.error(str(ex))
            else:
                st.session_state["pod_ver"] = ver + 1
                st.rerun()
        if not ok:
            b[1].markdown("<div style='color:#c94a4a;font-size:12px;margin-top:8px'>Saving is off: add github_token in Streamlit Secrets "
                          "(without it nothing is stored).</div>", unsafe_allow_html=True)
        elif changes:
            b[1].markdown(f"<div class='card-desc' style='margin-top:8px'>{len(changes)} cell(s) changed, not saved yet.</div>",
                          unsafe_allow_html=True)
