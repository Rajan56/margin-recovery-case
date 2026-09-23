-- 01_schema.sql
-- Star schema for the Northfold Packaging case (fictional company, synthetic data).
-- One integrated model replaces five separate sources:
--   ERP sales ledger  -> fact_sales
--   ERP cost ledger   -> fact_plant_cost
--   Energy meters     -> fact_energy_week
--   Treasury FX       -> fact_fx
--   CRM / master data -> dim_customer, dim_segment, dim_plant
-- Written for SQLite; runs on SQL Server or PostgreSQL with type-name changes only.

CREATE TABLE dim_plant (
    plant_id              TEXT PRIMARY KEY,
    plant_name            TEXT NOT NULL,
    country               TEXT NOT NULL,
    currency              TEXT NOT NULL,          -- EUR or SEK
    base_mwh_per_t        REAL,
    board_usage_t_per_t   REAL
);

CREATE TABLE dim_segment (
    segment_id            TEXT PRIMARY KEY,
    segment_name          TEXT NOT NULL,
    list_price_eur_t      REAL,
    other_var_eur_t       REAL                    -- standard inks, starch, glue per tonne
);

CREATE TABLE dim_customer (
    customer_id           TEXT PRIMARY KEY,
    customer_name         TEXT NOT NULL,
    tier                  TEXT NOT NULL,          -- Key / Mid / Small
    contract_type         TEXT NOT NULL,          -- Fixed annual / Indexed / List price
    plant_id              TEXT REFERENCES dim_plant(plant_id),
    segment_id            TEXT REFERENCES dim_segment(segment_id),
    annual_volume_2024_t  REAL,
    price_premium         REAL,
    t_per_delivery        REAL,
    t_per_order           REAL,
    print_complexity      REAL
);

CREATE TABLE dim_date (
    month                 TEXT PRIMARY KEY,       -- 'YYYY-MM'
    year                  INTEGER,
    quarter               TEXT,
    month_no              INTEGER,
    month_start           TEXT
);

CREATE TABLE fact_fx (
    month                 TEXT PRIMARY KEY REFERENCES dim_date(month),
    sek_per_eur           REAL NOT NULL
);

CREATE TABLE fact_sales (
    month                 TEXT REFERENCES dim_date(month),
    customer_id           TEXT REFERENCES dim_customer(customer_id),
    segment_id            TEXT REFERENCES dim_segment(segment_id),
    plant_id              TEXT REFERENCES dim_plant(plant_id),
    currency              TEXT,
    volume_t              REAL,
    net_sales_local       REAL,
    net_sales_eur         REAL,
    orders                INTEGER,
    deliveries            INTEGER,
    freight_local         REAL,
    freight_eur           REAL,
    order_handling_local  REAL,                   -- changeovers, set-up waste, planning
    order_handling_eur    REAL,
    PRIMARY KEY (month, customer_id)
);

CREATE TABLE fact_plant_cost (
    month                 TEXT REFERENCES dim_date(month),
    plant_id              TEXT REFERENCES dim_plant(plant_id),
    currency              TEXT,
    board_consumed_t      REAL,
    fibre_cost_eur        REAL,
    energy_mwh            REAL,
    energy_cost_local     REAL,
    energy_cost_eur       REAL,
    other_variable_eur    REAL,
    fixed_cost_local      REAL,
    fixed_cost_eur        REAL,
    PRIMARY KEY (month, plant_id)
);

CREATE TABLE fact_energy_week (
    week_start            TEXT,                   -- Monday, 'YYYY-MM-DD'
    month                 TEXT REFERENCES dim_date(month),
    plant_id              TEXT REFERENCES dim_plant(plant_id),
    production_t          REAL,
    energy_mwh            REAL,
    PRIMARY KEY (week_start, plant_id)
);
