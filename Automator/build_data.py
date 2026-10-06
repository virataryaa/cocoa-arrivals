"""Database/Mannual.xlsx -> Database/weekly.csv (history of the Weekly sheet; the dashboard reads it).

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

# Weekly: columns are Week Number, Eikon (24/25), Eikon (25/26), ETG (24/25), ETG (25/26) -> read by position.
w = pd.read_excel(tmp, sheet_name="Weekly", header=0)
w.columns = ["week", "eikon_2425", "eikon_2526", "etg_2425", "etg_2526"]
w = w.apply(pd.to_numeric, errors="coerce")             # '#N/A' -> NaN
w = w.dropna(subset=["week"]).astype({"week": int})
w.to_csv(DB / "weekly.csv", index=False)

# NOTE: Database/monthly.csv is NOT built here any more - the dashboard (Forestero : Monthly > Edit) owns it.

# NOTE: Database/ivc_projection.csv is NOT built here any more. The dashboard (This week tab) owns it - entries are saved
# straight into that file - so re-running this script must never overwrite it from the old "IVC Projection" sheet.

print(f"weekly.csv: {len(w)} rows")
