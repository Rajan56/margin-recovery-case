"""
01_generate_data.py
-------------------
Generates the synthetic dataset for the Northfold Packaging case.

Northfold Packaging is a FICTIONAL Nordic corrugated packaging business unit.
Every number produced here is synthetic. The market conditions built into the
data (flat sales, softer prices, tight fibre supply, rising energy and freight
costs, a weaker SEK) mirror publicly discussed conditions in the Nordic
packaging industry, but no company's internal data is used or implied.

Output: star-schema CSV files in ../data
    dim_plant.csv, dim_segment.csv, dim_customer.csv, dim_date.csv,
    fact_sales.csv          (customer x segment x month)
    fact_plant_cost.csv     (plant x month: fibre, energy, other variable, fixed)
    fact_energy_week.csv    (plant x week: production and energy use)
    fact_fx.csv             (month: SEK per EUR)

Run:  python 01_generate_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260929)
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

YEARS = [2024, 2025]
MONTHS = pd.period_range("2024-01", "2025-12", freq="M")

# ---------------------------------------------------------------- dimensions
plants = pd.DataFrame(
    [
        # id, name, country, currency, base MWh per tonne, board usage t/t
        ("P1", "Finland South", "FI", "EUR", 0.44, 1.100),
        ("P2", "Finland West", "FI", "EUR", 0.46, 1.105),
        ("P3", "Sweden Central", "SE", "SEK", 0.45, 1.100),
        ("P4", "Sweden South", "SE", "SEK", 0.47, 1.108),
        ("P5", "Baltics", "LV", "EUR", 0.48, 1.135),  # higher trim waste
    ],
    columns=["plant_id", "plant_name", "country", "currency",
             "base_mwh_per_t", "board_usage_t_per_t"],
)
plant_weight = np.array([0.27, 0.19, 0.23, 0.19, 0.12])

segments = pd.DataFrame(
    [
        # id, name, list price EUR/t 2024, other variable EUR/t, 2025 volume growth
        ("S1", "E-commerce", 1010, 48, 0.085),
        ("S2", "Fresh produce", 985, 46, -0.020),
        ("S3", "Industrial", 905, 40, 0.035),
        ("S4", "Retail-ready", 1240, 78, 0.000),
        ("S5", "Heavy-duty", 1150, 52, -0.030),
    ],
    columns=["segment_id", "segment_name", "list_price_eur_t",
             "other_var_eur_t", "growth_2025"],
)
seg_weight = np.array([0.30, 0.20, 0.27, 0.13, 0.10])

# FX: SEK per EUR (fictional path, SEK weaker in 2025)
fx = pd.DataFrame({"month": MONTHS.astype(str)})
fx["sek_per_eur"] = np.where(
    fx["month"].str.startswith("2024"),
    11.43 + RNG.normal(0, 0.04, len(fx)),
    11.88 + RNG.normal(0, 0.05, len(fx)),
).round(4)
fx_map = dict(zip(fx["month"], fx["sek_per_eur"]))

# Customers: 15 key accounts, 30 mid-size, 35 small
tiers = [("Key", 15, 19000, 20.0, 45.0),
         ("Mid", 30, 4800, 14.0, 16.0),
         ("Small", 35, 1350, 4.2, 5.5)]
rows = []
cid = 1
for tier, n, avg_vol, t_per_delivery, t_per_order in tiers:
    for _ in range(n):
        plant = RNG.choice(plants["plant_id"], p=plant_weight)
        seg = RNG.choice(segments["segment_id"], p=seg_weight)
        if tier == "Key":
            contract = "Fixed annual" if RNG.random() < 0.62 else "Indexed"
            premium = RNG.normal(-0.035, 0.015)       # volume discount
        elif tier == "Mid":
            contract = "Fixed annual" if RNG.random() < 0.40 else "Indexed"
            premium = RNG.normal(0.01, 0.02)
        else:
            contract = "List price"
            premium = RNG.normal(0.07, 0.025)
        complexity = RNG.choice([1.0, 1.3, 1.7],
                                p=[0.55, 0.30, 0.15] if tier != "Small" else [0.25, 0.40, 0.35])
        rows.append(dict(
            customer_id=f"C{cid:03d}",
            customer_name=f"Customer {cid:03d}",
            tier=tier,
            contract_type=contract,
            plant_id=plant,
            segment_id=seg,
            annual_volume_2024_t=max(300, RNG.lognormal(np.log(avg_vol), 0.35)),
            price_premium=round(float(premium), 4),
            t_per_delivery=max(2.5, RNG.normal(t_per_delivery, t_per_delivery * 0.12)),
            t_per_order=max(2.0, RNG.normal(t_per_order, t_per_order * 0.15)),
            print_complexity=complexity,
        ))
        cid += 1
customers = pd.DataFrame(rows)

# ------------------------------------------------------------ price & cost paths
seasonality = np.array([0.95, 0.96, 1.02, 1.00, 1.02, 0.98,
                        0.86, 0.95, 1.05, 1.07, 1.08, 1.02])
seasonality = seasonality / seasonality.mean()


def price_change_2025(contract: str) -> float:
    """Local-currency price change in 2025 versus 2024 by contract type."""
    return {"Fixed annual": -0.034,  # renegotiated down in a soft market, no index
            "Indexed": 0.016,        # follows the containerboard index
            "List price": 0.022}[contract]


board_price = {2024: 520.0, 2025: 533.0}          # EUR per tonne of containerboard
energy_price = {("FI", 2024): 68.0, ("FI", 2025): 76.0,   # EUR/MWh
                ("LV", 2024): 74.0, ("LV", 2025): 81.0,
                ("SE", 2024): 760.0, ("SE", 2025): 845.0}  # SEK/MWh
freight_per_delivery = {("EUR", 2024): 385.0, ("EUR", 2025): 404.0,
                        ("SEK", 2024): 4400.0, ("SEK", 2025): 4620.0}
cost_per_order = {("EUR", 2024): 880.0, ("EUR", 2025): 905.0,   # changeover, set-up waste, planning
                  ("SEK", 2024): 10050.0, ("SEK", 2025): 10350.0}
fixed_eur_per_t_2024 = {"P1": 135.0, "P2": 150.0, "P3": 138.0, "P4": 150.0, "P5": 145.0}  # personnel, maintenance, overhead
fixed_inflation_2025 = 0.031

# ------------------------------------------------------------------ fact_sales
sales = []
for _, c in customers.iterrows():
    seg = segments.set_index("segment_id").loc[c.segment_id]
    plant = plants.set_index("plant_id").loc[c.plant_id]
    growth = seg.growth_2025 + RNG.normal(0, 0.05)
    if c.tier == "Small":
        growth += 0.02
    for m in MONTHS:
        y, mo = m.year, m.month
        vol = c.annual_volume_2024_t / 12 * seasonality[mo - 1]
        if y == 2025:
            vol *= 1 + growth
        vol *= RNG.normal(1, 0.06)
        vol = max(vol, 5.0)

        base_eur = seg.list_price_eur_t * (1 + c.price_premium)
        if y == 2025:
            base_eur *= 1 + price_change_2025(c.contract_type)
        base_eur *= RNG.normal(1, 0.004)
        ccy = plant.currency
        month = str(m)
        if ccy == "SEK":
            price_local = base_eur * 11.43     # SEK list prices set on 2024 rate
            rate = fx_map[month]
        else:
            price_local = base_eur
            rate = 1.0
        gross_local = price_local * vol
        deliveries = max(1, round(vol / c.t_per_delivery))
        orders = max(1, round(vol / c.t_per_order * c.print_complexity))
        freight_local = deliveries * freight_per_delivery[(ccy, y)]
        order_cost_local = orders * cost_per_order[(ccy, y)]
        sales.append(dict(
            month=month, customer_id=c.customer_id, segment_id=c.segment_id,
            plant_id=c.plant_id, currency=ccy, volume_t=round(vol, 2),
            net_sales_local=round(gross_local, 2),
            net_sales_eur=round(gross_local / rate, 2),
            orders=orders, deliveries=deliveries,
            freight_local=round(freight_local, 2),
            freight_eur=round(freight_local / rate, 2),
            order_handling_local=round(order_cost_local, 2),
            order_handling_eur=round(order_cost_local / rate, 2),
        ))
fact_sales = pd.DataFrame(sales)

# ------------------------------------------------------------ fact_energy_week
# Weekly production is split from monthly plant volume; weekly energy intensity
# carries seasonality, noise and ONE planted anomaly: from April 2025 Sweden
# Central drifts ~17% above its normal intensity (think failing steam traps or
# a compressed-air leak) and nobody notices in monthly reporting.
plant_month_vol = fact_sales.groupby(["plant_id", "month"])["volume_t"].sum()
weeks = pd.date_range("2024-01-01", "2025-12-29", freq="W-MON")
energy_rows = []
for pid, p in plants.set_index("plant_id").iterrows():
    for w in weeks:
        month = str(w.to_period("M"))
        n_weeks = sum(1 for x in weeks if str(x.to_period("M")) == month)
        prod = plant_month_vol[(pid, month)] / n_weeks * RNG.normal(1, 0.035)
        winter = 1 + 0.06 * np.cos((w.dayofyear - 15) / 365 * 2 * np.pi)
        intensity = p.base_mwh_per_t * winter * RNG.normal(1, 0.018)
        if pid == "P3" and w >= pd.Timestamp("2025-04-07"):
            ramp = min(1.0, (w - pd.Timestamp("2025-04-07")).days / 35)
            intensity *= 1 + 0.17 * ramp
        energy_rows.append(dict(week_start=w.date().isoformat(), month=month,
                                plant_id=pid, production_t=round(prod, 2),
                                energy_mwh=round(prod * intensity, 2)))
fact_energy_week = pd.DataFrame(energy_rows)

# ------------------------------------------------------------- fact_plant_cost
cost_rows = []
e_month = fact_energy_week.groupby(["plant_id", "month"])[["production_t", "energy_mwh"]].sum()
for pid, p in plants.set_index("plant_id").iterrows():
    for m in MONTHS:
        month, y = str(m), m.year
        vol = plant_month_vol[(pid, month)]
        rate = fx_map[month] if p.currency == "SEK" else 1.0
        # fibre: board bought in EUR, usage includes trim waste
        board_t = vol * p.board_usage_t_per_t * RNG.normal(1, 0.004)
        board_eur = board_t * board_price[y] * RNG.normal(1, 0.01)
        # energy: scale weekly intensity to the monthly sold volume
        ew = e_month.loc[(pid, month)]
        mwh = vol * ew.energy_mwh / ew.production_t
        e_price_local = energy_price[(p.country, y)] * RNG.normal(1, 0.03)
        energy_local = mwh * e_price_local
        # other variable (inks, starch, glue) from the segment mix
        mix = fact_sales[(fact_sales.plant_id == pid) & (fact_sales.month == month)]
        other_eur = (mix.merge(segments, on="segment_id")
                     .eval("volume_t * other_var_eur_t").sum()) * (1.02 if y == 2025 else 1.0)
        vol_2024 = plant_month_vol[pid][[str(x) for x in MONTHS if x.year == 2024]].sum()
        fixed_local = vol_2024 / 12 * fixed_eur_per_t_2024[pid] * (11.43 if p.currency == "SEK" else 1.0)
        fixed_local *= (1 + fixed_inflation_2025) if y == 2025 else 1.0
        fixed_local *= RNG.normal(1, 0.02)
        cost_rows.append(dict(
            month=month, plant_id=pid, currency=p.currency,
            board_consumed_t=round(board_t, 2), fibre_cost_eur=round(board_eur, 2),
            energy_mwh=round(mwh, 2), energy_cost_local=round(energy_local, 2),
            energy_cost_eur=round(energy_local / rate, 2),
            other_variable_eur=round(other_eur, 2),
            fixed_cost_local=round(fixed_local, 2),
            fixed_cost_eur=round(fixed_local / rate, 2),
        ))
fact_plant_cost = pd.DataFrame(cost_rows)

# ----------------------------------------------------------------- dim_date
dim_date = pd.DataFrame({"month": MONTHS.astype(str)})
dim_date["year"] = MONTHS.year
dim_date["quarter"] = "Q" + MONTHS.quarter.astype(str)
dim_date["month_no"] = MONTHS.month
dim_date["month_start"] = MONTHS.to_timestamp().date

# -------------------------------------------------------------------- write
customers["annual_volume_2024_t"] = customers["annual_volume_2024_t"].round(0)
customers["t_per_delivery"] = customers["t_per_delivery"].round(1)
customers["t_per_order"] = customers["t_per_order"].round(1)
for name, df in {
    "dim_plant": plants, "dim_segment": segments.drop(columns="growth_2025"),
    "dim_customer": customers, "dim_date": dim_date, "fact_fx": fx,
    "fact_sales": fact_sales, "fact_plant_cost": fact_plant_cost,
    "fact_energy_week": fact_energy_week,
}.items():
    df.to_csv(OUT / f"{name}.csv", index=False)
    print(f"{name:18s} {len(df):6d} rows")
