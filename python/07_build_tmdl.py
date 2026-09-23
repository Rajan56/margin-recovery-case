"""
07_build_tmdl.py
----------------
Writes powerbi/model.tmdl: a TMDL script that creates the whole Power BI
semantic model (tables with Power Query sources, relationships, calculated
columns and measures). Paste it into Power BI Desktop > TMDL view > Apply.

Set DATA_DIR to the folder where the repository sits on your computer.
"""
from pathlib import Path
import csv

DATA_DIR = r"C:\Users\rajan\Documents\margin-recovery-case"
ROOT = Path(__file__).resolve().parent.parent

TABLES = {  # table name -> relative csv path
    "dim_date": "data/dim_date.csv", "dim_plant": "data/dim_plant.csv",
    "dim_segment": "data/dim_segment.csv", "dim_customer": "data/dim_customer.csv",
    "fact_fx": "data/fact_fx.csv", "fact_sales": "data/fact_sales.csv",
    "fact_plant_cost": "data/fact_plant_cost.csv",
    "bridge": "powerbi/outputs/out_ebitda_bridge.csv",
    "customer_profit": "powerbi/outputs/out_customer_profitability_2025.csv",
    "energy_weekly": "powerbi/outputs/out_energy_weekly.csv",
    "initiatives": "powerbi/outputs/out_initiatives.csv",
}
TEXT = {"month", "plant_id", "plant_name", "country", "currency", "segment_id", "segment_name",
        "customer_id", "customer_name", "tier", "contract_type", "quarter", "driver", "id", "name",
        "lever", "confidence", "time_to_value", "kpi", "how", "basis", "month_start"}
INT = {"year", "month_no", "orders", "deliveries", "order", "effort"}
DATE = {"week_start"}
BOOL = {"breach"}


def col_type(c):
    if c in TEXT: return "string", "type text"
    if c in INT: return "int64", "Int64.Type"
    if c in DATE: return "dateTime", "type date"
    if c in BOOL: return "boolean", "type logical"
    return "double", "type number"


CALC = {
    "fact_sales": [
        ("Rate24", 'LOOKUPVALUE ( fact_fx[sek_per_eur], fact_fx[month], "2024-" & RIGHT ( fact_sales[month], 2 ) )', "double"),
        ("Sales CC", 'IF ( fact_sales[currency] = "SEK", fact_sales[net_sales_local] / fact_sales[Rate24], fact_sales[net_sales_eur] )', "double"),
        ("CTS CC", 'IF ( fact_sales[currency] = "SEK", ( fact_sales[freight_local] + fact_sales[order_handling_local] ) / fact_sales[Rate24], fact_sales[freight_eur] + fact_sales[order_handling_eur] )', "double"),
    ],
    "fact_plant_cost": [
        ("Rate24", 'LOOKUPVALUE ( fact_fx[sek_per_eur], fact_fx[month], "2024-" & RIGHT ( fact_plant_cost[month], 2 ) )', "double"),
        ("Fixed CC", 'IF ( fact_plant_cost[currency] = "SEK", fact_plant_cost[fixed_cost_local] / fact_plant_cost[Rate24], fact_plant_cost[fixed_cost_eur] )', "double"),
    ],
}

EUR = r'\€#,0,,.0\m'
MEASURES = [
    ("Volume t", "SUM ( fact_sales[volume_t] )", "#,0"),
    ("Net Sales", "SUM ( fact_sales[net_sales_eur] )", EUR),
    ("Net Sales CC", "SUM ( fact_sales[Sales CC] )", EUR),
    ("Freight", "SUM ( fact_sales[freight_eur] )", EUR),
    ("Order Handling", "SUM ( fact_sales[order_handling_eur] )", EUR),
    ("Orders", "SUM ( fact_sales[orders] )", "#,0"),
    ("Fibre Cost", "SUM ( fact_plant_cost[fibre_cost_eur] )", EUR),
    ("Energy Cost", "SUM ( fact_plant_cost[energy_cost_eur] )", EUR),
    ("Other Variable Cost", "SUM ( fact_plant_cost[other_variable_eur] )", EUR),
    ("Fixed Cost", "SUM ( fact_plant_cost[fixed_cost_eur] )", EUR),
    ("Energy MWh", "SUM ( fact_plant_cost[energy_mwh] )", "#,0"),
    ("Board Consumed t", "SUM ( fact_plant_cost[board_consumed_t] )", "#,0"),
    ("Cost to Serve", "[Freight] + [Order Handling]", EUR),
    ("EBITDA", "[Net Sales] - [Fibre Cost] - [Energy Cost] - [Other Variable Cost] - [Cost to Serve] - [Fixed Cost]", EUR),
    ("EBITDA Margin %", "DIVIDE ( [EBITDA], [Net Sales] )", "0.0%"),
    ("Price per t", "DIVIDE ( [Net Sales], [Volume t] )", "#,0"),
    ("Fibre per t", "DIVIDE ( [Fibre Cost], [Volume t] )", "#,0.0"),
    ("Energy per t", "DIVIDE ( [Energy Cost], [Volume t] )", "#,0.0"),
    ("Cost to Serve per t", "DIVIDE ( [Cost to Serve], [Volume t] )", "#,0.0"),
    ("Fixed per t", "DIVIDE ( [Fixed Cost], [Volume t] )", "#,0.0"),
    ("EBITDA per t", "DIVIDE ( [EBITDA], [Volume t] )", "#,0.0"),
    ("Board Usage t per t", "DIVIDE ( [Board Consumed t], [Volume t] )", "0.000"),
    ("Energy MWh per t", "DIVIDE ( [Energy MWh], [Volume t] )", "0.000"),
    ("Orders per 1000 t", "DIVIDE ( [Orders], [Volume t] ) * 1000", "#,0.0"),
    ("EBITDA FY2024", "CALCULATE ( [EBITDA], dim_date[year] = 2024 )", EUR),
    ("EBITDA FY2025", "CALCULATE ( [EBITDA], dim_date[year] = 2025 )", EUR),
    ("EBITDA Change", "[EBITDA FY2025] - [EBITDA FY2024]", EUR),
    ("Net Sales FY2025", "CALCULATE ( [Net Sales], dim_date[year] = 2025 )", EUR),
    ("EBITDA Margin FY2024", "CALCULATE ( [EBITDA Margin %], dim_date[year] = 2024 )", "0.0%"),
    ("EBITDA Margin FY2025", "CALCULATE ( [EBITDA Margin %], dim_date[year] = 2025 )", "0.0%"),
    ("Price Effect CC", "SUMX ( VALUES ( dim_customer[customer_id] ), VAR V25 = CALCULATE ( [Volume t], dim_date[year] = 2025 ) VAR V24 = CALCULATE ( [Volume t], dim_date[year] = 2024 ) VAR P25 = DIVIDE ( CALCULATE ( [Net Sales CC], dim_date[year] = 2025 ), V25 ) VAR P24 = DIVIDE ( CALCULATE ( [Net Sales CC], dim_date[year] = 2024 ), V24 ) RETURN V25 * ( P25 - P24 ) )", EUR),
    ("Cost to Serve Effect CC", "SUMX ( VALUES ( dim_customer[customer_id] ), VAR V25 = CALCULATE ( [Volume t], dim_date[year] = 2025 ) VAR V24 = CALCULATE ( [Volume t], dim_date[year] = 2024 ) VAR C25 = DIVIDE ( CALCULATE ( SUM ( fact_sales[CTS CC] ), dim_date[year] = 2025 ), V25 ) VAR C24 = DIVIDE ( CALCULATE ( SUM ( fact_sales[CTS CC] ), dim_date[year] = 2024 ), V24 ) RETURN - V25 * ( C25 - C24 ) )", EUR),
    ("Fibre Effect", "SUMX ( VALUES ( dim_plant[plant_id] ), VAR V25 = CALCULATE ( [Volume t], dim_date[year] = 2025 ) VAR R25 = CALCULATE ( [Fibre per t], dim_date[year] = 2025 ) VAR R24 = CALCULATE ( [Fibre per t], dim_date[year] = 2024 ) RETURN - V25 * ( R25 - R24 ) )", EUR),
    ("Fixed Cost Effect CC", "- ( CALCULATE ( SUM ( fact_plant_cost[Fixed CC] ), dim_date[year] = 2025 ) - CALCULATE ( [Fixed Cost], dim_date[year] = 2024 ) )", EUR),
    ("Bridge Value", "SUM ( bridge[value_eur_m] )", "#,0.00"),
    ("Customer EBITDA", "SUM ( customer_profit[ebitda] )", EUR),
    ("Customer EBITDA Margin", "DIVIDE ( SUM ( customer_profit[ebitda] ), SUM ( customer_profit[sales] ) )", "0.0%"),
    ("Customer Cost to Serve per t", "DIVIDE ( SUM ( customer_profit[cost_to_serve] ), SUM ( customer_profit[vol] ) )", "#,0"),
    ("Loss-making Customers", "CALCULATE ( DISTINCTCOUNT ( customer_profit[customer_id] ), customer_profit[ebitda] < 0 )", "#,0"),
    ("Customers", "DISTINCTCOUNT ( customer_profit[customer_id] )", "#,0"),
    ("Cumulative EBITDA %", "VAR ThisEbitda = SELECTEDVALUE ( customer_profit[ebitda] ) VAR Cum = CALCULATE ( SUM ( customer_profit[ebitda] ), FILTER ( ALL ( customer_profit ), customer_profit[ebitda] >= ThisEbitda ) ) RETURN DIVIDE ( Cum, CALCULATE ( SUM ( customer_profit[ebitda] ), ALL ( customer_profit ) ) )", "0.0%"),
    ("Energy Intensity", "AVERAGE ( energy_weekly[intensity] )", "0.000"),
    ("Energy Baseline", "AVERAGE ( energy_weekly[baseline] )", "0.000"),
    ("Weeks in Alert", "CALCULATE ( COUNTROWS ( energy_weekly ), energy_weekly[dev_4w] > 0.06 )", "#,0"),
    ("Initiative Value", "SUM ( initiatives[value] )", "#,0.00"),
]

RELS = [
    ("fact_sales", "month", "dim_date", "month"), ("fact_sales", "customer_id", "dim_customer", "customer_id"),
    ("fact_sales", "segment_id", "dim_segment", "segment_id"), ("fact_sales", "plant_id", "dim_plant", "plant_id"),
    ("fact_plant_cost", "month", "dim_date", "month"), ("fact_plant_cost", "plant_id", "dim_plant", "plant_id"),
    ("customer_profit", "customer_id", "dim_customer", "customer_id"),
    ("energy_weekly", "plant_id", "dim_plant", "plant_id"),
]


def q(name):  # quote TMDL object names with spaces or symbols
    return name if name.replace("_", "").isalnum() else "'" + name.replace("'", "''") + "'"


T1, T2, T3, T4, T5 = "\t", "\t" * 2, "\t" * 3, "\t" * 4, "\t" * 5
out = ["createOrReplace", ""]
for t, rel in TABLES.items():
    with open(ROOT / rel, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    out.append(f"{T1}table {t}")
    out.append("")
    for c in header:
        dt, _ = col_type(c)
        out += [f"{T2}column {q(c)}", f"{T3}dataType: {dt}", f"{T3}sourceColumn: {c}", ""]
    for name, expr, dt in CALC.get(t, []):
        out += [f"{T2}column {q(name)} = {expr}", f"{T3}dataType: {dt}", ""]
    types = ", ".join('{"%s", %s}' % (c, col_type(c)[1]) for c in header)
    path = DATA_DIR + "\\" + rel.replace("/", "\\")
    out += [f"{T2}partition {t} = m", f"{T3}mode: import", f"{T3}source =",
            f"{T5}let",
            f'{T5}    Source = Csv.Document(File.Contents("{path}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
            f"{T5}    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
            f'{T5}    Typed = Table.TransformColumnTypes(Promoted, {{{types}}}, "en-US")',
            f"{T5}in",
            f"{T5}    Typed", ""]

out += [f"{T1}table _Measures", ""]
for name, expr, fmt in MEASURES:
    out += [f"{T2}measure {q(name)} = {expr}", f"{T3}formatString: {fmt}", ""]
out += [f"{T2}column Dummy", f"{T3}dataType: string", f"{T3}isHidden", f"{T3}sourceColumn: Dummy", "",
        f"{T2}partition _Measures = m", f"{T3}mode: import", f"{T3}source =",
        f"{T5}let", f'{T5}    Source = #table(type table [Dummy = text], {{}})', f"{T5}in", f"{T5}    Source", ""]

for i, (ft, fc, tt, tc) in enumerate(RELS, 1):
    out += [f"{T1}relationship rel_{ft}_{tt}", f"{T2}fromColumn: {ft}.{fc}", f"{T2}toColumn: {tt}.{tc}", ""]

(ROOT / "powerbi" / "model.tmdl").write_text("\n".join(out), encoding="utf-8")
print("powerbi/model.tmdl written,", len(out), "lines")
