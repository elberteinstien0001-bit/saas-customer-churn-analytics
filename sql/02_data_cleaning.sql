-- Deduplicate transactions
DELETE FROM transactions
WHERE transaction_id NOT IN (
    SELECT MIN(transaction_id)
    FROM transactions
    GROUP BY customer_id, transaction_date, amount, payment_method
);

-- Remove orphan records
DELETE FROM transactions
WHERE customer_id NOT IN (SELECT customer_id FROM customers);

DELETE FROM subscriptions
WHERE customer_id NOT IN (SELECT customer_id FROM customers);

-- Remove invalid transaction amounts
DELETE FROM transactions
WHERE amount IS NULL OR amount <= 0;

-- Clean categorical text fields
UPDATE customers
SET region = TRIM(region),
    acquisition_channel = TRIM(acquisition_channel);

UPDATE subscriptions
SET plan_type = TRIM(plan_type),
    status = TRIM(status);

-- Clear end dates for active subscriptions
UPDATE subscriptions
SET end_date = NULL
WHERE status = 'Active' AND end_date IS NOT NULL;

-- Remove invalid subscription date ranges
DELETE FROM subscriptions
WHERE end_date IS NOT NULL AND end_date < start_date;

-- Row count verification
SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL
SELECT 'subscriptions', COUNT(*) FROM subscriptions
UNION ALL
SELECT 'transactions', COUNT(*) FROM transactions;