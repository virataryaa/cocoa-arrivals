"""One-off: seed Database/eikon_weekly.csv (week Monday, Eikon weekly total in tonnes) from the Weekly sheet history.

Crop-year week 1 = the Monday of the week containing 1 October (checked: the desk's ETG series equals Abidjan + San Pedro on
that calendar). From now on the dashboard (This week tab) owns eikon_weekly.csv - never re-run this over live data.
"""
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parent.parent / "Database"
OUT = DB / "eikon_weekly.csv"
if OUT.exists():
    raise SystemExit(f"{OUT.name} already exists - the dashboard owns it, not overwriting.")

w = pd.read_csv(DB / "weekly.csv")


def week1(start_year: int) -> pd.Timestamp:
    d = pd.Timestamp(start_year, 10, 1)
    return d - pd.Timedelta(days=d.weekday())


# The sheet follows the calendar except at the tail of each year, where its rows run one week late (checked against
# Abidjan + San Pedro: from these week numbers on, the sheet's ETG equals the NEXT calendar week). Eikon is on the same rows.
SHIFT_FROM = {2024: 48, 2025: 49}

rows = []
for col, year in [("eikon_2425", 2024), ("eikon_2526", 2025)]:
    for n, v in zip(w.week, w[col]):
        if pd.notna(v):
            k = int(n) - 1 + (1 if int(n) >= SHIFT_FROM[year] else 0)
            rows.append((week1(year) + pd.Timedelta(days=7 * k), round(v * 1000)))
out = pd.DataFrame(rows, columns=["week", "eikon"]).sort_values("week")
out["week"] = out["week"].dt.strftime("%Y-%m-%d")
out.to_csv(OUT, index=False, lineterminator="\n")
print(f"{len(out)} weeks, {out.week.min()} .. {out.week.max()}")
