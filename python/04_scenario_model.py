"""
04_scenario_model.py
--------------------
FY2026 EBITDA scenario model for the Northfold Packaging case (fictional).
The same logic runs live in the browser (index.html, step 5); this file is
the auditable version, plus a one-at-a-time sensitivity table.

Run:  python 04_scenario_model.py
"""
import json
from dataclasses import dataclass, replace
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
res = json.loads((DATA / "case_results.json").read_text())
B = res["scenario_base"]
INIT = {i["id"]: i for i in res["initiatives"]}

# Share of each initiative's full-year value that lands inside FY2026
IN_YEAR = {"I1": 0.5, "I2": 0.6, "I3": 0.9, "I4": 0.4, "I5": 0.25, "I6": 0.0}


@dataclass(frozen=True)
class Levers:
    price_pct: float = 0.0        # price change vs FY2025, local currency
    volume_pct: float = 1.5       # volume change vs FY2025
    board_eur_t: float = round(B["board_price"])   # containerboard cost, EUR/t (rounded as on the page slider)
    energy_pct: float = 0.0       # energy price change
    cts_pct: float = 2.0          # freight and order-handling rate change
    sek_per_eur: float = round(B["fx_2025"], 2)
    fixed_pct: float = 3.0        # fixed cost inflation
    initiatives: tuple = ()       # e.g. ("I1", "I3")


def ebitda(l: Levers) -> dict:
    v, p = 1 + l.volume_pct / 100, 1 + l.price_pct / 100
    fx = l.sek_per_eur
    sales = (B["sales_eur"] + B["sales_sek_local"] / fx) * p * v
    fibre = B["board_t"] * v * l.board_eur_t
    energy = (B["energy_eur"] + B["energy_sek_local"] / fx) * (1 + l.energy_pct / 100) * v
    cts = (B["cts_eur"] + B["cts_sek_local"] / fx) * (1 + l.cts_pct / 100) * v
    other = B["other_var_eur"] * v
    fixed = (B["fixed_eur"] + B["fixed_sek_local"] / fx) * (1 + l.fixed_pct / 100)
    uplift = sum(INIT[i]["value"] * 1e6 * IN_YEAR[i] for i in l.initiatives)
    e = sales - fibre - energy - cts - other - fixed + uplift
    return {"sales_m": sales / 1e6, "ebitda_m": e / 1e6, "margin_pct": e / sales * 100,
            "initiatives_m": uplift / 1e6}


if __name__ == "__main__":
    base = Levers()
    b = ebitda(base)
    print(f"FY2026 base case: sales {b['sales_m']:.1f}  EBITDA {b['ebitda_m']:.1f}  margin {b['margin_pct']:.1f}%")
    full = ebitda(replace(base, initiatives=tuple(INIT)))
    print(f"With all initiatives (in-year share): EBITDA {full['ebitda_m']:.1f}  margin {full['margin_pct']:.1f}%")

    print("\nSensitivity, one lever at a time (EUR m EBITDA vs base):")
    tests = [("Price +1%", dict(price_pct=1.0)),
             ("Volume +1%", dict(volume_pct=base.volume_pct + 1)),
             ("Containerboard +10 EUR/t", dict(board_eur_t=base.board_eur_t + 10)),
             ("Energy price +10%", dict(energy_pct=10.0)),
             ("Cost-to-serve rates +5%", dict(cts_pct=base.cts_pct + 5)),
             ("SEK weaker by 0.30 per EUR", dict(sek_per_eur=base.sek_per_eur + 0.30)),
             ("Fixed cost inflation +1 pt", dict(fixed_pct=base.fixed_pct + 1))]
    for label, kw in tests:
        d = ebitda(replace(base, **kw))["ebitda_m"] - b["ebitda_m"]
        print(f"  {label:30s} {d:+6.2f}")
