# DAX Measures — SaaS Customer Health & Churn Risk Dashboard

This file documents the measures used by `SaaS_Customer_Health.pbix`
(source table: `final_customer_analytics`, produced by
`python/churn_prediction_model.ipynb`).

> **Note:** Power BI stores compiled measure definitions inside the binary
> data model (VertiPaq), not as plain text inside the `.pbix` file, so they
> can't be extracted with a text/zip tool. The four measures below were
> confirmed to exist in the report (via the visuals' field references) and
> are reconstructed here in standard DAX to match the dashboard's output —
> open the report in Power BI Desktop → **Model view** → select each
> measure to copy the exact formula, and paste it in here to replace this
> reconstruction with the authoritative version.

## Core measures

```DAX
Total Customers =
DISTINCTCOUNT ( final_customer_analytics[customer_id] )
```

```DAX
Total Revenue =
SUM ( final_customer_analytics[total_revenue] )
```

```DAX
Churn Rate =
DIVIDE (
    CALCULATE (
        DISTINCTCOUNT ( final_customer_analytics[customer_id] ),
        final_customer_analytics[is_churned] = 1
    ),
    [Total Customers]
)
```

```DAX
Avg LTV =
DIVIDE ( [Total Revenue], [Total Customers] )
```

## Supporting measure used in the Customer Action Table

```DAX
Average of Churn_Probability =
AVERAGE ( final_customer_analytics[Churn_Probability] )
```

## Fields used across the report

| Field | Role |
|---|---|
| `region`, `acquisition_channel`, `plan_type` | Slicers |
| `Customer_Segment` | K-Means segment label (Low-Value/At-Risk, Mid-Value/Moderate, High-Value/Loyal, VIP/High Spender) |
| `Risk_Category` | Churn-probability tier (Low / Medium / High Risk) |
| `sub_start_date` (Date Hierarchy: Year → Quarter → Month → Day) | Time axis for the Revenue & Churn Rate combo chart |
| `Churn_Probability` | Random Forest predicted probability, 0–1 |

## Report pages

1. **SaaS Customer Health & Churn Risk Analysis** — KPI cards (Total Revenue,
   Total Customers, Churn Rate, Avg LTV), customer count by segment/risk,
   churn rate by segment, revenue by plan, and revenue/churn trend over time.
2. **Risk Analysis** — same visuals filtered/pinned around the
   Customer Action Table, used to drill into the highest-risk accounts
   (currently `Basic` plan, `Low-Value / At-Risk` segment, 100% predicted
   churn probability).
