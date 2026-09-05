WITH customer_transactions AS (
    SELECT
        customer_id,
        COUNT(transaction_id) AS frequency,
        SUM(amount)           AS monetary_value,
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
        s.end_date   AS sub_end_date,
        COALESCE(t.frequency, 0)      AS frequency,
        COALESCE(t.monetary_value, 0) AS total_revenue,
        t.last_transaction_date,
        CAST(JULIANDAY('2026-08-01') - JULIANDAY(t.last_transaction_date) AS INTEGER) AS recency_days,
        CAST(JULIANDAY(COALESCE(s.end_date, '2026-08-01')) - JULIANDAY(s.start_date) AS INTEGER) AS tenure_days,
        CASE WHEN s.status = 'Cancelled' THEN 1 ELSE 0 END AS is_churned
    FROM customers c
    JOIN subscriptions s ON c.customer_id = s.customer_id
    LEFT JOIN customer_transactions t ON c.customer_id = t.customer_id
),
ranked_metrics AS (
    SELECT
        *,
        AVG(total_revenue) OVER (PARTITION BY region) AS avg_region_revenue,
        ROW_NUMBER() OVER (PARTITION BY region ORDER BY total_revenue DESC) AS region_spend_rank
    FROM customer_metrics
)
SELECT * FROM ranked_metrics;


-- Validation queries

-- Overall churn rate
SELECT
    ROUND(100.0 * SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) / COUNT(*), 2) AS churn_rate_pct
FROM subscriptions;

-- LTV and churn by plan
SELECT
    s.plan_type,
    COUNT(DISTINCT s.customer_id) AS customers,
    ROUND(AVG(rev.total_revenue), 2) AS avg_ltv,
    ROUND(100.0 * SUM(CASE WHEN s.status = 'Cancelled' THEN 1 ELSE 0 END) / COUNT(DISTINCT s.customer_id), 2) AS churn_rate_pct
FROM subscriptions s
LEFT JOIN (
    SELECT customer_id, SUM(amount) AS total_revenue
    FROM transactions
    GROUP BY customer_id
) rev ON rev.customer_id = s.customer_id
GROUP BY s.plan_type
ORDER BY avg_ltv DESC;

-- Revenue and churn by region
SELECT
    c.region,
    ROUND(SUM(rev.total_revenue), 2) AS total_revenue,
    ROUND(100.0 * SUM(CASE WHEN s.status = 'Cancelled' THEN 1 ELSE 0 END) / COUNT(DISTINCT c.customer_id), 2) AS churn_rate_pct
FROM customers c
JOIN subscriptions s ON s.customer_id = c.customer_id
LEFT JOIN (
    SELECT customer_id, SUM(amount) AS total_revenue
    FROM transactions
    GROUP BY customer_id
) rev ON rev.customer_id = c.customer_id
GROUP BY c.region
ORDER BY total_revenue DESC;