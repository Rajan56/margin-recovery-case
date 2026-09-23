"""
03_validate_sql.py
------------------
Loads the CSVs into an in-memory SQLite database built from sql/01_schema.sql,
runs every SQL view and checks it against the Python results in
data/case_results.json. Two independent routes to the same numbers.

Run:  python 03_validate_sql.py
"""
import json
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SQL, DATA = ROOT / "sql", ROOT / "data"
res = json.loads((DATA / "case_results.json").read_text())

con = sqlite3.connect(":memory:")
con.executescript((SQL / "01_schema.sql").read_text())
for t in ["dim_plant", "dim_segment", "dim_customer", "dim_date", "fact_fx",
          "fact_sales", "fact_plant_cost", "fact_energy_week"]:
    pd.read_csv(DATA / f"{t}.csv").to_sql(t, con, if_exists="append", index=False)


def q(name):
    return pd.read_sql_query((SQL / name).read_text(), con)


ok = True


def check(label, a, b, tol=0.011):
    global ok
    good = abs(a - b) <= tol
    ok &= good
    print(f"  [{'OK' if good else 'FAIL'}] {label:34s} SQL {a:10.3f}   Python {b:10.3f}")


print("P&L")
pnl = q("02_pnl_by_year.sql").set_index("year")
for y in (2024, 2025):
    check(f"EBITDA {y} (EUR m)", pnl.loc[y, "ebitda_m"], res["pnl"][str(y)]["ebitda"])
    check(f"Net sales {y} (EUR m)", pnl.loc[y, "net_sales_m"], res["pnl"][str(y)]["net_sales"])

print("EBITDA bridge")
br = q("03_ebitda_bridge.sql").set_index("driver")["value_m"]
for row in res["bridge"]:
    check(row["label"], br[row["label"]], row["value"])
check("Bridge total = EBITDA change", br.sum(),
      res["pnl"]["2025"]["ebitda"] - res["pnl"]["2024"]["ebitda"], tol=0.05)

print("Customer profitability")
cp = q("04_customer_profitability.sql")
py = {c["id"]: c for c in res["customers"]}
worst = max(abs(r.ebitda_m - py[r.customer_id]["ebitda"]) for r in cp.itertuples())
check("Max customer EBITDA difference", worst, 0.0, tol=0.002)
check("Customers with negative EBITDA", float((cp.ebitda_m < 0).sum()),
      float(res["cts_findings"]["negative_ebitda_count"]), tol=0)
check("Whale curve peak (%)", cp.cumulative_ebitda_pct.max(), res["cts_findings"]["peak_whale_pct"], tol=0.11)

print("Energy anomaly")
en = q("05_energy_anomaly.sql")
print(en.to_string(index=False))
sql_p3 = en.set_index("plant_id").loc["P3", "first_alert_week"]
match = sql_p3 == res["energy"]["alert_week_p3"]
ok &= match and len(en) == 1
print(f"  [{'OK' if match else 'FAIL'}] First alert week Sweden Central    SQL {sql_p3}   Python {res['energy']['alert_week_p3']}")

print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED")
raise SystemExit(0 if ok else 1)
