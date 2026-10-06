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


def get_crop_years(df, include_lta=False):
    years = _crop_year_order(df)
    return years if include_lta else [y for y in years if y != LTA_LABEL]


def compare_wide(df, country, classes_list, crop_year):
    """Period rows, one column per class, values for a single chosen crop
    year — used to overlay multiple classes on one chart."""
    out = pd.DataFrame({"Period": PERIOD_ORDER})
    for c in classes_list:
        w = _pivot(df, country, c).set_index("Period")
        out[c] = w[crop_year].reindex(PERIOD_ORDER).values if crop_year in w.columns else pd.NA
    return out


def class_mix(df, country, crop_years):
    """Total NUMBER per atomic class (Small-1/Small-2 shown separately, not
    the '2. Small' aggregate, to avoid double counting) summed across
    crop_years — feeds the pie chart and ranking bar."""
    rows = []
    for c in ATOMIC_CLASSES:
        w = _pivot(df, country, c)
        total = sum(w[y].sum(skipna=True) for y in crop_years if y in w.columns)
        if total > 0:
            rows.append((c, total))
    rows.sort(key=lambda p: p[1], reverse=True)
    return rows


def class_month_matrix(df, country, crop_years):
    """Class x Period matrix (Jul..Jun) summed across crop_years — feeds the heatmap."""
    country_mask = _country_mask(df, country)
    sub = df[country_mask & df["CropYear"].isin(crop_years) & df["CLASS"].isin(ATOMIC_CLASSES)]
    matrix = sub.pivot_table(index="CLASS", columns="Period", values="NUMBER", aggfunc="sum")
    matrix = matrix.reindex(columns=PERIOD_ORDER)
    matrix = matrix.loc[matrix.sum(axis=1, skipna=True).sort_values(ascending=False).index]
    return matrix


def long_run_series(df, country, class_):
    """Full chronological history, not windowed to a crop year."""
    country_mask = _country_mask(df, country)
    sub = _class_rows(df, country_mask, class_)
    sub = sub[sub["Year"] != LTA_YEAR]
    grouped = sub.groupby(["Year", "Month"], as_index=False)["NUMBER"].sum()
    grouped["Date"] = pd.to_datetime(dict(year=grouped["Year"], month=grouped["Month"], day=1))
    grouped = grouped.sort_values("Date")
    return grouped[["Date", "NUMBER"]]


def country_share_series(df, class_):
    """IVC's % share of GH+IVC combined NUMBER by crop year, for one class."""
    gh = _pivot(df, "GH", class_)
    ivc = _pivot(df, "IVC", class_)
    crop_years = [y for y in _crop_year_order(df) if y != LTA_LABEL]
    rows = []
    for y in crop_years:
        g = gh[y].sum(skipna=True) if y in gh.columns else 0.0
        i = ivc[y].sum(skipna=True) if y in ivc.columns else 0.0
        if g + i > 0:
            rows.append((y, i / (g + i) * 100))
    return rows


def monthly_country_mix(df, class_, crop_years=None):
    """Actual GH & IVC NUMBER per calendar month, plus IVC's % share of that
    same month — feeds the monthly country-mix chart."""
    country_mask = df["COUNTRY"].isin(COUNTRIES)
    sub = _class_rows(df, country_mask, class_)
    sub = sub[sub["Year"] != LTA_YEAR]
    if crop_years is not None:
        sub = sub[sub["CropYear"].isin(crop_years)]

    pivot = sub.pivot_table(index=["Year", "Month"], columns="COUNTRY", values="NUMBER", aggfunc="sum")
    pivot = pivot.reindex(columns=COUNTRIES).fillna(0.0).reset_index()
    pivot["Date"] = pd.to_datetime(dict(year=pivot["Year"], month=pivot["Month"], day=1))
    pivot = pivot.sort_values("Date")

    total = pivot["GH"] + pivot["IVC"]
    pivot["IVCSharePct"] = (pivot["IVC"] / total * 100).where(total > 0)
    return pivot[["Date", "GH", "IVC", "IVCSharePct"]]
