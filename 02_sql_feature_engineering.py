import sqlite3
import pandas as pd

conn = sqlite3.connect('data/churn_analytics.db')

query = """
WITH customer_tx AS (
    SELECT 
        customer_id,
        COUNT(transaction_id) AS frequency,
        SUM(amount) AS monetary_value,
        MAX(transaction_date) AS last_transaction_date,
        MIN(transaction_date) AS first_transaction_date
    FROM transactions
    GROUP BY customer_id
),
customer_metrics AS (
    SELECT 
        c.customer_id,
        c.signup_date,
        c.region,
        c.acquisition_channel,
        s.plan_type,
        s.monthly_price,
        s.status AS subscription_status,
        s.start_date AS sub_start_date,
        s.end_date AS sub_end_date,
        COALESCE(t.frequency, 0) AS frequency,
        COALESCE(t.monetary_value, 0) AS total_revenue,
        t.last_transaction_date,
        CAST(JULIANDAY('2026-08-01') - JULIANDAY(t.last_transaction_date) AS INTEGER) AS recency_days,
        CAST(JULIANDAY(COALESCE(s.end_date, '2026-08-01')) - JULIANDAY(s.start_date) AS INTEGER) AS tenure_days,
        CASE WHEN s.status = 'Cancelled' THEN 1 ELSE 0 END AS is_churned
    FROM customers c
    JOIN subscriptions s ON c.customer_id = s.customer_id
    LEFT JOIN customer_tx t ON c.customer_id = t.customer_id
),
ranked_metrics AS (
    SELECT 
        *,
        AVG(total_revenue) OVER(PARTITION BY region) AS avg_region_revenue,
        ROW_NUMBER() OVER(PARTITION BY region ORDER BY total_revenue DESC) AS region_spend_rank
    FROM customer_metrics
)
SELECT * FROM ranked_metrics;
"""

df = pd.read_sql_query(query, conn)
df.to_csv('data/customer_rfm_churn_data.csv', index=False)
conn.close()

print(f"Exported {len(df)} rows to customer_rfm_churn_data.csv")