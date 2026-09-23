"""
02_analysis.py
--------------
The analyst's workbench for the Northfold Packaging case (fictional company,
synthetic data). Answers one question:

    "Sales grew, yet EBITDA fell by a quarter. Why, and what do we do?"

Steps
    1. P&L summary FY2024 vs FY2025
    2. EBITDA bridge: volume, mix, price, FX, fibre, energy, cost-to-serve,
       other variable, fixed costs  (reconciles to the cent)
    3. Price effect split by contract type
    4. Customer profitability after cost-to-serve, including the whale curve
    5. Energy intensity anomaly detection (weekly, per plant)
    6. Board yield (trim waste) gap by plant
    7. Improvement initiatives with value, effort and confidence
    8. Base figures for the 2026 scenario simulator

Output: ../data/case_results.json  (read by index.html and the AI agent script)
Run:    python 02_analysis.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

sales = pd.read_csv(DATA / "fact_sales.csv")
cost = pd.read_csv(DATA / "fact_plant_cost.csv")
energy = pd.read_csv(DATA / "fact_energy_week.csv", parse_dates=["week_start"])
fx = pd.read_csv(DATA / "fact_fx.csv")
cust = pd.read_csv(DATA / "dim_customer.csv")
seg = pd.read_csv(DATA / "dim_segment.csv")
plant = pd.read_csv(DATA / "dim_plant.csv")

for df in (sales, cost, fx):
    df["year"] = df["month"].str[:4].astype(int)
fx_map = dict(zip(fx["month"], fx["sek_per_eur"]))
FX24 = fx[fx.year == 2024]["sek_per_eur"].mean()   # average 2024 rate for constant-currency views
m = 1e6


def r(x, n=2):
    return float(round(x, n))


# ------------------------------------------------------------ 1. P&L summary
def pnl(year: int) -> dict:
    s = sales[sales.year == year]
    c = cost[cost.year == year]
    out = dict(
        volume_t=s.volume_t.sum(),
        net_sales=s.net_sales_eur.sum(),
        fibre=c.fibre_cost_eur.sum(),
        energy=c.energy_cost_eur.sum(),
        other_variable=c.other_variable_eur.sum(),
        freight=s.freight_eur.sum(),
        order_handling=s.order_handling_eur.sum(),
        fixed=c.fixed_cost_eur.sum(),
    )
    out["ebitda"] = out["net_sales"] - sum(out[k] for k in
                                            ["fibre", "energy", "other_variable",
                                             "freight", "order_handling", "fixed"])
    out["ebitda_margin"] = out["ebitda"] / out["net_sales"]
    return out


P = {y: pnl(y) for y in (2024, 2025)}

# ------------------------------------------------------------ 2. EBITDA bridge
# Everything below is built at customer level, then summed.
# Constant-currency (CC) values restate 2025 SEK items at the matching 2024 monthly rate.


def to_cc(df, eur_col, local_col):
    """Restate SEK values at the same month's 2024 rate (2024 itself stays as reported)."""
    rate24 = df["month"].str[5:].map(lambda mo: fx_map[f"2024-{mo}"])
    return np.where(df["currency"] == "SEK", df[local_col] / rate24, df[eur_col])


sales["sales_cc"] = to_cc(sales, "net_sales_eur", "net_sales_local")
sales["freight_cc"] = to_cc(sales, "freight_eur", "freight_local")
sales["oh_cc"] = to_cc(sales, "order_handling_eur", "order_handling_local")
cost["energy_cc"] = to_cc(cost, "energy_cost_eur", "energy_cost_local")
cost["fixed_cc"] = to_cc(cost, "fixed_cost_eur", "fixed_cost_local")

# Plant-level variable cost rates per tonne (fibre and energy)
pv = sales.groupby(["plant_id", "year"]).volume_t.sum().rename("plant_vol")
pc = cost.groupby(["plant_id", "year"])[["fibre_cost_eur", "energy_cost_eur",
                                         "energy_cc", "other_variable_eur"]].sum().join(pv)
pc["fibre_t"] = pc.fibre_cost_eur / pc.plant_vol
pc["energy_t"] = pc.energy_cost_eur / pc.plant_vol
pc["energy_cc_t"] = pc.energy_cc / pc.plant_vol

# Other variable cost: allocate plant totals to customers by segment standard rate
sales = sales.merge(seg[["segment_id", "other_var_eur_t"]], on="segment_id")
sales["ov_std"] = sales.volume_t * sales.other_var_eur_t
ov_scale = (cost.groupby(["plant_id", "year"]).other_variable_eur.sum()
            / sales.groupby(["plant_id", "year"]).ov_std.sum()).rename("ov_scale")
sales = sales.merge(ov_scale.reset_index(), on=["plant_id", "year"])
sales["other_var"] = sales.ov_std * sales.ov_scale

sales = sales.merge(pc[["fibre_t", "energy_t", "energy_cc_t"]].reset_index(),
                    on=["plant_id", "year"])
sales["fibre"] = sales.volume_t * sales.fibre_t
sales["energy"] = sales.volume_t * sales.energy_t
sales["energy_cc"] = sales.volume_t * sales.energy_cc_t

cy = sales.groupby(["customer_id", "year"]).agg(
    vol=("volume_t", "sum"), sales_cc=("sales_cc", "sum"), sales=("net_sales_eur", "sum"),
    fibre=("fibre", "sum"), energy_cc=("energy_cc", "sum"), energy=("energy", "sum"),
    other_var=("other_var", "sum"), freight_cc=("freight_cc", "sum"),
    freight=("freight_eur", "sum"), oh_cc=("oh_cc", "sum"), oh=("order_handling_eur", "sum"),
).unstack("year")


def per_t(col, y):
    return cy[(col, y)] / cy[("vol", y)]


V24, V25 = cy[("vol", 2024)], cy[("vol", 2025)]
ucm24 = (per_t("sales_cc", 2024) - per_t("fibre", 2024) - per_t("energy_cc", 2024)
         - per_t("other_var", 2024) - per_t("freight_cc", 2024) - per_t("oh_cc", 2024))
ucm24_avg = (V24 * ucm24).sum() / V24.sum()

fixed24 = cost[cost.year == 2024].fixed_cost_eur.sum()
fixed25_cc = cost[cost.year == 2025].fixed_cc.sum()

ebitda25_cc = (cy[("sales_cc", 2025)].sum() - cy[("fibre", 2025)].sum()
               - cy[("energy_cc", 2025)].sum() - cy[("other_var", 2025)].sum()
               - cy[("freight_cc", 2025)].sum() - cy[("oh_cc", 2025)].sum() - fixed25_cc)

bridge = {
    "Volume": (V25.sum() - V24.sum()) * ucm24_avg,
    "Mix": (V25 * ucm24).sum() - V25.sum() * ucm24_avg,
    "Price": (V25 * (per_t("sales_cc", 2025) - per_t("sales_cc", 2024))).sum(),
    "Fibre cost": -(V25 * (per_t("fibre", 2025) - per_t("fibre", 2024))).sum(),
    "Energy cost": -(V25 * (per_t("energy_cc", 2025) - per_t("energy_cc", 2024))).sum(),
    "Cost-to-serve": -(V25 * (per_t("freight_cc", 2025) - per_t("freight_cc", 2024)
                              + per_t("oh_cc", 2025) - per_t("oh_cc", 2024))).sum(),
    "Other variable": -(V25 * (per_t("other_var", 2025) - per_t("other_var", 2024))).sum(),
    "Fixed costs": -(fixed25_cc - fixed24),
    "FX (SEK)": P[2025]["ebitda"] - ebitda25_cc,
}
bridge_total = sum(bridge.values())
recon_gap = bridge_total - (P[2025]["ebitda"] - P[2024]["ebitda"])
assert abs(recon_gap) < 1, f"Bridge does not reconcile: {recon_gap}"

# ------------------------------------------------ 3. price effect by contract
cinfo = cust.set_index("customer_id")
price_c = V25 * (per_t("sales_cc", 2025) - per_t("sales_cc", 2024))
price_by_contract = price_c.groupby(cinfo.contract_type).sum()
vol_by_contract = V25.groupby(cinfo.contract_type).sum()
price_chg_by_contract = (cy[("sales_cc", 2025)].groupby(cinfo.contract_type).sum()
                         / vol_by_contract
                         / (cy[("sales_cc", 2024)].groupby(cinfo.contract_type).sum()
                            / V24.groupby(cinfo.contract_type).sum()) - 1)

# ------------------------------------ 4. customer profitability (FY2025, EUR)
cp = pd.DataFrame({
    "sales": cy[("sales", 2025)], "vol": V25,
    "fibre": cy[("fibre", 2025)], "energy": cy[("energy", 2025)],
    "other_var": cy[("other_var", 2025)], "freight": cy[("freight", 2025)],
    "order_handling": cy[("oh", 2025)],
})
cp["contribution_before_cts"] = cp.sales - cp.fibre - cp.energy - cp.other_var
cp["cost_to_serve"] = cp.freight + cp.order_handling
cp["contribution_after_cts"] = cp.contribution_before_cts - cp.cost_to_serve
fixed25 = cost[cost.year == 2025].fixed_cost_eur.sum()
cp["fixed_alloc"] = fixed25 * cp.vol / cp.vol.sum()          # volume-driven allocation
cp["ebitda"] = cp.contribution_after_cts - cp.fixed_alloc
cp = cp.join(cinfo[["tier", "contract_type", "plant_id", "segment_id",
                    "t_per_order", "t_per_delivery", "print_complexity"]])
cp["margin"] = cp.ebitda / cp.sales
cp["cts_per_t"] = cp.cost_to_serve / cp.vol
cp["avg_order_t"] = cp.vol / sales[sales.year == 2025].groupby("customer_id").orders.sum()

assert abs(cp.ebitda.sum() - P[2025]["ebitda"]) < 1

loss = cp[cp.contribution_after_cts < 0]
neg_ebitda = cp[cp.ebitda < 0]
whale = cp.sort_values("ebitda", ascending=False)
whale_curve = (whale.ebitda.cumsum() / cp.ebitda.sum() * 100).round(1).tolist()

tier_summary = cp.groupby("tier").agg(
    customers=("sales", "size"), volume_t=("vol", "sum"), sales=("sales", "sum"),
    cts_per_t=("cost_to_serve", "sum"), ebitda=("ebitda", "sum"))
tier_summary["cts_per_t"] = tier_summary.cts_per_t / tier_summary.volume_t
tier_summary["margin"] = tier_summary.ebitda / tier_summary.sales

# ------------------------------------------------ 5. energy anomaly detection
e = energy.copy()
e["intensity"] = e.energy_mwh / e.production_t
e["woy"] = (e.week_start.dt.dayofyear - 1) // 7 + 1        # week-of-year, same rule as the SQL
e["yr"] = e.week_start.dt.year
base = (e[e.yr == 2024].groupby(["plant_id", "woy"]).intensity.mean()
        .groupby(level=0).transform(lambda s: s.rolling(5, center=True, min_periods=1).mean())
        .rename("baseline"))
e = e.merge(base.reset_index(), on=["plant_id", "woy"], how="left")
e["dev"] = e.intensity / e.baseline - 1
e["dev_4w"] = e.groupby("plant_id").dev.transform(lambda s: s.rolling(4, min_periods=4).mean())
# Rule: 4-week rolling deviation above +6% for 3 consecutive weeks => alert
e["breach"] = e.dev_4w > 0.06
e["run"] = e.groupby("plant_id").breach.transform(
    lambda s: s.groupby((~s).cumsum()).cumcount())
alerts = e[(e.run >= 3) & (e.yr == 2025)].groupby("plant_id").week_start.min()

p3 = e[(e.plant_id == "P3") & (e.yr == 2025)].copy()
p3["excess_mwh"] = (p3.energy_mwh - p3.production_t * p3.baseline).clip(lower=0)
p3["month"] = p3.week_start.dt.to_period("M").astype(str)
p3_price_eur = (cost[(cost.plant_id == "P3") & (cost.year == 2025)]
                .eval("energy_cost_eur / energy_mwh").mean())
anomaly_start = pd.Timestamp("2025-04-07")
excess_mwh_2025 = p3[p3.week_start >= anomaly_start].excess_mwh.sum()
excess_cost_2025 = excess_mwh_2025 * p3_price_eur
weeks_affected = int((p3.week_start >= anomaly_start).sum())
excess_cost_annual = excess_cost_2025 / weeks_affected * 52
alert_week = alerts.get("P3")
# the same drift in a monthly report: first month where plant MWh/t is +6% vs prior-year month
cm = cost.merge(sales.groupby(["plant_id", "month"]).volume_t.sum().reset_index(),
                on=["plant_id", "month"])
cm["mwh_t"] = cm.energy_mwh / cm.volume_t
cm["mo"] = cm.month.str[5:]
mm = cm.pivot_table(index=["plant_id", "mo"], columns="year", values="mwh_t")
mm["yoy"] = mm[2025] / mm[2024] - 1

energy_series = {}
for pid in plant.plant_id:
    s = e[e.plant_id == pid].sort_values("week_start")
    energy_series[pid] = {
        "weeks": s.week_start.dt.strftime("%Y-%m-%d").tolist(),
        "intensity": s.intensity.round(4).tolist(),
        "baseline": s.baseline.round(4).tolist(),
    }

# Emission factors (tCO2 per MWh) are illustrative, for the sustainability KPI only
EF = {"FI": 0.11, "SE": 0.04, "LV": 0.30}
co2 = []
for _, p in plant.iterrows():
    for y in (2024, 2025):
        c = cost[(cost.plant_id == p.plant_id) & (cost.year == y)]
        v = sales[(sales.plant_id == p.plant_id) & (sales.year == y)].volume_t.sum()
        co2.append(dict(plant_id=p.plant_id, year=y,
                        kg_co2_per_t=r(c.energy_mwh.sum() * EF[p.country] * 1000 / v, 1)))
excess_co2_t = excess_mwh_2025 * EF["SE"]

# ------------------------------------------------------ 6. board yield (trim)
yld = (cost[cost.year == 2025].groupby("plant_id")[["board_consumed_t", "fibre_cost_eur"]].sum()
       .join(sales[sales.year == 2025].groupby("plant_id").volume_t.sum()))
yld["usage"] = yld.board_consumed_t / yld.volume_t
best_usage = yld.usage.min()
board_price_25 = yld.fibre_cost_eur.sum() / yld.board_consumed_t.sum()
yld["gap_value"] = (yld.usage - best_usage) * yld.volume_t * board_price_25

# ------------------------------------------------------------- 7. initiatives
plant_names_short = dict(zip(plant.plant_id, plant.plant_name))
fixed_c = cp[cp.contract_type == "Fixed annual"]
fixed_gap = (price_chg_by_contract["Indexed"] - price_chg_by_contract["Fixed annual"]) \
    * fixed_c.sales.sum()
init = [
    dict(id="I1", name="Index clauses in fixed-price contracts",
         lever="Price", value=0.40 * fixed_gap / m, effort=2, confidence="Medium",
         time_to_value="At contract renewal, 3 to 12 months",
         kpi="Price realisation vs containerboard index (EUR/t)",
         how="Link price to a published containerboard index at renewal; commercial team owns, controlling tracks realisation monthly.",
         basis=f"40% capture of the {price_chg_by_contract['Indexed']*100:.1f}% vs {price_chg_by_contract['Fixed annual']*100:.1f}% price gap between indexed and fixed contracts"),
    dict(id="I2", name="Cost-to-serve pricing and order rules",
         lever="Cost-to-serve", value=0.5 * -loss.contribution_after_cts.sum() / m
         + 0.25 * -(neg_ebitda.ebitda.sum() - loss.contribution_after_cts.sum()) / m,
         effort=2, confidence="Medium",
         time_to_value="1 to 2 quarters",
         kpi="Cost-to-serve per tonne; share of loss-making customers",
         how="Minimum order quantities, small-drop surcharges and consolidated delivery days for accounts below break-even.",
         basis=f"Recover half of the negative contribution of {len(loss)} accounts and a quarter of the remaining EBITDA loss on {len(neg_ebitda)} accounts"),
    dict(id="I3", name="Energy anomaly alerting",
         lever="Energy", value=excess_cost_annual / m, effort=1, confidence="High",
         time_to_value="Weeks",
         kpi="MWh per tonne vs seasonal baseline, per plant per week",
         how="Weekly rule on meter data flags drift early; maintenance fixes root cause at Sweden Central.",
         basis=f"Excess energy at Sweden Central annualised from {weeks_affected} affected weeks"),
    dict(id="I4", name="Trim-waste reduction at three plants",
         lever="Fibre", value=0.5 * yld.gap_value.sum() / m, effort=3, confidence="Medium",
         time_to_value="2 to 3 quarters",
         kpi="Board usage, t of board per t sold",
         how="Order combination and trim optimisation on the corrugator; close half of the gap to the best plant.",
         basis="Half of the gap to best-plant board usage ("
               + ", ".join(f"{plant_names_short[i]} {x:.3f}" for i, x in yld.usage.items() if x - best_usage > 0.004)
               + f" vs best {best_usage:.3f} t/t)"),
    dict(id="I5", name="Demand sensing for production planning",
         lever="Cost-to-serve", value=0.04 * P[2025]["order_handling"] / m, effort=4,
         confidence="Low", time_to_value="3 to 4 quarters, after a pilot",
         kpi="Changeovers per 1,000 t; forecast accuracy (MAPE)",
         how="Machine-learning forecast feeds sequencing to cut changeovers; prove it in one plant first.",
         basis="4% lower order-handling and changeover cost, to be proven in a pilot"),
    dict(id="I6", name="AI agent for month-end variance commentary",
         lever="Productivity", value=0.0, effort=2, confidence="High",
         time_to_value="4 to 6 weeks",
         kpi="Controller hours on commentary; days to close",
         how="Agent drafts variance commentary from the bridge; controllers review and sign. Frees about 1,100 hours a year for analysis.",
         basis="6 controllers × 16 h per month, 95% of the drafting effort removed; value is capacity, not EBITDA"),
]
for i in init:
    i["value"] = r(i["value"], 2)

# --------------------------------------------------------- 8. scenario base
s25 = sales[sales.year == 2025]
c25 = cost[cost.year == 2025]
sek = s25.currency == "SEK"
csek = c25.currency == "SEK"
scenario_base = dict(
    fx_2025=r(fx[fx.year == 2025].sek_per_eur.mean(), 4),
    fx_2024=r(FX24, 4),
    volume_t=r(s25.volume_t.sum(), 0),
    sales_eur=r(s25[~sek].net_sales_eur.sum(), 0),
    sales_sek_local=r(s25[sek].net_sales_local.sum(), 0),
    board_t=r(c25.board_consumed_t.sum(), 0),
    board_price=r(c25.fibre_cost_eur.sum() / c25.board_consumed_t.sum(), 2),
    energy_eur=r(c25[~csek].energy_cost_eur.sum(), 0),
    energy_sek_local=r(c25[csek].energy_cost_local.sum(), 0),
    energy_mwh=r(c25.energy_mwh.sum(), 0),
    cts_eur=r(s25[~sek][["freight_eur", "order_handling_eur"]].sum().sum(), 0),
    cts_sek_local=r(s25[sek][["freight_local", "order_handling_local"]].sum().sum(), 0),
    other_var_eur=r(c25.other_variable_eur.sum(), 0),
    fixed_eur=r(c25[~csek].fixed_cost_eur.sum(), 0),
    fixed_sek_local=r(c25[csek].fixed_cost_local.sum(), 0),
)

# ------------------------------------------------------------------ output
monthly = (sales.groupby("month").agg(sales=("net_sales_eur", "sum"), vol=("volume_t", "sum"))
           .join(cost.groupby("month")[["fibre_cost_eur", "energy_cost_eur",
                                        "other_variable_eur", "fixed_cost_eur"]].sum())
           .join(sales.groupby("month")[["freight_eur", "order_handling_eur"]].sum()))
monthly["ebitda"] = monthly.sales - monthly[["fibre_cost_eur", "energy_cost_eur",
                                             "other_variable_eur", "fixed_cost_eur",
                                             "freight_eur", "order_handling_eur"]].sum(axis=1)
monthly["margin"] = monthly.ebitda / monthly.sales

seg_names = dict(zip(seg.segment_id, seg.segment_name))
plant_names = dict(zip(plant.plant_id, plant.plant_name))

results = dict(
    meta=dict(company="Northfold Packaging (fictional)", currency="EUR",
              note="Synthetic data generated by 01_generate_data.py",
              fx_2024_avg=r(FX24, 4), fx_2025_avg=scenario_base["fx_2025"]),
    pnl={str(y): {k: r(v / m, 2) if k not in ("ebitda_margin", "volume_t") else
                  (r(v, 4) if k == "ebitda_margin" else r(v, 0))
                  for k, v in P[y].items()} for y in P},
    bridge=[dict(label=k, value=r(v / m, 2)) for k, v in bridge.items()],
    bridge_reconciliation_gap_eur=r(recon_gap, 4),
    price_by_contract=[dict(contract=k,
                            effect=r(price_by_contract[k] / m, 2),
                            price_change_pct=r(price_chg_by_contract[k] * 100, 2),
                            volume_share=r(vol_by_contract[k] / V25.sum() * 100, 1))
                       for k in price_by_contract.index],
    monthly=[dict(month=i, sales=r(x.sales / m, 2), ebitda=r(x.ebitda / m, 2),
                  margin=r(x.margin * 100, 2)) for i, x in monthly.iterrows()],
    customers=[dict(id=i, tier=x.tier, contract=x.contract_type,
                    plant=plant_names[x.plant_id], segment=seg_names[x.segment_id],
                    volume_t=r(x.vol, 0), sales=r(x.sales / m, 3),
                    cts_per_t=r(x.cts_per_t, 1), avg_order_t=r(x.avg_order_t, 1),
                    contribution_after_cts=r(x.contribution_after_cts / m, 3),
                    ebitda=r(x.ebitda / m, 3), margin=r(x.margin * 100, 1))
               for i, x in cp.sort_values("ebitda", ascending=False).iterrows()],
    whale_curve=whale_curve,
    tier_summary=[dict(tier=t, customers=int(x.customers), volume_share=r(x.volume_t / cp.vol.sum() * 100, 1),
                       cts_per_t=r(x.cts_per_t, 1), ebitda=r(x.ebitda / m, 2),
                       margin=r(x.margin * 100, 1)) for t, x in tier_summary.iterrows()],
    cts_findings=dict(
        loss_after_cts_count=int(len(loss)),
        loss_after_cts_value=r(loss.contribution_after_cts.sum() / m, 2),
        loss_after_cts_volume_share=r(loss.vol.sum() / cp.vol.sum() * 100, 1),
        negative_ebitda_count=int(len(neg_ebitda)),
        negative_ebitda_value=r(neg_ebitda.ebitda.sum() / m, 2),
        negative_ebitda_volume_share=r(neg_ebitda.vol.sum() / cp.vol.sum() * 100, 1),
        peak_whale_pct=r(max(whale_curve), 1),
        negative_by_tier={t: int(n) for t, n in neg_ebitda.tier.value_counts().items()},
        small_order_negative=f"{int(((cp.avg_order_t < 6) & (cp.ebitda < 0)).sum())} of {int((cp.avg_order_t < 6).sum())}",
    ),
    ops=dict(
        orders_per_kt_2025=r(sales[sales.year == 2025].orders.sum() / sales[sales.year == 2025].volume_t.sum() * 1000, 1),
        commentary_hours_month=96,
    ),
    energy=dict(
        series=energy_series,
        alert_week_p3=alert_week.date().isoformat() if alert_week is not None else None,
        alerts_other_plants={k: v.date().isoformat() for k, v in alerts.items() if k != "P3"},
        anomaly_start="2025-04-07",
        monthly_yoy_p3={mo: r(v * 100, 1) for mo, v in mm.loc["P3"]["yoy"].items()},
        excess_mwh_2025=r(excess_mwh_2025, 0),
        excess_cost_2025=r(excess_cost_2025 / m, 3),
        excess_cost_annual=r(excess_cost_annual / m, 3),
        excess_co2_t=r(excess_co2_t, 0),
        co2=co2,
    ),
    yield_gap=[dict(plant=plant_names[i], usage=r(x.usage, 4),
                    gap_value=r(x.gap_value / m, 2)) for i, x in yld.iterrows()],
    initiatives=init,
    scenario_base=scenario_base,
    plants=[dict(id=p.plant_id, name=p.plant_name, country=p.country) for _, p in plant.iterrows()],
)
(DATA / "case_results.json").write_text(json.dumps(results, indent=1))

# Flat outputs for Power BI (heavy logic in Python/SQL, reporting in Power BI)
OUTP = DATA.parent / "powerbi" / "outputs"
OUTP.mkdir(parents=True, exist_ok=True)
pd.DataFrame([dict(order=i + 1, driver=k, value_eur_m=round(v / m, 3))
              for i, (k, v) in enumerate(bridge.items())]).to_csv(OUTP / "out_ebitda_bridge.csv", index=False)
(cp.reset_index().rename(columns={"index": "customer_id"})
   [["customer_id", "tier", "contract_type", "plant_id", "segment_id", "vol", "sales",
     "contribution_before_cts", "cost_to_serve", "contribution_after_cts", "fixed_alloc",
     "ebitda", "margin", "cts_per_t", "avg_order_t"]]
   .round(4).to_csv(OUTP / "out_customer_profitability_2025.csv", index=False))
(e[["week_start", "plant_id", "production_t", "energy_mwh", "intensity", "baseline", "dev", "dev_4w", "breach"]]
   .assign(week_start=lambda d: d.week_start.dt.date)
   .round(5).to_csv(OUTP / "out_energy_weekly.csv", index=False))
pd.DataFrame(init).to_csv(OUTP / "out_initiatives.csv", index=False)

# ------------------------------------------------------------ console report
print(f"FY2024 sales {P[2024]['net_sales']/m:7.1f}  EBITDA {P[2024]['ebitda']/m:6.1f}  margin {P[2024]['ebitda_margin']*100:.1f}%")
print(f"FY2025 sales {P[2025]['net_sales']/m:7.1f}  EBITDA {P[2025]['ebitda']/m:6.1f}  margin {P[2025]['ebitda_margin']*100:.1f}%")
print("\nEBITDA bridge (EUR m)")
for k, v in bridge.items():
    print(f"  {k:16s} {v/m:7.2f}")
print(f"  {'Total':16s} {bridge_total/m:7.2f}   (reconciliation gap {recon_gap:.4f} EUR)")
print("\nPrice by contract:", {k: (r(price_by_contract[k]/m), r(price_chg_by_contract[k]*100)) for k in price_by_contract.index})
print(f"\nAccounts negative after cost-to-serve: {len(loss)} ({loss.contribution_after_cts.sum()/m:.2f} m)")
print(f"Accounts with negative EBITDA: {len(neg_ebitda)} ({neg_ebitda.ebitda.sum()/m:.2f} m), whale peak {max(whale_curve)}%")
print(tier_summary.round(2))
print(f"\nEnergy alert P3 week: {alert_week}, other plants: {dict(alerts.drop('P3', errors='ignore'))}")
print("P3 monthly YoY MWh/t %:", {k: r(v*100, 1) for k, v in mm.loc['P3']['yoy'].items()})
print(f"Excess energy 2025: {excess_mwh_2025:.0f} MWh, EUR {excess_cost_2025/m:.3f} m, annualised {excess_cost_annual/m:.3f} m")
print("\nYield:", yld[["usage", "gap_value"]].round(3).to_dict())
print("\nInitiatives:")
for i in init:
    print(f"  {i['id']} {i['name'][:45]:45s} {i['value']:6.2f}  effort {i['effort']}")
