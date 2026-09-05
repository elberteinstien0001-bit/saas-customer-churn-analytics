
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS subscriptions;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id         INTEGER PRIMARY KEY,
    signup_date         DATE,
    region              TEXT,
    acquisition_channel TEXT
);

CREATE TABLE subscriptions (
    subscription_id INTEGER PRIMARY KEY,
    customer_id     INTEGER,
    plan_type       TEXT,
    monthly_price   REAL,
    start_date      DATE,
    end_date        DATE,
    status          TEXT, -- Active, Cancelled
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE transactions (
    transaction_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id      INTEGER,
    transaction_date DATE,
    amount           REAL,
    payment_method   TEXT, -- Credit Card, PayPal, Bank Transfer
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_customer ON subscriptions(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_customer  ON transactions(customer_id);