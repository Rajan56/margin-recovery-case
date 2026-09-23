# Power BI build guide

A step-by-step guide to building the Northfold Packaging report in Power BI Desktop (free). Budget about 2 to 3 hours. When you're done, save screenshots into `docs/img/` and link them from the README.

## 1. Load the data

**Home → Get data → Text/CSV.** Load every file in `data/` except `case_results.json`:

| Table | Grain |
|---|---|
| `fact_sales` | customer × month |
| `fact_plant_cost` | plant × month |
| `fact_energy_week` | plant × week |
| `fact_fx` | month |
| `dim_customer`, `dim_segment`, `dim_plant`, `dim_date` | one row per key |

Then load the files in `powerbi/outputs/` and rename them as follows:

- `out_customer_profitability_2025` → `customer_profit`
- `out_energy_weekly` → `energy_weekly`
- `out_ebitda_bridge` → `bridge`
- `out_initiatives` → `initiatives`

Before you close Power Query, check the column types:

- `month` stays **Text** (YYYY-MM)
- `week_start` becomes **Date**
- Money and tonne columns become **Decimal number**

## 2. Relationships (Model view)

All relationships are one-to-many with single-direction filtering.

| From (many) | To (one) |
|---|---|
| `fact_sales[month]` | `dim_date[month]` |
| `fact_sales[customer_id]` | `dim_customer[customer_id]` |
| `fact_sales[segment_id]` | `dim_segment[segment_id]` |
| `fact_sales[plant_id]` | `dim_plant[plant_id]` |
| `fact_plant_cost[month]` | `dim_date[month]` |
| `fact_plant_cost[plant_id]` | `dim_plant[plant_id]` |
| `fact_energy_week[plant_id]` | `dim_plant[plant_id]` |
| `fact_energy_week[month]` | `dim_date[month]` |
| `customer_profit[customer_id]` | `dim_customer[customer_id]` |
| `energy_weekly[plant_id]` | `dim_plant[plant_id]` |

Leave `fact_fx` unrelated. The calculated columns look it up with `LOOKUPVALUE`.

## 3. Calculated columns and measures

1. Open `measures.dax`.
2. Add the calculated columns first, on the tables named in the comments.
3. Create an empty table called `_Measures` (**Enter data**), then add every measure to it.
4. Format the measures:
   - EUR measures: currency, 1 decimal, display units in millions
   - `%` measures: percentage

**Check against the Python and SQL results.** These are the numbers Power BI must match:

| Check | Expected value |
|---|---|
| `EBITDA` for 2024 | 65.61 m |
| `EBITDA` for 2025 | 48.00 m |
| `EBITDA Margin %` | 13.0% → 9.3% |
| `Price Effect CC` | −4.55 m |
| `Cost to Serve Effect CC` | −1.63 m |
| `Fibre Effect` | −7.83 m |
| `Fixed Cost Effect CC` | −1.62 m |

If a number is off, check the calculated columns and the relationship directions first.

## 4. Report pages

### Page 1: Executive summary

- **Cards:** Net Sales, EBITDA, EBITDA Margin %, EBITDA Change
- **Line chart:** EBITDA Margin % by `dim_date[month]`
- **Slicers:** `dim_date[year]`, `dim_plant[plant_name]`

### Page 2: EBITDA bridge

- **Waterfall chart:** Category = `bridge[driver]` (sort by `bridge[order]`), Values = `bridge[value_eur_m]`
- **Clustered bar:** Price per t by `dim_customer[contract_type]`, with year in the legend

### Page 3: Customer profitability

- **Scatter chart:** X = `customer_profit[avg_order_t]` (log scale), Y = `customer_profit[margin]`, Legend = `tier`, Details = `customer_id`
- **Line chart (whale curve):** X = `customer_id` sorted by EBITDA descending, Y = `Cumulative EBITDA % (whale curve)`
- **Table:** tier, customers, Cost to Serve per t, Customer EBITDA, Loss-making Customers

### Page 4: Energy

- **Line chart:** X = `energy_weekly[week_start]`, Y = `intensity` and `baseline`, with a plant slicer
- **Conditional formatting:** red where `dev_4w` > 0.06
- **Card:** Weeks in Alert

### Page 5: Initiatives

- **Scatter chart:** X = `initiatives[effort]`, Y = `initiatives[value]`, Details = `name`
- **Table:** name, lever, value, confidence, time_to_value, kpi

## 5. Publish the screenshots

1. Export each page (**File → Export → PDF**, or screenshot each page).
2. Save the images as `docs/img/pbi_page1.png` and so on, then push them to GitHub.
3. Reference them in the README under "Power BI report".

This gives the hiring manager visible proof of Power BI work alongside the interactive page.
