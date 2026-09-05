import sqlite3
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)
num_customers = 1000

conn = sqlite3.connect('data/churn_analytics.db')
cursor = conn.cursor()

cursor.executescript('''
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS subscriptions;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    signup_date DATE,
    region TEXT,
    acquisition_channel TEXT
);

CREATE TABLE subscriptions (
    subscription_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    plan_type TEXT,
    monthly_price REAL,
    start_date DATE,
    end_date DATE,
    status TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    transaction_date DATE,
    amount REAL,
    payment_method TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
);
''')

regions = ['North America', 'Europe', 'Asia-Pacific', 'Latin America']
channels = ['Organic Search', 'Paid Ads', 'Referral', 'Social Media']

start_signup = datetime(2024, 1, 1)
customers = []

for cid in range(101, 101 + num_customers):
    signup_dt = start_signup + timedelta(days=int(np.random.randint(0, 500)))
    reg = np.random.choice(regions, p=[0.4, 0.3, 0.2, 0.1])
    chan = np.random.choice(channels, p=[0.3, 0.35, 0.15, 0.2])
    customers.append((cid, signup_dt.strftime('%Y-%m-%d'), reg, chan))

cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", customers)

plans = {'Basic': 15.0, 'Standard': 35.0, 'Premium': 75.0}
pm_list = ['Credit Card', 'PayPal', 'Bank Transfer']

subscriptions = []
transactions = []
sub_id = 5001

for cid, s_date_str, _, _ in customers:
    s_date = datetime.strptime(s_date_str, '%Y-%m-%d')
    p_type = np.random.choice(list(plans.keys()), p=[0.5, 0.35, 0.15])
    m_price = plans[p_type]
    
    is_churned = np.random.choice([True, False], p=[0.3, 0.7])
    if is_churned:
        e_date = s_date + timedelta(days=int(np.random.randint(30, 365)))
        status = 'Cancelled'
        e_date_str = e_date.strftime('%Y-%m-%d')
    else:
        e_date = datetime(2026, 8, 1)
        status = 'Active'
        e_date_str = None

    subscriptions.append((sub_id, cid, p_type, m_price, s_date_str, e_date_str, status))
    sub_id += 1

    curr_dt = s_date
    while curr_dt <= e_date and curr_dt <= datetime(2026, 8, 1):
        pm = np.random.choice(pm_list)
        transactions.append((cid, curr_dt.strftime('%Y-%m-%d'), m_price, pm))
        curr_dt += timedelta(days=30)

cursor.executemany(
    "INSERT INTO subscriptions VALUES (?, ?, ?, ?, ?, ?, ?)", subscriptions
)
cursor.executemany(
    "INSERT INTO transactions (customer_id, transaction_date, amount, payment_method) VALUES (?, ?, ?, ?)", 
    transactions
)

conn.commit()
conn.close()