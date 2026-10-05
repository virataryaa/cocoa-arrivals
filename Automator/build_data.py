"""Database/Mannual.xlsx -> Database/weekly.csv + Database/monthly.csv (the files the dashboard reads).

Mannual.xlsx is the hand-kept desk workbook (gitignored, often locked by Excel -> it is copied first).
Sheets: Weekly (IVC weekly arrivals, crop year Oct-Sep), IVC Monthly / Ghana Monthly (Forestero Stat + Tree).
"""
import shutil
import tempfile
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parent.parent / "Database"
SRC = DB / "Mannual.xlsx"

tmp = Path(tempfile.gettempdir()) / "cocoa_arrivals_src.xlsx"
shutil.copy(SRC, tmp)

# Weekly: header has two columns both called "Eikon (25/26)" -> read by position.
w = pd.read_excel(tmp, sheet_name="Weekly", header=0)
w.columns = ["week", "eikon_raw_2526", "eikon_adj_2526", "etg_2425", "etg_2526"]
w = w.apply(pd.to_numeric, errors="coerce")             # '#N/A' -> NaN
w = w.dropna(subset=["week"]).astype({"week": int})
w.to_csv(DB / "weekly.csv", index=False)

# Monthly: wide (one column per crop year) -> long
rows = []
for sheet, origin in [("IVC Monthly", "IVC"), ("Ghana Monthly", "Ghana")]:
    m = pd.read_excel(tmp, sheet_name=sheet)
    long = m.melt(id_vars=["Month", "Type"], var_name="crop_year", value_name="kt").dropna(subset=["kt"])
    long.insert(0, "origin", origin)
    rows.append(long.rename(columns={"Month": "month", "Type": "type"}))
pd.concat(rows).to_csv(DB / "monthly.csv", index=False)

# IVC Projection: Abidjan (cols B-G) and San Pedro (cols I-N), Monday-Saturday tonnes per week. Only the raw days are
# kept - the Total / Combined columns in the sheet are projections pasted as values, the dashboard recomputes them.
pr = pd.read_excel(tmp, sheet_name="IVC Projection", header=None, skiprows=2)
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
parts = []
for port, c0 in [("Abidjan", 1), ("San Pedro", 8)]:
    p_ = pr.iloc[:, [0] + list(range(c0, c0 + 6))].copy()
    p_.columns = ["week"] + DAYS
    p_["week"] = pd.to_datetime(p_["week"], errors="coerce")
    p_.insert(0, "port", port)
    parts.append(p_.dropna(subset=["week"]))
pd.concat(parts).to_csv(DB / "ivc_projection.csv", index=False, date_format="%Y-%m-%d")

print(f"weekly.csv: {len(w)} rows | monthly.csv: {sum(len(r) for r in rows)} rows")
