"""
08_build_pbir.py
----------------
Writes the Power BI report pages (PBIR format) for the Margin Recovery Case:
five pages of visuals bound to the semantic model built by 07_build_tmdl.py.
Output: build/pbir/definition/pages/...   (copied into <name>.Report/definition/)
"""
import json
import secrets
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "build" / "pbir" / "definition"
VIS_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
PAGES_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"


def nid():
    return secrets.token_hex(10)


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def col(e, p):
    return {"Column": {"Expression": {"SourceRef": {"Entity": e}}, "Property": p}}


def meas(e, p):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": e}}, "Property": p}}


def agg(e, p, fn):  # fn 0 = Sum, 1 = Average
    return {"Aggregation": {"Expression": col(e, p), "Function": fn}}


def proj(field):
    if "Measure" in field:
        e, p = field["Measure"]["Expression"]["SourceRef"]["Entity"], field["Measure"]["Property"]
        return {"field": field, "queryRef": f"{e}.{p}", "nativeQueryRef": p}
    if "Column" in field:
        e, p = field["Column"]["Expression"]["SourceRef"]["Entity"], field["Column"]["Property"]
        return {"field": field, "queryRef": f"{e}.{p}", "nativeQueryRef": p}
    c = field["Aggregation"]["Expression"]["Column"]
    e, p = c["Expression"]["SourceRef"]["Entity"], c["Property"]
    fn = {0: "Sum", 1: "Average"}[field["Aggregation"]["Function"]]
    return {"field": field, "queryRef": f"{fn}({e}.{p})", "nativeQueryRef": f"{fn} of {p}"}


def visual(vtype, x, y, w, h, roles, title=None, sort=None, objects=None, z=0):
    v = {"visualType": vtype, "query": {"queryState": {r: {"projections": [proj(f) for f in fs]}
                                                       for r, fs in roles.items()}}}
    if sort:
        field, direction = sort
        v["query"]["sortDefinition"] = {"sort": [{"field": field, "direction": direction}]}
    if objects:
        v["objects"] = objects
    if title:
        v["visualContainerObjects"] = {"title": [{"properties": {
            "show": lit("true"), "text": lit("'" + title.replace("'", "''") + "'")}}]}
    v["drillFilterOtherVisuals"] = True
    return {"$schema": VIS_SCHEMA, "name": nid(),
            "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z}, "visual": v}


def textbox(x, y, w, h, title, subtitle, z=0):
    paras = [{"textRuns": [{"value": title, "textStyle": {"fontWeight": "bold", "fontSize": "20pt"}}]},
             {"textRuns": [{"value": subtitle, "textStyle": {"fontSize": "11pt", "color": "#605E5C"}}]}]
    return {"$schema": VIS_SCHEMA, "name": nid(),
            "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z},
            "visual": {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": paras}}]},
                       "drillFilterOtherVisuals": True}}


M = lambda p: meas("_Measures", p)
SUB = "Northfold Packaging (fictional company, synthetic data)  |  Rajan Kumar V K  |  Margin Recovery Case"

pages = []

# ------------------------------------------------------------ 1 Executive summary
v = [
    textbox(30, 15, 1860, 80, "Executive summary: sales grew, EBITDA fell by a quarter", SUB, 0),
    visual("cardVisual", 30, 105, 1860, 170, {"Data": [M("Net Sales FY2025"), M("EBITDA FY2024"), M("EBITDA FY2025"),
                                                       M("EBITDA Change"), M("EBITDA Margin FY2025")]}, z=1),
    visual("lineChart", 30, 295, 1130, 360, {"Category": [col("dim_date", "month")], "Y": [M("EBITDA Margin %")]},
           "EBITDA margin by month", sort=(col("dim_date", "month"), "Ascending"), z=2),
    visual("clusteredColumnChart", 1180, 295, 710, 360,
           {"Category": [col("dim_plant", "plant_name")], "Series": [col("dim_date", "year")], "Y": [M("EBITDA per t")]},
           "EBITDA per tonne by plant (EUR)", z=3),
    visual("clusteredBarChart", 30, 675, 1130, 380,
           {"Category": [col("dim_customer", "contract_type")], "Series": [col("dim_date", "year")], "Y": [M("Price per t")]},
           "Price per tonne by contract type (EUR): fixed contracts lost price, indexed ones gained", z=4),
    visual("clusteredColumnChart", 1180, 675, 710, 380,
           {"Category": [col("dim_date", "year")], "Y": [M("Fibre per t"), M("Energy per t"), M("Cost to Serve per t")]},
           "Unit costs per tonne (EUR)", z=5),
]
# reuse the ids Power BI Desktop already created, so the saved page is overwritten in place
v[1]["name"] = "3b1e43665c55c304ae54"
v[2]["name"] = "8b0985cec70a868e6809"
pages.append(("Executive summary", v))

# ------------------------------------------------------------ 2 EBITDA bridge
v = [
    textbox(30, 15, 1860, 80, "EBITDA bridge FY2024 to FY2025 (EUR m)", SUB, 0),
    visual("waterfallChart", 30, 105, 1250, 700, {"Category": [col("bridge", "driver")], "Y": [M("Bridge Value")]},
           "Change in EBITDA by driver (EUR m), reconciles to the reported change",
           sort=(col("bridge", "driver"), "Ascending"), z=1),
    visual("cardVisual", 1300, 105, 590, 330, {"Data": [M("EBITDA FY2024"), M("EBITDA FY2025"), M("EBITDA Change")]}, z=2),
    visual("cardVisual", 1300, 455, 590, 350, {"Data": [M("Price Effect CC"), M("Fibre Effect"),
                                                        M("Cost to Serve Effect CC"), M("Fixed Cost Effect CC")]},
           "DAX check: bridge drivers recomputed in the model", z=3),
    visual("tableEx", 30, 825, 1860, 230, {"Values": [col("dim_customer", "contract_type"), M("Volume t"),
                                                      M("Price per t"), M("Price Effect CC")]},
           "Price effect by contract type (FY2025 vs FY2024, constant currency)", z=4),
]
pages.append(("EBITDA bridge", v))

# ------------------------------------------------------------ 3 Customer profitability
v = [
    textbox(30, 15, 1860, 80, "Customer profitability after cost-to-serve (FY2025)", SUB, 0),
    visual("scatterChart", 30, 105, 1150, 620,
           {"Category": [col("customer_profit", "customer_id")], "Series": [col("customer_profit", "tier")],
            "X": [agg("customer_profit", "avg_order_t", 1)], "Y": [agg("customer_profit", "margin", 1)]},
           "Average order size (t) vs EBITDA margin, per customer", z=1),
    visual("cardVisual", 1200, 105, 690, 300, {"Data": [M("Customers"), M("Loss-making Customers"), M("Customer EBITDA")]}, z=2),
    visual("clusteredBarChart", 1200, 425, 690, 300,
           {"Category": [col("customer_profit", "tier")], "Y": [M("Customer Cost to Serve per t")]},
           "Cost-to-serve per tonne by tier (EUR)", z=3),
    visual("tableEx", 30, 745, 1860, 310,
           {"Values": [col("customer_profit", "tier"), M("Customers"), M("Loss-making Customers"),
                       M("Customer Cost to Serve per t"), M("Customer EBITDA"), M("Customer EBITDA Margin")]},
           "Profitability by customer tier", z=4),
]
pages.append(("Customer profitability", v))

# ------------------------------------------------------------ 4 Energy
v = [
    textbox(30, 15, 1860, 80, "Energy intensity vs seasonal baseline (MWh per tonne, weekly)", SUB, 0),
    visual("slicer", 30, 105, 330, 420, {"Values": [col("dim_plant", "plant_name")]}, "Plant", z=1),
    visual("lineChart", 380, 105, 1510, 700,
           {"Category": [col("energy_weekly", "week_start")], "Y": [M("Energy Intensity"), M("Energy Baseline")]},
           "Actual vs FY2024 seasonal baseline", sort=(col("energy_weekly", "week_start"), "Ascending"), z=2),
    visual("cardVisual", 30, 545, 330, 260, {"Data": [M("Weeks in Alert")]}, "Weeks above +6% (4-week avg)", z=3),
    visual("tableEx", 30, 825, 1860, 230,
           {"Values": [col("dim_plant", "plant_name"), M("Energy Intensity"), M("Energy Baseline"), M("Weeks in Alert")]},
           "Summary by plant", z=4),
]
pages.append(("Energy", v))

# ------------------------------------------------------------ 5 Initiatives
v = [
    textbox(30, 15, 1860, 80, "Improvement initiatives: value vs effort", SUB, 0),
    visual("scatterChart", 30, 105, 900, 620,
           {"Category": [col("initiatives", "name")], "X": [agg("initiatives", "effort", 1)],
            "Y": [agg("initiatives", "value", 0)]},
           "Full-year value (EUR m) vs effort (1 to 5)", z=1),
    visual("cardVisual", 950, 105, 940, 200, {"Data": [M("Initiative Value")]}, "Total full-year value (EUR m)", z=2),
    visual("tableEx", 30, 745, 1860, 310,
           {"Values": [col("initiatives", "id"), col("initiatives", "name"), col("initiatives", "lever"),
                       agg("initiatives", "value", 0), col("initiatives", "confidence"),
                       col("initiatives", "time_to_value"), col("initiatives", "kpi")]},
           "Initiative register", z=3),
    visual("clusteredBarChart", 950, 325, 940, 400,
           {"Category": [col("initiatives", "name")], "Y": [agg("initiatives", "value", 0)]},
           "Value by initiative (EUR m)", z=4),
]
pages.append(("Initiatives", v))

# -------------------------------------------------------------------- write
import shutil
if OUT.exists():
    shutil.rmtree(OUT)
order = []
for i, (name, visuals) in enumerate(pages, 1):
    pid = "cd44c8031b082191447c" if i == 1 else nid()
    order.append(pid)
    pdir = OUT / "pages" / pid
    (pdir / "visuals").mkdir(parents=True)
    (pdir / "page.json").write_text(json.dumps({"$schema": PAGE_SCHEMA, "name": pid,
                                                "displayName": f"{i} {name}", "displayOption": "FitToPage",
                                                "height": 1080, "width": 1920}, indent=2))
    for vis in visuals:
        vdir = pdir / "visuals" / vis["name"]
        vdir.mkdir()
        (vdir / "visual.json").write_text(json.dumps(vis, indent=2))
(OUT / "pages" / "pages.json").write_text(json.dumps({"$schema": PAGES_SCHEMA, "pageOrder": order,
                                                      "activePageName": order[0]}, indent=2))
print("pages:", len(order), "visuals:", sum(len(v) for _, v in pages))
