from pathlib import Path

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "Database" / "pod_counts.csv"   # edited from the Entry Table

MONTH_ORDER = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]  # crop year: Apr -> Mar
MONTH_NAMES = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
               7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
PERIOD_ORDER = [MONTH_NAMES[m] for m in MONTH_ORDER]
MAIN_CROP_PERIODS = [MONTH_NAMES[m] for m in [4, 5, 6, 7, 8, 9]]   # Apr-Sep
MID_CROP_PERIODS = [MONTH_NAMES[m] for m in [10, 11, 12, 1, 2, 3]]  # Oct-Mar

LTA_YEAR = 1950
LTA_LABEL = "LTA"

TOTAL = "TOTAL"                       # Class value meaning "all classes combined"
SETTINGS_LABEL = "Settings"           # derived class: 1. Tiny + 2.1 Small-1
ATOMIC_CLASSES = ["1. Tiny", "2.1 Small-1", "2.2 Small-2", "3. Large",
                  "4. Mature", "5. Ripe", "6. Insect", "7. Forced", "8. Damaged", "9. Black"]

ALL_COUNTRIES = "All"                 # Country value meaning "GH + IVC combined"
COUNTRIES = ["GH", "IVC"]


def _crop_label_and_start(year, month):
    if year == LTA_YEAR:
        return LTA_LABEL, -1
    start = year if month >= 4 else year - 1
    return f"{str(start)[2:]}/{str(start + 1)[2:]}", start


@st.cache_data
def load_raw():
    df = pd.read_csv(DATA_PATH)
    labels_starts = df.apply(lambda r: _crop_label_and_start(int(r["Year"]), int(r["Month"])), axis=1)
    df["CropYear"] = labels_starts.apply(lambda t: t[0])
    df["CropStart"] = labels_starts.apply(lambda t: t[1])
    df["Period"] = df["Month"].map(MONTH_NAMES)
    return df


def classes(df, include_total=True, include_settings=True):
    """All selectable CLASS options — Settings and TOTAL first (most used),
    then the atomic growth-stage classes in their natural survey order."""
    order = []
    if include_settings:
        order = order + [SETTINGS_LABEL]
    if include_total:
        order = order + [TOTAL]
    order = order + ["1. Tiny", "2.1 Small-1", "2.2 Small-2", "2. Small", "3. Large",
                      "4. Mature", "5. Ripe", "6. Insect", "7. Forced", "8. Damaged", "9. Black"]
    return order


def _crop_year_order(df):
    return (df[["CropStart", "CropYear"]]
            .drop_duplicates()
            .sort_values("CropStart")["CropYear"]
            .tolist())


def _class_rows(df, country_mask, class_):
    """Rows matching a (possibly derived) class for an already-built country mask."""
    if class_ == SETTINGS_LABEL:
        return df[country_mask & df["CLASS"].isin(["1. Tiny", "2.1 Small-1"])]
    return df[country_mask & (df["CLASS"] == class_)]


def _country_mask(df, country):
    if country == ALL_COUNTRIES:
        return df["COUNTRY"].isin(COUNTRIES)
    return df["COUNTRY"] == country


def _pivot(df, country, class_):
    """Period rows (Apr..Mar), CropYear columns (LTA first, then ascending) —
    the wide shape all the chart/table helpers expect."""
    country_mask = _country_mask(df, country)
    sub = _class_rows(df, country_mask, class_)
    pivot = sub.pivot_table(index="Period", columns="CropYear", values="NUMBER", aggfunc="sum")
    pivot = pivot.reindex(PERIOD_ORDER)
    full_years = _crop_year_order(df)
    pivot = pivot.reindex(columns=full_years).reset_index()
    return pivot


def year_columns(df_wide):
    return [c for c in df_wide.columns if c != "Period"]


def window_wide(df_wide, periods):
    """Slice a full Apr..Mar wide table down to a sub-window (Main or Mid
    crop) — row order is preserved since df_wide is already Apr..Mar ordered.
    Reusable directly with all the existing chart/table helpers."""
    return df_wide[df_wide["Period"].isin(periods)].reset_index(drop=True)


def flow_wide(df, country, class_):
    return _pivot(df, country, class_)


def ytd_period_window(df_wide, year_cols):
    """Periods (Apr, Apr-May, ...) actually reported so far for the latest crop
    year — so every crop year's 'YTD' figure covers the same apples-to-apples
    span instead of summing a full season for old years against a few months
    for the current one. Returns (periods, label)."""
    periods = df_wide["Period"].tolist()
    real = [y for y in year_cols if y != LTA_LABEL]
    current_year = real[-1]
    last_valid = df_wide[current_year].last_valid_index()
    n = 0 if last_valid is None else last_valid + 1
    included = periods[:n] or periods[:1]
    span = included[0] if len(included) == 1 else f"{included[0]}-{included[-1]}"
    return included, f"YTD ({span})"


